#!/usr/bin/env python3
"""
WebSocket VPA系统演示脚本
展示币安WebSocket API与Anna Coulling VSA理论的完美结合

功能演示：
1. 实时K线完成检测 (毫秒级精度)
2. Anna Coulling VSA专业分析
3. 多时间框架同步监控
4. 成本优化和系统稳定性
5. 数据源智能切换 (WebSocket + REST备用)
"""

import asyncio
import logging
import sys
import signal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# 设置项目路径
sys.path.append('/Users/aries/Dve/ai_trader')

from ai.realtime_websocket_monitor import WebSocketVPAMonitor, AnalysisResult
from ai.hybrid_data_manager import HybridDataManager, DataHealth, DataSource
from data.binance_websocket import KlineData

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VPADemoAnalyzer:
    """VPA演示分析器"""
    
    def __init__(self):
        self.analysis_count = 0
        self.vsa_signals_detected = {}
        self.cost_summary = {'total': 0.0, 'by_timeframe': {}}
        self.performance_metrics = []
        self.start_time = datetime.now()
        
    def analyze_vpa_result(self, result: AnalysisResult):
        """分析VPA结果并生成洞察"""
        self.analysis_count += 1
        
        if result.success:
            # 统计成本
            self.cost_summary['total'] += result.cost
            tf = result.timeframe
            if tf not in self.cost_summary['by_timeframe']:
                self.cost_summary['by_timeframe'][tf] = 0.0
            self.cost_summary['by_timeframe'][tf] += result.cost
            
            # 统计VSA信号
            vsa_signals = result.vpa_signals.get('vsa_signals', [])
            for signal in vsa_signals:
                if signal not in self.vsa_signals_detected:
                    self.vsa_signals_detected[signal] = []
                self.vsa_signals_detected[signal].append({
                    'timeframe': tf,
                    'timestamp': result.timestamp,
                    'price': result.kline_data.close_price
                })
            
            # 性能指标
            self.performance_metrics.append({
                'timeframe': tf,
                'analysis_time': result.analysis_time,
                'model': result.model_used,
                'timestamp': result.timestamp
            })
            
            # 输出重要分析结果
            self._print_important_signals(result)
    
    def _print_important_signals(self, result: AnalysisResult):
        """输出重要的VPA信号"""
        signals = result.vpa_signals
        tf = result.timeframe
        price = result.kline_data.close_price
        
        # 检查关键VSA信号
        vsa_signals = signals.get('vsa_signals', [])
        critical_signals = ['climax_volume', 'upthrust', 'spring', 'no_demand', 'no_supply']
        
        important_detected = [sig for sig in vsa_signals if sig in critical_signals]
        
        if important_detected or signals.get('market_phase') in ['distribution', 'accumulation']:
            print(f"\n🎯 重要VPA信号 [{tf}] @ ${price:.2f}")
            print(f"   市场阶段: {signals.get('market_phase', 'unknown').upper()}")
            print(f"   VPA信号: {signals.get('vpa_signal', 'neutral').upper()}")
            
            if important_detected:
                print(f"   🚨 关键VSA信号: {', '.join(important_detected).upper()}")
                
            if signals.get('market_phase') == 'distribution':
                print("   ⚠️ Anna Coulling信号: 可能的分配阶段，注意卖压")
            elif signals.get('market_phase') == 'accumulation':
                print("   ✅ Anna Coulling信号: 可能的积累阶段，观察买盘")
    
    def get_summary_report(self) -> str:
        """生成摘要报告"""
        runtime = (datetime.now() - self.start_time).total_seconds()
        
        report = [
            "\n" + "="*80,
            "📊 WebSocket VPA演示系统 - 分析摘要报告",
            "="*80,
            f"⏱️ 运行时长: {runtime/60:.1f}分钟",
            f"🔍 完成分析: {self.analysis_count}次",
            f"💰 总成本: ${self.cost_summary['total']:.4f}",
            f"⚡ 平均分析时间: {sum(m['analysis_time'] for m in self.performance_metrics)/len(self.performance_metrics):.1f}s" if self.performance_metrics else "N/A"
        ]
        
        # 按时间框架统计
        if self.cost_summary['by_timeframe']:
            report.append("\n📈 时间框架分析统计:")
            for tf, cost in self.cost_summary['by_timeframe'].items():
                count = len([m for m in self.performance_metrics if m['timeframe'] == tf])
                avg_cost = cost / count if count > 0 else 0
                report.append(f"   {tf:>4}: {count:>2}次分析, ${avg_cost:.4f}/次")
        
        # VSA信号统计
        if self.vsa_signals_detected:
            report.append("\n🎯 检测到的Anna Coulling VSA信号:")
            for signal, occurrences in self.vsa_signals_detected.items():
                report.append(f"   {signal.upper():>15}: {len(occurrences)}次")
                
                # 显示最近的信号
                recent = sorted(occurrences, key=lambda x: x['timestamp'], reverse=True)[:3]
                for occ in recent:
                    report.append(f"      └─ {occ['timeframe']} @ ${occ['price']:.2f} "
                                f"({occ['timestamp'].strftime('%H:%M:%S')})")
        
        # 成本效率分析
        if self.analysis_count > 0 and runtime > 0:
            analyses_per_hour = self.analysis_count / (runtime / 3600)
            cost_per_hour = self.cost_summary['total'] / (runtime / 3600)
            report.extend([
                "\n💡 效率指标:",
                f"   分析频率: {analyses_per_hour:.1f}次/小时",
                f"   成本速率: ${cost_per_hour:.3f}/小时",
                f"   信号密度: {len(self.vsa_signals_detected)/(runtime/3600):.1f}个VSA信号/小时"
            ])
        
        report.append("="*80)
        return "\n".join(report)

