#!/usr/bin/env python3
"""
多时间周期AI分析器 - 专业级多周期分析核心组件
基于现有AI直接分析架构，实现智能多时间框架综合分析
"""

import time
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
from threading import Lock

from .raw_data_analyzer import RawDataAnalyzer
from data import BinanceFetcher
from formatters import DataFormatter

logger = logging.getLogger(__name__)

class AnalysisScenario(Enum):
    """分析场景类型"""
    INTRADAY_TRADING = "intraday"      # 日内交易
    TREND_ANALYSIS = "trend"           # 趋势分析  
    QUICK_CHECK = "quick"              # 快速检查
    SWING_TRADING = "swing"            # 波段交易
    POSITION_SIZING = "position"       # 仓位管理

class VolatilityLevel(Enum):
    """波动率级别"""
    LOW = "low"          # 低波动
    NORMAL = "normal"    # 正常波动
    HIGH = "high"        # 高波动
    EXTREME = "extreme"  # 极端波动

@dataclass
class TimeframeConfig:
    """时间框架配置"""
    primary: str              # 主要分析周期
    secondary: List[str]      # 辅助分析周期
    update_frequency: int     # 更新频率（秒）
    data_limit: int          # 数据量限制
    weight: float = 1.0      # 权重系数

@dataclass
class MultiTimeframeResult:
    """多时间周期分析结果"""
    scenario: AnalysisScenario
    primary_analysis: Dict[str, Any]
    secondary_analyses: Dict[str, Dict[str, Any]]
    consistency_score: float
    overall_signal: str
    risk_warnings: List[str]
    confidence_level: float
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)

class ScenarioDetector:
    """智能场景识别器"""
    
    def __init__(self):
        self.volatility_threshold = {
            'high': 2.0,      # ATR倍数
            'extreme': 3.5
        }
        self.volume_threshold = 3.0  # 成交量倍数
        
    def detect_scenario(self, df: pd.DataFrame, user_intent: str = None) -> AnalysisScenario:
        """
        智能识别分析场景
        
        Args:
            df: 原始OHLCV数据
            user_intent: 用户意图（可选）
            
        Returns:
            识别出的分析场景
        """
        if user_intent:
            intent_mapping = {
                'trade': AnalysisScenario.INTRADAY_TRADING,
                'trend': AnalysisScenario.TREND_ANALYSIS,
                'swing': AnalysisScenario.SWING_TRADING,
                'position': AnalysisScenario.POSITION_SIZING,
                'quick': AnalysisScenario.QUICK_CHECK
            }
            if user_intent.lower() in intent_mapping:
                return intent_mapping[user_intent.lower()]
        
        # 自动场景识别
        volatility = self._calculate_volatility(df)
        volume_surge = self._detect_volume_surge(df)
        price_action = self._analyze_price_action(df)
        
        logger.info(f"场景识别 - 波动率: {volatility.value}, 成交量异常: {volume_surge}, 价格行为: {price_action}")
        
        # 场景识别逻辑
        if volatility in [VolatilityLevel.HIGH, VolatilityLevel.EXTREME] and volume_surge:
            return AnalysisScenario.INTRADAY_TRADING
        elif price_action in ['breakout', 'trend_change']:
            return AnalysisScenario.TREND_ANALYSIS
        elif price_action == 'range_bound':
            return AnalysisScenario.SWING_TRADING
        else:
            return AnalysisScenario.QUICK_CHECK
    
    def _calculate_volatility(self, df: pd.DataFrame) -> VolatilityLevel:
        """计算波动率级别"""
        if len(df) < 20:
            return VolatilityLevel.NORMAL
            
        # 计算ATR（简化版）
        high_low = (df['high'] - df['low']).rolling(14).mean()
        close_open = abs(df['close'] - df['open']).rolling(14).mean()
        current_atr = (high_low + close_open) / 2
        
        # 历史ATR基准
        historical_atr = current_atr.rolling(50).mean()
        atr_ratio = current_atr.iloc[-1] / historical_atr.iloc[-1] if len(historical_atr) > 0 else 1.0
        
        if atr_ratio > self.volatility_threshold['extreme']:
            return VolatilityLevel.EXTREME
        elif atr_ratio > self.volatility_threshold['high']:
            return VolatilityLevel.HIGH
        elif atr_ratio < 0.7:
            return VolatilityLevel.LOW
        else:
            return VolatilityLevel.NORMAL
    
    def _detect_volume_surge(self, df: pd.DataFrame) -> bool:
        """检测成交量异常"""
        if len(df) < 20:
            return False
            
        avg_volume = df['volume'].rolling(20).mean()
        current_volume = df['volume'].iloc[-1]
        
        return current_volume > (avg_volume.iloc[-1] * self.volume_threshold)
    
    def _analyze_price_action(self, df: pd.DataFrame) -> str:
        """分析价格行为模式"""
        if len(df) < 10:
            return 'insufficient_data'
            
        recent_data = df.tail(10)
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        
        # 简化的价格行为识别
        if abs(price_change) > 0.05:  # 5%以上变化
            return 'breakout'
        elif abs(price_change) > 0.02:  # 2-5%变化
            return 'trend_change'
        else:
            return 'range_bound'

