#!/usr/bin/env python3
"""
多时间框架分析系统
基于Anna Coulling的VPA理论，提供不同时间周期的层次化分析

核心功能：
1. 多时间框架数据获取和同步
2. 层次化VPA信号优先级排序  
3. 时间框架间的信号确认和冲突解决
4. Context背景分析 (长周期对短周期的影响)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from data.binance_fetcher import BinanceFetcher
from data.data_processor import DataProcessor
from data.vsa_calculator import VSACalculator
from formatters.data_formatter import DataFormatter

logger = logging.getLogger(__name__)

class TimeframeImportance(Enum):
    """时间框架重要性等级"""
    CONTEXT = "context"        # 背景框架 (日线+)
    PRIMARY = "primary"        # 主要框架 (4小时)
    EXECUTION = "execution"    # 执行框架 (1小时)
    FINE_TUNE = "fine_tune"   # 微调框架 (15分钟)

@dataclass
class TimeframeSignal:
    """单个时间框架的VPA信号"""
    timeframe: str
    importance: TimeframeImportance
    market_phase: Optional[str] = None
    vpa_signal: Optional[str] = None
    price_direction: Optional[str] = None
    confidence: Optional[str] = None
    vsa_signals: Optional[List[str]] = None
    signal_strength: float = 0.0
    
    def __post_init__(self):
        if self.vsa_signals is None:
            self.vsa_signals = []

@dataclass
class MultiTimeframeAnalysis:
    """多时间框架分析结果"""
    signals: List[TimeframeSignal]
    consensus_score: float
    conflicts: List[Dict[str, Any]]
    primary_signal: Optional[TimeframeSignal]
    context_bias: str  # bullish/bearish/neutral
    recommended_action: str
    confidence_level: str

class TimeframeAnalyzer:
    """
    多时间框架分析器
    
    实现Anna Coulling的多时间框架VPA分析方法论
    """
    
    def __init__(self):
        """初始化时间框架分析器"""
        self.fetcher = BinanceFetcher()
        self.processor = DataProcessor()
        self.vsa_calculator = VSACalculator()
        self.formatter = DataFormatter()
        
        # 时间框架配置
        self.timeframe_config = {
            '1d': {
                'importance': TimeframeImportance.CONTEXT,
                'weight': 0.4,
                'limit': 30,
                'description': '日线背景趋势'
            },
            '4h': {
                'importance': TimeframeImportance.PRIMARY,
                'weight': 0.3,
                'limit': 50,
                'description': '主要交易框架'
            },
            '1h': {
                'importance': TimeframeImportance.EXECUTION,
                'weight': 0.2,
                'limit': 100,
                'description': '执行交易框架'
            },
            '15m': {
                'importance': TimeframeImportance.FINE_TUNE,
                'weight': 0.1,
                'limit': 200,
                'description': '精细调整框架'
            }
        }
        
        # VPA信号权重 (基于Anna Coulling理论)
        self.signal_weights = {
            'market_phase': 0.35,
            'vpa_signal': 0.25,
            'price_direction': 0.20,
            'vsa_signals': 0.15,
            'confidence': 0.05
        }
    
    def analyze_multiple_timeframes(self, symbol: str = 'ETH/USDT',
                                  timeframes: Optional[List[str]] = None) -> MultiTimeframeAnalysis:
        """
        执行多时间框架VPA分析
        
        Args:
            symbol: 交易对符号
            timeframes: 要分析的时间框架列表
            
        Returns:
            多时间框架分析结果
        """
        if timeframes is None:
            timeframes = ['1d', '4h', '1h', '15m']
        
        logger.info(f"开始多时间框架VPA分析: {symbol} - {timeframes}")
        
        try:
            # 获取各时间框架数据和信号
            timeframe_signals = []
            
            for tf in timeframes:
                if tf not in self.timeframe_config:
                    logger.warning(f"未识别的时间框架: {tf}")
                    continue
                    
                signal = self._analyze_single_timeframe(symbol, tf)
                if signal:
                    timeframe_signals.append(signal)
            
            # 计算整体共识
            consensus_score = self._calculate_consensus_score(timeframe_signals)
            
            # 识别冲突
            conflicts = self._identify_conflicts(timeframe_signals)
            
            # 确定主要信号 (基于权重和重要性)
            primary_signal = self._determine_primary_signal(timeframe_signals)
            
            # 分析背景偏向
            context_bias = self._analyze_context_bias(timeframe_signals)
            
            # 生成建议
            recommended_action = self._generate_recommendation(
                timeframe_signals, consensus_score, conflicts, context_bias
            )
            
            # 评估整体置信度
            confidence_level = self._assess_confidence(consensus_score, conflicts)
            
            return MultiTimeframeAnalysis(
                signals=timeframe_signals,
                consensus_score=consensus_score,
                conflicts=conflicts,
                primary_signal=primary_signal,
                context_bias=context_bias,
                recommended_action=recommended_action,
                confidence_level=confidence_level
            )
            
        except Exception as e:
            logger.error(f"多时间框架分析失败: {e}")
            raise
    
    def _analyze_single_timeframe(self, symbol: str, timeframe: str) -> Optional[TimeframeSignal]:
        """
        分析单个时间框架
        
        Args:
            symbol: 交易对符号
            timeframe: 时间框架
            
        Returns:
            时间框架VPA信号
        """
        try:
            config = self.timeframe_config[timeframe]
            logger.info(f"分析时间框架: {timeframe} - {config['description']}")
            
            # 获取OHLCV数据
            df = self.fetcher.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=config['limit']
            )
            
            # 添加VSA指标
            df_with_vsa = self.processor.add_vsa_indicators(df)
            
            # 提取VPA信号 (使用基础VPA提示词分析)
            formatted_data = self.formatter.to_pattern_description(df_with_vsa)
            
            # 这里简化处理，实际应该调用LLM分析
            # 暂时基于VSA指标生成信号
            vsa_summary = self.processor.get_vsa_summary(df_with_vsa)
            
            # 从VSA摘要推断VPA信号
            market_phase = self._infer_market_phase(df_with_vsa, vsa_summary)
            vpa_signal = self._infer_vpa_signal(df_with_vsa, vsa_summary)
            price_direction = self._infer_price_direction(df_with_vsa)
            confidence = self._infer_confidence(vsa_summary)
            
            # VSA信号列表
            vsa_signals = [vsa_summary.get('latest_vsa_signal', 'normal')]
            
            # 计算信号强度
            signal_strength = self._calculate_signal_strength(
                market_phase, vpa_signal, price_direction, vsa_summary
            )
            
            return TimeframeSignal(
                timeframe=timeframe,
                importance=config['importance'],
                market_phase=market_phase,
                vpa_signal=vpa_signal,
                price_direction=price_direction,
                confidence=confidence,
                vsa_signals=vsa_signals,
                signal_strength=signal_strength
            )
            
        except Exception as e:
            logger.error(f"分析时间框架 {timeframe} 失败: {e}")
            return None
    
    def _infer_market_phase(self, df: pd.DataFrame, vsa_summary: Dict[str, Any]) -> str:
        """根据VSA数据推断市场阶段"""
        # 简化的推断逻辑
        supply_demand_balance = vsa_summary.get('supply_demand_balance', 0)
        professional_activity = vsa_summary.get('professional_activity_count', 0)
        
        # 价格趋势
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        
        if professional_activity > 5:
            if price_change > 0.02:
                return 'markup'
            elif price_change < -0.02:
                return 'markdown'
            else:
                return 'distribution' if supply_demand_balance < 0 else 'accumulation'
        else:
            if abs(price_change) < 0.01:
                return 'accumulation' if supply_demand_balance > 0 else 'distribution'
            else:
                return 'markup' if price_change > 0 else 'markdown'
    
    def _infer_vpa_signal(self, df: pd.DataFrame, vsa_summary: Dict[str, Any]) -> str:
        """推断VPA信号"""
        balance = vsa_summary.get('supply_demand_balance', 0)
        latest_signal = vsa_summary.get('latest_vsa_signal', 'normal')
        
        if latest_signal == 'no_demand' or balance < -0.3:
            return 'bearish'
        elif latest_signal == 'no_supply' or balance > 0.3:
            return 'bullish'
        else:
            return 'neutral'
    
    def _infer_price_direction(self, df: pd.DataFrame) -> str:
        """推断价格方向"""
        short_trend = df['close'].iloc[-5:].mean()
        longer_trend = df['close'].iloc[-20:-5].mean()
        
        if short_trend > longer_trend * 1.01:
            return 'up'
        elif short_trend < longer_trend * 0.99:
            return 'down'
        else:
            return 'sideways'
    
    def _infer_confidence(self, vsa_summary: Dict[str, Any]) -> str:
        """推断分析置信度"""
        strength = vsa_summary.get('latest_signal_strength', 0)
        professional_activity = vsa_summary.get('professional_activity_count', 0)
        
        if strength > 0.7 and professional_activity > 3:
            return 'high'
        elif strength > 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_signal_strength(self, market_phase: str, vpa_signal: str, 
                                 price_direction: str, vsa_summary: Dict[str, Any]) -> float:
        """计算信号强度"""
        base_strength = vsa_summary.get('latest_signal_strength', 0.5)
        
        # 信号一致性加成
        consistency_bonus = 0.0
        if (vpa_signal == 'bullish' and price_direction == 'up') or \
           (vpa_signal == 'bearish' and price_direction == 'down'):
            consistency_bonus = 0.2
        
        # 市场阶段加成
        phase_bonus = 0.0
        if market_phase in ['markup', 'markdown']:
            phase_bonus = 0.1
        
        return min(base_strength + consistency_bonus + phase_bonus, 1.0)
    
    def _calculate_consensus_score(self, signals: List[TimeframeSignal]) -> float:
        """计算多时间框架共识得分"""
        if not signals:
            return 0.0
        
        total_weight = 0.0
        weighted_agreement = 0.0
        
        # 以最重要的信号为基准
        primary_signals = sorted(signals, key=lambda x: self.timeframe_config[x.timeframe]['weight'], reverse=True)
        if not primary_signals:
            return 0.0
            
        reference = primary_signals[0]
        
        for signal in signals:
            weight = self.timeframe_config[signal.timeframe]['weight']
            total_weight += weight
            
            # 计算与参考信号的一致性
            agreement = 0.0
            
            if signal.market_phase == reference.market_phase:
                agreement += self.signal_weights['market_phase']
            if signal.vpa_signal == reference.vpa_signal:
                agreement += self.signal_weights['vpa_signal']
            if signal.price_direction == reference.price_direction:
                agreement += self.signal_weights['price_direction']
                
            weighted_agreement += agreement * weight
        
        return weighted_agreement / total_weight if total_weight > 0 else 0.0
    
    def _identify_conflicts(self, signals: List[TimeframeSignal]) -> List[Dict[str, Any]]:
        """识别时间框架间的冲突"""
        conflicts = []
        
        # 按重要性排序
        sorted_signals = sorted(signals, 
                              key=lambda x: self.timeframe_config[x.timeframe]['weight'], 
                              reverse=True)
        
        for i, signal1 in enumerate(sorted_signals):
            for signal2 in sorted_signals[i+1:]:
                conflict_details = {}
                
                # 检查各维度冲突
                if signal1.market_phase != signal2.market_phase:
                    conflict_details['market_phase'] = {
                        'higher_tf': f"{signal1.timeframe}: {signal1.market_phase}",
                        'lower_tf': f"{signal2.timeframe}: {signal2.market_phase}"
                    }
                
                if signal1.vpa_signal != signal2.vpa_signal:
                    conflict_details['vpa_signal'] = {
                        'higher_tf': f"{signal1.timeframe}: {signal1.vpa_signal}",
                        'lower_tf': f"{signal2.timeframe}: {signal2.vpa_signal}"
                    }
                
                if signal1.price_direction != signal2.price_direction:
                    conflict_details['price_direction'] = {
                        'higher_tf': f"{signal1.timeframe}: {signal1.price_direction}",
                        'lower_tf': f"{signal2.timeframe}: {signal2.price_direction}"
                    }
                
                if conflict_details:
                    conflicts.append({
                        'timeframes': [signal1.timeframe, signal2.timeframe],
                        'conflicts': conflict_details,
                        'severity': len(conflict_details) / 3.0  # 标准化严重度
                    })
        
        return conflicts
    
    def _determine_primary_signal(self, signals: List[TimeframeSignal]) -> Optional[TimeframeSignal]:
        """确定主要信号 (权重最高的)"""
        if not signals:
            return None
            
        return max(signals, 
                  key=lambda x: self.timeframe_config[x.timeframe]['weight'] * x.signal_strength)
    
    def _analyze_context_bias(self, signals: List[TimeframeSignal]) -> str:
        """分析长周期背景偏向"""
        context_signals = [s for s in signals if s.importance == TimeframeImportance.CONTEXT]
        
        if not context_signals:
            # 如果没有背景信号，使用主要框架
            primary_signals = [s for s in signals if s.importance == TimeframeImportance.PRIMARY]
            if primary_signals:
                context_signals = primary_signals
            else:
                return 'neutral'
        
        # 统计背景偏向
        bullish_count = sum(1 for s in context_signals if s.vpa_signal == 'bullish')
        bearish_count = sum(1 for s in context_signals if s.vpa_signal == 'bearish')
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _generate_recommendation(self, signals: List[TimeframeSignal], 
                               consensus_score: float, conflicts: List[Dict[str, Any]],
                               context_bias: str) -> str:
        """生成交易建议"""
        if consensus_score > 0.8:
            primary_signal = self._determine_primary_signal(signals)
            if primary_signal:
                if primary_signal.vpa_signal == 'bullish' and context_bias != 'bearish':
                    return 'STRONG_BUY'
                elif primary_signal.vpa_signal == 'bearish' and context_bias != 'bullish':
                    return 'STRONG_SELL'
        
        if consensus_score > 0.6:
            primary_signal = self._determine_primary_signal(signals)
            if primary_signal:
                if primary_signal.vpa_signal == 'bullish':
                    return 'BUY'
                elif primary_signal.vpa_signal == 'bearish':
                    return 'SELL'
        
        if len(conflicts) > 2:
            return 'WAIT'
        
        return 'NEUTRAL'
    
    def _assess_confidence(self, consensus_score: float, conflicts: List[Dict[str, Any]]) -> str:
        """评估整体置信度"""
        if consensus_score > 0.8 and len(conflicts) < 2:
            return 'HIGH'
        elif consensus_score > 0.6 and len(conflicts) < 3:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def format_analysis_report(self, analysis: MultiTimeframeAnalysis) -> str:
        """格式化多时间框架分析报告"""
        report = []
        
        report.append("=" * 80)
        report.append("🕐 多时间框架VPA分析报告")
        report.append("=" * 80)
        
        # 总体评估
        report.append(f"📊 共识得分: {analysis.consensus_score:.2f}/1.00")
        report.append(f"🎯 背景偏向: {analysis.context_bias.upper()}")
        report.append(f"💡 推荐操作: {analysis.recommended_action}")
        report.append(f"🔒 置信水平: {analysis.confidence_level}")
        report.append("")
        
        # 各时间框架信号
        report.append("📈 各时间框架信号:")
        for signal in sorted(analysis.signals, 
                           key=lambda x: self.timeframe_config[x.timeframe]['weight'], 
                           reverse=True):
            config = self.timeframe_config[signal.timeframe]
            report.append(f"  {signal.timeframe:>4} | {config['description']:<12} | "
                        f"阶段:{signal.market_phase:<12} | 信号:{signal.vpa_signal:<8} | "
                        f"方向:{signal.price_direction:<8} | 强度:{signal.signal_strength:.2f}")
        
        # 冲突分析
        if analysis.conflicts:
            report.append("")
            report.append("⚠️ 检测到的时间框架冲突:")
            for i, conflict in enumerate(analysis.conflicts, 1):
                report.append(f"  冲突{i}: {' vs '.join(conflict['timeframes'])} "
                            f"(严重度:{conflict['severity']:.2f})")
                for dimension, details in conflict['conflicts'].items():
                    report.append(f"    {dimension}: {details['higher_tf']} vs {details['lower_tf']}")
        
        report.append("=" * 80)
        
        return "\n".join(report)