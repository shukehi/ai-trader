#!/usr/bin/env python3
"""
实时分析引擎 - 基于WebSocket的智能多时间周期实时分析系统
整合WebSocket数据流、多时间框架分析器和动态分析频率控制
"""

import time
from typing import Dict, List, Any, Optional, Callable
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import queue
import threading

from .multi_timeframe_analyzer import MultiTimeframeAnalyzer, AnalysisScenario, MultiTimeframeResult
from .analysis_context import AnalysisContext, ContextPriority
from data.binance_websocket import BinanceWebSocketClient, StreamConfig, KlineData, ConnectionState
from data import BinanceFetcher

logger = logging.getLogger(__name__)

class AnalysisFrequency(Enum):
    """分析频率级别"""
    REALTIME = "realtime"      # 实时分析（每个K线完成）
    HIGH = "high"              # 高频分析（5分钟）
    NORMAL = "normal"          # 标准频率（15分钟）
    LOW = "low"               # 低频分析（1小时）
    MANUAL = "manual"         # 手动触发

class MarketCondition(Enum):
    """市场状况"""
    VOLATILE = "volatile"      # 高波动
    TRENDING = "trending"      # 趋势行情
    RANGING = "ranging"        # 震荡行情
    QUIET = "quiet"           # 平静市场

@dataclass
class RealtimeConfig:
    """实时分析配置"""
    symbol: str = "ETHUSDT"
    timeframes: List[str] = field(default_factory=lambda: ["5m", "15m", "1h", "4h"])
    base_frequency: AnalysisFrequency = AnalysisFrequency.NORMAL
    adaptive_frequency: bool = True
    model: str = "gpt5-chat"
    analysis_type: str = "complete"
    analysis_method: Optional[str] = None
    volatility_threshold: float = 0.02  # 2%波动率阈值
    volume_threshold: float = 2.0       # 成交量异常倍数
    max_analysis_per_hour: int = 20     # 每小时最大分析次数

@dataclass
class AnalysisEvent:
    """分析事件"""
    timestamp: datetime
    trigger_type: str           # 触发类型：kline_complete, volatility_spike, volume_surge, manual
    timeframe: str
    priority: int              # 优先级 1-10
    market_condition: MarketCondition
    kline_data: Optional[KlineData] = None

class FrequencyAdaptor:
    """动态频率适配器"""
    
    def __init__(self, config: RealtimeConfig):
        self.config = config
        self.analysis_count = 0
        self.hour_start = datetime.now().hour
        self.recent_analyses = []
        self._lock = Lock()
    
    def should_analyze(self, event: AnalysisEvent) -> bool:
        """判断是否应该执行分析"""
        with self._lock:
            current_hour = datetime.now().hour
            
            # 重置小时计数
            if current_hour != self.hour_start:
                self.analysis_count = 0
                self.hour_start = current_hour
                self.recent_analyses = []
            
            # 检查频率限制
            if self.analysis_count >= self.config.max_analysis_per_hour:
                logger.warning(f"⚠️ 已达到每小时最大分析次数限制: {self.config.max_analysis_per_hour}")
                return False
            
            # 基于配置的频率控制
            if not self.config.adaptive_frequency:
                return self._check_base_frequency(event)
            
            # 自适应频率控制
            return self._check_adaptive_frequency(event)
    
    def _check_base_frequency(self, event: AnalysisEvent) -> bool:
        """检查基础频率"""
        now = datetime.now()
        
        if self.config.base_frequency == AnalysisFrequency.REALTIME:
            return event.trigger_type == "kline_complete"
        elif self.config.base_frequency == AnalysisFrequency.HIGH:
            # 5分钟内最多一次分析
            return not any(
                (now - analysis_time).total_seconds() < 300 
                for analysis_time in self.recent_analyses
            )
        elif self.config.base_frequency == AnalysisFrequency.NORMAL:
            # 15分钟内最多一次分析
            return not any(
                (now - analysis_time).total_seconds() < 900 
                for analysis_time in self.recent_analyses
            )
        elif self.config.base_frequency == AnalysisFrequency.LOW:
            # 1小时内最多一次分析
            return not any(
                (now - analysis_time).total_seconds() < 3600 
                for analysis_time in self.recent_analyses
            )
        else:
            return False
    
    def _check_adaptive_frequency(self, event: AnalysisEvent) -> bool:
        """检查自适应频率"""
        
        # 高优先级事件优先处理
        if event.priority >= 8:
            logger.info(f"🔥 高优先级事件，立即分析: {event.trigger_type}")
            return True
        
        # 基于市场状况调整频率
        if event.market_condition == MarketCondition.VOLATILE:
            # 高波动期间，提高分析频率
            min_interval = 180  # 3分钟
        elif event.market_condition == MarketCondition.TRENDING:
            # 趋势期间，正常频率
            min_interval = 600  # 10分钟
        elif event.market_condition == MarketCondition.RANGING:
            # 震荡期间，降低频率
            min_interval = 900  # 15分钟
        else:  # QUIET
            # 平静期间，大幅降低频率
            min_interval = 1800  # 30分钟
        
        # 检查是否满足时间间隔
        now = datetime.now()
        return not any(
            (now - analysis_time).total_seconds() < min_interval 
            for analysis_time in self.recent_analyses
        )
    
    def record_analysis(self):
        """记录分析执行"""
        with self._lock:
            now = datetime.now()
            self.recent_analyses.append(now)
            self.analysis_count += 1
            
            # 保持最近24小时的记录
            cutoff = now - timedelta(hours=24)
            self.recent_analyses = [t for t in self.recent_analyses if t > cutoff]

