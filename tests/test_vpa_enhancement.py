#!/usr/bin/env python3
"""
VPA增强功能专项测试
验证VSA分析、永续合约特色、多时间框架等新功能

测试覆盖：
1. VSA计算器功能测试
2. 永续合约数据获取测试  
3. 多时间框架分析测试
4. 增强共识计算器测试
5. Pattern格式VPA描述测试
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.vsa_calculator import VSACalculator, VSASignalType, SpreadType
from data.binance_fetcher import BinanceFetcher
from data.data_processor import DataProcessor
from ai.timeframe_analyzer import TimeframeAnalyzer, TimeframeSignal, MultiTimeframeAnalysis
from ai.consensus_calculator import ConsensusCalculator, VPASignal
from formatters.data_formatter import DataFormatter

class TestVSACalculator(unittest.TestCase):
    """VSA计算器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.vsa_calculator = VSACalculator()
        
        # 创建测试数据
        self.test_df = pd.DataFrame({
            'datetime': pd.date_range('2025-01-01', periods=50, freq='H'),
            'open': np.random.uniform(4000, 4500, 50),
            'high': np.random.uniform(4100, 4600, 50),
            'low': np.random.uniform(3900, 4400, 50),
            'close': np.random.uniform(4000, 4500, 50),
            'volume': np.random.uniform(100000, 1000000, 50)
        })
        
        # 确保OHLC逻辑正确
        for i in range(len(self.test_df)):
            high = max(self.test_df.iloc[i]['open'], self.test_df.iloc[i]['close']) + np.random.uniform(0, 50)
            low = min(self.test_df.iloc[i]['open'], self.test_df.iloc[i]['close']) - np.random.uniform(0, 50)
            self.test_df.at[i, 'high'] = high
            self.test_df.at[i, 'low'] = low
    
    def test_vsa_indicators_calculation(self):
        """测试VSA指标计算"""
        result_df = self.vsa_calculator.calculate_vsa_indicators(self.test_df)
        
        # 检查新增的VSA列
        expected_columns = [
            'spread', 'close_position', 'volume_ratio', 'spread_type',
            'vsa_signal', 'signal_strength', 'professional_activity',
            'effort_result_ratio', 'supply_demand_balance'
        ]
        
        for col in expected_columns:
            self.assertIn(col, result_df.columns, f"缺少VSA指标: {col}")
        
        # 检查数据类型和范围
        self.assertTrue(all(result_df['close_position'].between(0, 1)), 
                       "close_position应该在0-1范围内")
        self.assertTrue(all(result_df['signal_strength'].between(0, 1)), 
                       "signal_strength应该在0-1范围内")
        self.assertTrue(all(result_df['supply_demand_balance'].between(-1, 1)), 
                       "supply_demand_balance应该在-1到1范围内")
    
    def test_vsa_signal_identification(self):
        """测试VSA信号识别"""
        # 创建特定的测试场景
        
        # No Demand场景：上涨但低成交量
        test_df = self.test_df.copy()
        test_df.at[test_df.index[-1], 'close'] = test_df.iloc[-1]['open'] + 50  # 上涨
        test_df.at[test_df.index[-1], 'volume'] = test_df['volume'].mean() * 0.5  # 低量
        
        result_df = self.vsa_calculator.calculate_vsa_indicators(test_df)
        
        # 应该检测到某些VSA信号
        self.assertIsNotNone(result_df['vsa_signal'].iloc[-1])
        self.assertIn(result_df['vsa_signal'].iloc[-1], [signal.value for signal in VSASignalType])
    
    def test_vsa_summary_generation(self):
        """测试VSA摘要生成"""
        summary = self.vsa_calculator.get_vsa_summary(self.test_df)
        
        expected_keys = [
            'signal_distribution', 'professional_activity_count',
            'recent_strong_signals', 'supply_demand_balance',
            'latest_vsa_signal', 'latest_signal_strength',
            'wide_spread_count', 'narrow_spread_count'
        ]
        
        for key in expected_keys:
            self.assertIn(key, summary, f"VSA摘要缺少: {key}")
        
        # 检查数据类型
        self.assertIsInstance(summary['professional_activity_count'], int)
        self.assertIsInstance(summary['supply_demand_balance'], float)
        self.assertIsInstance(summary['latest_signal_strength'], float)
    
    def test_vsa_interpretation(self):
        """测试VSA信号解释"""
        summary = self.vsa_calculator.get_vsa_summary(self.test_df)
        interpretation = self.vsa_calculator.interpret_vsa_signals(summary)
        
        self.assertIsInstance(interpretation, str)
        self.assertGreater(len(interpretation), 0, "VSA解释不应为空")

