#!/usr/bin/env python3
"""
WebSocket VPA监控系统测试脚本
验证币安WebSocket API集成和Anna Coulling VSA分析
"""

import asyncio
import logging
import sys
from datetime import datetime

# 设置路径以导入项目模块
sys.path.append('/Users/aries/Dve/ai_trader')

from ai.realtime_websocket_monitor import WebSocketVPAMonitor, AnalysisResult
from data.binance_websocket import ConnectionState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket_vpa_test.log')
    ]
)

logger = logging.getLogger(__name__)

class VPATestMonitor:
    """VPA测试监控器"""
    
    def __init__(self):
        self.vpa_results = []
        self.error_count = 0
        self.cost_alerts = 0
        self.start_time = datetime.now()
    
    def vpa_result_handler(self, result: AnalysisResult):
        """VPA分析结果处理"""
        self.vpa_results.append(result)
        
        if result.success:
            signals = result.vpa_signals
            logger.info(f"🎯 {result.timeframe} VPA分析成功:")
            logger.info(f"   市场阶段: {signals.get('market_phase', 'unknown')}")
            logger.info(f"   VPA信号: {signals.get('vpa_signal', 'neutral')}")
            logger.info(f"   价格方向: {signals.get('price_direction', 'sideways')}")
            
            # VSA专业信号
            vsa_signals = signals.get('vsa_signals', [])
            if vsa_signals:
                logger.info(f"   VSA信号: {', '.join(vsa_signals)}")
            
            logger.info(f"   模型: {result.model_used}")
            logger.info(f"   成本: ${result.cost:.3f}")
            logger.info(f"   耗时: {result.analysis_time:.1f}s")
            
            # 输出分析摘要 (前200字符)
            analysis_summary = result.vpa_analysis[:200] + "..." if len(result.vpa_analysis) > 200 else result.vpa_analysis
            logger.info(f"   分析摘要: {analysis_summary}")
            
        else:
            self.error_count += 1
            logger.error(f"❌ {result.timeframe} VPA分析失败: {result.error}")
    
    def cost_alert_handler(self, current_cost: float, budget: float):
        """成本告警处理"""
        self.cost_alerts += 1
        utilization = (current_cost / budget) * 100
        logger.warning(f"💰 成本告警 #{self.cost_alerts}: ${current_cost:.3f}/${budget:.2f} ({utilization:.1f}%)")
        
        if utilization > 90:
            logger.error("🚨 成本接近预算上限！")
    
    def error_handler(self, error: Exception):
        """系统错误处理"""
        self.error_count += 1
        logger.error(f"❌ 系统错误 #{self.error_count}: {error}")
    
    def get_test_summary(self) -> dict:
        """获取测试摘要"""
        runtime = (datetime.now() - self.start_time).total_seconds()
        
        successful_analyses = [r for r in self.vpa_results if r.success]
        failed_analyses = [r for r in self.vpa_results if not r.success]
        
        # 按时间框架统计
        tf_stats = {}
        for result in successful_analyses:
            tf = result.timeframe
            if tf not in tf_stats:
                tf_stats[tf] = {'count': 0, 'total_cost': 0.0, 'total_time': 0.0}
            tf_stats[tf]['count'] += 1
            tf_stats[tf]['total_cost'] += result.cost
            tf_stats[tf]['total_time'] += result.analysis_time
        
        return {
            'runtime_seconds': runtime,
            'total_analyses': len(self.vpa_results),
            'successful_analyses': len(successful_analyses),
            'failed_analyses': len(failed_analyses),
            'error_count': self.error_count,
            'cost_alerts': self.cost_alerts,
            'total_cost': sum(r.cost for r in successful_analyses),
            'avg_analysis_time': sum(r.analysis_time for r in successful_analyses) / len(successful_analyses) if successful_analyses else 0,
            'timeframe_stats': tf_stats
        }

