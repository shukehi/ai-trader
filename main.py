#!/usr/bin/env python3
"""
ETH永续合约量价分析助手
使用OpenRouter API调用多种LLM模型分析原始K线数据
"""

# import asyncio  # 未使用
import argparse
from config import Settings
from data import BinanceFetcher
from formatters import DataFormatter
from formatters.executive_formatter import ExecutiveFormatter
from ai import OpenRouterClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_symbol_for_api(symbol: str) -> str:
    """
    标准化交易对符号格式以用于API调用
    
    Args:
        symbol: 输入符号，如 'ETHUSDT' 或 'ETH/USDT'
        
    Returns:
        标准化的符号格式 'ETH/USDT'
    """
    if '/' not in symbol:
        # 假设是 ETHUSDT 格式，转换为 ETH/USDT
        if symbol.endswith('USDT'):
            base = symbol[:-4]  # 移除 'USDT'
            return f"{base}/USDT"
    return symbol

def normalize_symbol_for_trading(symbol: str) -> str:
    """
    标准化交易对符号格式以用于交易系统
    
    Args:
        symbol: 输入符号，如 'ETH/USDT' 或 'ETHUSDT'
        
    Returns:
        标准化的符号格式 'ETHUSDT'
    """
    if '/' in symbol:
        # 移除斜杠
        return symbol.replace('/', '')
    return symbol

def validate_binance_connection(symbol: str) -> bool:
    """
    验证 Binance API 连通性和交易对有效性
    
    Args:
        symbol: 要验证的交易对符号
        
    Returns:
        bool: 连接是否成功
        
    Raises:
        Exception: 连接失败时抛出异常
    """
    try:
        from data import BinanceFetcher
        
        fetcher = BinanceFetcher()
        symbol_for_api = normalize_symbol_for_api(symbol)
        
        # 尝试获取少量数据以验证连接
        logger.info(f"测试获取 {symbol_for_api} 数据...")
        df = fetcher.get_ohlcv(symbol_for_api, '1h', 5)
        
        if df is not None and len(df) > 0:
            print(f"✅ Binance API 连接成功，交易对 {symbol_for_api} 有效")
            print(f"📊 最新价格: ${df.iloc[-1]['close']:.2f}")
            return True
        else:
            raise Exception("获取到空数据")
            
    except Exception as e:
        logger.error(f"Binance API 连接验证失败: {e}")
        print(f"❌ Binance API 连接失败: {e}")
        print("💡 建议检查:")
        print("   - 网络连接是否正常")
        print("   - 交易对符号是否正确")
        print("   - Binance API 是否可访问")
        raise

