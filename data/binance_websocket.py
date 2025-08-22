#!/usr/bin/env python3
"""
币安WebSocket实时数据客户端
基于Anna Coulling VSA理论的实时多时间框架数据流

核心功能：
1. 实时Kline数据流监听 (5m, 15m, 30m, 1h, 4h, 1d)
2. K线完成事件精确检测
3. 连接管理和自动重连
4. 多时间框架数据流同步处理
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import traceback

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """WebSocket连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"

@dataclass
class KlineData:
    """K线数据结构"""
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    is_closed: bool  # K线是否已完成
    trade_count: int = 0
    
    @classmethod
    def from_binance_data(cls, data: Dict[str, Any]) -> 'KlineData':
        """从币安WebSocket数据创建KlineData"""
        k = data['k']
        return cls(
            symbol=k['s'],
            timeframe=k['i'],
            open_time=datetime.fromtimestamp(k['t'] / 1000, timezone.utc),
            close_time=datetime.fromtimestamp(k['T'] / 1000, timezone.utc),
            open_price=float(k['o']),
            high_price=float(k['h']),
            low_price=float(k['l']),
            close_price=float(k['c']),
            volume=float(k['v']),
            is_closed=k['x'],  # 关键：K线是否完成
            trade_count=k['n']
        )

@dataclass
class StreamConfig:
    """数据流配置"""
    timeframes: List[str] = field(default_factory=lambda: ['5m', '15m', '30m', '1h', '4h', '1d'])
    symbol: str = 'ETHUSDT'
    base_url: str = 'wss://stream.binance.com:9443/ws/'
    
    def get_stream_names(self) -> List[str]:
        """获取数据流名称列表"""
        return [f"{self.symbol.lower()}@kline_{tf}" for tf in self.timeframes]
    
    def get_combined_stream_url(self) -> str:
        """获取组合数据流URL"""
        streams = '/'.join(self.get_stream_names())
        return f"{self.base_url}stream?streams={streams}"