class WebSocketVPADemo:
    """WebSocket VPA演示主类"""
    
    def __init__(self):
        self.monitor: Optional[WebSocketVPAMonitor] = None
        self.data_manager: Optional[HybridDataManager] = None
        self.analyzer = VPADemoAnalyzer()
        self.is_running = False
        
        # 设置信号处理器用于优雅停止
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"\n📡 接收到停止信号 {signum}")
        self.is_running = False
    
    async def start_demo(self, duration_minutes: int = 15):
        """启动演示"""
        logger.info("🚀 启动WebSocket VPA演示系统")
        logger.info(f"⏱️ 演示时长: {duration_minutes}分钟")
        logger.info("💡 展示功能: 实时K线 + Anna Coulling VSA + 成本优化")
        
        try:
            self.is_running = True
            
            # 1. 创建VPA监控器
            self.monitor = WebSocketVPAMonitor('ETH/USDT')
            
            # 演示配置：启用更多时间框架
            demo_timeframes = ['5m', '15m', '1h', '4h']  # 适合演示的时间框架
            for tf in demo_timeframes:
                if tf in self.monitor.timeframe_configs:
                    self.monitor.timeframe_configs[tf]['enabled'] = True
                    # 降低分析限制用于演示
                    self.monitor.timeframe_configs[tf]['max_daily_analyses'] = 10
            
            # 设置较低的预算用于演示
            self.monitor.max_daily_budget = 1.0  # $1演示预算
            
            # 2. 设置回调函数
            self.monitor.add_vpa_signal_callback(self._on_vpa_result)
            self.monitor.add_cost_alert_callback(self._on_cost_alert)
            self.monitor.add_error_callback(self._on_error)
            
            # 3. 创建数据管理器 (可选，用于展示稳定性)
            self.data_manager = HybridDataManager('ETH/USDT', demo_timeframes)
            self.data_manager.add_health_change_callback(self._on_health_change)
            self.data_manager.add_source_switch_callback(self._on_source_switch)
            
            # 4. 并行启动服务
            logger.info("🔧 启动服务组件...")
            
            tasks = [
                asyncio.create_task(self.monitor.start_monitoring(), name="vpa_monitor"),
                asyncio.create_task(self.data_manager.start(), name="data_manager"),
                asyncio.create_task(self._demo_status_reporter(), name="status_reporter")
            ]
            
            # 5. 运行指定时长或直到中断
            timeout_task = asyncio.create_task(asyncio.sleep(duration_minutes * 60), name="timeout")
            tasks.append(timeout_task)
            
            logger.info("✅ 所有组件已启动，开始演示...")
            self._print_demo_header()
            
            # 等待任务完成或超时
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except KeyboardInterrupt:
            logger.info("⏹️ 演示被用户中断")
        except Exception as e:
            logger.error(f"❌ 演示过程中出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()
    
    async def _demo_status_reporter(self):
        """演示状态报告器"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 每分钟报告一次
                
                if self.monitor:
                    stats = self.monitor.get_stats()
                    logger.info(f"📊 演示进度: 接收K线{stats.get('total_klines_received', 0)}, "
                              f"完成分析{stats.get('total_analyses_completed', 0)}, "
                              f"成本${stats.get('total_cost', 0):.3f}")
                
            except Exception as e:
                logger.error(f"❌ 状态报告错误: {e}")
    
    def _print_demo_header(self):
        """打印演示标题"""
        print("\n" + "="*80)
        print("🎯 WebSocket VPA 实时监控演示 - Anna Coulling理论应用")
        print("="*80)
        print("💡 观察要点:")
        print("   • K线完成检测精度 (毫秒级 vs 秒级)")
        print("   • VSA信号实时识别 (Climax Volume, Upthrust, Spring等)")
        print("   • 多时间框架信号一致性")
        print("   • 成本控制和数据源稳定性")
        print("   • Anna Coulling市场阶段判断 (积累/分配/上升/下降)")
        print("-"*80)
        print("⏱️ 实时监控中... (Ctrl+C 停止)")
        print()
    
    def _on_vpa_result(self, result: AnalysisResult):
        """VPA结果回调"""
        self.analyzer.analyze_vpa_result(result)
        
        if result.success:
            # 简化输出，避免刷屏
            signals = result.vpa_signals
            tf = result.timeframe
            price = result.kline_data.close_price
            
            print(f"📊 [{tf}] ${price:.2f} | "
                  f"阶段:{signals.get('market_phase', '?')[:4]} | "
                  f"信号:{signals.get('vpa_signal', '?')[:4]} | "
                  f"${result.cost:.3f} | {result.analysis_time:.1f}s")
    
    def _on_cost_alert(self, current: float, budget: float):
        """成本告警回调"""
        print(f"💰 成本告警: ${current:.3f}/${budget:.2f} ({current/budget*100:.1f}%)")
    
    def _on_error(self, error: Exception):
        """错误回调"""
        print(f"❌ 系统错误: {error}")
    
    def _on_health_change(self, health: DataHealth):
        """数据健康状态变化"""
        print(f"🏥 数据质量: {health.data_quality.value.upper()} | "
              f"源: {health.active_source.value.upper()}")
    
    def _on_source_switch(self, old_source: DataSource, new_source: DataSource):
        """数据源切换"""
        print(f"🔄 数据源切换: {old_source.value.upper()} → {new_source.value.upper()}")
    
    async def _cleanup(self):
        """清理资源"""
        logger.info("🧹 清理演示资源...")
        
        self.is_running = False
        
        if self.monitor:
            await self.monitor.stop_monitoring()
        
        if self.data_manager:
            await self.data_manager.stop()
        
        # 输出最终报告
        print(self.analyzer.get_summary_report())
        
        logger.info("✅ 演示清理完成")

async def main():
    """主函数"""
    print("🚀 WebSocket VPA演示系统")
    print("基于币安WebSocket API + Anna Coulling VSA理论")
    print("="*50)
    
    # 获取运行参数
    duration = 15  # 默认15分钟
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("⚠️ 无效的时长参数，使用默认15分钟")
    
    print(f"演示时长: {duration}分钟")
    print("按 Ctrl+C 可提前停止演示\n")
    
    # 检查配置
    try:
        from config import Settings
        Settings.validate()
        print("✅ API配置验证通过")
    except Exception as e:
        print(f"❌ API配置验证失败: {e}")
        print("请确保.env文件中配置了OPENROUTER_API_KEY")
        return
    
    # 启动演示
    demo = WebSocketVPADemo()
    await demo.start_demo(duration)
    
    print("\n🏁 WebSocket VPA演示结束")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
    except Exception as e:
        logger.error(f"❌ 演示程序异常: {e}")
        import traceback
        traceback.print_exc()