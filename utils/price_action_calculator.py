#!/usr/bin/env python3
"""
ETH永续合约AI分析助手 - 价格行动计算器
计算关键支撑阻力位、入场出场点位
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PriceLevel:
    """价格水平数据类"""
    price: float
    type: str  # 'support', 'resistance', 'pivot'
    strength: int  # 1-5强度评级
    source: str  # 'swing', 'volume', 'psychological', 'fibonacci'
    touches: int = 0  # 触及次数
    
class PriceActionCalculator:
    """价格行动计算器"""
    
    def __init__(self):
        self.pivot_window = 5  # 摆动点计算窗口
        self.volume_threshold = 1.5  # 成交量阈值（相对平均值）
        self.psychological_levels = [50, 100, 150, 200, 250, 300]  # 心理价位间隔
    
    def find_swing_points(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """识别摆动高点和低点"""
        highs = []
        lows = []
        
        for i in range(self.pivot_window, len(df) - self.pivot_window):
            # 摆动高点：比前后n个周期都高
            if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, self.pivot_window+1)) and \
               all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, self.pivot_window+1)):
                highs.append({
                    'index': i,
                    'price': df['high'].iloc[i],
                    'timestamp': df.index[i] if hasattr(df.index[i], 'strftime') else str(df.index[i]),
                    'volume': df['volume'].iloc[i]
                })
            
            # 摆动低点：比前后n个周期都低  
            if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, self.pivot_window+1)) and \
               all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, self.pivot_window+1)):
                lows.append({
                    'index': i,
                    'price': df['low'].iloc[i], 
                    'timestamp': df.index[i] if hasattr(df.index[i], 'strftime') else str(df.index[i]),
                    'volume': df['volume'].iloc[i]
                })
        
        return {'highs': highs, 'lows': lows}
    
    def find_volume_levels(self, df: pd.DataFrame) -> List[PriceLevel]:
        """基于成交量找关键价位"""
        volume_levels = []
        avg_volume = df['volume'].mean()
        
        # 找高成交量的价格区间
        high_volume_bars = df[df['volume'] > avg_volume * self.volume_threshold]
        
        for idx, bar in high_volume_bars.iterrows():
            # 以该K线的中位价作为关键价位
            mid_price = (bar['high'] + bar['low']) / 2
            
            volume_levels.append(PriceLevel(
                price=mid_price,
                type='volume_level',
                strength=min(5, int(bar['volume'] / avg_volume)),
                source='volume',
                touches=1
            ))
        
        return volume_levels
    
    def find_psychological_levels(self, current_price: float, price_range: float = 500) -> List[PriceLevel]:
        """找心理价位"""
        levels = []
        
        # 找到当前价格附近的整数关口
        for level in self.psychological_levels:
            # 找最接近当前价格的整数倍
            base = int(current_price / level) * level
            
            for multiplier in [-2, -1, 0, 1, 2]:
                price = base + (multiplier * level)
                if abs(price - current_price) <= price_range and price > 0:
                    levels.append(PriceLevel(
                        price=price,
                        type='psychological',
                        strength=3 if level in [100, 200, 500] else 2,
                        source='psychological'
                    ))
        
        return levels
    
    def calculate_fibonacci_levels(self, high_price: float, low_price: float) -> List[PriceLevel]:
        """计算斐波那契回撤位"""
        fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        levels = []
        
        price_range = high_price - low_price
        
        for ratio in fib_ratios:
            # 回撤位（从高点向下）
            retracement_price = high_price - (price_range * ratio)
            levels.append(PriceLevel(
                price=retracement_price,
                type='fibonacci',
                strength=4 if ratio in [0.382, 0.618] else 3,
                source='fibonacci'
            ))
            
            # 扩展位（从高点向上）
            extension_price = high_price + (price_range * ratio)
            levels.append(PriceLevel(
                price=extension_price,
                type='fibonacci',
                strength=3,
                source='fibonacci'
            ))
        
        return levels
    
    def cluster_price_levels(self, levels: List[PriceLevel], cluster_distance: float = 10) -> List[PriceLevel]:
        """聚合相近的价格水平"""
        if not levels:
            return []
        
        # 按价格排序
        sorted_levels = sorted(levels, key=lambda x: x.price)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # 如果价格相近，加入当前聚合
            if abs(level.price - current_cluster[-1].price) <= cluster_distance:
                current_cluster.append(level)
            else:
                # 完成当前聚合，开始新的聚合
                clusters.append(self._merge_cluster(current_cluster))
                current_cluster = [level]
        
        # 处理最后一个聚合
        if current_cluster:
            clusters.append(self._merge_cluster(current_cluster))
        
        return clusters
    
    def _merge_cluster(self, cluster: List[PriceLevel]) -> PriceLevel:
        """合并价格聚合"""
        if len(cluster) == 1:
            return cluster[0]
        
        # 加权平均价格（按强度加权）
        total_weight = sum(level.strength for level in cluster)
        weighted_price = sum(level.price * level.strength for level in cluster) / total_weight
        
        # 合并强度
        merged_strength = min(5, sum(level.strength for level in cluster))
        
        # 确定类型（优先级：fibonacci > volume > swing > psychological）
        type_priority = {'fibonacci': 4, 'volume': 3, 'swing': 2, 'psychological': 1}
        dominant_type = max(cluster, key=lambda x: type_priority.get(x.source, 0)).type
        
        return PriceLevel(
            price=weighted_price,
            type=dominant_type,
            strength=merged_strength,
            source='cluster',
            touches=sum(level.touches for level in cluster)
        )
    
    def calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """计算支撑阻力位"""
        current_price = df['close'].iloc[-1]
        all_levels = []
        
        # 1. 摆动点分析
        swing_points = self.find_swing_points(df)
        
        # 将摆动高点转为阻力位
        for high in swing_points['highs']:
            all_levels.append(PriceLevel(
                price=high['price'],
                type='resistance',
                strength=3,
                source='swing',
                touches=1
            ))
        
        # 将摆动低点转为支撑位
        for low in swing_points['lows']:
            all_levels.append(PriceLevel(
                price=low['price'],
                type='support',
                strength=3, 
                source='swing',
                touches=1
            ))
        
        # 2. 成交量分析
        volume_levels = self.find_volume_levels(df)
        for level in volume_levels:
            # 根据当前价格判断是支撑还是阻力
            level.type = 'support' if level.price < current_price else 'resistance'
            all_levels.append(level)
        
        # 3. 心理价位
        psych_levels = self.find_psychological_levels(current_price)
        for level in psych_levels:
            level.type = 'support' if level.price < current_price else 'resistance'
            all_levels.append(level)
        
        # 4. 斐波那契分析（使用最近的高低点）
        if len(df) > 20:
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            fib_levels = self.calculate_fibonacci_levels(recent_high, recent_low)
            
            for level in fib_levels:
                level.type = 'support' if level.price < current_price else 'resistance'
                all_levels.append(level)
        
        # 5. 聚合相近价位
        clustered_levels = self.cluster_price_levels(all_levels)
        
        # 分类为支撑和阻力
        supports = [level for level in clustered_levels if level.type == 'support']
        resistances = [level for level in clustered_levels if level.type == 'resistance']
        
        # 排序（支撑按价格从高到低，阻力按价格从低到高）
        supports.sort(key=lambda x: x.price, reverse=True)
        resistances.sort(key=lambda x: x.price)
        
        # 只返回最近的5个关键位
        return {
            'supports': [self._level_to_dict(level) for level in supports[:5]],
            'resistances': [self._level_to_dict(level) for level in resistances[:5]]
        }
    
    def _level_to_dict(self, level: PriceLevel) -> Dict:
        """将价格水平转为字典"""
        return {
            'price': round(level.price, 2),
            'type': level.type,
            'strength': level.strength,
            'source': level.source,
            'distance_pct': 0  # 将在调用时计算
        }
    
    def calculate_entry_exit_points(self, df: pd.DataFrame, signal_type: str) -> Dict:
        """计算入场出场点位"""
        current_price = df['close'].iloc[-1]
        atr = self._calculate_atr(df)
        sr_levels = self.calculate_support_resistance(df)
        
        # 添加距离百分比
        for level in sr_levels['supports'] + sr_levels['resistances']:
            level['distance_pct'] = abs(level['price'] - current_price) / current_price * 100
        
        if signal_type.lower() in ['buy', 'long', '做多']:
            return self._calculate_long_points(current_price, atr, sr_levels)
        elif signal_type.lower() in ['sell', 'short', '做空']:
            return self._calculate_short_points(current_price, atr, sr_levels)
        else:
            return self._calculate_neutral_points(current_price, atr, sr_levels)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算ATR (Average True Range)"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.tail(period).mean()
    
    def _calculate_long_points(self, current_price: float, atr: float, sr_levels: Dict) -> Dict:
        """计算做多交易点位"""
        # 入场：当前价格或最近支撑位上方
        entry_base = current_price
        if sr_levels['supports'] and sr_levels['supports'][0]['distance_pct'] < 2:
            entry_base = sr_levels['supports'][0]['price']
        
        entry_range = {
            'min': entry_base - atr * 0.5,
            'max': entry_base + atr * 0.2
        }
        
        # 止损：最近支撑位下方或基于ATR
        if sr_levels['supports']:
            stop_loss = sr_levels['supports'][0]['price'] - atr * 0.5
        else:
            stop_loss = current_price - atr * 2
        
        # 目标位：最近阻力位或基于风险回报比
        targets = []
        risk = abs(entry_base - stop_loss)
        
        # 目标1：1:1风险回报比
        targets.append(entry_base + risk)
        
        # 目标2：最近阻力位或1:2风险回报比  
        if sr_levels['resistances'] and sr_levels['resistances'][0]['distance_pct'] < 10:
            targets.append(sr_levels['resistances'][0]['price'])
        else:
            targets.append(entry_base + risk * 2)
        
        return {
            'signal_type': '做多',
            'entry_range': entry_range,
            'stop_loss': stop_loss,
            'targets': targets,
            'risk_pct': abs(entry_base - stop_loss) / entry_base * 100,
            'reward_ratios': [abs(target - entry_base) / risk for target in targets]
        }
    
    def _calculate_short_points(self, current_price: float, atr: float, sr_levels: Dict) -> Dict:
        """计算做空交易点位"""
        # 入场：当前价格或最近阻力位下方
        entry_base = current_price
        if sr_levels['resistances'] and sr_levels['resistances'][0]['distance_pct'] < 2:
            entry_base = sr_levels['resistances'][0]['price']
        
        entry_range = {
            'max': entry_base + atr * 0.5,
            'min': entry_base - atr * 0.2
        }
        
        # 止损：最近阻力位上方或基于ATR
        if sr_levels['resistances']:
            stop_loss = sr_levels['resistances'][0]['price'] + atr * 0.5
        else:
            stop_loss = current_price + atr * 2
        
        # 目标位
        targets = []
        risk = abs(stop_loss - entry_base)
        
        # 目标1：1:1风险回报比
        targets.append(entry_base - risk)
        
        # 目标2：最近支撑位或1:2风险回报比
        if sr_levels['supports'] and sr_levels['supports'][0]['distance_pct'] < 10:
            targets.append(sr_levels['supports'][0]['price'])
        else:
            targets.append(entry_base - risk * 2)
        
        return {
            'signal_type': '做空',
            'entry_range': entry_range,
            'stop_loss': stop_loss,
            'targets': targets,
            'risk_pct': abs(stop_loss - entry_base) / entry_base * 100,
            'reward_ratios': [abs(entry_base - target) / risk for target in targets]
        }
    
    def _calculate_neutral_points(self, current_price: float, atr: float, sr_levels: Dict) -> Dict:
        """计算观望时的关键点位"""
        return {
            'signal_type': '观望',
            'breakout_levels': {
                'bullish_breakout': sr_levels['resistances'][0]['price'] if sr_levels['resistances'] else current_price + atr,
                'bearish_breakdown': sr_levels['supports'][0]['price'] if sr_levels['supports'] else current_price - atr
            },
            'watch_levels': {
                'resistance': sr_levels['resistances'][:2] if len(sr_levels['resistances']) >= 2 else sr_levels['resistances'],
                'support': sr_levels['supports'][:2] if len(sr_levels['supports']) >= 2 else sr_levels['supports']
            }
        }