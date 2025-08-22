#!/usr/bin/env python3
"""
模拟交易系统测试 - 完整的交易功能测试套件
测试交易所、订单管理、持仓管理、风险控制和信号执行
"""

import unittest
import sys
import os
import time
from decimal import Decimal
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from trading import (
        SimulatedExchange, OrderManager, PositionManager, 
        TradeLogger, RiskManager, SignalExecutor, TradingMonitor
    )
    from trading.simulated_exchange import OrderType, OrderSide, OrderStatus
    from trading.risk_manager import RiskLevel
    from trading.signal_executor import ExecutionMode, SignalStrength
    from config import TradingConfig
    TRADING_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 交易模块未完全可用: {e}")
    TRADING_MODULES_AVAILABLE = False

class TestSimulatedExchange(unittest.TestCase):
    """测试模拟交易所"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
    
    def test_initial_state(self):
        """测试初始状态"""
        account = self.exchange.get_account_info()
        
        self.assertEqual(account['total_balance'], 10000.0)
        self.assertEqual(account['available_balance'], 10000.0)
        self.assertEqual(account['margin_used'], 0.0)
        self.assertEqual(len(self.exchange.get_positions()), 0)
    
    def test_place_market_order(self):
        """测试市价单"""
        # 下市价买单
        result = self.exchange.place_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            leverage=10.0
        )
        
        self.assertTrue(result['success'])
        self.assertIn('order_id', result)
        
        # 检查账户状态
        account = self.exchange.get_account_info()
        positions = self.exchange.get_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['symbol'], 'ETHUSDT')
        self.assertEqual(positions[0]['side'], 'long')
        self.assertEqual(positions[0]['size'], 1.0)
        self.assertLess(account['available_balance'], 10000.0)  # 应该有保证金占用
    
    def test_place_limit_order(self):
        """测试限价单"""
        result = self.exchange.place_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.5,
            price=2950.0,  # 低于当前价格
            leverage=5.0
        )
        
        self.assertTrue(result['success'])
        
        # 限价单应该挂单等待
        orders = self.exchange.get_orders(OrderStatus.PENDING)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['price'], 2950.0)
    
    def test_position_pnl_calculation(self):
        """测试持仓盈亏计算"""
        # 开多头仓位
        self.exchange.place_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            leverage=10.0
        )
        
        # 价格上涨
        self.exchange.update_market_price('ETHUSDT', 3100.0)
        positions = self.exchange.get_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertGreater(positions[0]['unrealized_pnl'], 90)  # 应该盈利约100(扣除滑点和手续费)
    
    def test_risk_checks(self):
        """测试风险检查"""
        # 尝试下超大订单
        result = self.exchange.place_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100.0,  # 超大订单
            leverage=20.0
        )
        
        self.assertFalse(result['success'])
        self.assertIn('保证金不足', result['error'])

class TestOrderManager(unittest.TestCase):
    """测试订单管理器"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
        self.order_manager = OrderManager(self.exchange)
    
    def test_market_order_with_sl_tp(self):
        """测试带止盈止损的市价单"""
        result = self.order_manager.place_market_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            quantity=1.0,
            stop_loss=2900.0,
            take_profit=3200.0
        )
        
        self.assertTrue(result['success'])
        
        # 检查条件订单
        active_orders = self.order_manager.get_active_orders()
        self.assertGreater(len(active_orders['conditional_orders']), 0)
    
    def test_trailing_stop(self):
        """测试追踪止损"""
        # 先开仓
        self.order_manager.place_market_order(
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            quantity=1.0
        )
        
        # 创建追踪止损
        trailing_id = self.order_manager.place_trailing_stop(
            symbol='ETHUSDT',
            side=OrderSide.SELL,
            quantity=1.0,
            trail_amount=50.0
        )
        
        self.assertIsNotNone(trailing_id)
        
        # 检查条件订单
        active_orders = self.order_manager.get_active_orders()
        conditional_orders = [o for o in active_orders['conditional_orders'] 
                            if o['condition_type'] == 'trailing_stop']
        self.assertEqual(len(conditional_orders), 1)