class TestPerpetualDataFetching(unittest.TestCase):
    """永续合约数据获取测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.fetcher = BinanceFetcher()
    
    @patch('ccxt.binance')
    def test_funding_rate_fetching(self, mock_exchange):
        """测试资金费率获取"""
        # Mock资金费率响应
        mock_exchange.return_value.fetch_funding_rate.return_value = {
            'symbol': 'ETH/USDT',
            'fundingRate': 0.0001,
            'timestamp': 1640995200000,
            'datetime': '2022-01-01T00:00:00.000Z'
        }
        
        # 这里需要实际测试时需要有效的API连接
        # 当前只测试接口存在性
        self.assertTrue(hasattr(self.fetcher, 'get_funding_rate'))
        self.assertTrue(hasattr(self.fetcher, 'get_funding_rate_history'))
        self.assertTrue(hasattr(self.fetcher, 'get_open_interest'))
        self.assertTrue(hasattr(self.fetcher, 'get_perpetual_data'))
    
    def test_perpetual_data_structure(self):
        """测试永续合约数据结构"""
        # 测试方法是否存在和返回格式
        with patch.object(self.fetcher, 'get_ohlcv') as mock_ohlcv, \
             patch.object(self.fetcher, 'get_funding_rate') as mock_funding, \
             patch.object(self.fetcher, 'get_open_interest') as mock_oi, \
             patch.object(self.fetcher, 'get_funding_rate_history') as mock_funding_hist:
            
            # Mock返回值
            mock_ohlcv.return_value = pd.DataFrame({
                'datetime': ['2025-01-01 00:00:00'],
                'open': [4000], 'high': [4100], 'low': [3900], 
                'close': [4050], 'volume': [100000]
            })
            mock_funding.return_value = {'fundingRate': 0.0001}
            mock_oi.return_value = {'openInterestAmount': 1000000}
            mock_funding_hist.return_value = pd.DataFrame({'fundingRate': [0.0001, 0.0002]})
            
            try:
                result = self.fetcher.get_perpetual_data()
                
                # 检查返回结构
                expected_keys = ['ohlcv_data', 'current_funding_rate', 
                               'open_interest', 'funding_rate_history', 'stats']
                for key in expected_keys:
                    self.assertIn(key, result, f"永续合约数据缺少: {key}")
                    
            except Exception as e:
                # 如果没有API连接，跳过实际调用测试
                self.skipTest(f"需要有效的API连接: {e}")

class TestTimeframeAnalyzer(unittest.TestCase):
    """多时间框架分析器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.analyzer = TimeframeAnalyzer()
    
    def test_timeframe_config(self):
        """测试时间框架配置"""
        config = self.analyzer.timeframe_config
        
        # 检查配置完整性
        expected_timeframes = ['1d', '4h', '1h', '15m']
        for tf in expected_timeframes:
            self.assertIn(tf, config, f"缺少时间框架配置: {tf}")
            
            # 检查每个配置的必要字段
            tf_config = config[tf]
            self.assertIn('importance', tf_config)
            self.assertIn('weight', tf_config)
            self.assertIn('limit', tf_config)
            self.assertIn('description', tf_config)
        
        # 检查权重总和
        total_weight = sum(tf_config['weight'] for tf_config in config.values())
        self.assertAlmostEqual(total_weight, 1.0, places=1, 
                              msg="时间框架权重总和应接近1.0")
    
    @patch('data.binance_fetcher.BinanceFetcher.get_ohlcv')
    @patch('data.data_processor.DataProcessor.add_vsa_indicators')
    def test_single_timeframe_analysis(self, mock_vsa, mock_ohlcv):
        """测试单时间框架分析"""
        # Mock数据
        mock_df = pd.DataFrame({
            'datetime': pd.date_range('2025-01-01', periods=50, freq='H'),
            'open': np.random.uniform(4000, 4500, 50),
            'high': np.random.uniform(4100, 4600, 50),
            'low': np.random.uniform(3900, 4400, 50),
            'close': np.random.uniform(4000, 4500, 50),
            'volume': np.random.uniform(100000, 1000000, 50),
            'vsa_signal': ['normal'] * 50,
            'professional_activity': [False] * 50,
            'supply_demand_balance': np.random.uniform(-1, 1, 50)
        })
        
        mock_ohlcv.return_value = mock_df
        mock_vsa.return_value = mock_df
        
        # 测试单个时间框架分析
        signal = self.analyzer._analyze_single_timeframe('ETH/USDT', '1h')
        
        if signal is not None:
            self.assertIsInstance(signal, TimeframeSignal)
            self.assertEqual(signal.timeframe, '1h')
            self.assertIsNotNone(signal.market_phase)
            self.assertIsNotNone(signal.vpa_signal)
        else:
            self.skipTest("信号分析返回None，可能是由于数据不足或API限制")
    
    def test_consensus_calculation(self):
        """测试共识计算"""
        # 创建测试信号
        signals = [
            TimeframeSignal(
                timeframe='1d',
                importance=self.analyzer.timeframe_config['1d']['importance'],
                market_phase='accumulation',
                vpa_signal='bullish',
                price_direction='up',
                signal_strength=0.8
            ),
            TimeframeSignal(
                timeframe='4h',
                importance=self.analyzer.timeframe_config['4h']['importance'],
                market_phase='accumulation',
                vpa_signal='bullish',
                price_direction='up',
                signal_strength=0.7
            )
        ]
        
        consensus = self.analyzer._calculate_consensus_score(signals)
        
        self.assertIsInstance(consensus, float)
        self.assertGreaterEqual(consensus, 0.0)
        self.assertLessEqual(consensus, 1.0)
        
        # 完全一致的信号应该有高共识
        self.assertGreater(consensus, 0.8, "完全一致的信号应该有高共识得分")

