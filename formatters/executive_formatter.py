#!/usr/bin/env python3
"""
ETH永续合约AI分析助手 - 执行摘要格式化器
为个人交易者提供简洁实用的分析报告格式
"""

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from utils.price_action_calculator import PriceActionCalculator

class ExecutiveFormatter:
    """执行摘要格式化器"""
    
    def __init__(self):
        self.price_calculator = PriceActionCalculator()
    
    def format_trading_signal_data(self, df: pd.DataFrame, vsa_analysis: Optional[Dict] = None, 
                                   funding_rate: Optional[float] = None, open_interest: Optional[float] = None) -> str:
        """格式化交易信号数据（简洁版）"""
        current_price = df['close'].iloc[-1]
        
        # 计算基础指标
        price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
        price_change_pct = (price_change / df['close'].iloc[-2]) * 100
        volume_avg = df['volume'].tail(20).mean()
        volume_ratio = df['volume'].iloc[-1] / volume_avg
        
        # 计算支撑阻力位
        sr_levels = self.price_calculator.calculate_support_resistance(df)
        
        # 格式化核心数据
        output = f"""## 📊 ETH/USDT 永续合约数据 (最新50根K线)

### 当前价格状态
- **价格**: ${current_price:.2f} ({price_change:+.2f}, {price_change_pct:+.2f}%)
- **24H高低**: ${df['high'].tail(24).max():.2f} / ${df['low'].tail(24).min():.2f}
- **成交量**: {df['volume'].iloc[-1]:,.0f} (平均值{volume_ratio:.1f}倍)"""

        # 添加永续合约数据
        if funding_rate is not None:
            funding_bias = "看多偏向" if funding_rate > 0 else "看空偏向" if funding_rate < 0 else "中性"
            output += f"\n- **资金费率**: {funding_rate*100:.4f}% ({funding_bias})"
        
        if open_interest is not None:
            output += f"\n- **持仓量**: {open_interest:,.0f}"

        # 关键价位
        output += f"\n\n### 关键价位"
        
        if sr_levels['resistances']:
            resistances = sr_levels['resistances'][:2]
            output += f"\n- **阻力位**: "
            output += " | ".join([f"${r['price']:.2f}" for r in resistances])
        
        if sr_levels['supports']:
            supports = sr_levels['supports'][:2]
            output += f"\n- **支撑位**: "
            output += " | ".join([f"${s['price']:.2f}" for s in supports])

        # VSA关键信息
        if vsa_analysis:
            output += f"\n\n### VSA信号"
            if 'key_signal' in vsa_analysis:
                output += f"\n- **主要信号**: {vsa_analysis['key_signal']}"
            if 'volume_analysis' in vsa_analysis:
                output += f"\n- **成交量**: {vsa_analysis['volume_analysis']}"
            if 'smart_money' in vsa_analysis:
                output += f"\n- **资金流向**: {vsa_analysis['smart_money']}"

        # 最近15根K线的简化数据
        recent_data = df.tail(15)[['open', 'high', 'low', 'close', 'volume']].copy()
        recent_data = recent_data.round(2)
        recent_data['volume'] = recent_data['volume'].astype(int)
        
        output += f"\n\n### 最近15根K线数据\n"
        output += "时间 | 开盘 | 最高 | 最低 | 收盘 | 成交量\n"
        output += "---|---|---|---|---|---\n"
        
        for i, (idx, row) in enumerate(recent_data.iterrows()):
            time_label = f"T-{14-i}" if i < 14 else "当前"
            output += f"{time_label} | ${row['open']:.2f} | ${row['high']:.2f} | ${row['low']:.2f} | ${row['close']:.2f} | {row['volume']:,}\n"
        
        return output
    
    def format_quick_signal_data(self, df: pd.DataFrame) -> str:
        """超简化数据格式（快速信号专用）"""
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 只显示核心信息
        return f"""当前价格: ${current['close']:.2f} ({((current['close'] - prev['close'])/prev['close']*100):+.2f}%)
最高/最低: ${current['high']:.2f}/${current['low']:.2f}
成交量: {current['volume']:,.0f}

最近5根K线:
{self._format_mini_table(df.tail(5))}"""

    def _format_mini_table(self, df: pd.DataFrame) -> str:
        """格式化迷你表格"""
        lines = []
        for i, (_, row) in enumerate(df.iterrows()):
            if i == 0:
                change = ""
            else:
                prev_price = df.iloc[i-1]['close']
                change_pct = ((row['close'] - prev_price) / prev_price * 100)
                change = f" ({change_pct:+.1f}%)"
            lines.append(f"${row['close']:.2f}{change}")
        return " → ".join(lines)

    def format_executive_summary_data(self, df: pd.DataFrame, analysis_result: Optional[str] = None) -> str:
        """执行摘要数据格式"""
        current_price = df['close'].iloc[-1]
        daily_change = ((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100
        volume_trend = "放量" if df['volume'].iloc[-1] > df['volume'].tail(10).mean() * 1.2 else "缩量"
        
        # 提取支撑阻力
        sr_levels = self.price_calculator.calculate_support_resistance(df)
        nearest_resistance = sr_levels['resistances'][0]['price'] if sr_levels['resistances'] else current_price * 1.02
        nearest_support = sr_levels['supports'][0]['price'] if sr_levels['supports'] else current_price * 0.98
        
        return f"""## 📈 ETH/USDT 执行摘要

**当前状态**: ${current_price:.2f} ({daily_change:+.1f}%, {volume_trend})
**关键阻力**: ${nearest_resistance:.2f} (+{((nearest_resistance-current_price)/current_price*100):+.1f}%)  
**关键支撑**: ${nearest_support:.2f} ({((nearest_support-current_price)/current_price*100):+.1f}%)

### 核心数据点:
- 24H波动: ${df['high'].tail(24).max():.2f} - ${df['low'].tail(24).min():.2f}
- 成交量状态: {df['volume'].iloc[-1]:,.0f} ({df['volume'].iloc[-1]/df['volume'].tail(20).mean():.1f}x平均值)
- 趋势方向: {self._determine_trend(df)}

### 最近价格行为:
{self._format_price_action_summary(df.tail(10))}

---
*数据基于最新50根K线，适用于短期交易决策*"""

    def _determine_trend(self, df: pd.DataFrame) -> str:
        """判断趋势方向"""
        recent_closes = df['close'].tail(10)
        if recent_closes.iloc[-1] > recent_closes.mean():
            if recent_closes.iloc[-1] > recent_closes.iloc[0]:
                return "上升趋势"
            else:
                return "震荡偏多"
        else:
            if recent_closes.iloc[-1] < recent_closes.iloc[0]:
                return "下降趋势" 
            else:
                return "震荡偏空"

    def _format_price_action_summary(self, df: pd.DataFrame) -> str:
        """格式化价格行动摘要"""
        highs = df['high']
        lows = df['low']
        closes = df['close']
        
        higher_highs = sum(1 for i in range(1, len(highs)) if highs.iloc[i] > highs.iloc[i-1])
        higher_lows = sum(1 for i in range(1, len(lows)) if lows.iloc[i] > lows.iloc[i-1])
        
        if higher_highs >= 6 and higher_lows >= 6:
            return "连续更高高点和更高低点，强势上升结构"
        elif higher_highs <= 3 and higher_lows <= 3:
            return "连续更低高点和更低低点，弱势下降结构"
        else:
            return "高点低点交替出现，震荡整理结构"

    def create_trading_plan_template(self, signal_type: str, entry_price: float, 
                                   stop_price: float, target_price: float) -> str:
        """创建交易计划模板"""
        risk_pct = abs(entry_price - stop_price) / entry_price * 100
        reward_pct = abs(target_price - entry_price) / entry_price * 100
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
        
        return f"""## 🎯 交易计划
        
**信号**: {signal_type}
**入场**: ${entry_price:.2f}  
**止损**: ${stop_price:.2f} (-{risk_pct:.1f}%)
**目标**: ${target_price:.2f} (+{reward_pct:.1f}%)
**风险回报比**: 1:{rr_ratio:.1f}

### 执行检查清单:
- [ ] 确认价格接近入场位
- [ ] 检查成交量配合
- [ ] 设置止损订单
- [ ] 确定仓位大小
- [ ] 监控关键支撑/阻力位"""

    def estimate_tokens_by_format(self, df: pd.DataFrame, format_type: str) -> Dict:
        """估算不同格式的token使用量"""
        estimates = {
            'trading_signal': {
                'tokens': 800,  # 大幅减少token数量
                'description': '交易信号专用格式（简化）',
                'cost_factor': 0.3  # 相比原来降低70%成本
            },
            'quick_signal': {
                'tokens': 300, 
                'description': '快速信号格式（超简化）',
                'cost_factor': 0.1  # 相比原来降低90%成本
            },
            'executive_summary': {
                'tokens': 500,
                'description': '执行摘要格式（精简）', 
                'cost_factor': 0.2  # 相比原来降低80%成本
            }
        }
        
        return estimates.get(format_type, estimates['trading_signal'])

class CostOptimizer:
    """成本优化器"""
    
    @staticmethod
    def get_economy_model_recommendations() -> Dict:
        """获取经济型模型推荐"""
        return {
            'ultra_economy': {
                'models': ['gpt5-nano', 'gemini-flash'],
                'estimated_cost': '$0.001-0.005',
                'use_case': '日常交易信号检查',
                'response_time': '10-30s'
            },
            'economy': {
                'models': ['gpt4o-mini', 'claude-haiku'],
                'estimated_cost': '$0.005-0.02', 
                'use_case': '标准交易分析',
                'response_time': '20-45s'
            },
            'balanced': {
                'models': ['gpt5-mini', 'gemini-pro'],
                'estimated_cost': '$0.02-0.1',
                'use_case': '重要交易决策',
                'response_time': '30-60s'
            }
        }
    
    @staticmethod
    def calculate_daily_usage_cost(signals_per_day: int, model_tier: str) -> Dict:
        """计算每日使用成本"""
        tier_costs = {
            'ultra_economy': 0.003,
            'economy': 0.015, 
            'balanced': 0.05
        }
        
        cost_per_signal = tier_costs.get(model_tier, 0.05)
        daily_cost = signals_per_day * cost_per_signal
        monthly_cost = daily_cost * 30
        
        return {
            'signals_per_day': signals_per_day,
            'cost_per_signal': f'${cost_per_signal:.3f}',
            'daily_cost': f'${daily_cost:.2f}',
            'monthly_cost': f'${monthly_cost:.2f}',
            'tier': model_tier
        }