class MarketConditionDetector:
    """市场状况检测器"""
    
    def __init__(self):
        self.price_history = []
        self.volume_history = []
        self.max_history = 100
        self._lock = Lock()
    
    def update_data(self, kline: KlineData):
        """更新市场数据"""
        with self._lock:
            self.price_history.append({
                'timestamp': kline.close_time,
                'price': kline.close_price,
                'volume': kline.volume
            })
            
            # 保持历史数据大小
            if len(self.price_history) > self.max_history:
                self.price_history.pop(0)
    
    def detect_condition(self, kline: KlineData) -> MarketCondition:
        """检测市场状况"""
        if len(self.price_history) < 10:
            return MarketCondition.QUIET
            
        with self._lock:
            recent_prices = [p['price'] for p in self.price_history[-20:]]
            recent_volumes = [p['volume'] for p in self.price_history[-20:]]
            
            # 计算价格波动率
            price_changes = [
                abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                for i in range(1, len(recent_prices))
            ]
            avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
            
            # 计算成交量比率
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            current_volume_ratio = kline.volume / avg_volume if avg_volume > 0 else 1
            
            # 趋势检测（简化版）
            if len(recent_prices) >= 10:
                trend_strength = self._calculate_trend_strength(recent_prices[-10:])
            else:
                trend_strength = 0
            
            # 状况判定逻辑
            if avg_volatility > 0.015 and current_volume_ratio > 1.5:  # 高波动 + 高成交量
                return MarketCondition.VOLATILE
            elif abs(trend_strength) > 0.7:  # 强趋势
                return MarketCondition.TRENDING
            elif avg_volatility > 0.005:  # 中等波动
                return MarketCondition.RANGING
            else:
                return MarketCondition.QUIET
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """计算趋势强度 (-1到1, 负数下跌，正数上涨)"""
        if len(prices) < 3:
            return 0
            
        # 简化的趋势强度计算
        start_price = prices[0]
        end_price = prices[-1]
        price_change = (end_price - start_price) / start_price
        
        # 计算价格一致性（减少噪音影响）
        direction_consistency = 0
        for i in range(1, len(prices)):
            if price_change > 0 and prices[i] > prices[i-1]:
                direction_consistency += 1
            elif price_change < 0 and prices[i] < prices[i-1]:
                direction_consistency += 1
        
        consistency_ratio = direction_consistency / (len(prices) - 1)
        
        # 结合价格变化幅度和方向一致性
        trend_strength = price_change * consistency_ratio
        
        # 限制在-1到1之间
        return max(-1, min(1, trend_strength * 10))