class BinanceWebSocketClient:
    """
    币安WebSocket实时数据客户端
    
    专为VPA多时间框架分析设计的高性能WebSocket客户端
    """
    
    def __init__(self, config: Optional[StreamConfig] = None):
        """初始化WebSocket客户端"""
        self.config = config or StreamConfig()
        self.connection_state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # 回调函数
        self.kline_callbacks: Dict[str, List[Callable]] = {}
        self.connection_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # 连接管理
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5.0  # 秒
        self.ping_interval = 20  # 币安2025年更新：20秒ping间隔
        self.pong_timeout = 60   # 币安2025年更新：1分钟pong超时
        
        # 统计信息
        self.stats = {
            'messages_received': 0,
            'klines_processed': 0,
            'reconnect_count': 0,
            'last_message_time': None,
            'connection_start_time': None
        }
        
        logger.info(f"🚀 币安WebSocket客户端初始化")
        logger.info(f"📊 监控时间框架: {', '.join(self.config.timeframes)}")
        logger.info(f"💱 监控交易对: {self.config.symbol}")
    
    def add_kline_callback(self, timeframe: str, callback: Callable[[KlineData], None]):
        """添加K线数据回调函数"""
        if timeframe not in self.kline_callbacks:
            self.kline_callbacks[timeframe] = []
        self.kline_callbacks[timeframe].append(callback)
        logger.info(f"📋 添加K线回调: {timeframe}")
    
    def add_connection_callback(self, callback: Callable[[ConnectionState], None]):
        """添加连接状态回调函数"""
        self.connection_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
    
    async def connect(self):
        """连接到币安WebSocket"""
        if self.connection_state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            logger.warning("WebSocket已连接或正在连接中")
            return
        
        try:
            self._set_connection_state(ConnectionState.CONNECTING)
            url = self.config.get_combined_stream_url()
            
            logger.info(f"🔗 连接币安WebSocket: {url}")
            
            # 建立WebSocket连接
            try:
                self.websocket = await websockets.connect(
                    url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.pong_timeout,
                    close_timeout=10,
                    max_size=2**20,  # 1MB max message size
                    compression=None  # 禁用压缩以减少延迟
                )
            except Exception as conn_error:
                # 如果直连失败，可能是网络问题
                logger.warning(f"⚠️ 直连失败: {conn_error}")
                if "socks" in str(conn_error).lower():
                    logger.info("💡 提示: 如果在特殊网络环境，可能需要配置代理")
                raise
            
            self._set_connection_state(ConnectionState.CONNECTED)
            self.reconnect_attempts = 0
            self.stats['connection_start_time'] = datetime.now()
            
            logger.info("✅ WebSocket连接成功建立")
            
            # 开始监听消息
            await self._listen_messages()
            
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            self._set_connection_state(ConnectionState.DISCONNECTED)
            self._trigger_error_callbacks(e)
            
            # 自动重连
            if self.reconnect_attempts < self.max_reconnect_attempts:
                await self._reconnect()
            else:
                logger.error("🚫 达到最大重连次数，停止重连")
    
    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("🔌 断开WebSocket连接...")
        self._set_connection_state(ConnectionState.CLOSED)
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        logger.info("✅ WebSocket连接已断开")
    
    async def _listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"⚠️ WebSocket连接关闭: {e}")
            if self.connection_state != ConnectionState.CLOSED:
                await self._reconnect()
                
        except Exception as e:
            logger.error(f"❌ 消息监听错误: {e}")
            logger.error(traceback.format_exc())
            self._trigger_error_callbacks(e)
            if self.connection_state != ConnectionState.CLOSED:
                await self._reconnect()
    
    async def _handle_message(self, message: str):
        """处理WebSocket消息"""
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            data = json.loads(message)
            
            # 处理Kline数据
            if 'stream' in data and 'data' in data:
                stream_name = data['stream']
                stream_data = data['data']
                
                if '@kline_' in stream_name and stream_data.get('e') == 'kline':
                    await self._handle_kline_data(stream_data)
            
        except json.JSONDecodeError:
            logger.error(f"❌ JSON解析失败: {message[:100]}...")
        except Exception as e:
            logger.error(f"❌ 消息处理错误: {e}")
            logger.error(traceback.format_exc())
    
    async def _handle_kline_data(self, data: Dict[str, Any]):
        """处理K线数据"""
        try:
            kline = KlineData.from_binance_data(data)
            
            # 只处理已完成的K线 (关键：VSA分析需要完整K线)
            if kline.is_closed:
                self.stats['klines_processed'] += 1
                
                logger.info(f"📊 K线完成: {kline.timeframe} | "
                          f"价格: {kline.close_price:.2f} | "
                          f"成交量: {kline.volume:.0f} | "
                          f"时间: {kline.close_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 触发对应时间框架的回调
                if kline.timeframe in self.kline_callbacks:
                    for callback in self.kline_callbacks[kline.timeframe]:
                        try:
                            # 异步调用回调函数
                            if asyncio.iscoroutinefunction(callback):
                                await callback(kline)
                            else:
                                callback(kline)
                        except Exception as e:
                            logger.error(f"❌ K线回调执行错误: {e}")
            
        except Exception as e:
            logger.error(f"❌ K线数据处理错误: {e}")
            logger.error(traceback.format_exc())
    
    async def _reconnect(self):
        """自动重连"""
        if self.connection_state == ConnectionState.CLOSED:
            return
            
        self.reconnect_attempts += 1
        self.stats['reconnect_count'] += 1
        self._set_connection_state(ConnectionState.RECONNECTING)
        
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60)  # 指数退避，最大60秒
        
        logger.info(f"🔄 第{self.reconnect_attempts}次重连尝试 (等待{delay}秒)...")
        await asyncio.sleep(delay)
        
        await self.connect()
    
    def _set_connection_state(self, state: ConnectionState):
        """设置连接状态并触发回调"""
        if self.connection_state != state:
            old_state = self.connection_state
            self.connection_state = state
            
            logger.info(f"🔄 连接状态变更: {old_state.value} -> {state.value}")
            
            # 触发连接状态回调
            for callback in self.connection_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # 异步回调需要创建任务
                        asyncio.create_task(callback(state))
                    else:
                        callback(state)
                except Exception as e:
                    logger.error(f"❌ 连接状态回调错误: {e}")
    
    def _trigger_error_callbacks(self, error: Exception):
        """触发错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"❌ 错误回调执行错误: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        stats = self.stats.copy()
        stats['connection_state'] = self.connection_state.value
        stats['reconnect_attempts'] = self.reconnect_attempts
        
        if stats['connection_start_time']:
            stats['uptime_seconds'] = (datetime.now() - stats['connection_start_time']).total_seconds()
        
        return stats
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection_state == ConnectionState.CONNECTED
    
    async def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """等待连接建立"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_connected():
                return True
            await asyncio.sleep(0.1)
        return False

# 使用示例和测试功能
async def example_kline_handler(kline: KlineData):
    """K线数据处理示例"""
    print(f"🎯 收到{kline.timeframe}完成K线: "
          f"价格{kline.close_price:.2f}, "
          f"成交量{kline.volume:.0f}, "
          f"时间{kline.close_time}")

def example_connection_handler(state: ConnectionState):
    """连接状态处理示例"""
    print(f"🔗 连接状态: {state.value}")

def example_error_handler(error: Exception):
    """错误处理示例"""
    print(f"❌ WebSocket错误: {error}")

async def test_websocket_client():
    """测试WebSocket客户端"""
    print("🧪 开始测试币安WebSocket客户端...")
    
    # 创建客户端
    config = StreamConfig(
        timeframes=['1m', '5m', '1h'],  # 测试用较短时间框架
        symbol='ETHUSDT'
    )
    
    client = BinanceWebSocketClient(config)
    
    # 添加回调函数
    for tf in config.timeframes:
        client.add_kline_callback(tf, example_kline_handler)
    
    client.add_connection_callback(example_connection_handler)
    client.add_error_callback(example_error_handler)
    
    try:
        # 连接并运行
        await client.connect()
        
        # 运行10分钟用于测试
        await asyncio.sleep(600)
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断测试")
    finally:
        await client.disconnect()
        
        # 显示统计信息
        stats = client.get_stats()
        print(f"\n📊 测试统计:")
        print(f"   消息接收: {stats['messages_received']}")
        print(f"   K线处理: {stats['klines_processed']}")
        print(f"   重连次数: {stats['reconnect_count']}")
        if 'uptime_seconds' in stats:
            print(f"   运行时间: {stats['uptime_seconds']:.1f}秒")

if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    asyncio.run(test_websocket_client())