def main():
    parser = argparse.ArgumentParser(description='ETH永续合约LLM量价分析助手')
    parser.add_argument('--symbol', default='ETHUSDT', help='交易对符号')
    parser.add_argument('--timeframe', default='1h', help='时间周期')
    parser.add_argument('--limit', type=int, default=50, help='K线数据数量')
    parser.add_argument('--model', choices=[
        # 🔥 2025 Latest Flagship Models
        'gpt5-chat', 'gpt5-mini', 'gpt5-nano', 'claude-opus-41', 'gemini-25-pro', 'grok4',
        # Standard Models
        'gpt4', 'gpt4o', 'gpt4o-mini', 'o1', 'o1-mini',
        'claude', 'claude-haiku', 'claude-opus', 
        'gemini', 'gemini-flash', 'gemini-2',
        'grok', 'grok-vision',
        'llama', 'llama-405b'
    ], default='gpt4o-mini', help='使用的LLM模型')
    parser.add_argument('--test-all', action='store_true', help='测试所有格式和模型')
    parser.add_argument('--enable-validation', action='store_true', default=False, help='启用多模型验证（推荐）')
    parser.add_argument('--fast-validation', action='store_true', help='快速验证模式（只用2个主要模型）')
    parser.add_argument('--validation-only', action='store_true', help='仅运行验证检查，不进行完整分析')
    
    # 新增交易模式参数
    parser.add_argument('--mode', choices=['signal', 'research', 'quick', 'executive'], 
                       default='research', help='分析模式：signal(交易信号), research(深度研究), quick(快速信号), executive(执行摘要)')
    parser.add_argument('--trading-signal', action='store_true', help='启用交易信号模式（包含具体入场出场价格）')
    parser.add_argument('--ultra-economy', action='store_true', help='超经济模式（降低成本90%）')
    
    # 🚀 NEW: 模拟交易参数
    parser.add_argument('--enable-trading', action='store_true', help='启用模拟交易功能')
    parser.add_argument('--initial-balance', type=float, default=10000.0, help='初始模拟资金(USDT)')
    parser.add_argument('--auto-trade', action='store_true', help='自动执行AI交易信号')
    parser.add_argument('--signal-only', action='store_true', help='仅记录交易信号，不执行')
    parser.add_argument('--max-risk', type=float, default=0.02, help='最大单笔交易风险比例')
    parser.add_argument('--risk-level', choices=['conservative', 'moderate', 'aggressive'], 
                       default='moderate', help='风险等级')
    parser.add_argument('--show-monitor', action='store_true', help='显示实时监控面板')
    parser.add_argument('--export-trades', help='导出交易记录到指定文件')
    
    args = parser.parse_args()
    
    try:
        # 验证配置
        Settings.validate()
        
        # 验证 Binance API 连通性（仅在交易模式下）
        if args.enable_trading:
            print("🔍 验证 Binance API 连通性...")
            validate_binance_connection(args.symbol)
        
        # 处理模式设置
        analysis_mode = determine_analysis_mode(args)
        
        print(f"🚀 启动ETH永续合约分析助手...")
        print(f"📊 分析参数: {args.symbol} {args.timeframe} 最近{args.limit}条数据")
        print(f"🤖 使用模型: {args.model}")
        print(f"🎯 分析模式: {analysis_mode['name']} - {analysis_mode['description']}")
        
        if args.test_all:
            print("🧪 运行全面测试模式...")
            run_comprehensive_test(args)
        elif args.validation_only:
            print("🔍 运行验证检查模式...")
            run_validation_check(args)
        elif args.enable_trading:
            print("🚀 启动模拟交易模式...")
            run_trading_mode(args, analysis_mode)
        elif args.show_monitor:
            print("📊 启动监控面板...")
            run_monitor_mode(args)
        else:
            print("📈 运行单次分析...")
            run_single_analysis(args, analysis_mode)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

def determine_analysis_mode(args):
    """确定分析模式"""
    from ai.trading_prompts import TradingModeSelector
    
    # 优先级：命令行标志 > mode参数 > 默认
    if args.trading_signal or args.mode == 'signal':
        return TradingModeSelector.get_mode('signal')
    elif args.ultra_economy or (args.mode == 'quick' and args.ultra_economy):
        return TradingModeSelector.get_mode('quick')
    elif args.mode == 'executive':
        return TradingModeSelector.get_mode('executive')
    elif args.mode == 'research':
        return TradingModeSelector.get_mode('research')
    else:
        # 默认根据用户类型推荐
        from ai.trading_prompts import get_recommended_mode
        mode_key = get_recommended_mode('trader')  # 假设是个人交易者
        return TradingModeSelector.get_mode(mode_key)