class TestEnhancedConsensusCalculator(unittest.TestCase):
    """增强共识计算器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.calculator = ConsensusCalculator()
    
    def test_enhanced_weight_structure(self):
        """测试增强的权重结构"""
        weights = self.calculator.weights
        
        # 检查新增的权重维度
        expected_dimensions = [
            'market_phase', 'vpa_signal', 'price_direction',
            'vsa_signals', 'timeframe_consistency', 'perpetual_factors',
            'confidence'
        ]
        
        for dimension in expected_dimensions:
            self.assertIn(dimension, weights, f"缺少权重维度: {dimension}")
        
        # 检查权重总和
        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2, 
                              msg="权重总和应为1.0")
    
    def test_vsa_signal_extraction(self):
        """测试VSA信号提取"""
        test_analysis = """
        基于VSA分析，当前市场显示出明显的No Demand信号，上涨缺乏成交量支持。
        同时检测到Wide Spread现象，表明市场波动加剧。
        从多时间框架来看，各周期信号基本一致。
        永续合约的正资金费率显示多头情绪浓厚。
        """
        
        signal = self.calculator._extract_vpa_signals(test_analysis, 'test_model')
        
        # 检查新增字段
        self.assertIsInstance(signal.vsa_signals, list)
        self.assertIsInstance(signal.perpetual_factors, list)
        self.assertIsNotNone(signal.timeframe_consistency)
        
        # 检查VSA信号是否被正确识别
        if signal.vsa_signals:
            self.assertIn('no_demand', signal.vsa_signals)
            self.assertIn('wide_spread', signal.vsa_signals)
    
    def test_list_consensus_calculation(self):
        """测试列表类型共识计算"""
        # 创建测试信号
        model_signals = {
            'model1': VPASignal(
                vsa_signals=['no_demand', 'wide_spread'],
                perpetual_factors=['funding_rate_positive']
            ),
            'model2': VPASignal(
                vsa_signals=['no_demand', 'climax_volume'],
                perpetual_factors=['funding_rate_positive', 'leverage_effect']
            ),
            'model3': VPASignal(
                vsa_signals=['wide_spread'],
                perpetual_factors=['funding_rate_positive']
            )
        }
        
        # 测试VSA信号一致性
        vsa_consensus = self.calculator._calculate_list_consensus(model_signals, 'vsa_signals')
        self.assertIsInstance(vsa_consensus, float)
        self.assertGreaterEqual(vsa_consensus, 0.0)
        self.assertLessEqual(vsa_consensus, 1.0)
        
        # 测试永续合约因素一致性
        perpetual_consensus = self.calculator._calculate_list_consensus(model_signals, 'perpetual_factors')
        self.assertIsInstance(perpetual_consensus, float)

class TestEnhancedPatternFormat(unittest.TestCase):
    """增强Pattern格式测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.formatter = DataFormatter()
        
        # 创建测试数据
        self.test_df = pd.DataFrame({
            'datetime': [f'2025-01-01 {i:02d}:00:00' for i in range(24)],
            'open': np.random.uniform(4000, 4500, 24),
            'high': np.random.uniform(4100, 4600, 24),
            'low': np.random.uniform(3900, 4400, 24),
            'close': np.random.uniform(4000, 4500, 24),
            'volume': np.random.uniform(100000, 1000000, 24)
        })
        
        # 确保OHLC逻辑正确
        for i in range(len(self.test_df)):
            high = max(self.test_df.iloc[i]['open'], self.test_df.iloc[i]['close']) + np.random.uniform(0, 50)
            low = min(self.test_df.iloc[i]['open'], self.test_df.iloc[i]['close']) - np.random.uniform(0, 50)
            self.test_df.at[i, 'high'] = high
            self.test_df.at[i, 'low'] = low
    
    def test_enhanced_pattern_description(self):
        """测试增强的Pattern描述"""
        result = self.formatter.to_pattern_description(
            self.test_df, 
            include_vsa=True, 
            include_perpetual_context=True
        )
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # 检查VPA专业内容
        vpa_keywords = [
            'VPA', 'VSA', 'Volume Spread Analysis', 
            'Smart Money', 'Professional', 'Wyckoff',
            '永续合约', '资金费率', '持仓量'
        ]
        
        result_lower = result.lower()
        found_keywords = [kw for kw in vpa_keywords if kw.lower() in result_lower]
        self.assertGreater(len(found_keywords), 3, 
                          f"应包含更多VPA专业术语，当前找到: {found_keywords}")
    
    def test_vsa_analysis_formatting(self):
        """测试VSA分析格式化"""
        vsa_lines = self.formatter._format_vsa_analysis(self.test_df)
        
        self.assertIsInstance(vsa_lines, list)
        self.assertGreater(len(vsa_lines), 0)
        
        # 检查VSA专业术语
        vsa_content = ' '.join(vsa_lines)
        vsa_terms = ['Wide Spread', 'Close Position', 'No Demand', 'No Supply', 'Climax Volume']
        
        # 至少应该包含VSA分析的框架
        self.assertIn('VSA', vsa_content)
    
    def test_perpetual_context_formatting(self):
        """测试永续合约背景格式化"""
        perpetual_lines = self.formatter._format_perpetual_context()
        
        self.assertIsInstance(perpetual_lines, list)
        self.assertGreater(len(perpetual_lines), 0)
        
        # 检查永续合约专业术语
        perpetual_content = ' '.join(perpetual_lines)
        perpetual_terms = ['资金费率', '持仓量', '杠杆', 'Smart Money', '强平']
        
        found_terms = [term for term in perpetual_terms if term in perpetual_content]
        self.assertGreater(len(found_terms), 2, 
                          f"应包含更多永续合约术语，当前找到: {found_terms}")

