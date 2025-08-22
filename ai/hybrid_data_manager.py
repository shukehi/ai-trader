#!/usr/bin/env python3
"""
混合数据管理器
结合WebSocket实时数据和REST API备用方案，确保系统稳定性

核心功能：
1. WebSocket优先，REST备用的数据获取策略
2. 数据完整性检查和自动切换
3. 连接健康监控和故障恢复
4. 数据缓存和同步机制
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import time

from data.binance_websocket import BinanceWebSocketClient, StreamConfig, KlineData, ConnectionState
from data.binance_fetcher import BinanceFetcher

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """数据源类型"""
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    CACHE = "cache"

class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"    # WebSocket实时数据，完整且及时
    GOOD = "good"             # REST API数据，完整但可能有延迟
    ACCEPTABLE = "acceptable"  # 缓存数据，可能不是最新的
    POOR = "poor"             # 数据不完整或过时

@dataclass
class DataHealth:
    """数据健康状况"""
    websocket_connected: bool
    last_websocket_data: Optional[datetime]
    rest_api_available: bool
    last_rest_api_data: Optional[datetime]
    data_quality: DataQuality
    active_source: DataSource
    
    def is_healthy(self) -> bool:
        """判断数据健康状况是否良好"""
        return self.data_quality in [DataQuality.EXCELLENT, DataQuality.GOOD]

@dataclass
class TimeframeDataCache:
    """时间框架数据缓存"""
    timeframe: str
    last_kline: Optional[KlineData] = None
    historical_data: Optional[pd.DataFrame] = None
    last_update: Optional[datetime] = None
    data_source: Optional[DataSource] = None
    
    def is_fresh(self, max_age_seconds: int = 300) -> bool:
        """检查缓存是否新鲜"""
        if not self.last_update:
            return False
        return (datetime.now() - self.last_update).total_seconds() < max_age_seconds
    
    def get_expected_next_kline_time(self) -> Optional[datetime]:
        """获取预期的下一个K线时间"""
        if not self.last_kline:
            return None
        
        # 计算时间框架的时间间隔
        intervals = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        
        interval = intervals.get(self.timeframe)
        if not interval:
            return None
            
        return self.last_kline.close_time + interval

class HybridDataManager:
    """
    混合数据管理器
    
    智能管理WebSocket和REST数据源，确保数据完整性和系统稳定性
    """
    
    def __init__(self, symbol: str = 'ETH/USDT', timeframes: List[str] = None):
        """初始化混合数据管理器"""
        self.symbol = symbol
        self.timeframes = timeframes or ['5m', '15m', '30m', '1h', '4h', '1d']
        
        # 数据源组件
        self.ws_client: Optional[BinanceWebSocketClient] = None
        self.rest_client = BinanceFetcher()
        
        # 数据缓存
        self.data_cache: Dict[str, TimeframeDataCache] = {
            tf: TimeframeDataCache(timeframe=tf) for tf in self.timeframes
        }
        
        # 健康监控
        self.data_health = DataHealth(
            websocket_connected=False,
            last_websocket_data=None,
            rest_api_available=True,
            last_rest_api_data=None,
            data_quality=DataQuality.POOR,
            active_source=DataSource.REST_API
        )
        
        # 配置参数
        self.config = {
            'websocket_timeout': 30,        # WebSocket数据超时时间(秒)
            'rest_fallback_delay': 5,       # REST备用延迟时间(秒)
            'health_check_interval': 60,    # 健康检查间隔(秒)
            'cache_max_age': 300,           # 缓存最大存活时间(秒)
            'max_websocket_retries': 3,     # WebSocket最大重试次数
            'data_validation_enabled': True # 启用数据验证
        }
        
        # 运行状态
        self.is_running = False
        self.websocket_retries = 0
        
        # 回调函数
        self.data_callbacks: Dict[str, List[Callable]] = {}
        self.health_change_callbacks: List[Callable] = []
        self.source_switch_callbacks: List[Callable] = []
        
        # 统计信息
        self.stats = {
            'websocket_data_count': 0,
            'rest_api_calls': 0,
            'source_switches': 0,
            'data_quality_downgrades': 0,
            'health_check_count': 0,
            'start_time': None
        }
        
        logger.info(f"🔄 混合数据管理器初始化完成")
        logger.info(f"💱 交易对: {self.symbol}")
        logger.info(f"📊 时间框架: {', '.join(self.timeframes)}")
    
    def add_data_callback(self, timeframe: str, callback: Callable[[KlineData, DataSource], None]):
        """添加数据回调函数"""
        if timeframe not in self.data_callbacks:
            self.data_callbacks[timeframe] = []
        self.data_callbacks[timeframe].append(callback)
    
    def add_health_change_callback(self, callback: Callable[[DataHealth], None]):
        """添加健康状态变化回调"""
        self.health_change_callbacks.append(callback)
    
    def add_source_switch_callback(self, callback: Callable[[DataSource, DataSource], None]):
        """添加数据源切换回调"""
        self.source_switch_callbacks.append(callback)
    
    async def start(self):
        """启动混合数据管理器"""
        logger.info("🚀 启动混合数据管理器...")
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        try:
            # 启动WebSocket连接
            await self._start_websocket_connection()
            
            # 启动健康监控任务
            health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            
            # 启动数据质量监控任务  
            quality_monitor_task = asyncio.create_task(self._data_quality_monitor_loop())
            
            # 等待任务完成
            await asyncio.gather(health_monitor_task, quality_monitor_task)
            
        except Exception as e:
            logger.error(f"❌ 混合数据管理器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止混合数据管理器"""
        logger.info("⏹️ 停止混合数据管理器...")
        
        self.is_running = False
        
        if self.ws_client:
            await self.ws_client.disconnect()
            self.ws_client = None
        
        logger.info("✅ 混合数据管理器已停止")
    
    async def _start_websocket_connection(self):
        """启动WebSocket连接"""
        try:
            # 创建WebSocket配置
            ws_config = StreamConfig(
                timeframes=self.timeframes,
                symbol=self.symbol.replace('/', '')  # ETHUSDT格式
            )
            
            self.ws_client = BinanceWebSocketClient(ws_config)
            
            # 设置WebSocket回调
            for tf in self.timeframes:
                self.ws_client.add_kline_callback(tf, self._on_websocket_kline)
            
            self.ws_client.add_connection_callback(self._on_websocket_connection_change)
            self.ws_client.add_error_callback(self._on_websocket_error)
            
            # 连接WebSocket
            await self.ws_client.connect()
            
            # 等待连接建立
            if await self.ws_client.wait_for_connection(timeout=30):
                logger.info("✅ WebSocket连接已建立")
                self._update_data_health(websocket_connected=True, active_source=DataSource.WEBSOCKET)
            else:
                logger.warning("⚠️ WebSocket连接超时，切换到REST模式")
                await self._switch_to_rest_mode()
                
        except Exception as e:
            logger.error(f"❌ WebSocket启动失败: {e}")
            await self._switch_to_rest_mode()
    
    async def _on_websocket_kline(self, kline: KlineData):
        """WebSocket K线数据处理"""
        if not kline.is_closed:
            return  # 只处理已完成的K线
        
        try:
            self.stats['websocket_data_count'] += 1
            self.data_health.last_websocket_data = datetime.now()
            
            # 更新缓存
            cache = self.data_cache[kline.timeframe]
            cache.last_kline = kline
            cache.last_update = datetime.now()
            cache.data_source = DataSource.WEBSOCKET
            
            # 触发回调
            if kline.timeframe in self.data_callbacks:
                for callback in self.data_callbacks[kline.timeframe]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(kline, DataSource.WEBSOCKET)
                        else:
                            callback(kline, DataSource.WEBSOCKET)
                    except Exception as e:
                        logger.error(f"❌ 数据回调执行错误: {e}")
            
            # 更新数据质量
            if self.data_health.active_source != DataSource.WEBSOCKET:
                await self._switch_data_source(DataSource.WEBSOCKET)
                
            self._update_data_quality(DataQuality.EXCELLENT)
            
        except Exception as e:
            logger.error(f"❌ WebSocket数据处理错误: {e}")
    
    async def _on_websocket_connection_change(self, state: ConnectionState):
        """WebSocket连接状态变化处理"""
        connected = (state == ConnectionState.CONNECTED)
        self.data_health.websocket_connected = connected
        
        if connected:
            logger.info("🔗 WebSocket重新连接成功")
            self.websocket_retries = 0
            if self.data_health.active_source == DataSource.REST_API:
                await self._switch_data_source(DataSource.WEBSOCKET)
        else:
            logger.warning("⚠️ WebSocket连接断开")
            if self.data_health.active_source == DataSource.WEBSOCKET:
                await self._switch_to_rest_mode()
    
    def _on_websocket_error(self, error: Exception):
        """WebSocket错误处理"""
        logger.error(f"❌ WebSocket错误: {error}")
        self.websocket_retries += 1
        
        if self.websocket_retries >= self.config['max_websocket_retries']:
            logger.error("🚫 WebSocket重试次数超限，切换到REST模式")
            asyncio.create_task(self._switch_to_rest_mode())
    
    async def _switch_to_rest_mode(self):
        """切换到REST API模式"""
        logger.info("🔄 切换到REST API数据模式")
        await self._switch_data_source(DataSource.REST_API)
        
        # 启动REST数据拉取任务
        for tf in self.timeframes:
            asyncio.create_task(self._rest_data_fetch_loop(tf))
    
    async def _switch_data_source(self, new_source: DataSource):
        """切换数据源"""
        old_source = self.data_health.active_source
        
        if old_source != new_source:
            self.stats['source_switches'] += 1
            self.data_health.active_source = new_source
            
            logger.info(f"🔄 数据源切换: {old_source.value} → {new_source.value}")
            
            # 触发数据源切换回调
            for callback in self.source_switch_callbacks:
                try:
                    callback(old_source, new_source)
                except Exception as e:
                    logger.error(f"❌ 数据源切换回调错误: {e}")
            
            # 更新数据质量
            if new_source == DataSource.WEBSOCKET:
                self._update_data_quality(DataQuality.EXCELLENT)
            elif new_source == DataSource.REST_API:
                self._update_data_quality(DataQuality.GOOD)
            else:
                self._update_data_quality(DataQuality.ACCEPTABLE)
    
    async def _rest_data_fetch_loop(self, timeframe: str):
        """REST API数据拉取循环"""
        logger.info(f"🔄 启动{timeframe} REST数据拉取")
        
        # 计算拉取间隔
        intervals = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400
        }
        interval = intervals.get(timeframe, 3600)
        
        while self.is_running and self.data_health.active_source == DataSource.REST_API:
            try:
                # 获取最新数据
                df = self.rest_client.get_ohlcv(
                    symbol=self.symbol,
                    timeframe=timeframe,
                    limit=2  # 只获取最新的2根K线
                )
                
                if not df.empty:
                    # 转换为KlineData格式
                    latest_row = df.iloc[-1]
                    kline = KlineData(
                        symbol=self.symbol.replace('/', ''),
                        timeframe=timeframe,
                        open_time=latest_row['datetime'] if 'datetime' in df.columns else datetime.now(),
                        close_time=latest_row['datetime'] if 'datetime' in df.columns else datetime.now(),
                        open_price=float(latest_row['open']),
                        high_price=float(latest_row['high']),
                        low_price=float(latest_row['low']),
                        close_price=float(latest_row['close']),
                        volume=float(latest_row['volume']),
                        is_closed=True  # REST数据都是已完成的
                    )
                    
                    # 检查是否是新数据
                    cache = self.data_cache[timeframe]
                    if not cache.last_kline or cache.last_kline.close_time != kline.close_time:
                        self.stats['rest_api_calls'] += 1
                        self.data_health.last_rest_api_data = datetime.now()
                        
                        # 更新缓存
                        cache.last_kline = kline
                        cache.last_update = datetime.now()
                        cache.data_source = DataSource.REST_API
                        
                        # 触发回调
                        if timeframe in self.data_callbacks:
                            for callback in self.data_callbacks[timeframe]:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(kline, DataSource.REST_API)
                                    else:
                                        callback(kline, DataSource.REST_API)
                                except Exception as e:
                                    logger.error(f"❌ REST数据回调错误: {e}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"❌ {timeframe} REST数据获取错误: {e}")
                self.data_health.rest_api_available = False
                await asyncio.sleep(60)  # 错误时等待更长时间
    
    async def _health_monitor_loop(self):
        """健康监控循环"""
        logger.info("🏥 启动数据健康监控")
        
        while self.is_running:
            try:
                self.stats['health_check_count'] += 1
                await self._check_data_health()
                await asyncio.sleep(self.config['health_check_interval'])
            except Exception as e:
                logger.error(f"❌ 健康监控错误: {e}")
                await asyncio.sleep(30)
    
    async def _check_data_health(self):
        """检查数据健康状况"""
        current_time = datetime.now()
        
        # 检查WebSocket数据新鲜度
        ws_healthy = True
        if self.data_health.last_websocket_data:
            ws_age = (current_time - self.data_health.last_websocket_data).total_seconds()
            ws_healthy = ws_age < self.config['websocket_timeout']
        else:
            ws_healthy = False
        
        # 检查REST API可用性
        rest_healthy = True
        if self.data_health.last_rest_api_data:
            rest_age = (current_time - self.data_health.last_rest_api_data).total_seconds()
            rest_healthy = rest_age < 300  # 5分钟内有REST数据
        
        # 更新健康状态
        old_quality = self.data_health.data_quality
        
        if self.data_health.websocket_connected and ws_healthy:
            self._update_data_quality(DataQuality.EXCELLENT)
        elif rest_healthy:
            self._update_data_quality(DataQuality.GOOD)
        else:
            self._update_data_quality(DataQuality.POOR)
        
        # 检查是否需要切换数据源
        if (self.data_health.active_source == DataSource.WEBSOCKET and 
            (not self.data_health.websocket_connected or not ws_healthy)):
            logger.warning("⚠️ WebSocket数据质量下降，切换到REST模式")
            await self._switch_to_rest_mode()
        elif (self.data_health.active_source == DataSource.REST_API and 
              self.data_health.websocket_connected and ws_healthy):
            logger.info("✅ WebSocket恢复，切换回WebSocket模式")
            await self._switch_data_source(DataSource.WEBSOCKET)
        
        # 触发健康状态变化回调
        if old_quality != self.data_health.data_quality:
            for callback in self.health_change_callbacks:
                try:
                    callback(self.data_health)
                except Exception as e:
                    logger.error(f"❌ 健康状态回调错误: {e}")
    
    async def _data_quality_monitor_loop(self):
        """数据质量监控循环"""
        while self.is_running:
            try:
                await self._validate_data_quality()
                await asyncio.sleep(30)  # 每30秒检查一次数据质量
            except Exception as e:
                logger.error(f"❌ 数据质量监控错误: {e}")
                await asyncio.sleep(60)
    
    async def _validate_data_quality(self):
        """验证数据质量"""
        if not self.config['data_validation_enabled']:
            return
        
        current_time = datetime.now()
        quality_issues = []
        
        for tf, cache in self.data_cache.items():
            if not cache.last_kline:
                quality_issues.append(f"{tf}: 无数据")
                continue
            
            # 检查数据新鲜度
            if cache.last_update:
                age = (current_time - cache.last_update).total_seconds()
                expected_interval = self._get_timeframe_seconds(tf)
                
                if age > expected_interval * 2:  # 超过预期间隔的2倍
                    quality_issues.append(f"{tf}: 数据过期 ({age/60:.1f}分钟)")
            
            # 检查数据合理性
            if cache.last_kline:
                kline = cache.last_kline
                if kline.high_price < kline.low_price:
                    quality_issues.append(f"{tf}: 价格数据异常")
                if kline.volume < 0:
                    quality_issues.append(f"{tf}: 成交量异常")
        
        if quality_issues:
            logger.warning(f"⚠️ 数据质量问题: {'; '.join(quality_issues)}")
            self.stats['data_quality_downgrades'] += 1
    
    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """获取时间框架对应的秒数"""
        intervals = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800, 
            '1h': 3600, '4h': 14400, '1d': 86400
        }
        return intervals.get(timeframe, 3600)
    
    def _update_data_health(self, **kwargs):
        """更新数据健康状态"""
        for key, value in kwargs.items():
            if hasattr(self.data_health, key):
                setattr(self.data_health, key, value)
    
    def _update_data_quality(self, quality: DataQuality):
        """更新数据质量"""
        if self.data_health.data_quality != quality:
            logger.info(f"📊 数据质量更新: {self.data_health.data_quality.value} → {quality.value}")
            self.data_health.data_quality = quality
    
    def get_latest_kline(self, timeframe: str) -> Optional[KlineData]:
        """获取最新K线数据"""
        cache = self.data_cache.get(timeframe)
        return cache.last_kline if cache else None
    
    def get_health_status(self) -> DataHealth:
        """获取健康状态"""
        return self.data_health
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['is_running'] = self.is_running
        stats['data_quality'] = self.data_health.data_quality.value
        stats['active_source'] = self.data_health.active_source.value
        stats['websocket_connected'] = self.data_health.websocket_connected
        stats['websocket_retries'] = self.websocket_retries
        
        if self.stats['start_time']:
            stats['uptime_seconds'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return stats