def run_single_analysis(args, analysis_mode):
    """运行单次分析（支持多模型验证）"""
    try:
        # 初始化组件
        fetcher = BinanceFetcher()
        
        # 根据分析模式选择格式化器
        if analysis_mode['name'] in ['交易信号模式', '快速信号模式', '执行摘要模式']:
            from formatters.executive_formatter import ExecutiveFormatter
            formatter = ExecutiveFormatter()
            print(f"📝 使用简化格式化器 - 降低{analysis_mode.get('cost_level', 'medium')}成本")
        else:
            formatter = DataFormatter()
            print("📝 使用标准格式化器")
        
        # 根据参数决定是否启用验证
        enable_validation = args.enable_validation
        if enable_validation:
            print("✅ 已启用多模型验证防幻觉机制")
            from ai import AnalysisEngine
            engine = AnalysisEngine(enable_validation=True)
        else:
            # 根据模式调整模型选择
            model_to_use = args.model
            if args.ultra_economy:
                model_to_use = 'gemini-flash'  # 强制使用最经济模型
                print(f"💰 超经济模式：自动切换到 {model_to_use}")
            elif analysis_mode['name'] == '交易信号模式':
                trading_models = Settings.RECOMMENDED_MODELS.get('trading_signal', [args.model])
                model_to_use = trading_models[0] if trading_models and args.model == 'gpt4o-mini' else args.model
                if model_to_use != args.model:
                    print(f"🎯 交易信号模式：建议使用 {model_to_use}")
            
            print(f"ℹ️ 使用单模型分析: {model_to_use}")
            client = OpenRouterClient()
        
        # 获取数据
        print(f"📊 获取 {args.symbol} 数据...")
        df = fetcher.get_ohlcv(
            symbol=args.symbol.replace('USDT', '/USDT'), 
            timeframe=args.timeframe, 
            limit=args.limit
        )
        
        if enable_validation:
            # 使用多模型验证分析
            print(f"🔍 开始多模型验证VPA分析...")
            if args.fast_validation:
                print("⚡ 使用快速验证模式")
            
            result = engine.validated_vpa_analysis(
                df=df,
                enable_fast_mode=args.fast_validation
            )
            
            # 显示验证结果
            display_validated_results(result, args)
            
        else:
            # 传统单模型分析 - 支持多种模式
            
            # 格式化数据（根据分析模式选择格式）
            executive_formatter = ExecutiveFormatter()
            if analysis_mode['name'] == '交易信号模式':
                data = executive_formatter.format_trading_signal_data(df)
                custom_prompt = analysis_mode['prompt']
            elif analysis_mode['name'] == '快速信号模式':
                data = executive_formatter.format_quick_signal_data(df)
                custom_prompt = analysis_mode['prompt']
            elif analysis_mode['name'] == '执行摘要模式':
                data = executive_formatter.format_executive_summary_data(df)
                custom_prompt = analysis_mode['prompt']
            else:
                # 使用标准Pattern格式  
                data = DataFormatter.to_pattern_description(df)
                custom_prompt = None
            
            # Token估算
            if hasattr(DataFormatter, 'estimate_tokens_by_format'):
                token_estimate = DataFormatter.estimate_tokens_by_format(df)
                print(f"📝 数据格式化完成，预估tokens: {token_estimate.get('pattern', '未知')}")
            
            # AI分析
            print(f"🤖 使用 {model_to_use} 进行{analysis_mode['name']}分析...")
            
            if custom_prompt:
                # 使用自定义提示
                full_prompt = custom_prompt + "\n\n" + data
                result = client.generate_response(
                    prompt=full_prompt,
                    model_name=model_to_use
                )
            else:
                # 使用标准VPA分析
                result = client.analyze_market_data(
                    data=data,
                    model_name=model_to_use,
                    analysis_type='vpa'
                )
            
            # 显示结果
            display_single_model_results(result, args, analysis_mode)
        
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        logger.error(f"单次分析失败: {e}")

