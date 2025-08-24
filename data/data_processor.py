import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from ta import trend, momentum, volatility, volume  # type: ignore
import logging
from .vsa_calculator import VSACalculator

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    数据处理器，用于计算技术指标和处理OHLCV数据
    """
    
    def __init__(self):
        """初始化数据处理器"""
        self.vsa_calculator = VSACalculator()
    
    @staticmethod
    def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        添加基础技术指标
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            添加了技术指标的DataFrame
        """
        df = df.copy()
        
        # 移动平均线
        df['sma_20'] = trend.sma_indicator(df['close'], window=20)
        df['ema_12'] = trend.ema_indicator(df['close'], window=12)
        df['ema_26'] = trend.ema_indicator(df['close'], window=26)
        
        # MACD
        df['macd'] = trend.macd_diff(df['close'])
        df['macd_signal'] = trend.macd_signal(df['close'])
        df['macd_histogram'] = trend.macd(df['close'])
        
        # RSI
        df['rsi'] = momentum.rsi(df['close'], window=14)
        
        # 布林带
        bollinger = volatility.BollingerBands(df['close'])
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        
        # 成交量指标 (修复ta库兼容性)
        df['volume_sma'] = df['volume'].rolling(window=20).mean()  # 手动计算成交量SMA
        try:
            df['vwap'] = volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
        except:
            # VWAP手动计算
            df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        # 价格变化
        df['price_change'] = df['close'].pct_change()
        df['price_change_abs'] = df['close'].diff()
        
        # 真实波幅
        df['atr'] = volatility.average_true_range(df['high'], df['low'], df['close'])
        
        return df
    
    def add_vsa_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加VSA (Volume Spread Analysis) 指标
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            添加了VSA指标的DataFrame
        """
        logger.info("开始计算VSA指标...")
        
        try:
            # 使用VSA计算器添加指标
            df_with_vsa = self.vsa_calculator.calculate_vsa_indicators(df)
            
            logger.info(f"VSA指标计算完成，添加了 {len(df_with_vsa.columns) - len(df.columns)} 个VSA指标")
            return df_with_vsa
            
        except Exception as e:
            logger.error(f"VSA指标计算失败: {e}")
            return df
    
    def get_vsa_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取VSA分析摘要
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            VSA分析摘要字典
        """
        return self.vsa_calculator.get_vsa_summary(df)
    
    def interpret_vsa_signals(self, summary: Dict[str, Any]) -> str:
        """
        解释VSA信号
        
        Args:
            summary: VSA摘要数据
            
        Returns:
            VSA信号的专业解释
        """
        return self.vsa_calculator.interpret_vsa_signals(summary)
    
    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """
        检测蜡烛图形态
        """
        df = df.copy()
        
        # 计算实体和影线
        df['body'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df['high'] - np.maximum(df['open'], df['close'])
        df['lower_shadow'] = np.minimum(df['open'], df['close']) - df['low']
        df['total_range'] = df['high'] - df['low']
        
        # 十字星 (小实体)
        df['is_doji'] = (df['body'] / df['total_range'] < 0.1) & (df['total_range'] > 0)
        
        # 锤子线 (下影线长，上影线短，实体小)
        df['is_hammer'] = (
            (df['lower_shadow'] > 2 * df['body']) &
            (df['upper_shadow'] < df['body']) &
            (df['body'] / df['total_range'] < 0.3)
        )
        
        # 流星线 (上影线长，下影线短，实体小)
        df['is_shooting_star'] = (
            (df['upper_shadow'] > 2 * df['body']) &
            (df['lower_shadow'] < df['body']) &
            (df['body'] / df['total_range'] < 0.3)
        )
        
        # 吞没形态
        df['bullish_engulfing'] = (
            (df['open'] > df['close'].shift(1)) &
            (df['close'] > df['open'].shift(1)) &
            (df['body'] > df['body'].shift(1) * 1.5)
        )
        
        df['bearish_engulfing'] = (
            (df['open'] < df['close'].shift(1)) &
            (df['close'] < df['open'].shift(1)) &
            (df['body'] > df['body'].shift(1) * 1.5)
        )
        
        return df
    
    @staticmethod
    def analyze_volume_price_relationship(df: pd.DataFrame) -> pd.DataFrame:
        """
        分析量价关系 (VPA核心)
        """
        df = df.copy()
        
        # 成交量变化
        df['volume_change'] = df['volume'].pct_change()
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 价格趋势
        df['price_trend'] = np.where(df['close'] > df['close'].shift(1), 'up',
                                   np.where(df['close'] < df['close'].shift(1), 'down', 'flat'))
        
        # VPA信号
        # 上涨 + 高成交量 = 健康上涨
        df['bullish_volume'] = (df['price_trend'] == 'up') & (df['volume_ratio'] > 1.5)
        
        # 下跌 + 高成交量 = 健康下跌
        df['bearish_volume'] = (df['price_trend'] == 'down') & (df['volume_ratio'] > 1.5)
        
        # 上涨 + 低成交量 = 可疑上涨
        df['suspicious_rally'] = (df['price_trend'] == 'up') & (df['volume_ratio'] < 0.8)
        
        # 下跌 + 低成交量 = 可疑下跌
        df['suspicious_decline'] = (df['price_trend'] == 'down') & (df['volume_ratio'] < 0.8)
        
        # 高成交量但价格平盘 = 可能的转折点
        df['high_volume_no_progress'] = (df['price_trend'] == 'flat') & (df['volume_ratio'] > 2.0)
        
        return df
    
    @staticmethod
    def get_key_levels(df: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """
        识别关键支撑阻力位
        """
        # 局部高点和低点
        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            # 局部高点
            if (df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max()):
                highs.append(df['high'].iloc[i])
            
            # 局部低点
            if (df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min()):
                lows.append(df['low'].iloc[i])
        
        return {
            'resistance_levels': sorted(set(highs), reverse=True)[:5],  # 前5个阻力位
            'support_levels': sorted(set(lows))[-5:],  # 前5个支撑位
        }
    
    @staticmethod
    def calculate_token_estimate(df: pd.DataFrame, format_type: str = 'csv') -> int:
        """
        估算不同格式下的token数量
        """
        if format_type == 'csv':
            # CSV格式：每行大约15-20个token
            return len(df) * 18
        elif format_type == 'json':
            # JSON格式：更详细，每行大约25-30个token
            return len(df) * 28
        elif format_type == 'text':
            # 文本描述格式：每行大约30-40个token
            return len(df) * 35
        else:
            return len(df) * 20  # 默认估算