class TimeframeSelector:
    """智能时间框架选择器"""
    
    # 预定义场景时间框架配置
    SCENARIO_CONFIGS = {
        AnalysisScenario.INTRADAY_TRADING: TimeframeConfig(
            primary="15m",
            secondary=["5m", "1h", "4h"],
            update_frequency=300,  # 5分钟
            data_limit=50
        ),
        AnalysisScenario.TREND_ANALYSIS: TimeframeConfig(
            primary="4h",
            secondary=["1h", "1d", "1w"],
            update_frequency=3600,  # 1小时
            data_limit=100
        ),
        AnalysisScenario.SWING_TRADING: TimeframeConfig(
            primary="1h",
            secondary=["4h", "1d"],
            update_frequency=1800,  # 30分钟
            data_limit=75
        ),
        AnalysisScenario.POSITION_SIZING: TimeframeConfig(
            primary="1d",
            secondary=["4h", "1w"],
            update_frequency=7200,  # 2小时
            data_limit=50
        ),
        AnalysisScenario.QUICK_CHECK: TimeframeConfig(
            primary="1h",
            secondary=[],
            update_frequency=3600,  # 1小时
            data_limit=30
        )
    }
    
    def select_timeframes(self, scenario: AnalysisScenario, custom_timeframes: List[str] = None) -> TimeframeConfig:
        """
        选择最优时间框架配置
        
        Args:
            scenario: 分析场景
            custom_timeframes: 用户自定义时间框架
            
        Returns:
            时间框架配置
        """
        if custom_timeframes:
            # 使用自定义时间框架
            primary = custom_timeframes[0]
            secondary = custom_timeframes[1:] if len(custom_timeframes) > 1 else []
            return TimeframeConfig(
                primary=primary,
                secondary=secondary,
                update_frequency=self._get_update_frequency(primary),
                data_limit=50
            )
        
        # 使用预定义配置
        config = self.SCENARIO_CONFIGS.get(scenario, self.SCENARIO_CONFIGS[AnalysisScenario.QUICK_CHECK])
        logger.info(f"选择时间框架配置 - 场景: {scenario.value}, 主周期: {config.primary}, 辅助周期: {config.secondary}")
        return config
    
    def _get_update_frequency(self, timeframe: str) -> int:
        """根据时间框架获取更新频率"""
        timeframe_to_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
            '1w': 604800
        }
        return timeframe_to_seconds.get(timeframe, 3600)