def display_validated_results(result, args):
    """显示多模型验证结果"""
    if result.get('error'):
        print(f"❌ 验证分析失败: {result['error']}")
        if 'fallback_analysis' in result:
            print("🔄 尝试显示后备分析结果...")
            display_single_model_results(result['fallback_analysis'], args)
        return
    
    print("\n" + "="*80)
    print(f"🔍 {args.symbol} 多模型验证VPA分析报告")
    print("="*80)
    
    # 验证摘要
    validation_summary = result.get('validation_summary', {})
    print(f"🎯 共识得分: {validation_summary.get('consensus_score', 0):.2f}/1.00")
    print(f"🔒 置信度: {validation_summary.get('confidence_level', 'unknown').upper()}")
    
    model_count = validation_summary.get('model_count', {})
    print(f"🤖 模型数量: 主要{model_count.get('primary', 0)}个 + 验证{model_count.get('validation', 0)}个 = 共{model_count.get('total', 0)}个")
    
    # 分歧检测
    if validation_summary.get('has_disagreements'):
        print(f"⚠️ 检测到 {validation_summary.get('disagreement_count', 0)} 个分歧点")
        if result.get('disagreement_analysis'):
            disagreements = result['disagreement_analysis']['disagreements']
            for i, disagreement in enumerate(disagreements[:3], 1):  # 只显示前3个
                print(f"  {i}. {disagreement}")
    else:
        print("✅ 模型间达成一致")
    
    # 风险评估
    risk_assessment = result.get('risk_assessment', {})
    risk_level = risk_assessment.get('risk_level', 'unknown')
    risk_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(risk_level, '❓')
    print(f"{risk_emoji} 风险等级: {risk_level.upper()}")
    
    # 性能指标
    performance = result.get('performance_metrics', {})
    print(f"⏱️ 处理时间: {performance.get('processing_time', 0):.1f}秒")
    print(f"💰 总成本: ${performance.get('total_cost', 0):.4f}")
    
    # 使用建议
    recommendation = validation_summary.get('recommendation', '')
    if recommendation:
        print(f"💡 建议: {recommendation}")
    
    # 共识分析
    consensus_analysis = result.get('consensus_analysis', {})
    if consensus_analysis.get('consensus_view'):
        print("\n🧠 共识分析:")
        consensus_view = consensus_analysis['consensus_view']
        
        for dimension, info in consensus_view.items():
            if isinstance(info, dict) and 'value' in info:
                confidence_pct = int(info.get('confidence', 0) * 100)
                print(f"  • {dimension}: {info['value']} (支持率: {confidence_pct}%)")
    
    # 显示主要分析结果
    primary_analyses = result.get('model_analyses', {}).get('primary', {})
    if primary_analyses:
        print("\n📋 主要分析结果:")
        for model_name, analysis in primary_analyses.items():
            if analysis.get('success') and analysis.get('analysis'):
                print(f"\n🤖 {model_name}:")
                # 显示前200个字符
                content = analysis['analysis'][:200] + "..." if len(analysis['analysis']) > 200 else analysis['analysis']
                print(f"  {content}")
    
    print("\n" + "="*80)

def display_single_model_results(result, args, analysis_mode=None):
    """显示单模型结果"""
    if result.get('error'):
        print(f"❌ 分析失败: {result['error']}")
        return
    
    print("\n" + "="*80)
    if analysis_mode and analysis_mode.get('name'):
        print(f"📈 {args.symbol} {analysis_mode['name']}报告")
    else:
        print(f"📈 {args.symbol} VPA量价分析报告")
    print(f"🤖 模型: {result.get('model_id', args.model)}")
    print(f"⏱️ 响应时间: {result.get('response_time', 0):.2f}秒")
    
    if 'usage' in result:
        usage = result['usage']
        print(f"💰 Token使用: {usage.get('total_tokens', 0)} (输入: {usage.get('prompt_tokens', 0)}, 输出: {usage.get('completion_tokens', 0)})")
        
        # 成本估算
        from ai import OpenRouterClient
        client = OpenRouterClient()
        cost = client.estimate_cost(args.model, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0))
        print(f"💵 预估成本: ${cost.get('estimated_cost', 0):.6f}")
    
    if result.get('warning'):
        print(f"⚠️ 警告: {result['warning']}")
    
    print("="*80)
    print("\n📋 分析内容:")
    
    # 处理不同的结果结构
    if 'analysis' in result:
        if isinstance(result['analysis'], dict) and 'analysis' in result['analysis']:
            print(result['analysis']['analysis'])
        else:
            print(result['analysis'])
    else:
        print('无分析内容')
    
    print("\n" + "="*80)

def run_validation_check(args):
    """运行快速验证检查"""
    try:
        print("🔍 开始验证检查模式...")
        
        # 初始化组件
        fetcher = BinanceFetcher()
        formatter = DataFormatter()
        from ai import AnalysisEngine
        engine = AnalysisEngine(enable_validation=True)
        
        # 获取数据
        print(f"📈 获取 {args.symbol} 数据...")
        df = fetcher.get_ohlcv(
            symbol=args.symbol.replace('USDT', '/USDT'), 
            timeframe=args.timeframe, 
            limit=args.limit
        )
        
        # 格式化数据
        data = DataFormatter.to_pattern_description(df)
        
        # 执行快速验证
        result = engine.quick_validation_check(data, 'vpa')
        
        # 显示结果
        print("\n" + "="*60)
        print("🔍 快速验证结果")
        print("="*60)
        
        if result.get('error'):
            print(f"❌ 验证失败: {result['error']}")
            return
        
        print(f"🎯 共识得分: {result.get('consensus_score', 0):.2f}/1.00")
        print(f"🔒 置信度: {result.get('confidence_level', 'unknown').upper()}")
        print(f"⚠️ 存在分歧: {'Yes' if result.get('has_disagreements') else 'No'}")
        print(f"⏱️ 处理时间: {result.get('processing_time', 0):.1f}秒")
        print(f"💰 成本: ${result.get('cost', 0):.4f}")
        
        recommendation = result.get('recommendation', '')
        if recommendation:
            print(f"\n💡 建议: {recommendation}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ 验证检查失败: {e}")
        logger.error(f"验证检查出错: {e}")