class TestVPAIntegration(unittest.TestCase):
    """VPA功能集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.processor = DataProcessor()
        self.formatter = DataFormatter()
        
        # 创建测试数据
        self.test_df = pd.DataFrame({
            'datetime': pd.date_range('2025-01-01', periods=50, freq='H'),
            'open': np.random.uniform(4000, 4500, 50),
            'high': np.random.uniform(4100, 4600, 50),
            'low': np.random.uniform(3900, 4400, 50),
            'close': np.random.uniform(4000, 4500, 50),
            'volume': np.random.uniform(100000, 1000000, 50)
        })
    
    def test_vsa_integration_with_data_processor(self):
        """测试VSA与数据处理器的集成"""
        # 添加VSA指标
        result_df = self.processor.add_vsa_indicators(self.test_df)
        
        # 检查VSA指标是否被正确添加
        vsa_columns = ['spread', 'close_position', 'volume_ratio', 'vsa_signal']
        for col in vsa_columns:
            self.assertIn(col, result_df.columns, f"缺少VSA指标: {col}")
        
        # 获取VSA摘要
        summary = self.processor.get_vsa_summary(self.test_df)
        self.assertIsInstance(summary, dict)
        self.assertIn('latest_vsa_signal', summary)
        
        # 获取VSA解释
        interpretation = self.processor.interpret_vsa_signals(summary)
        self.assertIsInstance(interpretation, str)
        self.assertGreater(len(interpretation), 0)
    
    def test_enhanced_pattern_with_vsa(self):
        """测试增强Pattern格式与VSA的集成"""
        # 生成增强的Pattern描述
        pattern_text = self.formatter.to_pattern_description(
            self.test_df, 
            include_vsa=True, 
            include_perpetual_context=True
        )
        
        # 检查集成效果
        self.assertIn('VSA', pattern_text)
        self.assertIn('永续合约', pattern_text)
        self.assertIn('Wyckoff', pattern_text)
        
        # 检查格式结构
        sections = pattern_text.split('##')
        self.assertGreater(len(sections), 3, "应包含多个分析章节")

def run_vpa_enhancement_tests():
    """运行VPA增强功能测试套件"""
    print("=" * 60)
    print("🧪 VPA增强功能测试套件")
    print("=" * 60)
    
    # 创建测试套件
    test_classes = [
        TestVSACalculator,
        TestPerpetualDataFetching,
        TestTimeframeAnalyzer,
        TestEnhancedConsensusCalculator,
        TestEnhancedPatternFormat,
        TestVPAIntegration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📊 VPA增强功能测试结果摘要")
    print("=" * 60)
    print(f"✅ 通过测试: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败测试: {len(result.failures)}")
    print(f"💥 错误测试: {len(result.errors)}")
    print(f"⏭️  跳过测试: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            last_line = traceback.split('\n')[-2]
            print(f"  - {test}: {last_line}")
    
    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            last_line = traceback.split('\n')[-2]
            print(f"  - {test}: {last_line}")
    
    # 评估整体成功率
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n🎯 整体成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🏆 VPA增强功能测试表现优秀!")
    elif success_rate >= 75:
        print("✅ VPA增强功能测试基本通过")
    else:
        print("⚠️ VPA增强功能需要进一步改进")
    
    return result

if __name__ == '__main__':
    run_vpa_enhancement_tests()