class MultiTimeframeAnalyzer:
    """
    多时间周期AI分析器
    
    核心功能：
    1. 智能场景识别和时间框架选择
    2. 并行多周期数据获取和AI分析
    3. 分析结果一致性检查和整合
    4. 专业级风险评估和信号生成
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化多时间周期分析器"""
        self.raw_analyzer = RawDataAnalyzer(api_key)
        self.fetcher = BinanceFetcher()
        self.formatter = DataFormatter()
        
        self.scenario_detector = ScenarioDetector()
        self.timeframe_selector = TimeframeSelector()
        
        # 结果缓存
        self._cache = {}
        self._cache_lock = Lock()
        self._cache_expiry = 300  # 5分钟缓存
        
        logger.info("✅ 多时间周期AI分析器初始化完成")
    
    def analyze_multi_timeframe(self, 
                               symbol: str = "ETHUSDT",
                               model: str = "gemini-flash",
                               analysis_type: str = "complete",
                               analysis_method: Optional[str] = None,
                               scenario: Optional[AnalysisScenario] = None,
                               custom_timeframes: Optional[List[str]] = None,
                               user_intent: Optional[str] = None) -> MultiTimeframeResult:
        """
        执行多时间周期综合分析
        
        Args:
            symbol: 交易对符号
            model: AI模型
            analysis_type: 分析类型
            analysis_method: 分析方法
            scenario: 指定分析场景
            custom_timeframes: 自定义时间框架
            user_intent: 用户意图
            
        Returns:
            多时间周期分析结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始多时间周期分析 - {symbol}, 模型: {model}")
            
            # 1. 获取主要周期数据用于场景识别
            primary_timeframe = custom_timeframes[0] if custom_timeframes else "1h"
            primary_df = self._get_data_with_cache(symbol, primary_timeframe, 100)
            
            # 2. 智能场景识别
            if not scenario:
                scenario = self.scenario_detector.detect_scenario(primary_df, user_intent)
            logger.info(f"📊 识别分析场景: {scenario.value}")
            
            # 3. 智能时间框架选择
            timeframe_config = self.timeframe_selector.select_timeframes(scenario, custom_timeframes)
            
            # 4. 并行获取多周期数据和分析
            all_analyses = self._execute_parallel_analysis(
                symbol=symbol,
                timeframe_config=timeframe_config,
                model=model,
                analysis_type=analysis_type,
                analysis_method=analysis_method
            )
            
            # 5. 分析结果整合和一致性检查
            result = self._integrate_analyses(
                scenario=scenario,
                timeframe_config=timeframe_config,
                analyses=all_analyses,
                execution_time=time.time() - start_time
            )
            
            logger.info(f"✅ 多时间周期分析完成 - 耗时: {result.execution_time:.2f}秒, 一致性: {result.consistency_score:.1f}/100")
            return result
            
        except Exception as e:
            logger.error(f"❌ 多时间周期分析失败: {e}")
            # 返回错误结果
            return MultiTimeframeResult(
                scenario=scenario or AnalysisScenario.QUICK_CHECK,
                primary_analysis={'error': str(e), 'success': False},
                secondary_analyses={},
                consistency_score=0.0,
                overall_signal="ERROR",
                risk_warnings=[f"分析失败: {str(e)}"],
                confidence_level=0.0,
                execution_time=time.time() - start_time
            )
    
    def _get_data_with_cache(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """带缓存的数据获取"""
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                cached_data, cache_time = self._cache[cache_key]
                if time.time() - cache_time < self._cache_expiry:
                    return cached_data
        
        # 获取新数据
        symbol_for_api = symbol.replace('USDT', '/USDT') if '/' not in symbol else symbol
        df = self.fetcher.get_ohlcv(symbol_for_api, timeframe, limit)
        
        # 缓存数据
        with self._cache_lock:
            self._cache[cache_key] = (df, time.time())
        
        return df
    
    def _execute_parallel_analysis(self, 
                                  symbol: str,
                                  timeframe_config: TimeframeConfig,
                                  model: str,
                                  analysis_type: str,
                                  analysis_method: Optional[str]) -> Dict[str, Dict[str, Any]]:
        """并行执行多周期分析"""
        
        all_timeframes = [timeframe_config.primary] + timeframe_config.secondary
        analyses = {}
        
        def analyze_single_timeframe(timeframe: str) -> Tuple[str, Dict[str, Any]]:
            """分析单个时间框架"""
            try:
                df = self._get_data_with_cache(symbol, timeframe, timeframe_config.data_limit)
                
                result = self.raw_analyzer.analyze_raw_ohlcv(
                    df=df,
                    model=model,
                    analysis_type=analysis_type,
                    analysis_method=analysis_method
                )
                
                result['timeframe'] = timeframe
                result['data_points'] = len(df)
                return timeframe, result
                
            except Exception as e:
                logger.error(f"❌ 分析时间框架 {timeframe} 失败: {e}")
                return timeframe, {
                    'error': str(e),
                    'success': False,
                    'timeframe': timeframe
                }
        
        # 使用线程池并行分析
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_timeframe = {
                executor.submit(analyze_single_timeframe, tf): tf 
                for tf in all_timeframes
            }
            
            for future in concurrent.futures.as_completed(future_to_timeframe):
                timeframe, result = future.result()
                analyses[timeframe] = result
        
        return analyses
    
    def _integrate_analyses(self, 
                           scenario: AnalysisScenario,
                           timeframe_config: TimeframeConfig,
                           analyses: Dict[str, Dict[str, Any]],
                           execution_time: float) -> MultiTimeframeResult:
        """整合分析结果"""
        
        primary_analysis = analyses.get(timeframe_config.primary, {})
        secondary_analyses = {
            tf: analysis for tf, analysis in analyses.items() 
            if tf != timeframe_config.primary
        }
        
        # 计算一致性评分
        consistency_score = self._calculate_consistency_score(analyses)
        
        # 生成综合信号
        overall_signal = self._generate_overall_signal(analyses, consistency_score)
        
        # 识别风险警告
        risk_warnings = self._identify_risk_warnings(analyses, consistency_score)
        
        # 计算信心水平
        confidence_level = self._calculate_confidence_level(analyses, consistency_score)
        
        return MultiTimeframeResult(
            scenario=scenario,
            primary_analysis=primary_analysis,
            secondary_analyses=secondary_analyses,
            consistency_score=consistency_score,
            overall_signal=overall_signal,
            risk_warnings=risk_warnings,
            confidence_level=confidence_level,
            execution_time=execution_time
        )
    
    def _calculate_consistency_score(self, analyses: Dict[str, Dict[str, Any]]) -> float:
        """计算分析一致性评分"""
        if len(analyses) < 2:
            return 100.0
            
        successful_analyses = [a for a in analyses.values() if a.get('success', False)]
        if len(successful_analyses) < 2:
            return 0.0
        
        # 简化的一致性计算（基于质量评分相似度）
        quality_scores = [a.get('quality_score', 50) for a in successful_analyses if 'quality_score' in a]
        
        if len(quality_scores) < 2:
            return 70.0  # 默认中等一致性
            
        # 计算评分标准差，转换为一致性分数
        import statistics
        std_dev = statistics.stdev(quality_scores)
        consistency = max(0, 100 - (std_dev * 2))  # 标准差越小，一致性越高
        
        return min(100.0, consistency)
    
    def _generate_overall_signal(self, analyses: Dict[str, Dict[str, Any]], consistency_score: float) -> str:
        """生成综合交易信号"""
        successful_analyses = [a for a in analyses.values() if a.get('success', False)]
        
        if not successful_analyses:
            return "NO_SIGNAL"
            
        if consistency_score > 80:
            return "STRONG_SIGNAL" 
        elif consistency_score > 60:
            return "MODERATE_SIGNAL"
        elif consistency_score > 40:
            return "WEAK_SIGNAL"
        else:
            return "CONFLICTING_SIGNALS"
    
    def _identify_risk_warnings(self, analyses: Dict[str, Dict[str, Any]], consistency_score: float) -> List[str]:
        """识别风险警告"""
        warnings = []
        
        if consistency_score < 50:
            warnings.append("多时间框架信号严重冲突，建议谨慎交易")
            
        failed_count = sum(1 for a in analyses.values() if not a.get('success', False))
        if failed_count > 0:
            warnings.append(f"{failed_count}个时间框架分析失败")
            
        # 检查数据质量
        low_quality_count = sum(1 for a in analyses.values() 
                               if a.get('success', False) and a.get('quality_score', 100) < 60)
        if low_quality_count > 0:
            warnings.append(f"{low_quality_count}个时间框架分析质量较低")
            
        return warnings
    
    def _calculate_confidence_level(self, analyses: Dict[str, Dict[str, Any]], consistency_score: float) -> float:
        """计算整体信心水平"""
        successful_analyses = [a for a in analyses.values() if a.get('success', False)]
        
        if not successful_analyses:
            return 0.0
            
        # 基于成功率、一致性和质量评分计算信心水平
        success_rate = len(successful_analyses) / len(analyses)
        avg_quality = sum(a.get('quality_score', 50) for a in successful_analyses) / len(successful_analyses)
        
        confidence = (success_rate * 40 + consistency_score * 0.4 + avg_quality * 0.2)
        return min(100.0, confidence)
    
    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("🗑️ 缓存已清空")