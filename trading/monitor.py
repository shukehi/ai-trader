#!/usr/bin/env python3
"""
实时监控面板 - 交易状态监控和性能展示
提供实时账户状态、持仓监控、风险警报和性能统计
"""

import os
import sys
import time
import json
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from .simulated_exchange import SimulatedExchange
from .order_manager import OrderManager
from .position_manager import PositionManager
from .trade_logger import TradeLogger
from .risk_manager import RiskManager
from .signal_executor import SignalExecutor

logger = logging.getLogger(__name__)

@dataclass
class MonitorStats:
    """监控统计数据"""
    timestamp: float
    account_balance: float
    available_balance: float
    unrealized_pnl: float
    total_pnl: float
    positions_count: int
    active_orders: int
    daily_trades: int
    win_rate: float
    risk_level: str
    emergency_stop: bool

class TradingMonitor:
    """
    交易监控器
    
    功能特性:
    - 实时账户状态监控
    - 持仓和订单跟踪
    - 风险警报监控
    - 性能统计展示
    - 历史数据记录
    """
    
    def __init__(self, exchange: SimulatedExchange, 
                 order_manager: Optional[OrderManager] = None,
                 position_manager: Optional[PositionManager] = None,
                 trade_logger: Optional[TradeLogger] = None,
                 risk_manager: Optional[RiskManager] = None,
                 signal_executor: Optional[SignalExecutor] = None):
        """
        初始化交易监控器
        
        Args:
            exchange: 模拟交易所(必需)
            order_manager: 订单管理器(可选)
            position_manager: 持仓管理器(可选)
            trade_logger: 交易日志器(可选)
            risk_manager: 风险管理器(可选)
            signal_executor: 信号执行器(可选)
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.trade_logger = trade_logger
        self.risk_manager = risk_manager
        self.signal_executor = signal_executor
        
        # 监控设置
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.refresh_interval = 1.0  # 秒
        
        # 历史统计数据
        self.stats_history: List[MonitorStats] = []
        self.max_history_length = 3600  # 保留1小时数据(1秒间隔)
        
        # 警报设置
        self.alert_thresholds = {
            'balance_drop_percent': 0.05,      # 余额下降5%触发警报
            'unrealized_loss_percent': 0.10,   # 未实现亏损10%触发警报
            'position_count_max': 8,           # 最大持仓数警报
            'risk_utilization_high': 0.85      # 风险利用率85%警报
        }
        
        # 当前状态
        self.current_stats: Optional[MonitorStats] = None
        self.alerts_triggered: List[Dict[str, Any]] = []
        
        logger.info("交易监控器初始化完成")
    
    def start_monitoring(self) -> bool:
        """启动监控"""
        try:
            if self.monitoring:
                logger.warning("监控已经在运行")
                return False
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("交易监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止监控"""
        try:
            if not self.monitoring:
                return True
            
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5.0)
            
            logger.info("交易监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            return False
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        try:
            dashboard = {
                'timestamp': time.time(),
                'system_status': self._get_system_status(),
                'account_summary': self._get_account_summary(),
                'positions_summary': self._get_positions_summary(),
                'orders_summary': self._get_orders_summary(),
                'risk_summary': self._get_risk_summary(),
                'performance_summary': self._get_performance_summary(),
                'recent_alerts': self._get_recent_alerts(),
                'market_data': self._get_market_data()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"获取仪表板数据失败: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def get_performance_chart_data(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能图表数据"""
        try:
            since_timestamp = time.time() - (hours * 3600)
            
            # 从历史数据获取
            chart_data = {
                'timestamps': [],
                'balance': [],
                'pnl': [],
                'positions_count': [],
                'win_rate': []
            }
            
            for stats in self.stats_history:
                if stats.timestamp >= since_timestamp:
                    chart_data['timestamps'].append(stats.timestamp)
                    chart_data['balance'].append(stats.account_balance)
                    chart_data['pnl'].append(stats.total_pnl)
                    chart_data['positions_count'].append(stats.positions_count)
                    chart_data['win_rate'].append(stats.win_rate)
            
            # 如果历史数据不足，添加当前数据点
            if not chart_data['timestamps']:
                current_stats = self._collect_stats()
                chart_data['timestamps'].append(current_stats.timestamp)
                chart_data['balance'].append(current_stats.account_balance)
                chart_data['pnl'].append(current_stats.total_pnl)
                chart_data['positions_count'].append(current_stats.positions_count)
                chart_data['win_rate'].append(current_stats.win_rate)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"获取性能图表数据失败: {e}")
            return {'error': str(e)}
    
    def print_status_summary(self) -> None:
        """打印状态摘要到控制台"""
        try:
            dashboard = self.get_dashboard_data()
            
            if 'error' in dashboard:
                print(f"❌ 获取状态失败: {dashboard['error']}")
                return
            
            print("\n" + "="*80)
            print("🎯 ETH永续合约AI交易助手 - 实时监控")
            print("="*80)
            
            # 系统状态
            system = dashboard['system_status']
            status_emoji = "🟢" if system['all_systems_ok'] else "🔴"
            print(f"{status_emoji} 系统状态: {'正常' if system['all_systems_ok'] else '异常'}")
            
            # 账户摘要
            account = dashboard['account_summary']
            balance_change = account['balance_change_24h']
            change_emoji = "📈" if balance_change >= 0 else "📉"
            
            print(f"💰 账户余额: ${account['total_balance']:.2f} {change_emoji} {balance_change:+.2f} (24h)")
            print(f"💳 可用余额: ${account['available_balance']:.2f}")
            print(f"📊 未实现盈亏: ${account['unrealized_pnl']:+.2f}")
            
            # 持仓和订单
            positions = dashboard['positions_summary']
            orders = dashboard['orders_summary']
            print(f"📍 持仓数量: {positions['total_positions']} | 活跃订单: {orders['active_orders']}")
            
            # 风险状况
            risk = dashboard['risk_summary']
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk['risk_level'], "❓")
            print(f"{risk_emoji} 风险等级: {risk['risk_level'].upper()} | 风险利用率: {risk['risk_utilization']:.1%}")
            
            # 性能统计
            perf = dashboard['performance_summary']
            win_rate_emoji = "🎯" if perf['win_rate'] > 0.6 else "📊"
            print(f"{win_rate_emoji} 胜率: {perf['win_rate']:.1%} | 今日交易: {perf['trades_today']}")
            
            # 最新警报
            alerts = dashboard['recent_alerts']
            if alerts:
                print(f"⚠️ 活跃警报: {len(alerts)}个")
                for alert in alerts[:3]:  # 显示最新3个
                    severity_emoji = {"warning": "🟡", "critical": "🔴", "emergency": "🚨"}.get(alert['severity'], "ℹ️")
                    print(f"  {severity_emoji} {alert['message']}")
            
            print("="*80)
            print(f"🕐 更新时间: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"打印状态摘要失败: {e}")
            print(f"❌ 状态显示错误: {e}")
    
    def export_monitoring_data(self, filepath: str) -> bool:
        """导出监控数据"""
        try:
            export_data = {
                'export_timestamp': time.time(),
                'export_time_iso': datetime.now(timezone.utc).isoformat(),
                'dashboard_data': self.get_dashboard_data(),
                'stats_history': [asdict(stats) for stats in self.stats_history],
                'alerts_history': self.alerts_triggered,
                'settings': {
                    'refresh_interval': self.refresh_interval,
                    'alert_thresholds': self.alert_thresholds,
                    'max_history_length': self.max_history_length
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"监控数据已导出到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"导出监控数据失败: {e}")
            return False
    
    def _monitoring_loop(self) -> None:
        """监控主循环"""
        logger.info("监控循环已启动")
        
        while self.monitoring:
            try:
                # 收集统计数据
                stats = self._collect_stats()
                self.current_stats = stats
                
                # 添加到历史记录
                self.stats_history.append(stats)
                
                # 限制历史记录长度
                if len(self.stats_history) > self.max_history_length:
                    self.stats_history = self.stats_history[-self.max_history_length:]
                
                # 检查警报条件
                self._check_alerts(stats)
                
                # 等待下次更新
                time.sleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(self.refresh_interval)
        
        logger.info("监控循环已结束")
    
    def _collect_stats(self) -> MonitorStats:
        """收集当前统计数据"""
        try:
            # 账户信息
            account = self.exchange.get_account_info()
            positions = self.exchange.get_positions()
            
            # 订单信息
            active_orders = 0
            if self.order_manager:
                orders = self.order_manager.get_active_orders()
                active_orders = len(orders.get('exchange_orders', []))
            
            # 交易统计
            daily_trades = 0
            win_rate = 0.0
            if self.trade_logger:
                today_performance = self.trade_logger.get_performance_summary(days=1)
                if 'total_trades' in today_performance:
                    daily_trades = today_performance['total_trades']
                    win_rate = today_performance.get('win_rate', 0.0)
            
            # 风险状态
            risk_level = "unknown"
            emergency_stop = False
            if self.risk_manager:
                risk_level = self.risk_manager.current_risk_level.value
                emergency_stop = self.risk_manager.emergency_stop_triggered
            
            return MonitorStats(
                timestamp=time.time(),
                account_balance=account['total_balance'],
                available_balance=account['available_balance'],
                unrealized_pnl=account['unrealized_pnl'],
                total_pnl=account['total_pnl'],
                positions_count=len(positions),
                active_orders=active_orders,
                daily_trades=daily_trades,
                win_rate=win_rate,
                risk_level=risk_level,
                emergency_stop=emergency_stop
            )
            
        except Exception as e:
            logger.error(f"收集统计数据失败: {e}")
            return MonitorStats(
                timestamp=time.time(),
                account_balance=0,
                available_balance=0,
                unrealized_pnl=0,
                total_pnl=0,
                positions_count=0,
                active_orders=0,
                daily_trades=0,
                win_rate=0,
                risk_level="error",
                emergency_stop=False
            )
    
    def _check_alerts(self, stats: MonitorStats) -> None:
        """检查警报条件"""
        try:
            current_time = time.time()
            
            # 余额下降警报
            if len(self.stats_history) > 100:  # 至少有历史数据
                historical_balance = self.stats_history[-100].account_balance
                balance_drop = (historical_balance - stats.account_balance) / historical_balance
                
                if balance_drop > self.alert_thresholds['balance_drop_percent']:
                    self._trigger_alert(
                        alert_type="balance_drop",
                        severity="warning",
                        message=f"账户余额下降 {balance_drop:.2%}",
                        current_value=stats.account_balance,
                        threshold=historical_balance
                    )
            
            # 未实现亏损警报
            if stats.unrealized_pnl < 0:
                loss_percent = abs(stats.unrealized_pnl) / stats.account_balance
                if loss_percent > self.alert_thresholds['unrealized_loss_percent']:
                    self._trigger_alert(
                        alert_type="unrealized_loss",
                        severity="critical",
                        message=f"未实现亏损达到 {loss_percent:.2%}",
                        current_value=stats.unrealized_pnl,
                        threshold=self.alert_thresholds['unrealized_loss_percent']
                    )
            
            # 持仓数量警报
            if stats.positions_count >= self.alert_thresholds['position_count_max']:
                self._trigger_alert(
                    alert_type="position_count",
                    severity="warning",
                    message=f"持仓数量达到 {stats.positions_count}",
                    current_value=stats.positions_count,
                    threshold=self.alert_thresholds['position_count_max']
                )
            
            # 紧急停止警报
            if stats.emergency_stop:
                self._trigger_alert(
                    alert_type="emergency_stop",
                    severity="emergency",
                    message="紧急停止已触发",
                    current_value=1,
                    threshold=0
                )
            
        except Exception as e:
            logger.error(f"检查警报失败: {e}")
    
    def _trigger_alert(self, alert_type: str, severity: str, message: str,
                      current_value: float, threshold: float) -> None:
        """触发警报"""
        try:
            # 避免重复警报(5分钟内相同类型)
            recent_alerts = [
                alert for alert in self.alerts_triggered
                if (alert['type'] == alert_type and 
                    time.time() - alert['timestamp'] < 300)
            ]
            
            if recent_alerts:
                return
            
            alert = {
                'alert_id': f"{alert_type}_{int(time.time())}",
                'timestamp': time.time(),
                'type': alert_type,
                'severity': severity,
                'message': message,
                'current_value': current_value,
                'threshold': threshold
            }
            
            self.alerts_triggered.append(alert)
            
            # 记录到交易日志
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type=alert_type,
                    severity=severity,
                    description=message,
                    impact=abs(current_value - threshold)
                )
            
            logger.warning(f"警报触发: {alert_type} - {message}")
            
        except Exception as e:
            logger.error(f"触发警报失败: {e}")
    
    def _get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'monitoring_active': self.monitoring,
            'exchange_connected': True,  # 模拟交易所总是连接的
            'order_manager_active': self.order_manager is not None,
            'risk_manager_active': self.risk_manager is not None,
            'signal_executor_active': self.signal_executor is not None,
            'all_systems_ok': True
        }
        
        # 检查各组件状态
        if self.risk_manager and self.risk_manager.emergency_stop_triggered:
            status['all_systems_ok'] = False
        
        return status
    
    def _get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要"""
        account = self.exchange.get_account_info()
        
        # 计算24小时变化
        balance_change_24h = 0.0
        if len(self.stats_history) > 1440:  # 24小时数据点(1分钟间隔)
            old_balance = self.stats_history[-1440].account_balance
            balance_change_24h = account['total_balance'] - old_balance
        
        return {
            'total_balance': account['total_balance'],
            'available_balance': account['available_balance'],
            'margin_used': account['margin_used'],
            'unrealized_pnl': account['unrealized_pnl'],
            'balance_change_24h': balance_change_24h,
            'initial_balance': self.exchange.initial_balance,
            'total_return_percent': ((account['total_balance'] / self.exchange.initial_balance) - 1) * 100
        }
    
    def _get_positions_summary(self) -> Dict[str, Any]:
        """获取持仓摘要"""
        positions = self.exchange.get_positions()
        
        total_unrealized = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        long_positions = [pos for pos in positions if pos.get('side') == 'long']
        short_positions = [pos for pos in positions if pos.get('side') == 'short']
        
        return {
            'total_positions': len(positions),
            'long_positions': len(long_positions),
            'short_positions': len(short_positions),
            'total_unrealized_pnl': total_unrealized,
            'largest_position': max(positions, key=lambda x: abs(x.get('unrealized_pnl', 0))) if positions else None
        }
    
    def _get_orders_summary(self) -> Dict[str, Any]:
        """获取订单摘要"""
        summary = {
            'active_orders': 0,
            'pending_orders': 0,
            'conditional_orders': 0
        }
        
        if self.order_manager:
            orders = self.order_manager.get_active_orders()
            summary.update({
                'active_orders': len(orders.get('exchange_orders', [])),
                'pending_orders': len(orders.get('exchange_orders', [])),
                'conditional_orders': len(orders.get('conditional_orders', []))
            })
        
        return summary
    
    def _get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        summary = {
            'risk_level': 'unknown',
            'risk_utilization': 0.0,
            'emergency_stop': False,
            'active_alerts': 0
        }
        
        if self.risk_manager:
            risk_report = self.risk_manager.get_risk_report()
            if 'error' not in risk_report:
                summary.update({
                    'risk_level': risk_report['risk_level']['current'],
                    'emergency_stop': risk_report['emergency_stop'],
                    'active_alerts': len(risk_report.get('recent_alerts', []))
                })
                
                # 计算风险利用率
                current_risks = risk_report.get('current_risks', {})
                risk_checks = current_risks.get('risk_checks', {})
                total_risk = risk_checks.get('total_risk', {})
                if total_risk and 'utilization' in total_risk:
                    summary['risk_utilization'] = total_risk['utilization']
        
        return summary
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {
            'win_rate': 0.0,
            'total_trades': 0,
            'trades_today': 0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
        
        if self.trade_logger:
            # 总体性能
            overall_perf = self.trade_logger.get_performance_summary(days=30)
            if 'error' not in overall_perf:
                summary.update({
                    'win_rate': overall_perf.get('win_rate', 0.0),
                    'total_trades': overall_perf.get('total_trades', 0),
                    'best_trade': overall_perf.get('largest_win', 0.0),
                    'worst_trade': overall_perf.get('largest_loss', 0.0)
                })
            
            # 今日性能
            today_perf = self.trade_logger.get_performance_summary(days=1)
            if 'error' not in today_perf:
                summary['trades_today'] = today_perf.get('total_trades', 0)
        
        return summary
    
    def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """获取最近警报"""
        # 返回24小时内的警报
        recent_time = time.time() - 24 * 3600
        recent_alerts = [
            alert for alert in self.alerts_triggered
            if alert['timestamp'] >= recent_time
        ]
        
        # 按时间倒序排列
        return sorted(recent_alerts, key=lambda x: x['timestamp'], reverse=True)
    
    def _get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        market_data = {
            'eth_price': 0.0,
            'price_change_24h': 0.0,
            'last_update': time.time()
        }
        
        # 从交易所获取当前价格
        current_price = self.exchange.get_current_price('ETHUSDT')
        if current_price:
            market_data['eth_price'] = current_price
        
        # TODO: 添加更多市场数据(如果需要)
        
        return market_data

# 命令行监控工具
def main():
    """命令行监控入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETH永续合约交易监控')
    parser.add_argument('--show-stats', action='store_true', help='显示统计信息')
    parser.add_argument('--period', default='24h', help='统计周期')
    parser.add_argument('--export', help='导出监控数据到文件')
    parser.add_argument('--continuous', action='store_true', help='持续监控模式')
    
    args = parser.parse_args()
    
    try:
        # 初始化基本组件(这里需要根据实际情况调整)
        from .simulated_exchange import SimulatedExchange
        
        exchange = SimulatedExchange()
        monitor = TradingMonitor(exchange)
        
        if args.show_stats:
            monitor.print_status_summary()
        elif args.export:
            success = monitor.export_monitoring_data(args.export)
            if success:
                print(f"✅ 监控数据已导出到: {args.export}")
            else:
                print("❌ 导出失败")
        elif args.continuous:
            print("🎯 启动持续监控模式 (Ctrl+C 退出)")
            monitor.start_monitoring()
            try:
                while True:
                    os.system('clear' if os.name == 'posix' else 'cls')
                    monitor.print_status_summary()
                    time.sleep(5)
            except KeyboardInterrupt:
                print("\n👋 监控已停止")
                monitor.stop_monitoring()
        else:
            monitor.print_status_summary()
    
    except Exception as e:
        logger.error(f"监控工具错误: {e}")
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()