#!/usr/bin/env python3
"""
阶段1: 基础可行性测试
测试LLM能否理解和分析OHLCV数据格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from data import BinanceFetcher, DataProcessor
from formatters import DataFormatter
from ai import OpenRouterClient, AnalysisEngine
from config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeasibilityTester:
    def __init__(self):
        try:
            Settings.validate()
            self.fetcher = BinanceFetcher()
            self.processor = DataProcessor()
            self.formatter = DataFormatter()
            self.client = OpenRouterClient()
            logger.info("✅ 所有组件初始化成功")
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise
    
    def test_data_fetching(self, symbol='ETH/USDT', limit=50):
        """测试数据获取功能"""
        logger.info(f"📊 测试数据获取: {symbol} 最近{limit}条")
        
        try:
            df = self.fetcher.get_ohlcv(symbol=symbol, limit=limit)
            logger.info(f"✅ 成功获取 {len(df)} 条数据")
            
            # 显示数据概要
            stats = self.fetcher.calculate_basic_stats(df)
            logger.info(f"数据范围: {stats['time_range']['start']} - {stats['time_range']['end']}")
            logger.info(f"价格范围: ${stats['price_range']['min']:.2f} - ${stats['price_range']['max']:.2f}")
            
            return df
        except Exception as e:
            logger.error(f"❌ 数据获取失败: {e}")
            return None
    
    def test_data_formatting(self, df):
        """测试4种数据格式"""
        logger.info("🔧 测试数据格式化...")
        
        formats_data = {}
        token_estimates = self.formatter.estimate_tokens_by_format(df)
        
        try:
            # CSV格式
            formats_data['csv'] = self.formatter.to_csv_format(df)
            logger.info(f"✅ CSV格式生成成功，预估tokens: {token_estimates['csv']}")
            
            # 文本描述格式
            formats_data['text'] = self.formatter.to_text_narrative(df)
            logger.info(f"✅ 文本格式生成成功，预估tokens: {token_estimates['text']}")
            
            # JSON格式
            formats_data['json'] = self.formatter.to_structured_json(df)
            logger.info(f"✅ JSON格式生成成功，预估tokens: {token_estimates['json']}")
            
            # 模式描述格式
            formats_data['pattern'] = self.formatter.to_pattern_description(df)
            logger.info(f"✅ 模式格式生成成功，预估tokens: {token_estimates['pattern']}")
            
            return formats_data, token_estimates
            
        except Exception as e:
            logger.error(f"❌ 数据格式化失败: {e}")
            return None, None
    
    def test_single_model_analysis(self, data, model='gpt4', format_type='csv'):
        """测试单个模型分析"""
        logger.info(f"🤖 测试 {model} 模型分析 ({format_type} 格式)...")
        
        try:
            result = self.client.analyze_market_data(
                data=data,
                model_name=model,
                analysis_type='vpa'
            )
            
            if result.get('error'):
                logger.error(f"❌ {model} 分析失败: {result['error']}")
                return None
            
            logger.info(f"✅ {model} 分析成功")
            logger.info(f"Token使用: {result.get('usage', {})}")
            logger.info(f"响应时间: {result.get('response_time', 0):.2f}秒")
            
            # 显示分析结果的前200字符
            analysis = result.get('analysis', '')
            preview = analysis[:200] + '...' if len(analysis) > 200 else analysis
            logger.info(f"分析预览: {preview}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 模型分析失败: {e}")
            return None
    
    def run_basic_feasibility_test(self):
        """运行基础可行性测试"""
        logger.info("🚀 开始基础可行性测试...")
        
        results = {
            'data_fetching': False,
            'data_formatting': False,
            'model_analysis': {},
            'token_usage': {},
            'recommendations': []
        }
        
        # 1. 测试数据获取
        df = self.test_data_fetching()
        if df is None:
            return results
        
        results['data_fetching'] = True
        
        # 2. 测试数据格式化
        formats_data, token_estimates = self.test_data_formatting(df)
        if formats_data is None:
            return results
        
        results['data_formatting'] = True
        results['token_usage'] = token_estimates
        
        # 3. 测试不同模型 - 只测试最优格式(CSV)以节省成本
        test_models = ['gpt4o-mini']  # 最经济的模型，可以添加其他: 'claude-haiku', 'gemini-flash'
        
        for model in test_models:
            if model in Settings.MODELS:
                result = self.test_single_model_analysis(
                    data=formats_data['csv'],
                    model=model,
                    format_type='csv'
                )
                results['model_analysis'][model] = result is not None
        
        # 生成建议
        self._generate_recommendations(results)
        
        return results
    
    def _generate_recommendations(self, results):
        """基于测试结果生成建议"""
        recommendations = []
        
        if results['data_fetching']:
            recommendations.append("✅ 数据获取功能正常，可以获取实时ETH永续合约数据")
        
        if results['data_formatting']:
            recommendations.append("✅ 数据格式化功能完整，支持4种不同的输入格式")
            
            # Token使用建议
            token_usage = results['token_usage']
            min_format = min(token_usage.keys(), key=lambda x: token_usage[x])
            max_format = max(token_usage.keys(), key=lambda x: token_usage[x])
            
            recommendations.append(f"💡 Token使用: {min_format}格式最节省({token_usage[min_format]}), {max_format}格式最详细({token_usage[max_format]})")
        
        # 模型分析建议
        successful_models = [model for model, success in results['model_analysis'].items() if success]
        if successful_models:
            recommendations.append(f"✅ 成功测试的模型: {', '.join(successful_models)}")
        
        failed_models = [model for model, success in results['model_analysis'].items() if not success]
        if failed_models:
            recommendations.append(f"⚠️ 需要检查的模型: {', '.join(failed_models)}")
        
        results['recommendations'] = recommendations

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 ETH永续合约LLM分析 - 基础可行性测试")
    print("=" * 60)
    
    try:
        tester = FeasibilityTester()
        results = tester.run_basic_feasibility_test()
        
        # 显示测试结果
        print("\\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        print(f"数据获取: {'✅ 成功' if results['data_fetching'] else '❌ 失败'}")
        print(f"数据格式化: {'✅ 成功' if results['data_formatting'] else '❌ 失败'}")
        
        print("\\nToken使用估算:")
        for format_type, tokens in results['token_usage'].items():
            print(f"  {format_type}: {tokens} tokens")
        
        print("\\n模型分析结果:")
        for model, success in results['model_analysis'].items():
            print(f"  {model}: {'✅ 成功' if success else '❌ 失败'}")
        
        print("\\n💡 建议和结论:")
        for rec in results['recommendations']:
            print(f"  {rec}")
        
        # 整体结论
        success_count = sum([
            results['data_fetching'],
            results['data_formatting'],
            len([s for s in results['model_analysis'].values() if s]) > 0
        ])
        
        if success_count >= 2:
            print("\\n🎉 基础可行性测试通过！可以继续进行格式优化测试。")
        else:
            print("\\n⚠️ 基础测试存在问题，需要解决后再继续。")
            
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\\n❌ 测试执行失败: {e}")

if __name__ == "__main__":
    main()