def run_trading_mode(args, analysis_mode):
    """运行模拟交易模式"""
    try:
        from trading import (
            SimulatedExchange, OrderManager, PositionManager, 
            TradeLogger, RiskManager, SignalExecutor, TradingMonitor
        )
        from trading.risk_manager import RiskLevel
        from trading.signal_executor import ExecutionMode
        
        print(f"💰 初始化模拟交易环境 - 资金: ${args.initial_balance:.2f}")
        
        # 初始化交易系统
        exchange = SimulatedExchange(initial_balance=args.initial_balance)
        order_manager = OrderManager(exchange)
        position_manager = PositionManager(exchange)
        trade_logger = TradeLogger()
        
        # 设置风险等级
        risk_level_map = {
            'conservative': RiskLevel.CONSERVATIVE,
            'moderate': RiskLevel.MODERATE,
            'aggressive': RiskLevel.AGGRESSIVE
        }
        risk_manager = RiskManager(
            exchange, position_manager, trade_logger,
            initial_risk_level=risk_level_map[args.risk_level]
        )
        
        # 初始化信号执行器
        signal_executor = SignalExecutor(
            exchange, order_manager, position_manager, 
            trade_logger, risk_manager
        )
        
        # 设置执行模式
        if args.signal_only:
            signal_executor.set_execution_mode(ExecutionMode.SIGNAL_ONLY)
            print("📝 信号模式: 仅记录，不执行")
        elif args.auto_trade:
            signal_executor.set_execution_mode(ExecutionMode.AUTO)
            print("⚙️ 自动模式: AI信号自动执行")
        else:
            signal_executor.set_execution_mode(ExecutionMode.CONFIRM)
            print("❓ 确认模式: 需要手动确认")
        
        # 启动监控
        monitor = TradingMonitor(
            exchange, order_manager, position_manager,
            trade_logger, risk_manager, signal_executor
        )
        order_manager.start_monitoring()
        monitor.start_monitoring()
        
        print("🎆 模拟交易系统已启动")
        
        try:
            # 运行AI分析并执行交易信号
            while True:
                # 获取数据并进行AI分析
                fetcher = BinanceFetcher()
                
                # 标准化符号格式：确保使用 ETH/USDT 格式
                symbol_for_api = normalize_symbol_for_api(args.symbol)
                
                df = fetcher.get_ohlcv(
                    symbol=symbol_for_api,
                    timeframe=args.timeframe,
                    limit=args.limit
                )
                
                # 更新市场价格（使用交易系统格式）
                current_price = df.iloc[-1]['close']
                symbol_for_trading = normalize_symbol_for_trading(args.symbol)
                exchange.update_market_price(symbol_for_trading, current_price)
                
                # 进行AI分析
                if args.enable_validation:
                    from ai import AnalysisEngine
                    engine = AnalysisEngine(enable_validation=True)
                    result = engine.validated_vpa_analysis(df=df, enable_fast_mode=args.fast_validation)
                    
                    if result.get('consensus_analysis'):
                        # 使用验证结果
                        analysis_text = str(result['consensus_analysis'])
                        ai_decision_id = trade_logger.log_ai_decision(
                            symbol=symbol_for_trading,
                            model_used="multi_model_validation",
                            analysis_type="validated_vpa",
                            raw_analysis=analysis_text,
                            extracted_signals=result.get('validation_summary', {}),
                            confidence_score=result.get('validation_summary', {}).get('consensus_score')
                        )
                    else:
                        print("⚠️ 验证分析失败")
                        continue
                else:
                    # 单模型分析
                    data = DataFormatter.to_pattern_description(df)
                    
                    client = OpenRouterClient()
                    result = client.analyze_market_data(
                        data=data,
                        model_name=args.model,
                        analysis_type='vpa'
                    )
                    
                    if result.get('analysis'):
                        analysis_text = result['analysis']
                        ai_decision_id = trade_logger.log_ai_decision(
                            symbol=symbol_for_trading,
                            model_used=args.model,
                            analysis_type="vpa",
                            raw_analysis=analysis_text,
                            extracted_signals={}
                        )
                    else:
                        print("⚠️ AI分析失败")
                        continue
                
                # 执行交易信号
                execution_result = signal_executor.process_ai_analysis(
                    analysis_text=analysis_text,
                    symbol=symbol_for_trading,
                    model_used=args.model,
                    analysis_type="vpa",
                    ai_decision_id=ai_decision_id
                )
                
                # 显示结果
                print(f"\n🤖 AI分析结果: {execution_result.get('action', 'unknown')}")
                if 'signal' in execution_result:
                    signal = execution_result['signal']
                    print(f"📈 信号: {signal.direction} - 强度: {signal.strength.name}")
                    if signal.entry_price:
                        print(f"🎯 入场: ${signal.entry_price:.2f}")
                    if signal.stop_loss:
                        print(f"🛑 止损: ${signal.stop_loss:.2f}")
                    if signal.take_profit:
                        print(f"🎆 止盈: ${signal.take_profit:.2f}")
                
                # 显示账户状态
                monitor.print_status_summary()
                
                # 等待用户输入或自动继续
                if args.auto_trade:
                    print("\n⏰ 等待60秒后继续下一次分析... (Ctrl+C 退出)")
                    import time
                    time.sleep(60)
                else:
                    input("\n⏎️ 按Enter继续下一次分析，或Ctrl+C退出...")
                    
        except KeyboardInterrupt:
            print("\n👋 交易系统关闭")
            
        finally:
            # 清理资源
            order_manager.stop_monitoring()
            monitor.stop_monitoring()
            
            # 显示最终统计
            account = exchange.get_account_info()
            print(f"\n📋 交易统计:")
            print(f"💰 最终余额: ${account['total_balance']:.2f}")
            print(f"📈 总盈亏: ${account['total_pnl']:+.2f}")
            print(f"🎯 收益率: {((account['total_balance']/args.initial_balance-1)*100):+.2f}%")
            
            # 导出交易记录
            if args.export_trades:
                success = trade_logger.export_to_csv("trades", 7)
                if success:
                    print(f"💾 交易记录已导出")
                    
    except ImportError as e:
        print(f"⚠️ 模拟交易模块未安装: {e}")
        print("🚀 请确保 trading 模块完整")
    except Exception as e:
        print(f"❌ 模拟交易失败: {e}")
        logger.error(f"模拟交易错误: {e}")

