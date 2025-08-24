#!/usr/bin/env python3
"""
持仓管理器 - 专业的持仓管理和风险控制
基于Anna Coulling VSA理论的持仓管理和风险控制
"""

import time
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from .simulated_exchange import SimulatedExchange, Position

logger = logging.getLogger(__name__)

@dataclass
class PositionMetrics:
    """持仓指标"""
    symbol: str
    entry_time: float
    holding_duration: float
    max_favorable_move: float  # 最大有利变动
    max_adverse_move: float    # 最大不利变动
    current_mae: float         # 当前最大不利变动(MAE)
    current_mfe: float         # 当前最大有利变动(MFE)
    risk_reward_ratio: float
    heat_level: int           # 风险热度 1-5
    drawdown_from_peak: float
    
@dataclass  
class RiskLevel:
    """风险等级定义"""
    level: int
    name: str
    max_position_percent: float  # 最大持仓比例
    max_leverage: float
    stop_loss_percent: float     # 建议止损百分比
    description: str

class PositionManager:
    """
    持仓管理器
    
    基于Anna Coulling VSA风险管理原则:
    - 单笔交易风险不超过资金的2%
    - 总持仓风险不超过资金的6%
    - 连续亏损后降低仓位
    - 基于市场条件调整风险等级
    """
    
    def __init__(self, exchange: SimulatedExchange):
        """
        初始化持仓管理器
        
        Args:
            exchange: 模拟交易所实例
        """
        self.exchange = exchange
        
        # 持仓指标跟踪
        self.position_metrics: Dict[str, PositionMetrics] = {}
        self.position_history: List[Dict[str, Any]] = []
        
        # Anna Coulling风险等级
        self.risk_levels = {
            1: RiskLevel(1, "极低风险", 0.01, 2.0, 0.005, "市场极度不确定时"),
            2: RiskLevel(2, "低风险", 0.02, 5.0, 0.01, "市场趋势不明确时"),
            3: RiskLevel(3, "中等风险", 0.20, 10.0, 0.02, "正常市场条件"),
            4: RiskLevel(4, "高风险", 0.08, 15.0, 0.03, "强趋势市场"),
            5: RiskLevel(5, "极高风险", 0.10, 20.0, 0.05, "突破性机会")
        }
        
        self.current_risk_level = 3  # 默认中等风险
        
        # 统计数据
        self.performance_stats = {
            'total_positions': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'avg_holding_time': 0.0,
            'max_concurrent_positions': 0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'current_streak': 0,
            'max_drawdown': 0.0,
            'recovery_factor': 0.0
        }
        
        logger.info("持仓管理器初始化完成")
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss_price: float, 
                               risk_percent: Optional[float] = None,
                               ai_confidence: Optional[float] = None) -> Dict[str, Any]:
        """
        根据Anna Coulling方法计算仓位大小 (增强版 - 动态风险管理)
        
        Args:
            symbol: 交易对
            entry_price: 入场价格
            stop_loss_price: 止损价格
            risk_percent: 风险百分比(默认使用当前风险等级)
            ai_confidence: AI置信度 (0.0-1.0，用于动态调整风险)
            
        Returns:
            仓位计算结果
        """
        try:
            account = self.exchange.get_account_info()
            available_balance = account['available_balance']
            
            if risk_percent is None:
                risk_percent = self.risk_levels[self.current_risk_level].stop_loss_percent
            
            # 🎯 动态风险调整基于AI置信度 (Kelly Criterion启发)
            if ai_confidence is not None:
                confidence_multiplier = self._calculate_confidence_multiplier(ai_confidence)
                risk_percent = risk_percent * confidence_multiplier
                
                # 确保风险不超过合理范围
                max_risk = self.risk_levels[self.current_risk_level].stop_loss_percent * 1.5  # 最多增加50%
                min_risk = self.risk_levels[self.current_risk_level].stop_loss_percent * 0.5  # 最少减少50%
                risk_percent = max(min_risk, min(max_risk, risk_percent))
            
            # 计算每单位的风险
            risk_per_unit = abs(entry_price - stop_loss_price)
            
            # 风险金额 = 账户资金 × 动态调整后的风险百分比
            risk_amount = available_balance * risk_percent
            
            # 基础仓位大小 = 风险金额 / 每单位风险
            base_position_size = risk_amount / risk_per_unit
            
            # 应用风险等级调整
            risk_level = self.risk_levels[self.current_risk_level]
            max_position_value = available_balance * risk_level.max_position_percent
            max_position_size = max_position_value / entry_price
            
            # 取较小值
            recommended_size = min(base_position_size, max_position_size)
            
            # 考虑连续亏损调整
            streak_adjustment = self._get_streak_adjustment()
            adjusted_size = recommended_size * streak_adjustment
            
            return {
                'recommended_size': adjusted_size,
                'max_size_by_risk': max_position_size,
                'base_size': base_position_size,
                'risk_amount': risk_amount,
                'risk_per_unit': risk_per_unit,
                'streak_adjustment': streak_adjustment,
                'risk_percent': risk_percent,
                'position_value': adjusted_size * entry_price,
                'max_leverage': risk_level.max_leverage,
                'ai_confidence': ai_confidence,
                'confidence_multiplier': self._calculate_confidence_multiplier(ai_confidence) if ai_confidence else 1.0
            }
            
        except Exception as e:
            logger.error(f"计算仓位大小失败: {e}")
            return {'error': str(e)}
    
    def assess_position_risk(self, symbol: str) -> Dict[str, Any]:
        """评估持仓风险"""
        try:
            positions = self.exchange.get_positions()
            position = next((p for p in positions if p['symbol'] == symbol), None)
            
            if not position:
                return {'error': '持仓不存在'}
            
            current_price = self.exchange.get_current_price(symbol)
            if not current_price:
                return {'error': '无法获取当前价格'}
            
            # 基础风险指标
            entry_price = position['avg_entry_price']
            unrealized_pnl = position['unrealized_pnl']
            position_value = position['size'] * current_price
            
            # 计算风险比率
            account = self.exchange.get_account_info()
            total_balance = account['total_balance']
            risk_ratio = abs(unrealized_pnl) / total_balance if unrealized_pnl < 0 else 0
            
            # 获取持仓指标
            metrics = self.position_metrics.get(symbol)
            if not metrics:
                metrics = self._initialize_position_metrics(symbol, position)
            
            # 更新指标
            self._update_position_metrics(symbol, current_price, metrics)
            
            # 计算热度等级
            heat_level = self._calculate_heat_level(metrics, risk_ratio)
            
            # 风险评估
            risk_assessment = {
                'heat_level': heat_level,
                'risk_ratio': risk_ratio,
                'mae_ratio': metrics.current_mae / entry_price if entry_price > 0 else 0,
                'mfe_ratio': metrics.current_mfe / entry_price if entry_price > 0 else 0,
                'holding_time_hours': metrics.holding_duration / 3600,
                'drawdown_from_peak': metrics.drawdown_from_peak,
                'position_health': self._assess_position_health(heat_level, risk_ratio)
            }
            
            # 建议行动
            recommendations = self._generate_position_recommendations(risk_assessment, position)
            
            return {
                'position_info': position,
                'risk_assessment': risk_assessment,
                'recommendations': recommendations,
                'metrics': metrics.__dict__
            }
            
        except Exception as e:
            logger.error(f"评估持仓风险失败: {e}")
            return {'error': str(e)}
    
    def set_risk_level(self, level: int, reason: str = "") -> None:
        """
        设置风险等级
        
        Args:
            level: 风险等级 1-5
            reason: 调整原因
        """
        if level not in self.risk_levels:
            raise ValueError("风险等级必须在1-5之间")
        
        old_level = self.current_risk_level
        self.current_risk_level = level
        
        risk_level = self.risk_levels[level]
        
        logger.info(f"风险等级调整: {old_level} → {level} ({risk_level.name})")
        if reason:
            logger.info(f"调整原因: {reason}")
    
    def get_portfolio_risk(self) -> Dict[str, Any]:
        """获取组合风险评估"""
        try:
            positions = self.exchange.get_positions()
            account = self.exchange.get_account_info()
            
            if not positions:
                return {
                    'total_risk': 0.0,
                    'position_count': 0,
                    'risk_distribution': {},
                    'recommendations': ['无持仓，可以建仓']
                }
            
            total_margin = 0.0
            total_unrealized_pnl = 0.0
            position_risks = {}
            
            for position in positions:
                symbol = position['symbol']
                margin_used = position['margin_used']
                unrealized_pnl = position['unrealized_pnl']
                
                total_margin += margin_used
                total_unrealized_pnl += unrealized_pnl
                
                # 计算单个持仓风险
                position_risk = margin_used / account['total_balance']
                position_risks[symbol] = {
                    'margin_ratio': position_risk,
                    'pnl': unrealized_pnl,
                    'heat_level': self.position_metrics.get(symbol, PositionMetrics("", 0, 0, 0, 0, 0, 0, 0, 3, 0)).heat_level
                }
            
            # 组合风险指标
            total_risk_ratio = total_margin / account['total_balance']
            pnl_ratio = total_unrealized_pnl / account['total_balance']
            
            # Anna Coulling风险控制检查
            max_risk = self.risk_levels[self.current_risk_level].max_position_percent * len(positions)
            risk_utilization = total_risk_ratio / max_risk if max_risk > 0 else 0
            
            # 生成建议
            recommendations = []
            if total_risk_ratio > 0.06:  # 超过6%总风险
                recommendations.append("警告：总持仓风险超过Anna Coulling建议的6%上限")
            if risk_utilization > 0.8:
                recommendations.append("风险利用率过高，建议减仓")
            if len(positions) > 5:
                recommendations.append("持仓过于分散，建议集中优势仓位")
                
            return {
                'total_risk_ratio': total_risk_ratio,
                'pnl_ratio': pnl_ratio,
                'risk_utilization': risk_utilization,
                'position_count': len(positions),
                'position_risks': position_risks,
                'max_allowed_risk': max_risk,
                'recommendations': recommendations,
                'overall_health': 'healthy' if total_risk_ratio < 0.04 else 'warning' if total_risk_ratio < 0.08 else 'danger'
            }
            
        except Exception as e:
            logger.error(f"获取组合风险失败: {e}")
            return {'error': str(e)}
    
    def suggest_position_adjustments(self) -> List[Dict[str, Any]]:
        """建议持仓调整"""
        suggestions = []
        
        try:
            positions = self.exchange.get_positions()
            
            for position in positions:
                symbol = position['symbol']
                risk_assessment = self.assess_position_risk(symbol)
                
                if 'error' in risk_assessment:
                    continue
                
                risk_info = risk_assessment['risk_assessment']
                heat_level = risk_info['heat_level']
                
                suggestion = {
                    'symbol': symbol,
                    'current_size': position['size'],
                    'heat_level': heat_level,
                    'actions': []
                }
                
                # 基于热度等级给出建议
                if heat_level >= 4:
                    suggestion['actions'].append({
                        'action': 'reduce_position',
                        'reason': '风险热度过高',
                        'urgency': 'high'
                    })
                
                if risk_info['mae_ratio'] > 0.03:  # MAE超过3%
                    suggestion['actions'].append({
                        'action': 'tighten_stop',
                        'reason': 'MAE过大，需要收紧止损',
                        'urgency': 'medium'
                    })
                
                if risk_info['holding_time_hours'] > 72:  # 持仓超过3天
                    suggestion['actions'].append({
                        'action': 'review_position',
                        'reason': '持仓时间较长，需要重新评估',
                        'urgency': 'low'
                    })
                
                if suggestion['actions']:
                    suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"生成持仓建议失败: {e}")
            return []
    
    def update_performance_stats(self, closed_position: Dict[str, Any]) -> None:
        """更新业绩统计"""
        try:
            self.performance_stats['total_positions'] += 1
            
            realized_pnl = closed_position.get('realized_pnl', 0)
            
            if realized_pnl > 0:
                self.performance_stats['winning_positions'] += 1
                self.performance_stats['consecutive_losses'] = 0
                self.performance_stats['consecutive_wins'] += 1
                self.performance_stats['current_streak'] = self.performance_stats['consecutive_wins']
                
                if realized_pnl > self.performance_stats['largest_win']:
                    self.performance_stats['largest_win'] = realized_pnl
            else:
                self.performance_stats['losing_positions'] += 1
                self.performance_stats['consecutive_wins'] = 0
                self.performance_stats['consecutive_losses'] += 1
                self.performance_stats['current_streak'] = -self.performance_stats['consecutive_losses']
                
                if abs(realized_pnl) > abs(self.performance_stats['largest_loss']):
                    self.performance_stats['largest_loss'] = realized_pnl
            
            # 更新平均持仓时间
            if 'holding_duration' in closed_position:
                current_avg = self.performance_stats['avg_holding_time']
                total_positions = self.performance_stats['total_positions']
                new_duration = closed_position['holding_duration']
                
                self.performance_stats['avg_holding_time'] = (
                    (current_avg * (total_positions - 1) + new_duration) / total_positions
                )
            
            # 记录历史
            self.position_history.append({
                'timestamp': time.time(),
                'position': closed_position,
                'stats_snapshot': self.performance_stats.copy()
            })
            
        except Exception as e:
            logger.error(f"更新业绩统计失败: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取业绩摘要"""
        stats = self.performance_stats.copy()
        
        # 计算胜率
        total = stats['total_positions']
        if total > 0:
            win_rate = stats['winning_positions'] / total
            stats['win_rate'] = win_rate
            
            # 计算期望值
            if stats['winning_positions'] > 0 and stats['losing_positions'] > 0:
                avg_win = stats['largest_win'] * 0.6  # 估算
                avg_loss = stats['largest_loss'] * 0.6  # 估算
                expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
                stats['expectancy'] = expectancy
        
        # 添加当前状态
        account = self.exchange.get_account_info()
        stats['current_balance'] = account['total_balance']
        stats['total_return'] = (account['total_balance'] / self.exchange.initial_balance - 1) * 100
        
        return stats
    
    def _initialize_position_metrics(self, symbol: str, position: Dict[str, Any]) -> PositionMetrics:
        """初始化持仓指标"""
        metrics = PositionMetrics(
            symbol=symbol,
            entry_time=time.time(),
            holding_duration=0.0,
            max_favorable_move=0.0,
            max_adverse_move=0.0,
            current_mae=0.0,
            current_mfe=0.0,
            risk_reward_ratio=0.0,
            heat_level=3,
            drawdown_from_peak=0.0
        )
        
        self.position_metrics[symbol] = metrics
        return metrics
    
    def _update_position_metrics(self, symbol: str, current_price: float, metrics: PositionMetrics) -> None:
        """更新持仓指标"""
        positions = self.exchange.get_positions()
        position = next((p for p in positions if p['symbol'] == symbol), None)
        
        if not position:
            return
        
        entry_price = position['avg_entry_price']
        position_side = position['side']
        
        # 更新持仓时间
        metrics.holding_duration = time.time() - metrics.entry_time
        
        # 计算当前盈亏
        if position_side == "long":
            current_move = current_price - entry_price
        else:
            current_move = entry_price - current_price
        
        # 更新最大有利/不利变动
        if current_move > 0:
            metrics.current_mfe = max(metrics.current_mfe, current_move)
            metrics.max_favorable_move = metrics.current_mfe
        else:
            metrics.current_mae = max(metrics.current_mae, abs(current_move))
            metrics.max_adverse_move = metrics.current_mae
        
        # 更新峰值回撤
        if metrics.current_mfe > 0:
            drawdown = (metrics.current_mfe - current_move) / metrics.current_mfe
            metrics.drawdown_from_peak = max(metrics.drawdown_from_peak, drawdown)
    
    def _calculate_heat_level(self, metrics: PositionMetrics, risk_ratio: float) -> int:
        """计算风险热度等级"""
        heat_score = 0
        
        # 基于MAE的热度
        if metrics.current_mae / 100 > 0.02:  # 假设价格在100左右
            heat_score += 1
        if metrics.current_mae / 100 > 0.05:
            heat_score += 1
        
        # 基于风险比率
        if risk_ratio > 0.02:
            heat_score += 1
        if risk_ratio > 0.05:
            heat_score += 1
        
        # 基于持仓时间
        if metrics.holding_duration > 86400:  # 超过1天
            heat_score += 1
        
        return max(1, min(5, heat_score + 1))
    
    def _assess_position_health(self, heat_level: int, risk_ratio: float) -> str:
        """评估持仓健康度"""
        if heat_level <= 2 and risk_ratio < 0.02:
            return "healthy"
        elif heat_level <= 3 and risk_ratio < 0.04:
            return "normal"
        elif heat_level <= 4 or risk_ratio < 0.06:
            return "warning"
        else:
            return "danger"
    
    def _generate_position_recommendations(self, risk_assessment: Dict[str, Any], 
                                         position: Dict[str, Any]) -> List[str]:
        """生成持仓建议"""
        recommendations = []
        
        heat_level = risk_assessment['heat_level']
        risk_ratio = risk_assessment['risk_ratio']
        mae_ratio = risk_assessment['mae_ratio']
        
        if heat_level >= 4:
            recommendations.append("考虑减仓或平仓")
        
        if risk_ratio > 0.03:
            recommendations.append("风险过高，建议收紧止损")
        
        if mae_ratio > 0.025:
            recommendations.append("最大不利变动过大，重新评估入场逻辑")
        
        if risk_assessment['holding_time_hours'] > 48:
            recommendations.append("长期持仓，考虑是否符合预期")
        
        if not recommendations:
            recommendations.append("持仓状态良好，继续持有")
        
        return recommendations
    
    def _get_streak_adjustment(self) -> float:
        """根据连胜/连败调整仓位"""
        consecutive_losses = self.performance_stats['consecutive_losses']
        consecutive_wins = self.performance_stats['consecutive_wins']
        
        # Anna Coulling风险管理：连续亏损后减仓
        if consecutive_losses >= 3:
            return 0.5  # 减半
        elif consecutive_losses >= 2:
            return 0.75  # 减25%
        elif consecutive_wins >= 3:
            return 1.2  # 连胜时可适度加大仓位
        else:
            return 1.0  # 正常仓位
    
    def _calculate_confidence_multiplier(self, ai_confidence: float) -> float:
        """
        基于AI置信度计算风险倍数 (Kelly Criterion启发)
        
        Args:
            ai_confidence: AI置信度 (0.0-1.0)
            
        Returns:
            风险倍数 (0.5-1.5之间)
        """
        if ai_confidence is None:
            return 1.0
        
        # 确保置信度在合理范围内
        confidence = max(0.0, min(1.0, ai_confidence))
        
        # Kelly Criterion启发的风险调整
        # 高置信度(>0.8): 增加风险至1.25x
        # 中置信度(0.6-0.8): 正常风险 1.0x
        # 低置信度(<0.6): 减少风险至0.75x
        # 非常低置信度(<0.4): 大幅减少风险至0.5x
        
        if confidence >= 0.85:
            return 1.5  # 非常高置信度，增加50%风险
        elif confidence >= 0.75:
            return 1.25  # 高置信度，增加25%风险
        elif confidence >= 0.60:
            return 1.0   # 中等置信度，正常风险
        elif confidence >= 0.40:
            return 0.75  # 低置信度，减少25%风险
        else:
            return 0.5   # 很低置信度，减少50%风险