class TestPositionManager(unittest.TestCase):
    """测试持仓管理器"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
        self.position_manager = PositionManager(self.exchange)
    
    def test_position_size_calculation(self):
        """测试仓位大小计算"""
        # Anna Coulling 2%风险计算
        calc_result = self.position_manager.calculate_position_size(
            symbol='ETHUSDT',
            entry_price=3000.0,
            stop_loss_price=2940.0  # 2%止损
        )
        
        self.assertIn('recommended_size', calc_result)
        self.assertGreater(calc_result['recommended_size'], 0)
        self.assertLessEqual(calc_result['risk_amount'], 200)  # 2% of 10000
    
    def test_risk_level_adjustment(self):
        """测试风险等级调整"""
        # 设置保守风险等级
        self.position_manager.set_risk_level(1, "测试保守模式")
        
        # 计算仓位
        calc_result = self.position_manager.calculate_position_size(
            symbol='ETHUSDT',
            entry_price=3000.0,
            stop_loss_price=2970.0  # 1%止损
        )
        
        # 保守模式下风险应该更小
        self.assertLessEqual(calc_result['risk_amount'], 100)  # 1% of 10000
    
    def test_portfolio_risk_assessment(self):
        """测试组合风险评估"""
        # 创建多个持仓
        self.exchange.place_order('ETHUSDT', OrderSide.BUY, OrderType.MARKET, 1.0)
        self.exchange.update_market_price('BTCUSDT', 45000.0)
        self.exchange.place_order('BTCUSDT', OrderSide.BUY, OrderType.MARKET, 0.1)
        
        portfolio_risk = self.position_manager.get_portfolio_risk()
        
        self.assertIn('total_risk_ratio', portfolio_risk)
        self.assertIn('position_count', portfolio_risk)
        self.assertEqual(portfolio_risk['position_count'], 2)

class TestRiskManager(unittest.TestCase):
    """测试风险管理器"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
        self.position_manager = PositionManager(self.exchange)
        self.trade_logger = TradeLogger()
        self.risk_manager = RiskManager(
            self.exchange, self.position_manager, self.trade_logger,
            initial_risk_level=RiskLevel.MODERATE
        )
    
    def test_new_position_risk_check(self):
        """测试新仓位风险检查"""
        # 正常仓位应该通过
        result = self.risk_manager.check_new_position_risk(
            symbol='ETHUSDT',
            side='long',
            entry_price=3000.0,
            stop_loss=2940.0,
            position_size=1.0
        )
        
        self.assertTrue(result['approved'])
        self.assertIn('risk_ratio', result)
    
    def test_risk_limit_violation(self):
        """测试风险限制违规"""
        # 尝试超大仓位
        result = self.risk_manager.check_new_position_risk(
            symbol='ETHUSDT',
            side='long',
            entry_price=3000.0,
            stop_loss=2940.0,
            position_size=10.0  # 超大仓位
        )
        
        self.assertFalse(result['approved'])
        self.assertIn('reason', result)
    
    def test_emergency_stop(self):
        """测试紧急停止"""
        # 触发紧急停止
        result = self.risk_manager.trigger_emergency_stop("测试紧急停止")
        
        self.assertTrue(result['success'])
        self.assertTrue(self.risk_manager.emergency_stop_triggered)
        
        # 紧急停止后应该拒绝新仓位
        check_result = self.risk_manager.check_new_position_risk(
            symbol='ETHUSDT',
            side='long',
            entry_price=3000.0,
            stop_loss=2940.0,
            position_size=1.0
        )
        
        self.assertFalse(check_result['approved'])
    
    def test_risk_monitoring(self):
        """测试风险监控"""
        # 创建一些仓位
        self.exchange.place_order('ETHUSDT', OrderSide.BUY, OrderType.MARKET, 1.0)
        
        # 运行风险监控
        risk_summary = self.risk_manager.monitor_current_risks()
        
        self.assertIn('risk_checks', risk_summary)
        self.assertIn('alerts', risk_summary)
        self.assertIn('recommendations', risk_summary)

