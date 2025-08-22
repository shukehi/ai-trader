#!/usr/bin/env python3
"""
风险管理器 - 基于Anna Coulling VSA理论的专业风险管理
实现多层次风险控制、实时风险监控和动态风险调整
"""

import time
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .simulated_exchange import SimulatedExchange
from .position_manager import PositionManager
from .trade_logger import TradeLogger

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """风险等级"""
    CONSERVATIVE = "conservative"  # 保守
    MODERATE = "moderate"         # 适中
    AGGRESSIVE = "aggressive"     # 激进

class AlertSeverity(Enum):
    """警报严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class RiskLimit:
    """风险限制"""
    name: str
    limit_type: str  # "percentage", "absolute", "ratio"
    threshold: float
    current_value: float
    status: str = "safe"  # "safe", "warning", "danger", "critical"
    description: str = ""

@dataclass
class RiskAlert:
    """风险警报"""
    alert_id: str
    timestamp: float
    severity: AlertSeverity
    risk_type: str
    message: str
    current_value: float
    threshold: float
    symbol: Optional[str] = None
    action_required: str = ""
    auto_action_taken: bool = False

class RiskManager:
    """
    风险管理器
    
    基于Anna Coulling VSA风险管理原则:
    - 单笔交易风险不超过2%
    - 总风险敞口不超过6%
    - 连续亏损后自动降低风险等级
    - 基于市场波动性动态调整
    """
    
    def __init__(self, exchange: SimulatedExchange, position_manager: PositionManager,
                 trade_logger: TradeLogger, initial_risk_level: RiskLevel = RiskLevel.MODERATE):
        """
        初始化风险管理器
        
        Args:
            exchange: 模拟交易所
            position_manager: 持仓管理器
            trade_logger: 交易日志器
            initial_risk_level: 初始风险等级
        """
        self.exchange = exchange
        self.position_manager = position_manager
        self.trade_logger = trade_logger
        
        # 风险等级设置
        self.current_risk_level = initial_risk_level
        self.risk_level_settings = {
            RiskLevel.CONSERVATIVE: {
                'max_single_trade_risk': 0.01,    # 1%
                'max_total_risk': 0.03,           # 3%
                'max_positions': 3,
                'max_leverage': 5.0,
                'max_correlation_exposure': 0.50,
                'drawdown_limit': 0.05,           # 5%
                'volatility_multiplier': 0.8
            },
            RiskLevel.MODERATE: {
                'max_single_trade_risk': 0.02,    # 2%
                'max_total_risk': 0.06,           # 6%
                'max_positions': 5,
                'max_leverage': 10.0,
                'max_correlation_exposure': 0.70,
                'drawdown_limit': 0.10,           # 10%
                'volatility_multiplier': 1.0
            },
            RiskLevel.AGGRESSIVE: {
                'max_single_trade_risk': 0.03,    # 3%
                'max_total_risk': 0.10,           # 10%
                'max_positions': 8,
                'max_leverage': 20.0,
                'max_correlation_exposure': 0.80,
                'drawdown_limit': 0.15,           # 15%
                'volatility_multiplier': 1.2
            }
        }
        
        # 风险监控
        self.risk_limits: Dict[str, RiskLimit] = {}
        self.risk_alerts: List[RiskAlert] = []
        self.emergency_stop_triggered = False
        
        # 统计数据
        self.risk_stats = {
            'total_risk_events': 0,
            'emergency_stops': 0,
            'risk_level_changes': 0,
            'max_drawdown_reached': 0.0,
            'violations_count': 0,
            'last_risk_check': 0.0
        }
        
        # 初始化风险限制
        self._initialize_risk_limits()
        
        logger.info(f"风险管理器初始化完成 - 风险等级: {initial_risk_level.value}")
    
    def _initialize_risk_limits(self) -> None:
        """初始化风险限制"""
        settings = self.risk_level_settings[self.current_risk_level]
        
        self.risk_limits = {
            'single_trade_risk': RiskLimit(
                name="单笔交易风险",
                limit_type="percentage",
                threshold=settings['max_single_trade_risk'],
                current_value=0.0,
                description="单笔交易最大风险比例"
            ),
            'total_risk': RiskLimit(
                name="总风险敞口",
                limit_type="percentage", 
                threshold=settings['max_total_risk'],
                current_value=0.0,
                description="所有持仓的总风险"
            ),
            'position_count': RiskLimit(
                name="持仓数量",
                limit_type="absolute",
                threshold=settings['max_positions'],
                current_value=0,
                description="同时持有的最大仓位数"
            ),
            'leverage': RiskLimit(
                name="杠杆倍数",
                limit_type="ratio",
                threshold=settings['max_leverage'],
                current_value=1.0,
                description="最大允许杠杆倍数"
            ),
            'drawdown': RiskLimit(
                name="最大回撤",
                limit_type="percentage",
                threshold=settings['drawdown_limit'],
                current_value=0.0,
                description="账户最大回撤限制"
            )
        }
    
    def check_new_position_risk(self, symbol: str, side: str, entry_price: float,
                               stop_loss: Optional[float] = None, 
                               position_size: Optional[float] = None) -> Dict[str, Any]:
        """
        检查新仓位风险
        
        Args:
            symbol: 交易对
            side: 交易方向
            entry_price: 入场价格
            stop_loss: 止损价格
            position_size: 仓位大小
            
        Returns:
            风险检查结果
        """
        try:
            account = self.exchange.get_account_info()
            total_balance = account['total_balance']
            
            # 计算风险金额
            if stop_loss and position_size:
                risk_per_unit = abs(entry_price - stop_loss)
                total_risk = risk_per_unit * position_size
                risk_ratio = total_risk / total_balance
            else:
                # 使用默认风险比例估算
                settings = self.risk_level_settings[self.current_risk_level]
                risk_ratio = settings['max_single_trade_risk'] * 0.8  # 保守估算
                total_risk = risk_ratio * total_balance
            
            # 单笔交易风险检查
            max_single_risk = self.risk_limits['single_trade_risk'].threshold
            if risk_ratio > max_single_risk:
                return {
                    'approved': False,
                    'reason': f'单笔交易风险过高: {risk_ratio:.2%} > {max_single_risk:.2%}',
                    'risk_ratio': risk_ratio,
                    'max_allowed': max_single_risk
                }
            
            # 总风险检查
            current_positions = self.exchange.get_positions()
            current_total_risk = sum(pos.get('margin_used', 0) for pos in current_positions) / total_balance
            projected_total_risk = current_total_risk + risk_ratio
            
            max_total_risk = self.risk_limits['total_risk'].threshold
            if projected_total_risk > max_total_risk:
                return {
                    'approved': False,
                    'reason': f'总风险敞口将超限: {projected_total_risk:.2%} > {max_total_risk:.2%}',
                    'current_total_risk': current_total_risk,
                    'projected_total_risk': projected_total_risk,
                    'max_allowed': max_total_risk
                }
            
            # 持仓数量检查
            position_count = len(current_positions)
            max_positions = self.risk_limits['position_count'].threshold
            if position_count >= max_positions:
                return {
                    'approved': False,
                    'reason': f'持仓数量已达上限: {position_count} >= {max_positions}',
                    'current_positions': position_count,
                    'max_allowed': max_positions
                }
            
            # 相关性检查(简化版 - 检查同一交易对)
            if any(pos.get('symbol') == symbol for pos in current_positions):
                return {
                    'approved': False,
                    'reason': f'已持有{symbol}仓位，避免过度集中',
                    'existing_symbol': symbol
                }
            
            # 紧急停止检查
            if self.emergency_stop_triggered:
                return {
                    'approved': False,
                    'reason': '紧急停止已触发，暂停新开仓',
                    'emergency_stop': True
                }
            
            return {
                'approved': True,
                'risk_ratio': risk_ratio,
                'projected_total_risk': projected_total_risk,
                'recommendations': self._generate_position_recommendations(risk_ratio)
            }
            
        except Exception as e:
            logger.error(f"检查新仓位风险失败: {e}")
            return {
                'approved': False,
                'reason': f'风险检查出错: {str(e)}',
                'error': True
            }
    
    def monitor_current_risks(self) -> Dict[str, Any]:
        """监控当前风险状况"""
        try:
            risk_summary = {
                'timestamp': time.time(),
                'risk_level': self.current_risk_level.value,
                'emergency_stop': self.emergency_stop_triggered,
                'risk_checks': {},
                'alerts': [],
                'recommendations': []
            }
            
            # 更新所有风险指标
            self._update_risk_metrics()
            
            # 检查每个风险限制
            for risk_name, risk_limit in self.risk_limits.items():
                status = self._assess_risk_status(risk_limit)
                risk_limit.status = status
                
                risk_summary['risk_checks'][risk_name] = {
                    'name': risk_limit.name,
                    'current': risk_limit.current_value,
                    'threshold': risk_limit.threshold,
                    'status': status,
                    'utilization': (risk_limit.current_value / risk_limit.threshold 
                                  if risk_limit.threshold > 0 else 0)
                }
                
                # 生成警报
                if status in ['warning', 'danger', 'critical']:
                    alert = self._create_risk_alert(risk_name, risk_limit, status)
                    if alert:
                        self.risk_alerts.append(alert)
                        risk_summary['alerts'].append(alert.__dict__)
            
            # 检查回撤
            drawdown_check = self._check_drawdown()
            if drawdown_check['alert']:
                risk_summary['alerts'].append(drawdown_check['alert'])
            
            # 生成建议
            risk_summary['recommendations'] = self._generate_risk_recommendations()
            
            # 触发自动行动
            self._trigger_auto_actions(risk_summary)
            
            self.risk_stats['last_risk_check'] = time.time()
            
            return risk_summary
            
        except Exception as e:
            logger.error(f"风险监控失败: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def set_risk_level(self, new_level: RiskLevel, reason: str = "") -> bool:
        """
        设置风险等级
        
        Args:
            new_level: 新的风险等级
            reason: 调整原因
            
        Returns:
            是否成功
        """
        try:
            if new_level == self.current_risk_level:
                return True
            
            old_level = self.current_risk_level
            self.current_risk_level = new_level
            
            # 重新初始化风险限制
            self._initialize_risk_limits()
            
            # 记录风险事件
            self.trade_logger.log_risk_event(
                event_type="risk_level_change",
                severity="medium",
                description=f"风险等级从 {old_level.value} 调整为 {new_level.value}",
                action_taken=reason or "手动调整"
            )
            
            # 更新统计
            self.risk_stats['risk_level_changes'] += 1
            
            logger.info(f"风险等级调整: {old_level.value} → {new_level.value} ({reason})")
            
            return True
            
        except Exception as e:
            logger.error(f"设置风险等级失败: {e}")
            return False
    
    def trigger_emergency_stop(self, reason: str = "手动触发") -> Dict[str, Any]:
        """
        触发紧急停止
        
        Args:
            reason: 触发原因
            
        Returns:
            紧急停止结果
        """
        try:
            if self.emergency_stop_triggered:
                return {'success': False, 'reason': '紧急停止已经触发'}
            
            self.emergency_stop_triggered = True
            
            # 记录紧急事件
            self.trade_logger.log_risk_event(
                event_type="emergency_stop",
                severity="critical",
                description=f"紧急停止触发: {reason}",
                action_taken="停止所有新开仓，准备清仓"
            )
            
            # 统计更新
            self.risk_stats['emergency_stops'] += 1
            
            # 尝试平仓所有持仓(可选)
            positions_closed = []
            if reason.startswith("auto_"):  # 自动触发时才自动平仓
                positions = self.exchange.get_positions()
                for position in positions:
                    close_result = self.exchange.close_position(position['symbol'])
                    if close_result['success']:
                        positions_closed.append(position['symbol'])
            
            logger.critical(f"紧急停止已触发: {reason}")
            
            return {
                'success': True,
                'reason': reason,
                'positions_closed': positions_closed,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"触发紧急停止失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def reset_emergency_stop(self, confirmation: str = "") -> bool:
        """重置紧急停止状态"""
        if confirmation != "CONFIRM_RESET":
            logger.warning("紧急停止重置需要确认码: CONFIRM_RESET")
            return False
        
        self.emergency_stop_triggered = False
        
        self.trade_logger.log_risk_event(
            event_type="emergency_stop_reset",
            severity="medium", 
            description="紧急停止状态已重置",
            action_taken="手动重置"
        )
        
        logger.info("紧急停止状态已重置")
        return True
    
    def get_risk_report(self) -> Dict[str, Any]:
        """获取风险报告"""
        try:
            account = self.exchange.get_account_info()
            positions = self.exchange.get_positions()
            
            # 当前风险状况
            current_risks = self.monitor_current_risks()
            
            # 历史统计
            recent_alerts = [alert for alert in self.risk_alerts 
                           if time.time() - alert.timestamp < 24 * 3600]  # 24小时内
            
            # 性能影响分析
            performance = self.position_manager.get_performance_summary()
            
            report = {
                'report_time': time.time(),
                'account_status': {
                    'total_balance': account['total_balance'],
                    'available_balance': account['available_balance'],
                    'margin_used': account['margin_used'],
                    'unrealized_pnl': account['unrealized_pnl'],
                    'positions_count': len(positions)
                },
                'risk_level': {
                    'current': self.current_risk_level.value,
                    'settings': self.risk_level_settings[self.current_risk_level]
                },
                'current_risks': current_risks,
                'recent_alerts': [alert.__dict__ for alert in recent_alerts],
                'risk_statistics': self.risk_stats,
                'emergency_stop': self.emergency_stop_triggered,
                'performance_impact': {
                    'win_rate': performance.get('win_rate', 0),
                    'total_pnl': performance.get('total_pnl', 0),
                    'max_drawdown': performance.get('max_drawdown', 0)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成风险报告失败: {e}")
            return {'error': str(e)}
    
    def _update_risk_metrics(self) -> None:
        """更新风险指标"""
        try:
            account = self.exchange.get_account_info()
            positions = self.exchange.get_positions()
            total_balance = account['total_balance']
            
            if total_balance <= 0:
                return
            
            # 更新总风险敞口
            total_margin = sum(pos.get('margin_used', 0) for pos in positions)
            self.risk_limits['total_risk'].current_value = total_margin / total_balance
            
            # 更新持仓数量
            self.risk_limits['position_count'].current_value = len(positions)
            
            # 更新最大杠杆
            max_leverage = max([pos.get('leverage', 1) for pos in positions], default=1)
            self.risk_limits['leverage'].current_value = max_leverage
            
            # 计算账户回撤
            peak_balance = max(self.exchange.initial_balance, total_balance)
            current_drawdown = (peak_balance - total_balance) / peak_balance
            self.risk_limits['drawdown'].current_value = current_drawdown
            
            # 更新最大回撤记录
            if current_drawdown > self.risk_stats['max_drawdown_reached']:
                self.risk_stats['max_drawdown_reached'] = current_drawdown
            
        except Exception as e:
            logger.error(f"更新风险指标失败: {e}")
    
    def _assess_risk_status(self, risk_limit: RiskLimit) -> str:
        """评估风险状态"""
        if risk_limit.threshold <= 0:
            return "safe"
        
        utilization = risk_limit.current_value / risk_limit.threshold
        
        if utilization >= 1.0:
            return "critical"
        elif utilization >= 0.9:
            return "danger"
        elif utilization >= 0.75:
            return "warning"
        else:
            return "safe"
    
    def _create_risk_alert(self, risk_name: str, risk_limit: RiskLimit, status: str) -> Optional[RiskAlert]:
        """创建风险警报"""
        try:
            severity_map = {
                'warning': AlertSeverity.WARNING,
                'danger': AlertSeverity.CRITICAL,
                'critical': AlertSeverity.EMERGENCY
            }
            
            alert_id = f"alert_{risk_name}_{int(time.time())}"
            
            # 检查是否需要创建新警报(避免重复)
            recent_alerts = [a for a in self.risk_alerts 
                           if a.risk_type == risk_name and time.time() - a.timestamp < 300]  # 5分钟内
            if recent_alerts:
                return None
            
            alert = RiskAlert(
                alert_id=alert_id,
                timestamp=time.time(),
                severity=severity_map.get(status, AlertSeverity.INFO),
                risk_type=risk_name,
                message=f"{risk_limit.name}: {risk_limit.current_value:.4f} / {risk_limit.threshold:.4f}",
                current_value=risk_limit.current_value,
                threshold=risk_limit.threshold
            )
            
            # 确定需要的行动
            if status == "critical":
                alert.action_required = "立即减仓或平仓"
            elif status == "danger":
                alert.action_required = "考虑减仓"
            elif status == "warning":
                alert.action_required = "密切监控"
            
            return alert
            
        except Exception as e:
            logger.error(f"创建风险警报失败: {e}")
            return None
    
    def _check_drawdown(self) -> Dict[str, Any]:
        """检查回撤情况"""
        current_drawdown = self.risk_limits['drawdown'].current_value
        threshold = self.risk_limits['drawdown'].threshold
        
        if current_drawdown >= threshold:
            alert = {
                'type': 'drawdown_limit_reached',
                'severity': 'critical',
                'message': f'账户回撤达到限制: {current_drawdown:.2%} >= {threshold:.2%}',
                'current_drawdown': current_drawdown,
                'threshold': threshold
            }
            return {'alert': alert, 'trigger_emergency': True}
        
        return {'alert': None, 'trigger_emergency': False}
    
    def _generate_risk_recommendations(self) -> List[str]:
        """生成风险管理建议"""
        recommendations = []
        
        # 基于当前风险状况
        for risk_name, risk_limit in self.risk_limits.items():
            if risk_limit.status == "critical":
                recommendations.append(f"紧急: {risk_limit.name}超限，立即采取行动")
            elif risk_limit.status == "danger":
                recommendations.append(f"警告: {risk_limit.name}接近上限，考虑调整")
            elif risk_limit.status == "warning":
                recommendations.append(f"注意: {risk_limit.name}使用率较高，建议监控")
        
        # 基于连续亏损
        performance = self.position_manager.get_performance_summary()
        consecutive_losses = performance.get('consecutive_losses', 0)
        if consecutive_losses >= 3:
            recommendations.append(f"连续亏损{consecutive_losses}次，建议降低风险等级")
        
        # 基于市场波动
        # TODO: 添加基于市场波动性的建议
        
        return recommendations
    
    def _generate_position_recommendations(self, risk_ratio: float) -> List[str]:
        """为新仓位生成建议"""
        recommendations = []
        
        settings = self.risk_level_settings[self.current_risk_level]
        
        if risk_ratio > settings['max_single_trade_risk'] * 0.8:
            recommendations.append("建议减小仓位规模")
        
        if risk_ratio < settings['max_single_trade_risk'] * 0.5:
            recommendations.append("可适当增加仓位规模")
        
        recommendations.append("确保设置合理的止损价格")
        recommendations.append("避免在同一时间开设过多相关仓位")
        
        return recommendations
    
    def _trigger_auto_actions(self, risk_summary: Dict[str, Any]) -> None:
        """触发自动风险控制行动"""
        try:
            # 检查是否需要紧急停止
            critical_alerts = [alert for alert in risk_summary['alerts'] 
                             if alert.get('severity') == 'critical' or alert.get('severity') == 'emergency']
            
            if critical_alerts and not self.emergency_stop_triggered:
                # 触发紧急停止
                self.trigger_emergency_stop("auto_critical_risk_detected")
                return
            
            # 自动降级风险等级
            danger_alerts = [alert for alert in risk_summary['alerts']
                           if alert.get('severity') in ['critical', 'emergency']]
            
            if len(danger_alerts) >= 2 and self.current_risk_level != RiskLevel.CONSERVATIVE:
                if self.current_risk_level == RiskLevel.AGGRESSIVE:
                    self.set_risk_level(RiskLevel.MODERATE, "auto_multiple_dangers")
                elif self.current_risk_level == RiskLevel.MODERATE:
                    self.set_risk_level(RiskLevel.CONSERVATIVE, "auto_multiple_dangers")
            
        except Exception as e:
            logger.error(f"自动风险控制行动失败: {e}")