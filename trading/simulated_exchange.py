#!/usr/bin/env python3
"""
模拟交易所 - 提供完整的永续合约模拟交易环境
基于实时Binance数据进行模拟执行，支持杠杆交易和保证金管理
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit" 
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL_FILLED = "partial_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"

@dataclass
class Order:
    """订单数据结构"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    timestamp: float = 0.0
    fill_timestamp: Optional[float] = None
    fees: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return asdict(self)
    
    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_complete(self) -> bool:
        """订单是否完全成交"""
        return self.filled_quantity >= self.quantity

@dataclass
class Position:
    """持仓数据结构"""
    symbol: str
    side: str  # "long" or "short"
    size: float
    avg_entry_price: float
    leverage: float
    margin_used: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return asdict(self)

class SimulatedExchange:
    """
    模拟永续合约交易所
    
    功能特性:
    - 基于实时价格的订单执行
    - 杠杆交易和保证金管理
    - 滑点和手续费计算
    - 强制平仓机制
    """
    
    def __init__(self, initial_balance: float = 10000.0, 
                 default_leverage: float = 10.0,
                 maker_fee: float = 0.0002,
                 taker_fee: float = 0.0004,
                 slippage_factor: float = 0.0001):
        """
        初始化模拟交易所
        
        Args:
            initial_balance: 初始资金(USDT)
            default_leverage: 默认杠杆倍数
            maker_fee: Maker手续费率
            taker_fee: Taker手续费率  
            slippage_factor: 滑点因子
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.default_leverage = default_leverage
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_factor = slippage_factor
        
        # 订单和持仓
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}  # key: symbol
        
        # 交易统计
        self.total_trades = 0
        self.total_fees = 0.0
        self.total_pnl = 0.0
        
        # 当前市场价格(由外部更新)
        self.current_prices: Dict[str, float] = {}
        
        logger.info(f"模拟交易所初始化完成 - 初始资金: ${initial_balance:.2f}, 杠杆: {default_leverage}x")
    
    def update_market_price(self, symbol: str, price: float) -> None:
        """更新市场价格"""
        self.current_prices[symbol] = price
        # 更新持仓的未实现盈亏
        if symbol in self.positions:
            self._update_position_pnl(symbol)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        return self.current_prices.get(symbol)
    
    def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                   quantity: float, price: Optional[float] = None,
                   stop_price: Optional[float] = None,
                   leverage: Optional[float] = None) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易对符号
            side: 买卖方向
            order_type: 订单类型
            quantity: 数量
            price: 价格(限价单必需)
            stop_price: 止损价格(止损单必需)
            leverage: 杠杆倍数
            
        Returns:
            订单信息字典
        """
        try:
            # 参数验证
            if quantity <= 0:
                raise ValueError("订单数量必须大于0")
            
            if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and price is None:
                raise ValueError("限价单必须指定价格")
                
            if order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT] and stop_price is None:
                raise ValueError("止损单必须指定止损价格")
            
            # 创建订单
            order_id = str(uuid.uuid4())[:8]
            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price
            )
            
            # 风险检查
            risk_check = self._check_order_risk(order, leverage or self.default_leverage)
            if not risk_check['success']:
                order.status = OrderStatus.REJECTED
                self.orders[order_id] = order
                return {
                    'success': False,
                    'order_id': order_id,
                    'error': risk_check['error'],
                    'order': order.to_dict()
                }
            
            # 立即尝试执行(市价单)或加入订单簿(限价单)
            if order_type == OrderType.MARKET:
                execution_result = self._execute_market_order(order, leverage or self.default_leverage)
                if execution_result['success']:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.avg_fill_price = execution_result['fill_price']
                    order.fees = execution_result['fees']
                    order.fill_timestamp = time.time()
                    self.total_trades += 1
                    self.total_fees += order.fees
                else:
                    order.status = OrderStatus.REJECTED
            
            self.orders[order_id] = order
            
            logger.info(f"订单已创建: {order_id} - {side.value} {quantity} {symbol} @ {price or 'MARKET'}")
            
            return {
                'success': order.status != OrderStatus.REJECTED,
                'order_id': order_id,
                'order': order.to_dict()
            }
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            if order_id not in self.orders:
                return {'success': False, 'error': '订单不存在'}
            
            order = self.orders[order_id]
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                return {'success': False, 'error': '订单无法取消'}
            
            order.status = OrderStatus.CANCELLED
            logger.info(f"订单已取消: {order_id}")
            
            return {'success': True, 'order': order.to_dict()}
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        # 计算总保证金和未实现盈亏
        total_margin = 0.0
        total_unrealized_pnl = 0.0
        
        for position in self.positions.values():
            total_margin += position.margin_used
            total_unrealized_pnl += position.unrealized_pnl
        
        # 可用余额 = 总余额 - 已用保证金 + 未实现盈亏
        available_balance = self.balance - total_margin + total_unrealized_pnl
        
        return {
            'total_balance': self.balance,
            'available_balance': available_balance,
            'margin_used': total_margin,
            'unrealized_pnl': total_unrealized_pnl,
            'total_pnl': self.total_pnl + total_unrealized_pnl,
            'total_trades': self.total_trades,
            'total_fees': self.total_fees,
            'positions_count': len(self.positions),
            'active_orders_count': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING])
        }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取所有持仓"""
        positions = []
        for position in self.positions.values():
            pos_dict = position.to_dict()
            # 添加当前市价
            current_price = self.get_current_price(position.symbol)
            if current_price:
                pos_dict['current_price'] = current_price
            positions.append(pos_dict)
        
        return positions
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """获取订单列表"""
        orders = []
        for order in self.orders.values():
            if status is None or order.status == status:
                orders.append(order.to_dict())
        
        return sorted(orders, key=lambda x: x['timestamp'], reverse=True)
    
    def _check_order_risk(self, order: Order, leverage: float) -> Dict[str, Any]:
        """风险检查"""
        try:
            current_price = self.get_current_price(order.symbol)
            if not current_price:
                return {'success': False, 'error': f'无法获取{order.symbol}价格'}
            
            # 估算订单价值
            estimated_price = order.price if order.price else current_price
            order_value = order.quantity * estimated_price
            required_margin = order_value / leverage
            
            # 检查保证金充足性
            account = self.get_account_info()
            if account['available_balance'] < required_margin:
                return {
                    'success': False, 
                    'error': f'保证金不足: 需要${required_margin:.2f}, 可用${account["available_balance"]:.2f}'
                }
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_market_order(self, order: Order, leverage: float) -> Dict[str, Any]:
        """执行市价单"""
        try:
            current_price = self.get_current_price(order.symbol)
            if not current_price:
                return {'success': False, 'error': f'无法获取{order.symbol}价格'}
            
            # 计算滑点
            slippage = current_price * self.slippage_factor
            if order.side == OrderSide.BUY:
                fill_price = current_price + slippage
            else:
                fill_price = current_price - slippage
            
            # 计算手续费(市价单使用taker费率)
            order_value = order.quantity * fill_price
            fees = order_value * self.taker_fee
            
            # 更新或创建持仓
            self._update_position(order.symbol, order.side, order.quantity, fill_price, leverage, fees)
            
            return {
                'success': True,
                'fill_price': fill_price,
                'fees': fees
            }
            
        except Exception as e:
            logger.error(f"执行市价单失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_position(self, symbol: str, side: OrderSide, quantity: float, 
                        price: float, leverage: float, fees: float) -> None:
        """更新持仓"""
        position_side = "long" if side == OrderSide.BUY else "short"
        
        if symbol not in self.positions:
            # 创建新持仓
            order_value = quantity * price
            margin_used = order_value / leverage
            
            self.positions[symbol] = Position(
                symbol=symbol,
                side=position_side,
                size=quantity,
                avg_entry_price=price,
                leverage=leverage,
                margin_used=margin_used
            )
            
            # 扣除保证金和手续费
            self.balance -= fees
            
        else:
            # 更新现有持仓
            position = self.positions[symbol]
            
            if position.side == position_side:
                # 同向加仓
                total_value = position.size * position.avg_entry_price + quantity * price
                total_size = position.size + quantity
                position.avg_entry_price = total_value / total_size
                position.size = total_size
                position.margin_used += (quantity * price) / leverage
            else:
                # 反向减仓或开反向仓
                if position.size > quantity:
                    # 部分平仓
                    close_ratio = quantity / position.size
                    realized_pnl = self._calculate_realized_pnl(position, quantity, price)
                    
                    position.size -= quantity
                    position.margin_used *= (1 - close_ratio)
                    position.realized_pnl += realized_pnl
                    self.balance += realized_pnl
                    
                elif position.size == quantity:
                    # 完全平仓
                    realized_pnl = self._calculate_realized_pnl(position, quantity, price)
                    self.balance += position.margin_used + realized_pnl
                    self.total_pnl += realized_pnl
                    del self.positions[symbol]
                    
                else:
                    # 平仓后反向开仓
                    close_pnl = self._calculate_realized_pnl(position, position.size, price)
                    remaining_qty = quantity - position.size
                    
                    # 清理旧持仓
                    self.balance += position.margin_used + close_pnl
                    self.total_pnl += close_pnl
                    
                    # 创建新持仓
                    order_value = remaining_qty * price
                    margin_used = order_value / leverage
                    
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        side=position_side,
                        size=remaining_qty,
                        avg_entry_price=price,
                        leverage=leverage,
                        margin_used=margin_used
                    )
            
            # 扣除手续费
            self.balance -= fees
    
    def _calculate_realized_pnl(self, position: Position, close_quantity: float, close_price: float) -> float:
        """计算已实现盈亏"""
        if position.side == "long":
            pnl_per_unit = close_price - position.avg_entry_price
        else:
            pnl_per_unit = position.avg_entry_price - close_price
        
        return pnl_per_unit * close_quantity
    
    def _update_position_pnl(self, symbol: str) -> None:
        """更新持仓的未实现盈亏"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        current_price = self.get_current_price(symbol)
        
        if current_price:
            if position.side == "long":
                pnl_per_unit = current_price - position.avg_entry_price
            else:
                pnl_per_unit = position.avg_entry_price - current_price
            
            position.unrealized_pnl = pnl_per_unit * position.size
    
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> Dict[str, Any]:
        """平仓"""
        try:
            if symbol not in self.positions:
                return {'success': False, 'error': '持仓不存在'}
            
            position = self.positions[symbol]
            close_qty = quantity if quantity else position.size
            
            if close_qty > position.size:
                return {'success': False, 'error': '平仓数量超过持仓'}
            
            # 确定平仓方向(与持仓方向相反)
            close_side = OrderSide.SELL if position.side == "long" else OrderSide.BUY
            
            # 执行市价平仓
            return self.place_order(
                symbol=symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=close_qty
            )
            
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_liquidation(self) -> List[str]:
        """检查强制平仓(保证金不足时触发)"""
        liquidated_positions = []
        
        for symbol, position in list(self.positions.items()):
            # 计算保证金比例
            current_price = self.get_current_price(symbol)
            if not current_price:
                continue
            
            # 计算当前价值和未实现盈亏
            if position.side == "long":
                unrealized_pnl = (current_price - position.avg_entry_price) * position.size
            else:
                unrealized_pnl = (position.avg_entry_price - current_price) * position.size
            
            # 计算保证金比例 = (保证金 + 未实现盈亏) / 仓位价值
            position_value = position.size * current_price
            margin_ratio = (position.margin_used + unrealized_pnl) / position_value
            
            # 如果保证金比例低于5%，触发强制平仓
            if margin_ratio < 0.05:
                logger.warning(f"触发强制平仓: {symbol} - 保证金比例: {margin_ratio:.2%}")
                self.close_position(symbol)
                liquidated_positions.append(symbol)
        
        return liquidated_positions