def run_monitor_mode(args):
    """运行监控模式"""
    try:
        from trading import SimulatedExchange, TradingMonitor
        import os
        import time
        
        exchange = SimulatedExchange(initial_balance=args.initial_balance)
        monitor = TradingMonitor(exchange)
        
        print("📊 启动实时监控面板 (Ctrl+C 退出)")
        monitor.start_monitoring()
        
        try:
            while True:
                # 清屏显示
                os.system('clear' if os.name == 'posix' else 'cls')
                monitor.print_status_summary()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
        finally:
            monitor.stop_monitoring()
            
    except ImportError as e:
        print(f"⚠️ 监控模块未安装: {e}")
    except Exception as e:
        print(f"❌ 监控失败: {e}")
        logger.error(f"监控错误: {e}")

def run_comprehensive_test(args):
    """运行全面测试"""
    print("🔄 全面测试功能开发中，请使用:")
    print("python tests/test_2025_models.py")
    print("python tests/test_flagship_2025.py")
    print("python tests/test_multi_model_validation.py")
    print("\n🚀 模拟交易测试:")
    print("python main.py --enable-trading --signal-only --initial-balance 1000")
    print("python main.py --enable-trading --auto-trade --max-risk 0.01")
    print("python main.py --show-monitor")

if __name__ == "__main__":
    exit(main())