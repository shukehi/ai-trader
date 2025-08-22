#!/usr/bin/env python3
"""
订单管理系统 - 高级订单管理和自动化交易逻辑
支持复杂订单类型、条件订单和自动止盈止损
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

from .simulated_exchange import SimulatedExchange, OrderType, OrderSide, OrderStatus, Order

logger = logging.getLogger(__name__)

@dataclass
class ConditionalOrder:
    """条件订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    condition_type: str  # "stop_loss", "take_profit", "trailing_stop"
    trigger_price: float
    condition_params: Dict[str, Any]
    parent_order_id: Optional[str] = None
    created_at: float = 0.0
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

@dataclass
class OrderGroup:
    """订单组(如：一键开仓+止盈+止损)"""
    group_id: str
    parent_order_id: str
    child_orders: List[str]  # 子订单ID列表
    group_type: str  # "bracket", "oco" (One-Cancels-Other)
    is_active: bool = True
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

class OrderManager:
    """
    高级订单管理系统
    
    功能特性:
    - 条件订单(止损、止盈、追踪止损)
    - 订单组管理(括号订单、OCO订单)
    - 自动订单管理
    - 订单统计和分析
    """
    
    def __init__(self, exchange: SimulatedExchange):
        """
        初始化订单管理器
        
        Args:
            exchange: 模拟交易所实例
        """
        self.exchange = exchange
        
        # 条件订单
        self.conditional_orders: Dict[str, ConditionalOrder] = {}
        self.order_groups: Dict[str, OrderGroup] = {}
        
        # 订单历史和统计
        self.order_history: List[Dict[str, Any]] = []
        self.execution_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'cancelled_orders': 0,
            'avg_execution_time': 0.0
        }
        
        # 自动管理线程
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.order_callbacks: Dict[str, Callable] = {}
        
        logger.info("订单管理器初始化完成")
    
    def start_monitoring(self) -> None:
        """启动订单监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_orders, daemon=True)
        self._monitor_thread.start()
        logger.info("订单监控已启动")
    
    def stop_monitoring(self) -> None:
        """停止订单监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("订单监控已停止")
    
    def place_market_order(self, symbol: str, side: OrderSide, quantity: float,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        下市价单(支持自动止盈止损)
        
        Args:
            symbol: 交易对
            side: 买卖方向
            quantity: 数量
            stop_loss: 止损价格
            take_profit: 止盈价格
            
        Returns:
            订单结果
        """
        try:
            start_time = time.time()
            
            # 下主订单
            main_order = self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity
            )
            
            execution_time = time.time() - start_time
            
            if not main_order['success']:
                self._update_stats('failed')
                return main_order
            
            order_id = main_order['order_id']
            
            # 如果订单成功且设置了止盈止损，创建条件订单
            if main_order['success'] and (stop_loss or take_profit):
                group_id = f"bracket_{order_id}"
                child_orders = []
                
                # 创建止损单
                if stop_loss:
                    stop_order_id = self._create_stop_loss_order(
                        symbol, side, quantity, stop_loss, order_id
                    )
                    if stop_order_id:
                        child_orders.append(stop_order_id)
                
                # 创建止盈单
                if take_profit:
                    profit_order_id = self._create_take_profit_order(
                        symbol, side, quantity, take_profit, order_id
                    )
                    if profit_order_id:
                        child_orders.append(profit_order_id)
                
                # 创建订单组
                if child_orders:
                    self.order_groups[group_id] = OrderGroup(
                        group_id=group_id,
                        parent_order_id=order_id,
                        child_orders=child_orders,
                        group_type="bracket"
                    )
            
            self._update_stats('successful', execution_time)
            self._record_order_history(main_order, execution_time)
            
            return main_order
            
        except Exception as e:
            logger.error(f"下市价单失败: {e}")
            self._update_stats('failed')
            return {'success': False, 'error': str(e)}
    
    def place_limit_order(self, symbol: str, side: OrderSide, quantity: float,
                         price: float, time_in_force: str = "GTC") -> Dict[str, Any]:
        """
        下限价单
        
        Args:
            symbol: 交易对
            side: 买卖方向
            quantity: 数量
            price: 限价
            time_in_force: 订单有效期 (GTC, IOC, FOK)
            
        Returns:
            订单结果
        """
        try:
            start_time = time.time()
            
            result = self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=price
            )
            
            execution_time = time.time() - start_time
            
            if result['success']:
                self._update_stats('successful', execution_time)
            else:
                self._update_stats('failed')
            
            self._record_order_history(result, execution_time)
            
            return result
            
        except Exception as e:
            logger.error(f"下限价单失败: {e}")
            self._update_stats('failed')
            return {'success': False, 'error': str(e)}
    
    def place_trailing_stop(self, symbol: str, side: OrderSide, quantity: float,
                           trail_amount: float, trail_percent: Optional[float] = None) -> str:
        """
        创建追踪止损单
        
        Args:
            symbol: 交易对
            side: 买卖方向
            quantity: 数量
            trail_amount: 追踪距离(绝对值)
            trail_percent: 追踪距离(百分比)
            
        Returns:
            条件订单ID
        """
        try:
            current_price = self.exchange.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"无法获取{symbol}当前价格")
            
            # 计算初始触发价格
            if side == OrderSide.SELL:  # 多头止损
                trigger_price = current_price - trail_amount
            else:  # 空头止损
                trigger_price = current_price + trail_amount
            
            order_id = f"trail_{int(time.time() * 1000)}"
            
            conditional_order = ConditionalOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=None,
                condition_type="trailing_stop",
                trigger_price=trigger_price,
                condition_params={
                    'trail_amount': trail_amount,
                    'trail_percent': trail_percent,
                    'best_price': current_price
                }
            )
            
            self.conditional_orders[order_id] = conditional_order
            
            logger.info(f"创建追踪止损单: {order_id} - {side.value} {quantity} {symbol} @ {trigger_price:.2f}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"创建追踪止损单失败: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """取消订单(包括条件订单)"""
        try:
            # 尝试取消交易所订单
            result = self.exchange.cancel_order(order_id)
            
            if result['success']:
                self._update_stats('cancelled')
            
            # 取消条件订单
            if order_id in self.conditional_orders:
                self.conditional_orders[order_id].is_active = False
                result = {'success': True, 'message': '条件订单已取消'}
            
            # 取消订单组中的所有订单
            for group in self.order_groups.values():
                if order_id == group.parent_order_id:
                    for child_id in group.child_orders:
                        self.cancel_order(child_id)
                    group.is_active = False
                elif order_id in group.child_orders:
                    # 如果是OCO订单，取消其他子订单
                    if group.group_type == "oco":
                        for child_id in group.child_orders:
                            if child_id != order_id:
                                self.cancel_order(child_id)
            
            return result
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_orders(self) -> Dict[str, Any]:
        """获取所有活跃订单"""
        # 交易所订单
        exchange_orders = self.exchange.get_orders(OrderStatus.PENDING)
        
        # 条件订单
        conditional_orders = [
            {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'type': 'conditional',
                'condition_type': order.condition_type,
                'quantity': order.quantity,
                'trigger_price': order.trigger_price,
                'status': 'active' if order.is_active else 'inactive'
            }
            for order in self.conditional_orders.values() if order.is_active
        ]
        
        # 订单组
        active_groups = [
            {
                'group_id': group.group_id,
                'type': group.group_type,
                'parent_order': group.parent_order_id,
                'child_orders': group.child_orders,
                'status': 'active' if group.is_active else 'inactive'
            }
            for group in self.order_groups.values() if group.is_active
        ]
        
        return {
            'exchange_orders': exchange_orders,
            'conditional_orders': conditional_orders,
            'order_groups': active_groups
        }
    
    def get_order_stats(self) -> Dict[str, Any]:
        """获取订单统计信息"""
        return {
            'execution_stats': self.execution_stats.copy(),
            'conditional_orders_count': len([o for o in self.conditional_orders.values() if o.is_active]),
            'order_groups_count': len([g for g in self.order_groups.values() if g.is_active]),
            'total_history_records': len(self.order_history)
        }
    
    def _create_stop_loss_order(self, symbol: str, side: OrderSide, quantity: float,
                               stop_price: float, parent_id: str) -> Optional[str]:
        """创建止损订单"""
        try:
            # 止损方向与开仓方向相反
            stop_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            
            order_id = f"sl_{parent_id}"
            
            conditional_order = ConditionalOrder(
                order_id=order_id,
                symbol=symbol,
                side=stop_side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=None,
                condition_type="stop_loss",
                trigger_price=stop_price,
                condition_params={},
                parent_order_id=parent_id
            )
            
            self.conditional_orders[order_id] = conditional_order
            
            return order_id
            
        except Exception as e:
            logger.error(f"创建止损单失败: {e}")
            return None
    
    def _create_take_profit_order(self, symbol: str, side: OrderSide, quantity: float,
                                 profit_price: float, parent_id: str) -> Optional[str]:
        """创建止盈订单"""
        try:
            # 止盈方向与开仓方向相反
            profit_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            
            order_id = f"tp_{parent_id}"
            
            conditional_order = ConditionalOrder(
                order_id=order_id,
                symbol=symbol,
                side=profit_side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=None,
                condition_type="take_profit",
                trigger_price=profit_price,
                condition_params={},
                parent_order_id=parent_id
            )
            
            self.conditional_orders[order_id] = conditional_order
            
            return order_id
            
        except Exception as e:
            logger.error(f"创建止盈单失败: {e}")
            return None
    
    def _monitor_orders(self) -> None:
        """订单监控主循环"""
        while self._monitoring:
            try:
                self._check_conditional_orders()
                time.sleep(0.1)  # 100ms检查间隔
            except Exception as e:
                logger.error(f"订单监控错误: {e}")
                time.sleep(1.0)
    
    def _check_conditional_orders(self) -> None:
        """检查条件订单触发条件"""
        for order_id, order in list(self.conditional_orders.items()):
            if not order.is_active:
                continue
            
            current_price = self.exchange.get_current_price(order.symbol)
            if not current_price:
                continue
            
            triggered = False
            
            if order.condition_type == "stop_loss":
                # 止损触发逻辑
                if order.side == OrderSide.SELL:  # 多头止损
                    triggered = current_price <= order.trigger_price
                else:  # 空头止损
                    triggered = current_price >= order.trigger_price
            
            elif order.condition_type == "take_profit":
                # 止盈触发逻辑
                if order.side == OrderSide.SELL:  # 多头止盈
                    triggered = current_price >= order.trigger_price
                else:  # 空头止盈
                    triggered = current_price <= order.trigger_price
            
            elif order.condition_type == "trailing_stop":
                # 追踪止损逻辑
                triggered = self._check_trailing_stop(order, current_price)
            
            if triggered:
                self._execute_conditional_order(order)
    
    def _check_trailing_stop(self, order: ConditionalOrder, current_price: float) -> bool:
        """检查追踪止损触发"""
        params = order.condition_params
        trail_amount = params['trail_amount']
        best_price = params['best_price']
        
        if order.side == OrderSide.SELL:  # 多头追踪止损
            if current_price > best_price:
                # 价格创新高，更新最佳价格和触发价格
                params['best_price'] = current_price
                order.trigger_price = current_price - trail_amount
                return False
            else:
                # 检查是否触发
                return current_price <= order.trigger_price
        else:  # 空头追踪止损
            if current_price < best_price:
                # 价格创新低，更新最佳价格和触发价格
                params['best_price'] = current_price
                order.trigger_price = current_price + trail_amount
                return False
            else:
                # 检查是否触发
                return current_price >= order.trigger_price
    
    def _execute_conditional_order(self, order: ConditionalOrder) -> None:
        """执行条件订单"""
        try:
            logger.info(f"触发条件订单: {order.order_id} - {order.condition_type}")
            
            # 执行订单
            result = self.exchange.place_order(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price
            )
            
            # 标记为非活跃
            order.is_active = False
            
            if result['success']:
                logger.info(f"条件订单执行成功: {order.order_id}")
                
                # 如果是订单组中的订单，处理相关逻辑
                for group in self.order_groups.values():
                    if order.order_id in group.child_orders and group.group_type == "oco":
                        # OCO订单，取消其他子订单
                        for child_id in group.child_orders:
                            if child_id != order.order_id:
                                self.cancel_order(child_id)
                        group.is_active = False
                        break
            else:
                logger.error(f"条件订单执行失败: {order.order_id} - {result.get('error')}")
            
        except Exception as e:
            logger.error(f"执行条件订单失败: {e}")
            order.is_active = False
    
    def _update_stats(self, result_type: str, execution_time: float = 0.0) -> None:
        """更新订单统计"""
        self.execution_stats['total_orders'] += 1
        
        if result_type == 'successful':
            self.execution_stats['successful_orders'] += 1
        elif result_type == 'failed':
            self.execution_stats['failed_orders'] += 1
        elif result_type == 'cancelled':
            self.execution_stats['cancelled_orders'] += 1
        
        if execution_time > 0:
            # 更新平均执行时间
            current_avg = self.execution_stats['avg_execution_time']
            successful_count = self.execution_stats['successful_orders']
            self.execution_stats['avg_execution_time'] = (
                (current_avg * (successful_count - 1) + execution_time) / successful_count
            )
    
    def _record_order_history(self, order_result: Dict[str, Any], execution_time: float) -> None:
        """记录订单历史"""
        history_record = {
            'timestamp': time.time(),
            'order_result': order_result,
            'execution_time': execution_time
        }
        
        self.order_history.append(history_record)
        
        # 保持历史记录数量在合理范围内
        if len(self.order_history) > 1000:
            self.order_history = self.order_history[-500:]