class TestSignalExecutor(unittest.TestCase):
    """测试信号执行器"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
        self.order_manager = OrderManager(self.exchange)
        self.position_manager = PositionManager(self.exchange)
        self.trade_logger = TradeLogger()
        self.risk_manager = RiskManager(
            self.exchange, self.position_manager, self.trade_logger
        )
        self.signal_executor = SignalExecutor(
            self.exchange, self.order_manager, self.position_manager,
            self.trade_logger, self.risk_manager
        )
    
    def test_signal_extraction(self):
        """测试信号提取"""
        # 模拟AI分析文本
        analysis_text = """
        基于当前的VPA分析，ETH/USDT呈现强烈的看多信号。
        建议做多，入场价格: $3000，止损: $2940，止盈: $3200。
        信号强度: 强，置信度: 85%
        VSA信号: No Supply, Wide Spread
        市场阶段: Accumulation
        """
        
        result = self.signal_executor.process_ai_analysis(
            analysis_text=analysis_text,
            symbol='ETHUSDT',
            model_used='test_model',
            analysis_type='vpa'
        )
        
        self.assertIn('signal', result)
        signal = result['signal']
        
        self.assertEqual(signal.direction, 'long')
        self.assertEqual(signal.entry_price, 3000.0)
        self.assertEqual(signal.stop_loss, 2940.0)
        self.assertEqual(signal.take_profit, 3200.0)
        self.assertIn('no_supply', signal.vsa_signals)
        self.assertEqual(signal.market_phase, 'accumulation')
    
    def test_signal_execution_modes(self):
        """测试不同执行模式"""
        analysis_text = "强烈看多ETH，建议做多，入场价格: $3000"
        
        # 测试仅记录模式
        self.signal_executor.set_execution_mode(ExecutionMode.SIGNAL_ONLY)
        result = self.signal_executor.process_ai_analysis(
            analysis_text=analysis_text,
            symbol='ETHUSDT',
            model_used='test_model'
        )
        
        self.assertEqual(result['action'], 'logged_only')
        
        # 测试确认模式
        self.signal_executor.set_execution_mode(ExecutionMode.CONFIRM)
        result = self.signal_executor.process_ai_analysis(
            analysis_text=analysis_text,
            symbol='ETHUSDT',
            model_used='test_model'
        )
        
        self.assertIn(result['action'], ['awaiting_confirmation', 'awaiting_manual_confirmation'])
    
    def test_signal_quality_checks(self):
        """测试信号质量检查"""
        # 弱信号应该被拒绝
        weak_analysis = "可能会上涨，不确定"
        
        result = self.signal_executor.process_ai_analysis(
            analysis_text=weak_analysis,
            symbol='ETHUSDT',
            model_used='test_model'
        )
        
        # 应该被拒绝或返回弱信号
        if result.get('signal'):
            self.assertEqual(result['signal'].strength, SignalStrength.WEAK)

class TestTradeLogger(unittest.TestCase):
    """测试交易日志系统"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        self.trade_logger = TradeLogger(log_dir="test_logs")
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists("test_logs"):
            shutil.rmtree("test_logs")
    
    def test_trade_logging(self):
        """测试交易记录"""
        # 记录开仓
        trade_id = self.trade_logger.log_trade_entry(
            symbol='ETHUSDT',
            side='long',
            quantity=1.0,
            entry_price=3000.0,
            leverage=10.0
        )
        
        self.assertIsNotNone(trade_id)
        
        # 记录平仓
        success = self.trade_logger.log_trade_exit(
            trade_id=trade_id,
            exit_price=3100.0,
            realized_pnl=100.0,
            exit_reason='manual'
        )
        
        self.assertTrue(success)
    
    def test_ai_decision_logging(self):
        """测试AI决策记录"""
        decision_id = self.trade_logger.log_ai_decision(
            symbol='ETHUSDT',
            model_used='gpt4o-mini',
            analysis_type='vpa',
            raw_analysis='看多ETH',
            extracted_signals={'direction': 'long', 'strength': 3}
        )
        
        self.assertIsNotNone(decision_id)
    
    def test_performance_summary(self):
        """测试性能摘要"""
        # 添加一些交易记录
        for i in range(5):
            trade_id = self.trade_logger.log_trade_entry(
                symbol='ETHUSDT',
                side='long' if i % 2 == 0 else 'short',
                quantity=1.0,
                entry_price=3000.0
            )
            
            # 模拟盈利/亏损
            pnl = 50.0 if i < 3 else -30.0
            self.trade_logger.log_trade_exit(
                trade_id=trade_id,
                exit_price=3000.0 + pnl,
                realized_pnl=pnl
            )
        
        summary = self.trade_logger.get_performance_summary(days=1)
        
        self.assertIn('total_trades', summary)
        self.assertIn('win_rate', summary)
        self.assertEqual(summary['total_trades'], 5)

class TestTradingConfig(unittest.TestCase):
    """测试交易配置"""
    
    def test_config_loading(self):
        """测试配置加载"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        config = TradingConfig()
        
        self.assertEqual(config.initial_balance, 10000.0)
        self.assertEqual(config.default_symbol, "ETHUSDT")
        self.assertIsNotNone(config.risk_management)
        self.assertIsNotNone(config.exchange_settings)
    
    def test_config_validation(self):
        """测试配置验证"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        config = TradingConfig()
        validation = config.validate_config()
        
        self.assertIn('valid', validation)
        self.assertIn('issues', validation)

