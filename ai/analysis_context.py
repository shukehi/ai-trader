#!/usr/bin/env python3
"""
分析上下文管理器 - 专业级多周期分析结果整合和上下文管理
提供高级的分析结果整合、历史记录管理和决策支持功能
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from threading import Lock

logger = logging.getLogger(__name__)

class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = "critical"    # 关键信息
    HIGH = "high"           # 高优先级
    NORMAL = "normal"       # 普通
    LOW = "low"            # 低优先级

class SignalStrength(Enum):
    """信号强度"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"
    CONFLICTING = "conflicting"

@dataclass
class ContextEvent:
    """上下文事件"""
    timestamp: datetime
    event_type: str
    description: str
    priority: ContextPriority
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'description': self.description,
            'priority': self.priority.value,
            'metadata': self.metadata
        }

@dataclass
class TimeframeAnalysisContext:
    """单时间框架分析上下文 - Al Brooks专用"""
    timeframe: str
    quality_score: float
    signal_strength: SignalStrength
    key_insights: List[str]
    risk_factors: List[str]
    volume_analysis: Dict[str, Any]
    timestamp: datetime
    
    def get_weight(self) -> float:
        """获取时间框架权重"""
        timeframe_weights = {
            '1m': 0.1, '5m': 0.3, '15m': 0.5, '30m': 0.7,
            '1h': 1.0, '4h': 1.2, '1d': 1.5, '1w': 2.0
        }
        return timeframe_weights.get(self.timeframe, 1.0)

@dataclass
class MultiTimeframeContext:
    """多时间框架分析上下文"""
    symbol: str
    analysis_timestamp: datetime
    primary_timeframe: str
    timeframe_contexts: Dict[str, TimeframeAnalysisContext]
    overall_signal: SignalStrength
    consistency_score: float
    confidence_level: float
    major_confluence_zones: List[Dict[str, Any]]
    risk_warnings: List[str]
    trading_recommendations: List[str]
    
    def get_dominant_signal(self) -> Tuple[SignalStrength, float]:
        """获取主导信号和置信度"""
        if not self.timeframe_contexts:
            return SignalStrength.NEUTRAL, 0.0
            
        weighted_signals = {}
        total_weight = 0
        
        for tf, context in self.timeframe_contexts.items():
            weight = context.get_weight()
            signal = context.signal_strength
            
            if signal not in weighted_signals:
                weighted_signals[signal] = 0
            weighted_signals[signal] += weight
            total_weight += weight
        
        if total_weight == 0:
            return SignalStrength.NEUTRAL, 0.0
            
        # 计算权重最高的信号
        dominant_signal = max(weighted_signals.items(), key=lambda x: x[1])
        confidence = dominant_signal[1] / total_weight
        
        return dominant_signal[0], confidence

