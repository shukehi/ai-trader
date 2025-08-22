import pandas as pd
import json
from typing import Dict, List, Any, Optional
import numpy as np

class DataFormatter:
    """
    数据格式化器，提供4种不同的LLM输入格式
    """
    
    @staticmethod
    def to_csv_format(df: pd.DataFrame, include_volume: bool = True) -> str:
        """
        格式A: 原始CSV数值格式
        最简洁，token使用最少
        """
        # 选择需要的列
        columns = ['datetime', 'open', 'high', 'low', 'close']
        if include_volume:
            columns.append('volume')
        
        # 转换为CSV字符串
        selected_df = df[columns].copy()
        
        # 格式化数值，减少小数位以节省token
        numeric_cols = ['open', 'high', 'low', 'close']
        if include_volume:
            numeric_cols.append('volume')
        
        for col in numeric_cols:
            if col == 'volume':
                selected_df[col] = selected_df[col].astype(int)  # 成交量取整
            else:
                selected_df[col] = selected_df[col].round(2)  # 价格保留2位小数
        
        return selected_df.to_csv(index=False, lineterminator='\\n')
    
    @staticmethod
    def to_text_narrative(df: pd.DataFrame, window_size: int = 5) -> str:
        """
        格式B: 文本化描述格式
        将数值转化为自然语言描述
        """
        lines = ["# ETH/USDT 永续合约市场分析数据\\n"]
        
        # 市场概况
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        high_price = df['high'].max()
        low_price = df['low'].min()
        total_volume = df['volume'].sum()
        
        change_pct = ((end_price / start_price) - 1) * 100
        
        lines.append(f"## 市场概况")
        lines.append(f"时间范围: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")
        lines.append(f"价格变化: 从 ${start_price:.2f} 至 ${end_price:.2f} ({change_pct:+.2f}%)")
        lines.append(f"区间高低: ${high_price:.2f} / ${low_price:.2f}")
        lines.append(f"总成交量: {total_volume:,.0f}")
        lines.append("")
        
        # 关键价格行为描述
        lines.append("## 关键价格行为")
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # 价格变化
            price_change = current['close'] - previous['close']
            price_change_pct = (price_change / previous['close']) * 100
            
            # 成交量变化
            volume_change = current['volume'] - previous['volume']
            volume_change_pct = (volume_change / previous['volume']) * 100 if previous['volume'] > 0 else 0
            
            # 波动幅度
            range_size = current['high'] - current['low']
            range_pct = (range_size / current['low']) * 100 if current['low'] > 0 else 0
            
            # 生成描述
            direction = "上涨" if price_change > 0 else "下跌" if price_change < 0 else "平盘"
            intensity = "大幅" if abs(price_change_pct) > 2 else "温和" if abs(price_change_pct) > 0.5 else "微"
            
            volume_desc = "成交量激增" if volume_change_pct > 50 else "成交量增加" if volume_change_pct > 20 else "成交量萎缩" if volume_change_pct < -20 else "成交量平稳"
            
            if abs(price_change_pct) > 0.5 or abs(volume_change_pct) > 30:  # 只描述重要的变化
                lines.append(f"{current['datetime']}: {intensity}{direction} {price_change_pct:+.2f}%, {volume_desc} {volume_change_pct:+.1f}%, 波幅 {range_pct:.2f}%")
        
        return "\\n".join(lines)
    
    @staticmethod 
    def to_structured_json(df: pd.DataFrame, include_analysis: bool = True) -> str:
        """
        格式C: 结构化JSON + 关键指标预计算
        包含原始数据和预处理分析
        """
        # 基础数据结构
        data = {
            "metadata": {
                "symbol": "ETH/USDT",
                "contract_type": "perpetual",
                "timeframe": "1h",
                "total_bars": len(df),
                "time_range": {
                    "start": str(df['datetime'].iloc[0]),
                    "end": str(df['datetime'].iloc[-1])
                }
            },
            "market_summary": {
                "price_action": {
                    "open": float(df['open'].iloc[0]),
                    "close": float(df['close'].iloc[-1]),
                    "high": float(df['high'].max()),
                    "low": float(df['low'].min()),
                    "change_percent": float(((df['close'].iloc[-1] / df['open'].iloc[0]) - 1) * 100)
                },
                "volume_profile": {
                    "total_volume": float(df['volume'].sum()),
                    "average_volume": float(df['volume'].mean()),
                    "max_volume_bar": float(df['volume'].max()),
                    "volume_trend": "increasing" if df['volume'].tail(10).mean() > df['volume'].head(10).mean() else "decreasing"
                }
            },
            "candlestick_data": []
        }
        
        # 添加蜡烛图数据
        for _, row in df.iterrows():
            candle = {
                "timestamp": str(row['datetime']),
                "ohlcv": {
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                }
            }
            
            # 添加计算字段
            body_size = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            
            candle["analysis"] = {
                "candle_type": "bullish" if row['close'] > row['open'] else "bearish" if row['close'] < row['open'] else "doji",
                "body_size_percent": float((body_size / total_range * 100) if total_range > 0 else 0),
                "upper_shadow": float(row['high'] - max(row['open'], row['close'])),
                "lower_shadow": float(min(row['open'], row['close']) - row['low'])
            }
            
            data["candlestick_data"].append(candle)
        
        # 添加技术指标（如果数据中存在）
        if include_analysis and 'rsi' in df.columns:
            data["technical_indicators"] = {
                "rsi_current": float(df['rsi'].iloc[-1]) if not pd.isna(df['rsi'].iloc[-1]) else None,
                "rsi_overbought": (df['rsi'] > 70).sum(),
                "rsi_oversold": (df['rsi'] < 30).sum()
            }
        
        if include_analysis and 'macd' in df.columns:
            data["technical_indicators"]["macd"] = {
                "current": float(df['macd'].iloc[-1]) if not pd.isna(df['macd'].iloc[-1]) else None,
                "signal": float(df['macd_signal'].iloc[-1]) if 'macd_signal' in df.columns and not pd.isna(df['macd_signal'].iloc[-1]) else None
            }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def to_pattern_description(df: pd.DataFrame, include_vsa: bool = True, 
                             include_perpetual_context: bool = True) -> str:
        """
        格式D: 增强的VPA专业分析格式
        整合VSA分析和永续合约特色，基于Anna Coulling理论
        
        Args:
            df: OHLCV数据
            include_vsa: 是否包含VSA分析
            include_perpetual_context: 是否包含永续合约背景
        """
        lines = ["# ETH/USDT 永续合约VPA专业分析\\n"]
        
        # 市场概况
        lines.append("## 🎯 市场概况")
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        high_price = df['high'].max()
        low_price = df['low'].min()
        total_volume = df['volume'].sum()
        avg_volume = df['volume'].mean()
        
        price_change = (end_price - start_price) / start_price * 100
        lines.append(f"- 价格区间: {low_price:.2f} - {high_price:.2f} USDT")
        lines.append(f"- 期间变动: {start_price:.2f} → {end_price:.2f} ({price_change:+.2f}%)")
        lines.append(f"- 总成交量: {total_volume:,.0f}, 平均: {avg_volume:,.0f}")
        lines.append("")
        
        # VSA核心分析 (如果启用)
        if include_vsa:
            lines.extend(DataFormatter._format_vsa_analysis(df))
        
        # 永续合约背景 (如果启用)
        if include_perpetual_context:
            lines.extend(DataFormatter._format_perpetual_context())
        
        # 关键K线形态识别
        patterns_found = DataFormatter._identify_key_patterns(df)
        
        if patterns_found:
            lines.append("## 📊 关键K线形态")
            lines.extend(patterns_found)
        
        # Wyckoff市场阶段分析提示
        lines.append("## 🎓 Wyckoff市场阶段分析框架")
        lines.append("请基于以上数据判断当前市场阶段:")
        lines.append("- **Accumulation(吸筹)**: Smart Money在低位建仓")
        lines.append("- **Markup(拉升)**: 价格上升阶段，成交量应配合")
        lines.append("- **Distribution(派发)**: Smart Money在高位出货")  
        lines.append("- **Markdown(下跌)**: 价格下降阶段，关注Volume Climax")
        lines.append("")
        
        return "\\n".join(lines)
    
    @staticmethod
    def _format_vsa_analysis(df: pd.DataFrame) -> List[str]:
        """格式化VSA分析内容"""
        lines = []
        lines.append("## 🔍 VSA (Volume Spread Analysis) 核心指标")
        
        # 最近几根K线的VSA分析
        recent_bars = df.tail(10)
        vsa_highlights = []
        
        for i, (_, row) in enumerate(recent_bars.iterrows()):
            bar_analysis = []
            
            # 计算VSA指标
            open_price = row['open']
            high_price = row['high'] 
            low_price = row['low']
            close_price = row['close']
            volume = row['volume']
            
            spread = high_price - low_price
            body_size = abs(close_price - open_price)
            close_position = (close_price - low_price) / spread if spread > 0 else 0.5
            
            # Volume比较 (与平均值)
            if i >= 5:  # 有足够历史数据
                recent_avg_vol = recent_bars['volume'].iloc[max(0, i-5):i].mean()
                vol_ratio = volume / recent_avg_vol if recent_avg_vol > 0 else 1.0
            else:
                vol_ratio = 1.0
            
            # VSA信号识别
            datetime_str = row['datetime']
            is_up = close_price > open_price
            
            # Wide Spread + High Volume
            if spread > recent_bars['high'].subtract(recent_bars['low']).quantile(0.7) and vol_ratio > 1.5:
                if close_position > 0.7:
                    bar_analysis.append(f"✅ **{datetime_str}**: Wide Spread + 高量收高位 → Professional Buying")
                elif close_position < 0.3:
                    bar_analysis.append(f"⚠️ **{datetime_str}**: Wide Spread + 高量收低位 → Selling Pressure")
            
            # Narrow Spread + Low Volume  
            elif spread < recent_bars['high'].subtract(recent_bars['low']).quantile(0.3) and vol_ratio < 0.8:
                if is_up:
                    bar_analysis.append(f"🔴 **{datetime_str}**: No Demand → 上涨缺乏成交量支持")
                else:
                    bar_analysis.append(f"🟢 **{datetime_str}**: No Supply → 下跌缺乏真实卖压")
            
            # Climax Volume
            elif vol_ratio > 2.0:
                bar_analysis.append(f"🔥 **{datetime_str}**: Climax Volume (量比{vol_ratio:.1f}) → 可能的转折点")
            
            vsa_highlights.extend(bar_analysis)
        
        if vsa_highlights:
            lines.extend(vsa_highlights)
        else:
            lines.append("- 近期未发现明显VSA信号，市场处于相对平衡状态")
        
        lines.append("")
        return lines
    
    @staticmethod
    def _format_perpetual_context() -> List[str]:
        """格式化永续合约背景信息"""
        lines = []
        lines.append("## ⚡ 永续合约VPA分析要点")
        lines.append("**请特别关注以下永续合约特有因素:**")
        lines.append("- 📈 **资金费率影响**: 正费率=多头支付(看涨情绪)，负费率=空头支付(看跌情绪)")
        lines.append("- 🎯 **持仓量(OI)变化**: OI增加+价格上涨=新多头开仓，OI减少+价格下跌=多头平仓")
        lines.append("- ⚡ **杠杆效应放大**: 散户情绪被杠杆放大，强平cascade创造额外Supply/Demand")
        lines.append("- 🎪 **Smart Money操控**: 利用资金费率和杠杆诱导散户开仓，然后反向操作")
        lines.append("- 🌊 **多空转换**: 资金费率变化导致持仓结构快速转换，创造新的VPA信号")
        lines.append("")
        return lines
    
    @staticmethod  
    def _identify_key_patterns(df: pd.DataFrame) -> List[str]:
        """识别关键K线形态"""
        patterns_found = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            patterns = []
            
            # 基础形态识别
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            volume = row['volume']
            
            body_size = abs(close_price - open_price)
            upper_shadow = high_price - max(open_price, close_price)
            lower_shadow = min(open_price, close_price) - low_price
            total_range = high_price - low_price
            
            # 蜡烛线类型
            if close_price > open_price:
                candle_type = "阳线"
            elif close_price < open_price:
                candle_type = "阴线"
            else:
                candle_type = "十字线"
            
            # VPA相关形态识别 (结合成交量)
            if total_range > 0:
                body_ratio = body_size / total_range
                upper_shadow_ratio = upper_shadow / total_range
                lower_shadow_ratio = lower_shadow / total_range
                
                # 计算成交量比率 (与前10根平均比较)
                if i >= 10:
                    avg_volume = df['volume'].iloc[max(0, i-10):i].mean()
                    vol_ratio = volume / avg_volume if avg_volume > 0 else 1.0
                else:
                    vol_ratio = 1.0
                
                # VPA关键形态识别
                
                # 1. Climax Bar (Volume Climax)
                if vol_ratio > 2.0 and total_range > df['high'].subtract(df['low']).iloc[max(0, i-20):i].quantile(0.8):
                    if close_price > open_price:
                        patterns.append(f"📈 Buying Climax (量比{vol_ratio:.1f})")
                    else:
                        patterns.append(f"📉 Selling Climax (量比{vol_ratio:.1f})")
                
                # 2. No Demand (上涨但成交量低)
                elif close_price > open_price and vol_ratio < 0.7 and body_ratio > 0.3:
                    patterns.append("🔴 No Demand (无量上涨)")
                
                # 3. No Supply (下跌但成交量低)  
                elif close_price < open_price and vol_ratio < 0.7 and body_ratio > 0.3:
                    patterns.append("🟢 No Supply (无量下跌)")
                
                # 4. Upthrust (高位长上影大量)
                elif (upper_shadow_ratio > 0.6 and vol_ratio > 1.5 and 
                      close_price < (high_price + low_price) / 2):
                    patterns.append("⚠️ Upthrust (高位假突破)")
                
                # 5. Spring (低位长下影后收回)  
                elif (lower_shadow_ratio > 0.6 and vol_ratio > 1.2 and
                      close_price > (high_price + low_price) / 2):
                    patterns.append("✅ Spring (低位测试成功)")
                
                # 6. Wide Spread + Close Position分析
                elif total_range > df['high'].subtract(df['low']).iloc[max(0, i-20):i].quantile(0.7):
                    close_position = (close_price - low_price) / total_range
                    if close_position > 0.8 and vol_ratio > 1.2:
                        patterns.append("💪 Wide Spread收高位 (Professional Buying)")
                    elif close_position < 0.2 and vol_ratio > 1.2:
                        patterns.append("😰 Wide Spread收低位 (Selling Pressure)")
                
                # 7. Narrow Spread分析
                elif total_range < df['high'].subtract(df['low']).iloc[max(0, i-20):i].quantile(0.3):
                    if vol_ratio < 0.8:
                        patterns.append("😴 Narrow Spread低量 (缺乏兴趣)")
            
            # 多根K线VPA组合形态
            if i > 0:
                prev_row = df.iloc[i-1]
                prev_close = prev_row['close']
                prev_volume = prev_row['volume']
                
                # Test Bar (测试前期低点/高点)
                if abs(low_price - df['low'].iloc[max(0, i-20):i].min()) / low_price < 0.01:
                    if vol_ratio < 0.8:
                        patterns.append("🧪 Test (低量测试低点)")
                
                # Stopping Volume (阻止性成交量)
                if (close_price > prev_close and vol_ratio > 2.0 and 
                    body_ratio < 0.3):  # 高量但实体小
                    patterns.append("🛑 Stopping Volume (阻止性成交量)")
            
            # 只记录有VPA意义的形态
            if patterns:
                datetime_str = row['datetime']
                pattern_desc = f"**{datetime_str}**: {candle_type} - {', '.join(patterns)}"
                pattern_desc += f" (价格:{close_price:.2f}, 量:{volume:,.0f})"
                patterns_found.append(pattern_desc)
        
        return patterns_found
    
    @staticmethod
    def estimate_tokens_by_format(df: pd.DataFrame) -> Dict[str, int]:
        """
        估算不同格式的token使用量
        """
        formatter = DataFormatter()
        
        estimates = {}
        
        # CSV格式
        csv_data = formatter.to_csv_format(df)
        estimates['csv'] = len(csv_data.split()) + len(csv_data) // 4  # 粗略估算
        
        # 文本格式
        text_data = formatter.to_text_narrative(df)
        estimates['text'] = len(text_data.split())
        
        # JSON格式
        json_data = formatter.to_structured_json(df)
        estimates['json'] = len(json_data.split()) + len(json_data) // 3  # JSON的token密度更高
        
        # 模式描述格式
        pattern_data = formatter.to_pattern_description(df)
        estimates['pattern'] = len(pattern_data.split())
        
        return estimates