class TestIntegration(unittest.TestCase):
    """集成测试 - 测试完整交易流程"""
    
    def setUp(self):
        """测试前设置"""
        if not TRADING_MODULES_AVAILABLE:
            self.skipTest("交易模块不可用")
        
        # 初始化完整交易系统
        self.exchange = SimulatedExchange(initial_balance=10000.0)
        self.exchange.update_market_price('ETHUSDT', 3000.0)
        
        self.order_manager = OrderManager(self.exchange)
        self.position_manager = PositionManager(self.exchange)
        self.trade_logger = TradeLogger(log_dir="test_logs")
        self.risk_manager = RiskManager(
            self.exchange, self.position_manager, self.trade_logger
        )
        self.signal_executor = SignalExecutor(
            self.exchange, self.order_manager, self.position_manager,
            self.trade_logger, self.risk_manager
        )
        self.monitor = TradingMonitor(
            self.exchange, self.order_manager, self.position_manager,
            self.trade_logger, self.risk_manager, self.signal_executor
        )
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists("test_logs"):
            shutil.rmtree("test_logs")
    
    def test_complete_trading_cycle(self):
        """测试完整交易周期"""
        # 1. AI分析生成信号
        analysis_text = """
        基于VSA分析，ETH/USDT出现强烈看多信号。
        Spring信号确认，建议做多。
        入场价格: $3000, 止损: $2940, 止盈: $3180
        信号强度: 很强, 置信度: 90%
        """
        
        # 2. 处理信号并执行交易
        self.signal_executor.set_execution_mode(ExecutionMode.AUTO)
        result = self.signal_executor.process_ai_analysis(
            analysis_text=analysis_text,
            symbol='ETHUSDT',
            model_used='test_model'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'executed')
        
        # 3. 检查持仓
        positions = self.exchange.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['side'], 'long')
        
        # 4. 模拟价格变动和盈利
        self.exchange.update_market_price('ETHUSDT', 3150.0)
        
        # 5. 检查监控数据
        dashboard = self.monitor.get_dashboard_data()
        
        self.assertIn('account_summary', dashboard)
        self.assertIn('positions_summary', dashboard)
        self.assertGreater(dashboard['account_summary']['unrealized_pnl'], 100)
        
        # 6. 手动平仓
        close_result = self.exchange.close_position('ETHUSDT')
        self.assertTrue(close_result['success'])
        
        # 7. 检查最终状态
        final_account = self.exchange.get_account_info()
        self.assertGreater(final_account['total_balance'], 10000.0)  # 应该有盈利
    
    def test_risk_management_integration(self):
        """测试风险管理集成"""
        # 尝试创建超出风险限制的大仓位
        large_position_analysis = """
        超强看多信号，建议大幅做多ETH！
        入场价格: $3000, 数量: 20 ETH
        """
        
        result = self.signal_executor.process_ai_analysis(
            analysis_text=large_position_analysis,
            symbol='ETHUSDT',
            model_used='test_model'
        )
        
        # 应该被风险管理拒绝
        self.assertFalse(result['success'])
    
    def test_monitoring_and_alerts(self):
        """测试监控和警报"""
        # 启动监控
        self.monitor.start_monitoring()
        
        # 创建一些交易活动
        self.exchange.place_order('ETHUSDT', OrderSide.BUY, OrderType.MARKET, 2.0)
        
        # 模拟亏损
        self.exchange.update_market_price('ETHUSDT', 2800.0)
        
        # 等待监控更新
        time.sleep(2)
        
        # 检查监控数据
        dashboard = self.monitor.get_dashboard_data()
        self.assertIn('recent_alerts', dashboard)
        
        # 停止监控
        self.monitor.stop_monitoring()

def run_tests():
    """运行所有测试"""
    print("🧪 开始运行模拟交易系统测试...")
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestSimulatedExchange,
        TestOrderManager,
        TestPositionManager,
        TestRiskManager,
        TestSignalExecutor,
        TestTradeLogger,
        TestTradingConfig,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 显示结果摘要
    print(f"\n📊 测试结果摘要:")
    print(f"✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败: {len(result.failures)}")
    print(f"⚠️ 错误: {len(result.errors)}")
    print(f"⏭️ 跳过: {len(result.skipped)}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)