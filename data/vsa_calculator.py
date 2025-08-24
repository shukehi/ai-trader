#!/usr/bin/env python3
"""
VSA (Volume Spread Analysis) 核心计算模块
基于Anna Coulling的VSA理论，提供专业的量价分析指标

核心功能：
1. Spread分析 - 计算价差与成交量关系
2. Close位置分析 - 收盘价在Range中的位置
3. VSA信号识别 - No Demand, No Supply, Climax等
4. 专业VSA指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SpreadType(Enum):
    """价差类型枚举"""
    WIDE = "wide"
    NARROW = "narrow"
    NORMAL = "normal"

class VSASignalType(Enum):
    """VSA信号类型枚举"""
    NO_DEMAND = "no_demand"
    NO_SUPPLY = "no_supply"
    CLIMAX_VOLUME = "climax_volume"
    UPTHRUST = "upthrust"
    SPRING = "spring"
    TEST = "test"
    NORMAL = "normal"

@dataclass
class VSABar:
    """单个K线的VSA分析结果"""
    spread: float                    # 价差 (high - low)
    spread_type: SpreadType         # 价差类型
    close_position: float           # 收盘位置 (0-1, 0为最低，1为最高)
    volume_ratio: float             # 成交量比率 (当前/平均)
    vsa_signal: VSASignalType       # VSA信号类型
    signal_strength: float          # 信号强度 (0-1)
    professional_activity: bool    # 是否有专业资金活动
    
class VSACalculator:
    """
    VSA计算器
    
    提供完整的VSA分析功能，遵循Anna Coulling的理论框架
    """
    
    def __init__(self, volume_window: int = 20, spread_percentile: float = 0.7):
        """
        初始化VSA计算器
        
        Args:
            volume_window: 成交量移动平均窗口
            spread_percentile: 价差分类阈值百分位数
        """
        self.volume_window = volume_window
        self.spread_percentile = spread_percentile
        
    def calculate_vsa_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算完整的VSA指标
        
        Args:
            df: OHLCV数据DataFrame
            
        Returns:
            包含VSA指标的DataFrame
        """
        df = df.copy()
        
        # 基础计算
        df['spread'] = df['high'] - df['low']
        df['close_position'] = self._calculate_close_position(df)
        df['volume_sma'] = df['volume'].rolling(window=self.volume_window).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 价差分类
        df['spread_type'] = self._classify_spread(df)
        
        # VSA信号识别
        vsa_signals = self._identify_vsa_signals(df)
        df['vsa_signal'] = [signal.vsa_signal.value for signal in vsa_signals]
        df['signal_strength'] = [signal.signal_strength for signal in vsa_signals]
        df['professional_activity'] = [signal.professional_activity for signal in vsa_signals]
        
        # 额外VSA指标
        df['effort_result_ratio'] = self._calculate_effort_result_ratio(df)
        df['supply_demand_balance'] = self._calculate_supply_demand_balance(df)
        
        return df
    
    def _calculate_close_position(self, df: pd.DataFrame) -> pd.Series:
        """
        计算收盘位置 (Close Position)
        
        0 = 收于最低价
        1 = 收于最高价
        0.5 = 收于中间位置
        """
        spread = df['high'] - df['low']
        close_from_low = df['close'] - df['low']
        
        # 避免除零错误
        position = np.where(spread == 0, 0.5, close_from_low / spread)
        return pd.Series(position, index=df.index).clip(0, 1)
    
    def _classify_spread(self, df: pd.DataFrame) -> List[str]:
        """
        分类价差类型 (Wide/Narrow/Normal)
        """
        spread_low = df['spread'].rolling(window=50).quantile(0.3)
        spread_high = df['spread'].rolling(window=50).quantile(0.7)
        
        spread_types = []
        for i, spread in enumerate(df['spread']):
            if i < 49:  # 前49个数据不足以计算百分位数
                spread_types.append(SpreadType.NORMAL.value)
                continue
                
            if spread > spread_high.iloc[i]:
                spread_types.append(SpreadType.WIDE.value)
            elif spread < spread_low.iloc[i]:
                spread_types.append(SpreadType.NARROW.value)
            else:
                spread_types.append(SpreadType.NORMAL.value)
        
        return spread_types
    
    def _identify_vsa_signals(self, df: pd.DataFrame) -> List[VSABar]:
        """
        识别VSA信号
        
        基于Anna Coulling的VSA信号识别规则
        """
        signals = []
        
        for i in range(len(df)):
            bar = df.iloc[i]
            
            # 获取当前K线的基本属性
            spread = bar['spread']
            close_pos = bar['close_position']
            vol_ratio = bar['volume_ratio']
            is_up = bar['close'] > bar['open']
            is_down = bar['close'] < bar['open']
            
            # 初始化信号
            signal_type = VSASignalType.NORMAL
            strength = 0.0
            professional = False
            
            # No Demand - 上涨但成交量低
            if (is_up and vol_ratio < 0.8 and 
                spread <= df['spread'].rolling(20).quantile(0.4).iloc[i]):
                signal_type = VSASignalType.NO_DEMAND
                strength = 0.7
                professional = True
            
            # No Supply - 下跌但成交量低
            elif (is_down and vol_ratio < 0.8 and 
                  spread <= df['spread'].rolling(20).quantile(0.4).iloc[i]):
                signal_type = VSASignalType.NO_SUPPLY
                strength = 0.7
                professional = True
            
            # Climax Volume - 极高成交量
            elif vol_ratio > 2.0:
                signal_type = VSASignalType.CLIMAX_VOLUME
                strength = min(vol_ratio / 3.0, 1.0)
                professional = True
            
            # Upthrust - 高位长上影大量
            elif (close_pos < 0.3 and vol_ratio > 1.5 and 
                  spread > df['spread'].rolling(20).quantile(0.7).iloc[i]):
                signal_type = VSASignalType.UPTHRUST
                strength = 0.8
                professional = True
            
            # Spring - 低位长下影后收回
            elif (close_pos > 0.7 and i > 0 and 
                  df.iloc[i-1]['close_position'] < 0.3 and
                  vol_ratio > 1.2):
                signal_type = VSASignalType.SPRING
                strength = 0.8
                professional = True
            
            # Test - 低量测试前期低点/高点
            elif (vol_ratio < 0.6 and self._is_testing_level(df, i)):
                signal_type = VSASignalType.TEST
                strength = 0.6
                professional = True
            
            signals.append(VSABar(
                spread=spread,
                spread_type=SpreadType.NORMAL,  # 会在后面更新
                close_position=close_pos,
                volume_ratio=vol_ratio,
                vsa_signal=signal_type,
                signal_strength=strength,
                professional_activity=professional
            ))
        
        return signals
    
    def _is_testing_level(self, df: pd.DataFrame, current_idx: int, 
                         lookback: int = 20) -> bool:
        """
        判断是否在测试前期重要价位
        """
        if current_idx < lookback:
            return False
            
        current_low = df.iloc[current_idx]['low']
        current_high = df.iloc[current_idx]['high']
        
        # 获取前期数据
        historical = df.iloc[max(0, current_idx-lookback):current_idx]
        
        # 检查是否接近前期低点或高点 (2%容差)
        for _, hist_bar in historical.iterrows():
            if (abs(current_low - hist_bar['low']) / hist_bar['low'] < 0.02 or
                abs(current_high - hist_bar['high']) / hist_bar['high'] < 0.02):
                return True
                
        return False
    
    def _calculate_effort_result_ratio(self, df: pd.DataFrame) -> pd.Series:
        """
        计算努力与结果比率
        
        努力 = 成交量
        结果 = 价格变动幅度
        """
        price_change = abs(df['close'] - df['open'])
        volume_normalized = df['volume'] / df['volume'].rolling(20).mean()
        
        # 避免除零错误
        ratio = np.where(price_change == 0, volume_normalized, 
                        volume_normalized / (price_change / df['close']))
        
        return pd.Series(ratio, index=df.index)
    
    def _calculate_supply_demand_balance(self, df: pd.DataFrame) -> pd.Series:
        """
        计算供需平衡指标
        
        基于成交量、价差和收盘位置的综合评估
        """
        # 需求信号：高量上涨且收于高位
        demand = (df['volume_ratio'] * df['close_position'] * 
                 (df['close'] > df['open']).astype(int))
        
        # 供给信号：高量下跌且收于低位  
        supply = (df['volume_ratio'] * (1 - df['close_position']) * 
                 (df['close'] < df['open']).astype(int))
        
        # 供需平衡 (-1到1，正值表示需求占优)
        balance = (demand - supply) / (demand + supply + 0.001)  # 避免除零
        
        return pd.Series(balance, index=df.index)
    
    def get_vsa_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取VSA分析摘要
        
        Returns:
            包含VSA分析摘要的字典
        """
        # 计算VSA指标
        vsa_df = self.calculate_vsa_indicators(df)
        
        # 统计各类VSA信号
        signal_counts = vsa_df['vsa_signal'].value_counts()
        
        # 专业资金活动统计
        professional_activity = vsa_df['professional_activity'].sum()
        
        # 最近的强信号
        recent_strong_signals = vsa_df[
            (vsa_df['signal_strength'] > 0.7) & 
            (vsa_df.index >= len(vsa_df) - 10)
        ]
        
        # 供需平衡趋势
        recent_balance = vsa_df['supply_demand_balance'].iloc[-10:].mean()
        
        return {
            'signal_distribution': signal_counts.to_dict(),
            'professional_activity_count': int(professional_activity),
            'recent_strong_signals': len(recent_strong_signals),
            'supply_demand_balance': float(recent_balance),
            'latest_vsa_signal': vsa_df['vsa_signal'].iloc[-1],
            'latest_signal_strength': float(vsa_df['signal_strength'].iloc[-1]),
            'wide_spread_count': (vsa_df['spread_type'] == 'wide').sum(),
            'narrow_spread_count': (vsa_df['spread_type'] == 'narrow').sum()
        }
    
    def interpret_vsa_signals(self, summary: Dict[str, Any]) -> str:
        """
        解释VSA信号的市场含义
        
        Args:
            summary: VSA摘要数据
            
        Returns:
            VSA信号的专业解释
        """
        interpretation = []
        
        # 最新信号解释
        latest_signal = summary['latest_vsa_signal']
        strength = summary['latest_signal_strength']
        
        if latest_signal == 'no_demand':
            interpretation.append(f"⚠️ No Demand信号 (强度:{strength:.2f}) - 上涨缺乏真实买盘支持，Smart Money不愿追高")
        elif latest_signal == 'no_supply':
            interpretation.append(f"✅ No Supply信号 (强度:{strength:.2f}) - 下跌缺乏真实卖压，可能是洗盘行为")
        elif latest_signal == 'climax_volume':
            interpretation.append(f"🔥 Climax Volume (强度:{strength:.2f}) - 极端成交量，可能标志趋势转折点")
        elif latest_signal == 'upthrust':
            interpretation.append(f"🔴 Upthrust信号 (强度:{strength:.2f}) - 高位假突破，专业资金可能在派发")
        elif latest_signal == 'spring':
            interpretation.append(f"🟢 Spring信号 (强度:{strength:.2f}) - 低位测试成功，可能开始新一轮上涨")
        
        # 供需平衡解释
        balance = summary['supply_demand_balance']
        if balance > 0.3:
            interpretation.append("📈 供需平衡偏向需求，买方力量占优")
        elif balance < -0.3:
            interpretation.append("📉 供需平衡偏向供给，卖方力量占优")
        else:
            interpretation.append("⚖️ 供需基本平衡，市场处于胶着状态")
        
        # 专业资金活动
        if summary['professional_activity_count'] > 5:
            interpretation.append("🎯 检测到频繁的专业资金活动，市场可能面临重要转折")
        
        return "\n".join(interpretation)