async def test_websocket_vpa_monitor(duration_minutes: int = 10):
    """测试WebSocket VPA监控系统"""
    logger.info("🧪 开始WebSocket VPA监控系统测试")
    logger.info(f"⏱️ 测试时长: {duration_minutes}分钟")
    
    # 创建测试监控器
    test_monitor = VPATestMonitor()
    
    # 创建VPA监控器 (使用较短时间框架便于测试)
    vpa_monitor = WebSocketVPAMonitor('ETH/USDT')
    
    # 为测试启用更多时间框架
    vpa_monitor.timeframe_configs['5m']['enabled'] = True  # 启用5分钟用于测试
    vpa_monitor.timeframe_configs['15m']['enabled'] = True
    vpa_monitor.timeframe_configs['1h']['enabled'] = True
    
    # 降低预算和分析限制用于测试
    vpa_monitor.max_daily_budget = 2.0  # $2预算用于测试
    for tf_config in vpa_monitor.timeframe_configs.values():
        tf_config['max_daily_analyses'] = 5  # 每个时间框架最多5次分析
    
    # 设置回调函数
    vpa_monitor.add_vpa_signal_callback(test_monitor.vpa_result_handler)
    vpa_monitor.add_cost_alert_callback(test_monitor.cost_alert_handler)
    vpa_monitor.add_error_callback(test_monitor.error_handler)
    
    try:
        logger.info("🚀 启动WebSocket VPA监控...")
        
        # 创建监控任务和超时任务
        monitor_task = asyncio.create_task(vpa_monitor.start_monitoring())
        timeout_task = asyncio.create_task(asyncio.sleep(duration_minutes * 60))
        
        # 等待监控启动或超时
        done, pending = await asyncio.wait(
            [monitor_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
        
        logger.info("⏹️ 测试时间结束，停止监控...")
        
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试过程中出错: {e}")
    finally:
        # 停止监控
        await vpa_monitor.stop_monitoring()
        
        # 获取系统统计
        system_stats = vpa_monitor.get_stats()
        test_summary = test_monitor.get_test_summary()
        
        # 输出测试报告
        print_test_report(system_stats, test_summary)

def print_test_report(system_stats: dict, test_summary: dict):
    """打印测试报告"""
    print("\n" + "="*80)
    print("📊 WebSocket VPA监控系统测试报告")
    print("="*80)
    
    # 基本统计
    print(f"⏱️ 运行时间: {test_summary['runtime_seconds']/60:.1f}分钟")
    print(f"📡 WebSocket连接时间: {system_stats.get('connection_uptime', 0)/60:.1f}分钟")
    print(f"📊 接收K线: {system_stats.get('total_klines_received', 0)}")
    print(f"🔍 执行分析: {test_summary['total_analyses']}")
    print(f"✅ 成功分析: {test_summary['successful_analyses']}")
    print(f"❌ 失败分析: {test_summary['failed_analyses']}")
    print(f"⚠️ 系统错误: {test_summary['error_count']}")
    print(f"💰 成本告警: {test_summary['cost_alerts']}")
    
    # 性能指标
    print(f"\n📈 性能指标:")
    print(f"💵 总成本: ${test_summary['total_cost']:.3f}")
    if test_summary['avg_analysis_time'] > 0:
        print(f"⏱️ 平均分析时间: {test_summary['avg_analysis_time']:.1f}秒")
    
    # 按时间框架统计
    if test_summary['timeframe_stats']:
        print(f"\n📊 时间框架分析统计:")
        for tf, stats in test_summary['timeframe_stats'].items():
            avg_cost = stats['total_cost'] / stats['count'] if stats['count'] > 0 else 0
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            print(f"   {tf:>4}: {stats['count']:>2}次 | "
                  f"${avg_cost:.3f}/次 | {avg_time:.1f}s/次")
    
    # WebSocket统计
    if 'websocket_stats' in system_stats:
        ws_stats = system_stats['websocket_stats']
        print(f"\n🔗 WebSocket连接统计:")
        print(f"   消息接收: {ws_stats.get('messages_received', 0)}")
        print(f"   K线处理: {ws_stats.get('klines_processed', 0)}")
        print(f"   重连次数: {ws_stats.get('reconnect_count', 0)}")
        print(f"   连接状态: {ws_stats.get('connection_state', 'Unknown')}")
    
    # 队列状态
    queue_sizes = system_stats.get('queue_sizes', {})
    if any(size > 0 for size in queue_sizes.values()):
        print(f"\n📋 分析队列状态:")
        for priority, size in queue_sizes.items():
            if size > 0:
                print(f"   {priority}: {size}个待处理任务")
    
    print("="*80)
    
    # 测试结果评估
    success_rate = (test_summary['successful_analyses'] / test_summary['total_analyses'] * 100) if test_summary['total_analyses'] > 0 else 0
    
    print(f"🎯 测试结果评估:")
    if success_rate >= 90:
        print("✅ 优秀 - 系统运行稳定，分析成功率高")
    elif success_rate >= 75:
        print("🟡 良好 - 系统基本稳定，有少量失败")
    elif success_rate >= 50:
        print("⚠️ 一般 - 系统不够稳定，需要优化")
    else:
        print("❌ 较差 - 系统存在严重问题，需要修复")
    
    print(f"   成功率: {success_rate:.1f}%")
    print(f"   错误率: {test_summary['error_count'] / (test_summary['runtime_seconds']/60):.1f}次/分钟")
    
    if test_summary['total_cost'] > 0:
        cost_efficiency = test_summary['successful_analyses'] / test_summary['total_cost']
        print(f"   成本效率: {cost_efficiency:.1f}次分析/美元")

async def quick_connectivity_test():
    """快速连接测试"""
    logger.info("🔍 执行快速WebSocket连接测试...")
    
    from data.binance_websocket import BinanceWebSocketClient, StreamConfig
    
    config = StreamConfig(
        timeframes=['1m'],  # 只测试1分钟图
        symbol='ETHUSDT'
    )
    
    client = BinanceWebSocketClient(config)
    
    received_klines = []
    
    async def test_kline_handler(kline):
        received_klines.append(kline)
        logger.info(f"✅ 接收到K线: {kline.timeframe} | 价格: ${kline.close_price:.2f}")
        if len(received_klines) >= 3:  # 接收3个K线后停止
            await client.disconnect()
    
    client.add_kline_callback('1m', test_kline_handler)
    
    try:
        logger.info("📡 连接币安WebSocket...")
        await asyncio.wait_for(client.connect(), timeout=60)
    except asyncio.TimeoutError:
        logger.error("❌ 连接超时")
    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
    finally:
        if client.websocket:
            await client.disconnect()
        
        if received_klines:
            logger.info(f"✅ 连接测试成功，接收到{len(received_klines)}个K线")
            return True
        else:
            logger.error("❌ 连接测试失败，未接收到数据")
            return False

async def main():
    """主测试函数"""
    print("🚀 WebSocket VPA监控系统测试")
    print("="*50)
    
    # 检查参数
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            duration = 5
    else:
        duration = 5  # 默认5分钟测试
    
    # 选择测试模式
    print("选择测试模式:")
    print("1. 快速连接测试 (30秒)")
    print("2. 完整VPA监控测试")
    
    try:
        choice = input("请选择 (1/2): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"
    
    if choice == "1":
        success = await quick_connectivity_test()
        if success:
            print("\n✅ 快速测试通过，WebSocket连接正常")
        else:
            print("\n❌ 快速测试失败，请检查网络连接")
    else:
        print(f"\n🧪 开始{duration}分钟完整测试...")
        await test_websocket_vpa_monitor(duration)
    
    print("\n🏁 测试完成")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试程序异常: {e}")
        import traceback
        traceback.print_exc()