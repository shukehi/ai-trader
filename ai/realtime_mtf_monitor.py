#!/usr/bin/env python3
"""
实时多时间框架VPA监控系统
基于Anna Coulling VSA理论，提供智能化的K线结束触发分析

核心功能：
1. 智能K线结束检测和分析触发
2. 多时间框架优先级管理
3. 成本控制和分析频率优化
4. VSA信号变化检测和告警
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import time

from ai.timeframe_analyzer import TimeframeAnalyzer, MultiTimeframeAnalysis
from ai.openrouter_client import OpenRouterClient
from ai.trading_prompts import TradingPromptTemplates
from data.binance_fetcher import BinanceFetcher
from formatters.data_formatter import DataFormatter

logger = logging.getLogger(__name__)

class MonitorPriority(Enum):
    """监控优先级"""
    CRITICAL = "critical"     # 日线、4小时 (VPA价值最高)
    HIGH = "high"            # 1小时、30分钟 (执行重要)
    MEDIUM = "medium"        # 15分钟 (入场确认)
    LOW = "low"             # 5分钟 (噪音高，谨慎使用)

@dataclass
class TimeframeMonitorConfig:
    """时间框架监控配置"""
    timeframe: str
    priority: MonitorPriority
    vpa_value_score: int           # VPA分析价值 (0-100)
    cost_per_analysis: float       # 单次分析成本估算
    max_daily_analysis: int        # 每日最大分析次数
    smart_money_visibility: int    # 专业资金可见性 (0-100)
    noise_ratio: int              # 噪音比例 (0-100)
    enabled: bool = True
    last_analysis_time: Optional[datetime] = None
    analysis_count_today: int = 0

@dataclass
class VPASignalChange:
    """VPA信号变化检测"""
    timeframe: str
    timestamp: datetime
    old_signal: Dict[str, Any] = field(default_factory=dict)
    new_signal: Dict[str, Any] = field(default_factory=dict)
    change_type: str = "update"    # new, update, critical_change
    significance: float = 0.0      # 变化重要性 (0-1)

class RealtimeMultiTimeframeMonitor:
    """
    实时多时间框架VPA监控器
    
    智能化Anna Coulling VSA分析，K线结束时自动触发
    """
    
    def __init__(self, symbol: str = 'ETH/USDT'):
        """初始化实时监控器"""
        self.symbol = symbol
        self.fetcher = BinanceFetcher()
        self.timeframe_analyzer = TimeframeAnalyzer()
        self.openrouter_client = OpenRouterClient()
        self.formatter = DataFormatter()
        
        # 监控配置 (基于Anna Coulling理论和成本效益分析)
        self.monitor_configs = {
            '1d': TimeframeMonitorConfig(
                timeframe='1d',
                priority=MonitorPriority.CRITICAL,
                vpa_value_score=100,
                cost_per_analysis=0.05,  # 深度分析
                max_daily_analysis=1,    # 每日一次
                smart_money_visibility=95,
                noise_ratio=5
            ),
            '4h': TimeframeMonitorConfig(
                timeframe='4h',
                priority=MonitorPriority.CRITICAL,
                vpa_value_score=95,
                cost_per_analysis=0.03,
                max_daily_analysis=6,    # 每日最多6次
                smart_money_visibility=90,
                noise_ratio=15
            ),
            '1h': TimeframeMonitorConfig(
                timeframe='1h',
                priority=MonitorPriority.HIGH,
                vpa_value_score=80,
                cost_per_analysis=0.02,
                max_daily_analysis=24,   # 每小时一次
                smart_money_visibility=75,
                noise_ratio=30
            ),
            '30m': TimeframeMonitorConfig(
                timeframe='30m',
                priority=MonitorPriority.HIGH,
                vpa_value_score=60,
                cost_per_analysis=0.015,
                max_daily_analysis=20,   # 控制频率
                smart_money_visibility=60,
                noise_ratio=45
            ),
            '15m': TimeframeMonitorConfig(
                timeframe='15m',
                priority=MonitorPriority.MEDIUM,
                vpa_value_score=45,
                cost_per_analysis=0.01,
                max_daily_analysis=30,   # 限制频率
                smart_money_visibility=40,
                noise_ratio=60
            ),
            '5m': TimeframeMonitorConfig(
                timeframe='5m',
                priority=MonitorPriority.LOW,
                vpa_value_score=15,
                cost_per_analysis=0.005,
                max_daily_analysis=50,   # 严格限制
                smart_money_visibility=10,
                noise_ratio=85,
                enabled=False  # 默认关闭，噪音太高
            )
        }
        
        # 运行状态
        self.is_monitoring = False
        self.previous_signals: Dict[str, Dict[str, Any]] = {}
        self.daily_cost = 0.0
        self.max_daily_budget = 10.0  # 每日最大预算
        
        # 回调函数
        self.signal_change_callback: Optional[Callable] = None
        self.cost_alert_callback: Optional[Callable] = None
        
    def set_signal_change_callback(self, callback: Callable):
        """设置信号变化回调函数"""
        self.signal_change_callback = callback
        
    def set_cost_alert_callback(self, callback: Callable):
        """设置成本告警回调函数"""
        self.cost_alert_callback = callback
    
    async def start_monitoring(self):
        """开始实时监控"""
        logger.info(f"🚀 开始实时多时间框架VPA监控: {self.symbol}")
        logger.info(f"💰 每日预算: ${self.max_daily_budget:.2f}")
        
        self.is_monitoring = True
        
        # 显示监控配置
        self._log_monitor_configuration()
        
        # 并发监控各时间框架
        tasks = []
        for tf, config in self.monitor_configs.items():
            if config.enabled:
                task = asyncio.create_task(self._monitor_timeframe(tf, config))
                tasks.append(task)
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        finally:
            self.is_monitoring = False
            logger.info("⏹️ 多时间框架VPA监控已停止")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        logger.info("🛑 正在停止多时间框架VPA监控...")
    
    async def _monitor_timeframe(self, timeframe: str, config: TimeframeMonitorConfig):
        """监控单个时间框架"""
        logger.info(f"📊 开始监控时间框架: {timeframe} (优先级: {config.priority.value})")
        
        while self.is_monitoring:
            try:
                # 检查是否需要分析
                if await self._should_analyze(timeframe, config):
                    # 执行VPA分析
                    analysis_result = await self._perform_vpa_analysis(timeframe, config)
                    
                    if analysis_result:
                        # 检测信号变化
                        signal_changes = self._detect_signal_changes(timeframe, analysis_result)
                        
                        if signal_changes:
                            # 触发信号变化回调
                            if self.signal_change_callback:
                                self.signal_change_callback(signal_changes)
                            
                            self._log_signal_changes(signal_changes)
                        
                        # 更新配置状态
                        config.last_analysis_time = datetime.now()
                        config.analysis_count_today += 1
                        
                        # 更新成本
                        self.daily_cost += config.cost_per_analysis
                        
                        # 成本告警
                        if self.daily_cost > self.max_daily_budget * 0.8:
                            if self.cost_alert_callback:
                                self.cost_alert_callback(self.daily_cost, self.max_daily_budget)
                
                # 等待到下一个K线结束时间
                await self._wait_for_next_candle(timeframe)
                
            except Exception as e:
                logger.error(f"监控 {timeframe} 时出错: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟
    
    async def _should_analyze(self, timeframe: str, config: TimeframeMonitorConfig) -> bool:
        """判断是否应该执行分析"""
        # 检查是否启用
        if not config.enabled:
            return False
            
        # 检查每日分析次数限制
        if config.analysis_count_today >= config.max_daily_analysis:
            return False
            
        # 检查每日预算限制
        if self.daily_cost + config.cost_per_analysis > self.max_daily_budget:
            return False
        
        # 检查时间间隔 (避免重复分析)
        if config.last_analysis_time:
            time_diff = datetime.now() - config.last_analysis_time
            min_interval = self._get_min_analysis_interval(timeframe)
            if time_diff < min_interval:
                return False
        
        # 检查K线是否刚结束
        if not self._is_candle_just_finished(timeframe):
            return False
            
        return True
    
    def _get_min_analysis_interval(self, timeframe: str) -> timedelta:
        """获取最小分析间隔"""
        intervals = {
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return intervals.get(timeframe, timedelta(minutes=60))
    
    def _is_candle_just_finished(self, timeframe: str) -> bool:
        """检查K线是否刚刚结束"""
        now = datetime.now()
        
        # 简化检查逻辑 - 实际应该更精确地检测K线结束时间
        if timeframe == '5m':
            return now.minute % 5 == 0 and now.second < 30
        elif timeframe == '15m':
            return now.minute % 15 == 0 and now.second < 30
        elif timeframe == '30m':
            return now.minute % 30 == 0 and now.second < 30
        elif timeframe == '1h':
            return now.minute == 0 and now.second < 30
        elif timeframe == '4h':
            return now.hour % 4 == 0 and now.minute == 0 and now.second < 30
        elif timeframe == '1d':
            return now.hour == 0 and now.minute == 0 and now.second < 30
        
        return False
    
    async def _perform_vpa_analysis(self, timeframe: str, config: TimeframeMonitorConfig) -> Optional[Dict[str, Any]]:
        """执行VPA分析"""
        try:
            logger.info(f"🔍 执行 {timeframe} VPA分析...")
            start_time = time.time()
            
            # 获取数据
            limit = 100 if timeframe in ['1h', '4h', '1d'] else 50
            df = self.fetcher.get_ohlcv(self.symbol, timeframe, limit)
            
            # 格式化数据
            formatted_data = self.formatter.to_pattern_description(df.tail(50))
            
            # 选择模型 (基于时间框架重要性)
            model = self._select_model_for_timeframe(config.priority)
            
            # 获取Anna Coulling VSA提示词
            prompt = TradingPromptTemplates.get_trading_signal_prompt()
            full_prompt = prompt + "\n\n" + formatted_data
            
            # 执行分析
            result = self.openrouter_client.generate_response(full_prompt, model)
            
            if result.get('success'):
                analysis_time = time.time() - start_time
                logger.info(f"✅ {timeframe} VPA分析完成 ({analysis_time:.1f}s, ${config.cost_per_analysis:.3f})")
                
                # 解析VPA信号 (简化版)
                vpa_signals = self._parse_vpa_signals(result['analysis'])
                
                return {
                    'timeframe': timeframe,
                    'timestamp': datetime.now(),
                    'raw_analysis': result['analysis'],
                    'vpa_signals': vpa_signals,
                    'model_used': model,
                    'analysis_time': analysis_time,
                    'cost': config.cost_per_analysis
                }
            else:
                logger.error(f"❌ {timeframe} VPA分析失败: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"VPA分析异常 {timeframe}: {e}")
            return None
    
    def _select_model_for_timeframe(self, priority: MonitorPriority) -> str:
        """根据时间框架优先级选择模型"""
        model_mapping = {
            MonitorPriority.CRITICAL: 'gpt5-mini',      # 最重要的分析
            MonitorPriority.HIGH: 'gpt4o-mini',         # 平衡质量和成本
            MonitorPriority.MEDIUM: 'gemini-flash',     # 快速分析
            MonitorPriority.LOW: 'gemini-flash'         # 经济分析
        }
        return model_mapping.get(priority, 'gpt4o-mini')
    
    def _parse_vpa_signals(self, analysis_text: str) -> Dict[str, Any]:
        """解析VPA信号 (简化版)"""
        # 这里应该实现更复杂的NLP解析
        # 临时使用关键词匹配
        signals = {
            'market_phase': 'unknown',
            'vpa_signal': 'neutral',
            'price_direction': 'sideways',
            'confidence': 'medium',
            'key_levels': []
        }
        
        # 市场阶段识别
        if 'accumulation' in analysis_text.lower():
            signals['market_phase'] = 'accumulation'
        elif 'distribution' in analysis_text.lower():
            signals['market_phase'] = 'distribution'
        elif 'markup' in analysis_text.lower():
            signals['market_phase'] = 'markup'
        elif 'markdown' in analysis_text.lower():
            signals['market_phase'] = 'markdown'
        
        # VPA信号识别
        if 'bullish' in analysis_text.lower() or '做多' in analysis_text:
            signals['vpa_signal'] = 'bullish'
        elif 'bearish' in analysis_text.lower() or '做空' in analysis_text:
            signals['vpa_signal'] = 'bearish'
        
        # 价格方向
        if 'up' in analysis_text.lower() or '上升' in analysis_text:
            signals['price_direction'] = 'up'
        elif 'down' in analysis_text.lower() or '下降' in analysis_text:
            signals['price_direction'] = 'down'
        
        return signals
    
    def _detect_signal_changes(self, timeframe: str, current_analysis: Dict[str, Any]) -> List[VPASignalChange]:
        """检测VPA信号变化"""
        changes = []
        
        if timeframe not in self.previous_signals:
            # 第一次分析
            changes.append(VPASignalChange(
                timeframe=timeframe,
                timestamp=current_analysis['timestamp'],
                new_signal=current_analysis['vpa_signals'],
                change_type='new',
                significance=0.5
            ))
        else:
            # 比较信号变化
            old_signals = self.previous_signals[timeframe]['vpa_signals']
            new_signals = current_analysis['vpa_signals']
            
            # 检测关键变化
            significance = 0.0
            change_details = {}
            
            if old_signals.get('market_phase') != new_signals.get('market_phase'):
                significance += 0.4
                change_details['market_phase'] = {
                    'old': old_signals.get('market_phase'),
                    'new': new_signals.get('market_phase')
                }
            
            if old_signals.get('vpa_signal') != new_signals.get('vpa_signal'):
                significance += 0.3
                change_details['vpa_signal'] = {
                    'old': old_signals.get('vpa_signal'),
                    'new': new_signals.get('vpa_signal')
                }
            
            if old_signals.get('price_direction') != new_signals.get('price_direction'):
                significance += 0.2
                change_details['price_direction'] = {
                    'old': old_signals.get('price_direction'),
                    'new': new_signals.get('price_direction')
                }
            
            if significance > 0.1:  # 有意义的变化
                change_type = 'critical_change' if significance > 0.6 else 'update'
                changes.append(VPASignalChange(
                    timeframe=timeframe,
                    timestamp=current_analysis['timestamp'],
                    old_signal=old_signals,
                    new_signal=new_signals,
                    change_type=change_type,
                    significance=significance
                ))
        
        # 更新历史信号
        self.previous_signals[timeframe] = current_analysis
        
        return changes
    
    def _log_signal_changes(self, changes: List[VPASignalChange]):
        """记录信号变化"""
        for change in changes:
            if change.change_type == 'critical_change':
                logger.warning(f"🚨 {change.timeframe} 关键信号变化 (重要性: {change.significance:.2f})")
            else:
                logger.info(f"📊 {change.timeframe} VPA信号更新 (重要性: {change.significance:.2f})")
    
    async def _wait_for_next_candle(self, timeframe: str):
        """等待到下一个K线结束时间"""
        # 简化等待逻辑
        wait_times = {
            '5m': 300,    # 5分钟
            '15m': 900,   # 15分钟
            '30m': 1800,  # 30分钟
            '1h': 3600,   # 1小时
            '4h': 14400,  # 4小时
            '1d': 86400   # 1天
        }
        
        wait_time = wait_times.get(timeframe, 3600)
        await asyncio.sleep(wait_time)
    
    def _log_monitor_configuration(self):
        """记录监控配置"""
        logger.info("📋 多时间框架VPA监控配置:")
        logger.info("-" * 80)
        logger.info(f"{'时间框架':<8} | {'优先级':<12} | {'VPA价值':<8} | {'成本':<8} | {'每日次数':<8} | {'状态':<8}")
        logger.info("-" * 80)
        
        for tf, config in self.monitor_configs.items():
            status = "✅启用" if config.enabled else "❌禁用"
            logger.info(f"{tf:<8} | {config.priority.value:<12} | {config.vpa_value_score:>6}% | ${config.cost_per_analysis:<6.3f} | {config.max_daily_analysis:>6} | {status:<8}")
        
        total_daily_cost = sum(c.cost_per_analysis * c.max_daily_analysis for c in self.monitor_configs.values() if c.enabled)
        logger.info("-" * 80)
        logger.info(f"预计每日最大成本: ${total_daily_cost:.2f} (预算: ${self.max_daily_budget:.2f})")

# 使用示例回调函数
def vpa_signal_change_handler(changes: List[VPASignalChange]):
    """VPA信号变化处理器"""
    for change in changes:
        if change.change_type == 'critical_change':
            print(f"🚨 关键VPA信号变化: {change.timeframe}")
            print(f"   旧信号: {change.old_signal}")
            print(f"   新信号: {change.new_signal}")
            # 这里可以发送通知、邮件、webhook等

def cost_alert_handler(current_cost: float, budget: float):
    """成本告警处理器"""
    utilization = (current_cost / budget) * 100
    print(f"💰 成本告警: 已使用 ${current_cost:.2f}/{budget:.2f} ({utilization:.1f}%)")

# 主函数示例
async def main():
    """主程序示例"""
    monitor = RealtimeMultiTimeframeMonitor('ETH/USDT')
    
    # 设置回调函数
    monitor.set_signal_change_callback(vpa_signal_change_handler)
    monitor.set_cost_alert_callback(cost_alert_handler)
    
    # 开始监控
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())