class AnalysisHistoryManager:
    """分析历史管理器"""
    
    def __init__(self, db_path: str = "logs/analysis_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    timeframes TEXT NOT NULL,
                    overall_signal TEXT,
                    consistency_score REAL,
                    confidence_level REAL,
                    analysis_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    priority TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON analysis_history(symbol, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_symbol ON context_events(symbol, timestamp)")
    
    def save_analysis_context(self, context: MultiTimeframeContext):
        """保存分析上下文"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    timeframes = list(context.timeframe_contexts.keys())
                    analysis_data = json.dumps({
                        'timeframe_contexts': {
                            tf: {
                                'timeframe': ctx.timeframe,
                                'quality_score': ctx.quality_score,
                                'signal_strength': ctx.signal_strength.value,
                                'key_insights': ctx.key_insights,
                                'risk_factors': ctx.risk_factors,
                                'volume_analysis': ctx.volume_analysis
                            }
                            for tf, ctx in context.timeframe_contexts.items()
                        },
                        'major_confluence_zones': context.major_confluence_zones,
                        'risk_warnings': context.risk_warnings,
                        'trading_recommendations': context.trading_recommendations
                    }, ensure_ascii=False)
                    
                    conn.execute("""
                        INSERT INTO analysis_history 
                        (symbol, timestamp, timeframes, overall_signal, consistency_score, confidence_level, analysis_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context.symbol,
                        context.analysis_timestamp.isoformat(),
                        json.dumps(timeframes),
                        context.overall_signal.value,
                        context.consistency_score,
                        context.confidence_level,
                        analysis_data
                    ))
                    
            except Exception as e:
                logger.error(f"❌ 保存分析上下文失败: {e}")
    
    def get_recent_analysis(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的分析记录"""
        since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM analysis_history 
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (symbol, since_time))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_context_event(self, symbol: str, event: ContextEvent):
        """保存上下文事件"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO context_events 
                        (symbol, timestamp, event_type, description, priority, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        event.timestamp.isoformat(),
                        event.event_type,
                        event.description,
                        event.priority.value,
                        json.dumps(event.metadata, ensure_ascii=False)
                    ))
                    
            except Exception as e:
                logger.error(f"❌ 保存上下文事件失败: {e}")

class ConfluenceAnalyzer:
    """汇聚分析器 - 识别多时间框架的关键汇聚区域"""
    
    def __init__(self):
        self.confluence_threshold = 0.02  # 2%价格距离内视为汇聚
    
    def find_confluence_zones(self, timeframe_contexts: Dict[str, TimeframeAnalysisContext]) -> List[Dict[str, Any]]:
        """查找汇聚区域"""
        confluence_zones = []
        
        # Al Brooks分析专注于价格行为模式而非传统支撑阻力
        all_levels = []
        
        if len(all_levels) < 2:
            return confluence_zones
            
        # 按价格排序
        all_levels.sort(key=lambda x: x['price'])
        
        # 查找汇聚区域
        i = 0
        while i < len(all_levels):
            current_group = [all_levels[i]]
            j = i + 1
            
            # 找到价格相近的所有水平
            while j < len(all_levels):
                price_diff = abs(all_levels[j]['price'] - current_group[0]['price']) / current_group[0]['price']
                if price_diff <= self.confluence_threshold:
                    current_group.append(all_levels[j])
                    j += 1
                else:
                    break
            
            # 如果有多个时间框架的汇聚，创建汇聚区域
            if len(current_group) >= 2:
                confluence_zones.append(self._create_confluence_zone(current_group))
            
            i = j if j > i + 1 else i + 1
        
        # 按强度排序
        confluence_zones.sort(key=lambda x: x['strength'], reverse=True)
        return confluence_zones[:5]  # 返回前5个最强的汇聚区域
    
    def _create_confluence_zone(self, levels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建汇聚区域"""
        avg_price = sum(level['price'] for level in levels) / len(levels)
        total_weight = sum(level['weight'] for level in levels)
        avg_quality = sum(level['quality'] for level in levels) / len(levels)
        
        timeframes_involved = list(set(level['timeframe'] for level in levels))
        level_types = list(set(level['type'] for level in levels))
        
        # 计算强度 (基于权重、时间框架数量和质量)
        strength = total_weight * len(timeframes_involved) * (avg_quality / 100)
        
        return {
            'price': avg_price,
            'strength': strength,
            'timeframes': timeframes_involved,
            'level_types': level_types,
            'total_weight': total_weight,
            'average_quality': avg_quality,
            'levels_count': len(levels)
        }

class AnalysisContext:
    """
    分析上下文管理器
    
    核心功能：
    1. 多时间框架分析结果整合
    2. 历史分析记录管理
    3. 汇聚区域识别和分析
    4. 上下文事件跟踪
    5. 智能决策支持
    """
    
    def __init__(self, db_path: str = "logs/analysis_history.db"):
        self.history_manager = AnalysisHistoryManager(db_path)
        self.confluence_analyzer = ConfluenceAnalyzer()
        logger.info("✅ 分析上下文管理器初始化完成")
    
    def create_multi_timeframe_context(self,
                                     symbol: str,
                                     primary_timeframe: str,
                                     analysis_results: Dict[str, Dict[str, Any]]) -> MultiTimeframeContext:
        """
        创建多时间框架分析上下文
        
        Args:
            symbol: 交易对符号
            primary_timeframe: 主要时间框架
            analysis_results: 各时间框架的分析结果
            
        Returns:
            多时间框架分析上下文
        """
        timestamp = datetime.now()
        timeframe_contexts = {}
        
        # 处理各时间框架分析结果
        for timeframe, result in analysis_results.items():
            if not result.get('success', False):
                continue
                
            # 从分析结果中提取结构化信息
            context = self._extract_timeframe_context(timeframe, result, timestamp)
            timeframe_contexts[timeframe] = context
        
        # 计算整体指标
        overall_signal = self._calculate_overall_signal(timeframe_contexts)
        consistency_score = self._calculate_consistency_score(analysis_results)
        confidence_level = self._calculate_confidence_level(timeframe_contexts, consistency_score)
        
        # 查找汇聚区域
        confluence_zones = self.confluence_analyzer.find_confluence_zones(timeframe_contexts)
        
        # 生成风险警告和交易建议
        risk_warnings = self._generate_risk_warnings(timeframe_contexts, consistency_score)
        trading_recommendations = self._generate_trading_recommendations(
            timeframe_contexts, confluence_zones, overall_signal
        )
        
        context = MultiTimeframeContext(
            symbol=symbol,
            analysis_timestamp=timestamp,
            primary_timeframe=primary_timeframe,
            timeframe_contexts=timeframe_contexts,
            overall_signal=overall_signal,
            consistency_score=consistency_score,
            confidence_level=confidence_level,
            major_confluence_zones=confluence_zones,
            risk_warnings=risk_warnings,
            trading_recommendations=trading_recommendations
        )
        
        # 保存到历史记录
        self.history_manager.save_analysis_context(context)
        
        logger.info(f"📊 创建多时间框架上下文 - {symbol}, 一致性: {consistency_score:.1f}, 信心: {confidence_level:.1f}")
        return context
    
    def _extract_timeframe_context(self, timeframe: str, result: Dict[str, Any], timestamp: datetime) -> TimeframeAnalysisContext:
        """从分析结果提取时间框架上下文"""
        
        # 从AI分析文本中提取结构化信息（简化版）
        analysis_text = result.get('analysis_text', result.get('analysis', ''))
        
        # 简单的关键词提取（实际应用中可以使用更复杂的NLP方法）
        key_insights = self._extract_insights(analysis_text)
        risk_factors = self._extract_risk_factors(analysis_text)
        
        # 生成信号强度
        quality_score = result.get('quality_score', 50)
        signal_strength = self._determine_signal_strength(analysis_text, quality_score)
        
        return TimeframeAnalysisContext(
            timeframe=timeframe,
            quality_score=quality_score,
            signal_strength=signal_strength,
            key_insights=key_insights,
            risk_factors=risk_factors,
            volume_analysis={'pattern': 'normal'},  # 简化
            timestamp=timestamp
        )
    
    def _extract_insights(self, text: str) -> List[str]:
        """提取关键洞察"""
        insights = []
        
        # 简单的关键词匹配
        insight_keywords = [
            ('突破', '价格突破关键水平'),
            ('支撑', '发现重要支撑位'),
            ('阻力', '识别关键阻力位'),
            ('成交量', '成交量模式分析'),
            ('趋势', '趋势方向分析')
        ]
        
        for keyword, insight in insight_keywords:
            if keyword in text:
                insights.append(insight)
        
        return insights[:3]  # 最多3个关键洞察
    
    def _extract_risk_factors(self, text: str) -> List[str]:
        """提取风险因素"""
        risks = []
        
        risk_keywords = [
            ('波动', '高波动性风险'),
            ('流动性', '流动性风险'),
            ('背离', '技术指标背离风险'),
            ('不确定', '市场不确定性风险')
        ]
        
        for keyword, risk in risk_keywords:
            if keyword in text:
                risks.append(risk)
        
        return risks[:2]  # 最多2个风险因素
    
    
    def _determine_signal_strength(self, text: str, quality_score: float) -> SignalStrength:
        """确定信号强度"""
        if quality_score < 40:
            return SignalStrength.WEAK
        elif quality_score < 60:
            return SignalStrength.MODERATE
        elif quality_score < 80:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG
    
    def _calculate_overall_signal(self, contexts: Dict[str, TimeframeAnalysisContext]) -> SignalStrength:
        """计算整体信号强度"""
        if not contexts:
            return SignalStrength.NEUTRAL
            
        # 基于质量评分加权平均
        weighted_sum = 0
        total_weight = 0
        
        for context in contexts.values():
            weight = context.get_weight()
            signal_value = self._signal_to_value(context.signal_strength)
            weighted_sum += signal_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return SignalStrength.NEUTRAL
            
        avg_signal = weighted_sum / total_weight
        return self._value_to_signal(avg_signal)
    
    def _signal_to_value(self, signal: SignalStrength) -> float:
        """信号强度转数值"""
        mapping = {
            SignalStrength.VERY_STRONG: 5.0,
            SignalStrength.STRONG: 4.0,
            SignalStrength.MODERATE: 3.0,
            SignalStrength.WEAK: 2.0,
            SignalStrength.NEUTRAL: 1.0,
            SignalStrength.CONFLICTING: 0.5
        }
        return mapping.get(signal, 1.0)
    
    def _value_to_signal(self, value: float) -> SignalStrength:
        """数值转信号强度"""
        if value >= 4.5:
            return SignalStrength.VERY_STRONG
        elif value >= 3.5:
            return SignalStrength.STRONG
        elif value >= 2.5:
            return SignalStrength.MODERATE
        elif value >= 1.5:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NEUTRAL
    
    def _calculate_consistency_score(self, results: Dict[str, Dict[str, Any]]) -> float:
        """计算一致性评分"""
        successful_results = [r for r in results.values() if r.get('success', False)]
        
        if len(successful_results) < 2:
            return 100.0 if successful_results else 0.0
            
        quality_scores = [r.get('quality_score', 50) for r in successful_results]
        
        # 基于质量评分标准差计算一致性
        import statistics
        if len(quality_scores) > 1:
            std_dev = statistics.stdev(quality_scores)
            consistency = max(0, 100 - (std_dev * 1.5))
        else:
            consistency = 100.0
            
        return min(100.0, consistency)
    
    def _calculate_confidence_level(self, contexts: Dict[str, TimeframeAnalysisContext], consistency_score: float) -> float:
        """计算信心水平"""
        if not contexts:
            return 0.0
            
        avg_quality = sum(ctx.quality_score for ctx in contexts.values()) / len(contexts)
        timeframe_count = len(contexts)
        
        # 信心水平 = (平均质量 * 0.4) + (一致性 * 0.4) + (时间框架数量奖励 * 0.2)
        timeframe_bonus = min(20, timeframe_count * 5)  # 每个时间框架+5分，最多20分
        confidence = (avg_quality * 0.4) + (consistency_score * 0.4) + timeframe_bonus
        
        return min(100.0, confidence)
    
    def _generate_risk_warnings(self, contexts: Dict[str, TimeframeAnalysisContext], consistency_score: float) -> List[str]:
        """生成风险警告"""
        warnings = []
        
        if consistency_score < 50:
            warnings.append("多时间框架信号严重冲突，建议等待确认")
            
        low_quality_count = sum(1 for ctx in contexts.values() if ctx.quality_score < 60)
        if low_quality_count > 0:
            warnings.append(f"{low_quality_count}个时间框架分析质量较低")
            
        # 检查是否有风险因素
        all_risks = []
        for ctx in contexts.values():
            all_risks.extend(ctx.risk_factors)
        
        if all_risks:
            warnings.append("识别到潜在风险因素，请谨慎交易")
            
        return warnings
    
    def _generate_trading_recommendations(self,
                                        contexts: Dict[str, TimeframeAnalysisContext],
                                        confluence_zones: List[Dict[str, Any]],
                                        overall_signal: SignalStrength) -> List[str]:
        """生成交易建议"""
        recommendations = []
        
        if overall_signal == SignalStrength.VERY_STRONG:
            recommendations.append("强烈信号确认，可考虑加大仓位")
        elif overall_signal == SignalStrength.STRONG:
            recommendations.append("信号较强，建议标准仓位交易")
        elif overall_signal == SignalStrength.MODERATE:
            recommendations.append("信号一般，建议小仓位试探")
        else:
            recommendations.append("信号较弱，建议观望或降低仓位")
            
        if confluence_zones:
            recommendations.append(f"发现{len(confluence_zones)}个关键汇聚区域，可作为重要参考水平")
            
        return recommendations
    
    def get_analysis_history(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取分析历史"""
        return self.history_manager.get_recent_analysis(symbol, hours)
    
    def add_context_event(self, symbol: str, event_type: str, description: str, 
                         priority: ContextPriority = ContextPriority.NORMAL,
                         metadata: Dict[str, Any] = None):
        """添加上下文事件"""
        event = ContextEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.history_manager.save_context_event(symbol, event)
        logger.info(f"📝 添加上下文事件 - {symbol}: {description}")