import ccxt
import pandas as pd
from datetime import datetime, timezone
import time
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceFetcher:
    """
    Binance永续合约数据获取器
    使用ccxt库获取ETH永续合约OHLCV数据
    """
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'sandbox': False,
            'rateLimit': 1200,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # 使用永续合约 (swap, 不是 future)
            }
        })
        
        # 添加连接验证
        try:
            # 测试连接
            self.exchange.load_markets()
            logger.info("✅ Binance 永续合约 API 连接成功")
        except Exception as e:
            logger.warning(f"⚠️ 初始连接测试失败: {e}, 将在使用时重试")
        
    def get_ohlcv(self, symbol: str = 'ETH/USDT', timeframe: str = '1h', 
                  limit: int = 50, since: Optional[int] = None) -> pd.DataFrame:
        """
        获取OHLCV数据
        
        Args:
            symbol: 交易对符号，如 'ETH/USDT'
            timeframe: 时间周期，如 '1m', '5m', '1h', '4h', '1d'
            limit: 获取数据条数
            since: 开始时间戳(毫秒)，None表示获取最新数据
            
        Returns:
            pandas.DataFrame: 包含OHLCV数据的DataFrame
        """
        # 重试机制
        max_retries = 3
        
        for retry_count in range(max_retries):
            try:
                logger.info(f"获取 {symbol} {timeframe} 数据，数量: {limit}")
                
                # 确保市场数据已加载
                if not hasattr(self.exchange, 'markets') or not self.exchange.markets:
                    logger.info("正在加载市场数据...")
                    self.exchange.load_markets()
                
                # 获取原始OHLCV数据
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                    since=since
                    )
                
                # 转换为DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 转换时间戳
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df['datetime'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # 确保数值类型
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                df[numeric_columns] = df[numeric_columns].astype(float)
                
                logger.info(f"成功获取 {len(df)} 条数据")
                logger.info(f"时间范围: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")
                
                return df
                
            except Exception as e:
                if retry_count < max_retries - 1:
                    wait_time = (retry_count + 1) * 2  # 指数退避
                    logger.warning(f"获取数据失败 (重试 {retry_count + 1}/{max_retries}): {e}")
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"获取数据最终失败: {e}")
                    raise
        
        # 理论上不应该到达这里，但为了类型检查器
        raise RuntimeError("获取数据失败：超出最大重试次数")
    
    def get_latest_price(self, symbol: str = 'ETH/USDT') -> Dict[str, Any]:
        """获取最新价格信息"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume_24h': ticker['baseVolume'],
                'change_24h': ticker['change'],
                'change_percent_24h': ticker['percentage'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"获取最新价格失败: {e}")
            raise
    
    def get_funding_rate(self, symbol: str = 'ETH/USDT') -> Dict[str, Any]:
        """
        获取永续合约资金费率
        
        Args:
            symbol: 交易对符号
            
        Returns:
            包含资金费率信息的字典
        """
        try:
            logger.info(f"获取 {symbol} 资金费率...")
            
            # Binance 支持资金费率查询
            if hasattr(self.exchange, 'fetch_funding_rate'):
                funding = self.exchange.fetch_funding_rate(symbol)
                if isinstance(funding, dict):
                    logger.info(f"当前资金费率: {funding.get('fundingRate', 'N/A')}")
                    return dict(funding)  # Ensure it's a proper Dict[str, Any]
                elif funding:
                    # 处理非字典类型的数据
                    logger.info(f"当前资金费率: {funding}")
                    return {'funding_rate_data': str(funding)}
                else:
                    return {}
            else:
                logger.warning("当前交易所不支持资金费率查询")
                return {}
                
        except Exception as e:
            logger.error(f"获取资金费率失败: {e}")
            return {}
    
    def get_funding_rate_history(self, symbol: str = 'ETH/USDT', 
                                limit: int = 50) -> pd.DataFrame:
        """
        获取资金费率历史数据
        
        Args:
            symbol: 交易对符号
            limit: 获取数据条数
            
        Returns:
            包含历史资金费率的DataFrame
        """
        try:
            logger.info(f"获取 {symbol} 资金费率历史，数量: {limit}")
            
            if hasattr(self.exchange, 'fetch_funding_rate_history'):
                funding_history = self.exchange.fetch_funding_rate_history(symbol, limit=limit)
                
                # 转换为DataFrame
                df = pd.DataFrame(funding_history)
                if not df.empty:
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    df['datetime_str'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    
                    logger.info(f"成功获取 {len(df)} 条资金费率历史数据")
                    return df
                else:
                    logger.warning("未获取到资金费率历史数据")
                    return pd.DataFrame()
            else:
                logger.warning("当前交易所不支持资金费率历史查询")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取资金费率历史失败: {e}")
            return pd.DataFrame()
    
    def get_open_interest(self, symbol: str = 'ETH/USDT') -> Dict[str, Any]:
        """
        获取持仓量 (Open Interest)
        
        Args:
            symbol: 交易对符号
            
        Returns:
            包含持仓量信息的字典
        """
        try:
            logger.info(f"获取 {symbol} 持仓量...")
            
            # 尝试获取持仓量数据
            if hasattr(self.exchange, 'fetch_open_interest'):
                oi_data = self.exchange.fetch_open_interest(symbol)
                if isinstance(oi_data, dict):
                    logger.info(f"当前持仓量: {oi_data.get('openInterestAmount', 'N/A')}")
                    return oi_data
                elif oi_data:
                    # 处理非字典类型的数据
                    logger.info(f"当前持仓量: {oi_data}")
                    return {'open_interest_data': str(oi_data)}
                else:
                    return {}
            else:
                # 备选方法：通过ticker获取
                ticker = self.exchange.fetch_ticker(symbol)
                if 'info' in ticker and 'openInterest' in ticker['info']:
                    oi_value = float(ticker['info']['openInterest'])
                    logger.info(f"当前持仓量 (via ticker): {oi_value}")
                    return {
                        'symbol': symbol,
                        'openInterestAmount': oi_value,
                        'timestamp': ticker['timestamp'],
                        'datetime': ticker['datetime']
                    }
                else:
                    logger.warning("无法获取持仓量数据")
                    return {}
                    
        except Exception as e:
            logger.error(f"获取持仓量失败: {e}")
            return {}
    
    def get_perpetual_data(self, symbol: str = 'ETH/USDT', 
                          timeframe: str = '1h', limit: int = 50) -> Dict[str, Any]:
        """
        获取永续合约完整数据 (OHLCV + 资金费率 + 持仓量)
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 获取数据条数
            
        Returns:
            包含完整永续合约数据的字典
        """
        try:
            logger.info(f"获取 {symbol} 永续合约完整数据...")
            
            # 获取OHLCV数据
            ohlcv_df = self.get_ohlcv(symbol, timeframe, limit)
            
            # 获取当前资金费率
            funding_rate = self.get_funding_rate(symbol)
            
            # 获取持仓量
            open_interest = self.get_open_interest(symbol)
            
            # 获取资金费率历史 (最近10个周期)
            funding_history = self.get_funding_rate_history(symbol, limit=10)
            
            return {
                'ohlcv_data': ohlcv_df,
                'current_funding_rate': funding_rate,
                'open_interest': open_interest,
                'funding_rate_history': funding_history,
                'stats': self.calculate_basic_stats(ohlcv_df)
            }
            
        except Exception as e:
            logger.error(f"获取永续合约数据失败: {e}")
            raise
    
    def calculate_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算基础统计信息"""
        return {
            'total_bars': len(df),
            'price_range': {
                'min': df['low'].min(),
                'max': df['high'].max(),
                'current': df['close'].iloc[-1]
            },
            'volume_stats': {
                'total': df['volume'].sum(),
                'avg': df['volume'].mean(),
                'max': df['volume'].max()
            },
            'volatility': df['close'].pct_change().std() * 100,
            'time_range': {
                'start': df['datetime'].iloc[0],
                'end': df['datetime'].iloc[-1]
            }
        }