class RealtimeAnalysisEngine:
    """
    实时分析引擎
    
    核心功能：
    1. WebSocket实时数据监听和处理
    2. 智能分析频率控制和事件触发
    3. 多时间框架实时分析执行
    4. 分析结果缓存和历史管理
    5. 市场状况检测和自适应调整
    """
    
    def __init__(self, config: Optional[RealtimeConfig] = None, api_key: Optional[str] = None):
        """初始化实时分析引擎"""
        self.config = config or RealtimeConfig()
        
        # 核心组件
        self.multi_analyzer = MultiTimeframeAnalyzer(api_key)
        self.analysis_context = AnalysisContext()
        self.fetcher = BinanceFetcher()
        
        # WebSocket客户端
        ws_config = StreamConfig(
            symbol=self.config.symbol,
            timeframes=self.config.timeframes
        )
        self.ws_client = BinanceWebSocketClient(ws_config)
        
        # 辅助组件
        self.frequency_adaptor = FrequencyAdaptor(self.config)
        self.condition_detector = MarketConditionDetector()
        
        # 运行时状态
        self.is_running = False
        self.analysis_queue = queue.Queue()
        self.current_analysis_task = None
        
        # 结果缓存
        self.latest_results = {}
        self.results_lock = Lock()
        
        # 事件回调
        self.analysis_callbacks: List[Callable[[MultiTimeframeResult], None]] = []
        self.error_callbacks: List[Callable[[Exception], None]] = []
        
        # 统计信息
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'start_time': None,
            'last_analysis_time': None
        }
        
        # 设置WebSocket回调
        self._setup_websocket_callbacks()
        
        logger.info("✅ 实时分析引擎初始化完成")
        logger.info(f"📊 监控配置: {self.config.symbol}, {self.config.timeframes}")
        logger.info(f"🔄 基础频率: {self.config.base_frequency.value}, 自适应: {self.config.adaptive_frequency}")
    
    def _setup_websocket_callbacks(self):
        """设置WebSocket回调函数"""
        
        async def on_kline_complete(kline: KlineData):
            """K线完成回调"""
            try:
                # 更新市场状况检测器
                self.condition_detector.update_data(kline)
                market_condition = self.condition_detector.detect_condition(kline)
                
                # 创建分析事件
                event = AnalysisEvent(
                    timestamp=kline.close_time,
                    trigger_type="kline_complete",
                    timeframe=kline.timeframe,
                    priority=self._calculate_event_priority(kline, market_condition),
                    market_condition=market_condition,
                    kline_data=kline
                )
                
                # 检查是否需要分析
                if self.frequency_adaptor.should_analyze(event):
                    logger.info(f"📊 触发分析事件: {kline.symbol} {kline.timeframe} - {market_condition.value}")
                    self.analysis_queue.put(event)
                    
            except Exception as e:
                logger.error(f"❌ K线回调处理失败: {e}")
                self._notify_error_callbacks(e)
        
        def on_connection_state_change(state: ConnectionState):
            """连接状态变化回调"""
            logger.info(f"🔗 WebSocket连接状态: {state.value}")
            
            if state == ConnectionState.CONNECTED:
                self.analysis_context.add_context_event(
                    symbol=self.config.symbol,
                    event_type="websocket_connected",
                    description="WebSocket连接已建立",
                    priority=ContextPriority.NORMAL
                )
            elif state == ConnectionState.DISCONNECTED:
                self.analysis_context.add_context_event(
                    symbol=self.config.symbol,
                    event_type="websocket_disconnected", 
                    description="WebSocket连接已断开",
                    priority=ContextPriority.HIGH
                )
        
        # 为所有监控的时间框架添加回调
        for timeframe in self.config.timeframes:
            self.ws_client.add_kline_callback(timeframe, on_kline_complete)
        
        self.ws_client.add_connection_callback(on_connection_state_change)
    
    def _calculate_event_priority(self, kline: KlineData, market_condition: MarketCondition) -> int:
        """计算事件优先级 (1-10)"""
        priority = 5  # 基础优先级
        
        # 基于市场状况调整优先级
        if market_condition == MarketCondition.VOLATILE:
            priority += 3
        elif market_condition == MarketCondition.TRENDING:
            priority += 1
        elif market_condition == MarketCondition.QUIET:
            priority -= 2
        
        # 基于时间框架调整优先级（更长的时间框架优先级更高）
        timeframe_priorities = {
            '1m': 1, '5m': 2, '15m': 3, '30m': 4,
            '1h': 5, '4h': 7, '1d': 9, '1w': 10
        }
        tf_priority = timeframe_priorities.get(kline.timeframe, 5)
        priority = max(1, min(10, priority + (tf_priority - 5)))
        
        return priority
    
    async def start_realtime_analysis(self):
        """启动实时分析"""
        if self.is_running:
            logger.warning("实时分析已在运行中")
            return
            
        try:
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            logger.info("🚀 启动实时分析引擎")
            
            # 启动分析处理线程
            analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
            analysis_thread.start()
            
            # 连接WebSocket
            await self.ws_client.connect()
            
            # 启动WebSocket监听循环
            await self.ws_client.listen()
            
        except Exception as e:
            logger.error(f"❌ 启动实时分析失败: {e}")
            self.is_running = False
            self._notify_error_callbacks(e)
            raise
    
    def _analysis_worker(self):
        """分析任务工作线程"""
        logger.info("📊 分析工作线程已启动")
        
        while self.is_running:
            try:
                # 获取分析事件（阻塞等待）
                try:
                    event = self.analysis_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 执行分析
                self._execute_analysis(event)
                self.analysis_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ 分析工作线程错误: {e}")
                self._notify_error_callbacks(e)
    
    def _execute_analysis(self, event: AnalysisEvent):
        """执行分析任务"""
        start_time = time.time()
        
        try:
            logger.info(f"🔍 执行分析: {self.config.symbol} - 触发类型: {event.trigger_type}")
            
            # 记录分析执行
            self.frequency_adaptor.record_analysis()
            
            # 执行多时间框架分析
            result = self.multi_analyzer.analyze_multi_timeframe(
                symbol=self.config.symbol,
                model=self.config.model,
                analysis_type=self.config.analysis_type,
                analysis_method=self.config.analysis_method,
                scenario=self._determine_analysis_scenario(event)
            )
            
            # 更新统计信息
            self.stats['total_analyses'] += 1
            self.stats['last_analysis_time'] = datetime.now()
            
            if result.overall_signal != "ERROR":
                self.stats['successful_analyses'] += 1
                
                # 缓存最新结果
                with self.results_lock:
                    self.latest_results[self.config.symbol] = result
                
                # 添加上下文事件
                self.analysis_context.add_context_event(
                    symbol=self.config.symbol,
                    event_type="analysis_completed",
                    description=f"实时分析完成 - {result.overall_signal}",
                    priority=ContextPriority.NORMAL,
                    metadata={
                        'consistency_score': result.consistency_score,
                        'confidence_level': result.confidence_level,
                        'execution_time': result.execution_time,
                        'trigger_type': event.trigger_type
                    }
                )
                
                # 通知回调函数
                self._notify_analysis_callbacks(result)
                
                logger.info(f"✅ 实时分析完成 - 信号: {result.overall_signal}, 耗时: {time.time() - start_time:.2f}秒")
            else:
                self.stats['failed_analyses'] += 1
                logger.error(f"❌ 分析失败 - 错误: {result.risk_warnings}")
                
        except Exception as e:
            self.stats['failed_analyses'] += 1
            logger.error(f"❌ 执行分析时发生错误: {e}")
            self._notify_error_callbacks(e)
    
    def _determine_analysis_scenario(self, event: AnalysisEvent) -> AnalysisScenario:
        """根据事件确定分析场景"""
        if event.market_condition == MarketCondition.VOLATILE:
            return AnalysisScenario.INTRADAY_TRADING
        elif event.market_condition == MarketCondition.TRENDING:
            return AnalysisScenario.TREND_ANALYSIS
        elif event.market_condition == MarketCondition.RANGING:
            return AnalysisScenario.SWING_TRADING
        else:
            return AnalysisScenario.QUICK_CHECK
    
    def trigger_manual_analysis(self) -> bool:
        """手动触发分析"""
        try:
            event = AnalysisEvent(
                timestamp=datetime.now(),
                trigger_type="manual",
                timeframe=self.config.timeframes[0],  # 使用第一个时间框架
                priority=10,  # 最高优先级
                market_condition=MarketCondition.QUIET  # 默认市场状况
            )
            
            self.analysis_queue.put(event)
            logger.info("🖱️ 手动分析已触发")
            return True
            
        except Exception as e:
            logger.error(f"❌ 手动触发分析失败: {e}")
            return False
    
    def get_latest_result(self) -> Optional[MultiTimeframeResult]:
        """获取最新分析结果"""
        with self.results_lock:
            return self.latest_results.get(self.config.symbol)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = dict(self.stats)
        if stats['start_time']:
            stats['running_time'] = (datetime.now() - stats['start_time']).total_seconds()
        stats['success_rate'] = (
            stats['successful_analyses'] / stats['total_analyses'] 
            if stats['total_analyses'] > 0 else 0
        )
        stats['is_running'] = self.is_running
        stats['queue_size'] = self.analysis_queue.qsize()
        return stats
    
    def add_analysis_callback(self, callback: Callable[[MultiTimeframeResult], None]):
        """添加分析结果回调"""
        self.analysis_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]):
        """添加错误回调"""
        self.error_callbacks.append(callback)
    
    def _notify_analysis_callbacks(self, result: MultiTimeframeResult):
        """通知分析回调"""
        for callback in self.analysis_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"❌ 分析回调执行失败: {e}")
    
    def _notify_error_callbacks(self, error: Exception):
        """通知错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"❌ 错误回调执行失败: {e}")
    
    async def stop(self):
        """停止实时分析"""
        if not self.is_running:
            return
            
        logger.info("🛑 正在停止实时分析引擎")
        
        self.is_running = False
        
        # 停止WebSocket连接
        if self.ws_client:
            await self.ws_client.close()
        
        # 等待队列清空
        self.analysis_queue.join()
        
        logger.info("✅ 实时分析引擎已停止")
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'is_running') and self.is_running:
            logger.warning("⚠️ 实时分析引擎未正常关闭")