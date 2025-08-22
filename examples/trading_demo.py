#!/usr/bin/env python3
"""
模拟交易演示脚本 - 展示完整的AI驱动交易流程
结合实时数据、AI分析、信号执行和风险管理
"""

import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import Settings, TradingConfig
    from data import BinanceFetcher
    from formatters import DataFormatter
    from ai import OpenRouterClient
    from trading import (
        SimulatedExchange, OrderManager, PositionManager,
        TradeLogger, RiskManager, SignalExecutor, TradingMonitor
    )
    from trading.simulated_exchange import OrderSide, OrderType
    from trading.risk_manager import RiskLevel
    from trading.signal_executor import ExecutionMode
    
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    MODULES_AVAILABLE = False

def demo_basic_trading():
    """基础交易演示"""
    print("🎯 基础模拟交易演示")
    print("="*50)
    
    if not MODULES_AVAILABLE:
        print("❌ 交易模块不可用，跳过演示")
        return
    
    try:
        # 1. 初始化交易系统
        print("📊 初始化交易系统...")
        config = TradingConfig()
        exchange = SimulatedExchange(initial_balance=config.initial_balance)
        order_manager = OrderManager(exchange)
        position_manager = PositionManager(exchange)
        trade_logger = TradeLogger()
        risk_manager = RiskManager(exchange, position_manager, trade_logger)
        
        # 2. 获取实时数据
        print("📈 获取ETH永续合约数据...")
        fetcher = BinanceFetcher()
        df = fetcher.get_ohlcv('ETH/USDT', '1h', 20)
        current_price = float(df.iloc[-1]['close'])
        
        print(f"💰 当前ETH价格: ${current_price:.2f}")
        exchange.update_market_price('ETHUSDT', current_price)
        
        # 3. 手动创建交易信号（模拟AI分析结果）
        print("🤖 模拟AI分析生成交易信号...")
        
        # 计算合理的止损和止盈价格
        stop_loss_price = current_price * 0.98  # 2%止损
        take_profit_price = current_price * 1.06  # 6%止盈
        
        signal_executor = SignalExecutor(
            exchange, order_manager, position_manager, 
            trade_logger, risk_manager
        )
        
        # 模拟强烈看多信号
        analysis_text = f"""
        基于VSA分析，ETH/USDT出现强烈看多信号。
        当前价格 ${current_price:.2f} 附近出现 Spring 信号，
        成交量配合良好，建议做多。
        
        入场价格: ${current_price:.2f}
        止损价格: ${stop_loss_price:.2f}
        止盈价格: ${take_profit_price:.2f}
        
        信号强度: 很强
        置信度: 85%
        VSA信号: Spring, No Supply
        市场阶段: Accumulation
        """
        
        # 4. 执行交易信号
        print("⚡ 执行交易信号...")
        signal_executor.set_execution_mode(ExecutionMode.AUTO)
        
        result = signal_executor.process_ai_analysis(
            analysis_text=analysis_text,
            symbol='ETHUSDT',
            model_used='demo_model',
            analysis_type='vpa'
        )
        
        print(f"📋 信号执行结果: {result.get('action', 'unknown')}")
        
        if result['success'] and 'signal' in result:
            signal = result['signal']
            print(f"📊 信号详情:")
            print(f"  方向: {signal.direction}")
            print(f"  强度: {signal.strength.name}")
            print(f"  入场: ${signal.entry_price:.2f}")
            print(f"  止损: ${signal.stop_loss:.2f}" if signal.stop_loss else "  止损: 未设置")
            print(f"  止盈: ${signal.take_profit:.2f}" if signal.take_profit else "  止盈: 未设置")
            print(f"  置信度: {signal.confidence:.0%}")
        
        # 5. 显示账户状态
        print(f"\\n💼 账户状态:")
        account = exchange.get_account_info()
        print(f"  总资金: ${account['total_balance']:.2f}")
        print(f"  可用资金: ${account['available_balance']:.2f}")
        print(f"  已用保证金: ${account['margin_used']:.2f}")
        print(f"  未实现盈亏: ${account['unrealized_pnl']:+.2f}")
        
        # 6. 显示持仓信息
        positions = exchange.get_positions()
        if positions:
            print(f"\\n📍 当前持仓:")
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['side']} {pos['size']} @ ${pos['avg_entry_price']:.2f}")
                print(f"  未实现盈亏: ${pos['unrealized_pnl']:+.2f}")
        
        # 7. 模拟价格变动
        print(f"\\n📈 模拟价格上涨...")
        new_price = current_price * 1.03  # 3%涨幅
        exchange.update_market_price('ETHUSDT', new_price)
        print(f"💰 新价格: ${new_price:.2f} (+{((new_price/current_price-1)*100):.1f}%)")
        
        # 8. 显示更新后状态
        account = exchange.get_account_info()
        print(f"💼 更新后账户:")
        print(f"  总资金: ${account['total_balance']:.2f}")
        print(f"  未实现盈亏: ${account['unrealized_pnl']:+.2f}")
        
        # 9. 平仓
        if positions:
            print(f"\\n🔄 手动平仓...")
            for pos in positions:
                close_result = exchange.close_position(pos['symbol'])
                if close_result['success']:
                    print(f"✅ {pos['symbol']} 平仓成功")
        
        # 10. 最终统计
        final_account = exchange.get_account_info()
        final_pnl = final_account['total_balance'] - config.initial_balance
        print(f"\\n📊 演示结果:")
        print(f"  初始资金: ${config.initial_balance:.2f}")
        print(f"  最终资金: ${final_account['total_balance']:.2f}")
        print(f"  总盈亏: ${final_pnl:+.2f}")
        print(f"  收益率: {(final_pnl/config.initial_balance*100):+.2f}%")
        
    except Exception as e:
        print(f"❌ 演示过程出错: {e}")

def demo_ai_integration():
    """AI集成演示（需要API密钥）"""
    print("\\n🤖 AI集成模拟交易演示")
    print("="*50)
    
    if not MODULES_AVAILABLE:
        print("❌ 交易模块不可用，跳过演示")
        return
    
    try:
        # 检查API配置
        Settings.validate()
        print("✅ API配置验证通过")
        
        # 初始化系统
        config = TradingConfig()
        exchange = SimulatedExchange(initial_balance=config.initial_balance)
        trade_logger = TradeLogger()
        
        # 获取实时数据
        fetcher = BinanceFetcher()
        df = fetcher.get_ohlcv('ETH/USDT', '1h', 30)
        current_price = float(df.iloc[-1]['close'])
        exchange.update_market_price('ETHUSDT', current_price)
        
        print(f"📊 获取到 {len(df)} 条K线数据，当前价格: ${current_price:.2f}")
        
        # AI分析
        print("🧠 运行AI分析...")
        formatter = DataFormatter()
        data = formatter.to_pattern_description(df)
        
        client = OpenRouterClient()
        ai_result = client.analyze_market_data(
            data=data,
            model_name=config.ai_analysis.default_model,
            analysis_type='vpa'
        )
        
        if ai_result.get('analysis'):
            print("✅ AI分析完成")
            analysis_text = ai_result['analysis']
            
            # 记录AI决策
            decision_id = trade_logger.log_ai_decision(
                symbol='ETHUSDT',
                model_used=config.ai_analysis.default_model,
                analysis_type='vpa',
                raw_analysis=analysis_text,
                extracted_signals={}
            )
            
            print(f"📝 AI决策已记录: {decision_id}")
            
            # 显示分析摘要
            if len(analysis_text) > 300:
                print(f"📋 AI分析摘要: {analysis_text[:300]}...")
            else:
                print(f"📋 AI分析: {analysis_text}")
        else:
            print("❌ AI分析失败")
            return
    
    except Exception as e:
        print(f"❌ AI集成演示失败: {e}")
        if "API" in str(e):
            print("💡 提示: 需要配置 OPENROUTER_API_KEY 环境变量")

def demo_monitoring():
    """监控演示"""
    print("\\n📊 实时监控演示")
    print("="*50)
    
    if not MODULES_AVAILABLE:
        print("❌ 交易模块不可用，跳过演示")
        return
    
    try:
        # 初始化监控系统
        exchange = SimulatedExchange(initial_balance=5000.0)
        exchange.update_market_price('ETHUSDT', 3000.0)
        
        monitor = TradingMonitor(exchange)
        
        # 创建一些活动
        exchange.place_order('ETHUSDT', OrderSide.BUY, OrderType.MARKET, 1.0)
        exchange.update_market_price('ETHUSDT', 3050.0)
        
        # 显示监控面板
        print("📈 当前监控状态:")
        monitor.print_status_summary()
        
        # 导出监控数据
        export_path = "demo_monitoring_export.json"
        success = monitor.export_monitoring_data(export_path)
        if success:
            print(f"💾 监控数据已导出到: {export_path}")
    
    except Exception as e:
        print(f"❌ 监控演示失败: {e}")

def main():
    """主演示程序"""
    print("🚀 ETH永续合约AI交易助手 - 模拟交易演示")
    print("="*80)
    print("本演示将展示完整的模拟交易功能，包括:")
    print("• 模拟交易所和订单执行")
    print("• AI信号提取和自动执行") 
    print("• 风险管理和持仓控制")
    print("• 实时监控和交易日志")
    print("• 完整的交易周期管理")
    print("="*80)
    
    # 运行演示
    demo_basic_trading()
    
    # 如果有API密钥，运行AI集成演示
    try:
        Settings.validate()
        demo_ai_integration()
    except:
        print("\\n💡 跳过AI集成演示 (需要OPENROUTER_API_KEY)")
    
    demo_monitoring()
    
    print("\\n🎉 模拟交易演示完成！")
    print("\\n📚 更多使用方法:")
    print("python main.py --enable-trading --initial-balance 1000")
    print("python main.py --enable-trading --auto-trade --max-risk 0.01")
    print("python main.py --show-monitor")
    print("python tests/test_simulated_trading.py")

if __name__ == "__main__":
    main()