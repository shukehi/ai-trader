#!/usr/bin/env python3
"""
2025年最新模型测试
测试OpenAI GPT-4o、Claude 3.5、Gemini 2.0、Grok等最新模型的性能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from data import BinanceFetcher, DataProcessor
from formatters import DataFormatter
from ai import OpenRouterClient
from config import Settings
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Model2025Tester:
    def __init__(self):
        try:
            Settings.validate()
            self.fetcher = BinanceFetcher()
            self.formatter = DataFormatter()
            self.client = OpenRouterClient()
            logger.info("✅ 2025模型测试器初始化成功")
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise
    
    def get_test_models(self):
        """获取要测试的模型分组"""
        return {
            'flagship': ['gpt5', 'claude-opus-41', 'gemini-25-pro', 'grok4'],  # 🔥 2025最新旗舰版
            'economy': ['gpt4o-mini', 'claude-haiku', 'gemini-flash', 'llama'],
            'balanced': ['gpt4o', 'claude', 'gemini', 'grok'],
            'premium': ['o1-mini', 'claude-opus', 'gemini-2', 'llama-405b'],
            'reasoning': ['o1', 'o1-mini']  # 专门的推理模型
        }
    
    def test_model_performance(self, model_name: str, data: str) -> dict:
        """测试单个模型的性能"""
        logger.info(f"🧪 测试模型: {model_name}")
        
        start_time = time.time()
        
        try:
            result = self.client.analyze_market_data(
                data=data,
                model_name=model_name,
                analysis_type='vpa'
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if result.get('error'):
                return {
                    'model': model_name,
                    'success': False,
                    'error': result['error'],
                    'response_time': response_time
                }
            
            # 分析结果质量指标
            analysis = result.get('analysis', '')
            
            performance_metrics = {
                'model': model_name,
                'success': True,
                'response_time': response_time,
                'token_usage': result.get('usage', {}),
                'analysis_length': len(analysis),
                'analysis_quality_score': self._assess_analysis_quality(analysis),
                'cost_estimate': self.client.estimate_cost(
                    model_name, 
                    result.get('usage', {}).get('prompt_tokens', 0),
                    result.get('usage', {}).get('completion_tokens', 0)
                )
            }
            
            logger.info(f"✅ {model_name} 测试完成 - {response_time:.2f}s, ${performance_metrics['cost_estimate']['estimated_cost']:.6f}")
            
            return performance_metrics
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"❌ {model_name} 测试失败: {e}")
            return {
                'model': model_name,
                'success': False,
                'error': str(e),
                'response_time': end_time - start_time
            }
    
    def _assess_analysis_quality(self, analysis: str) -> float:
        """评估分析质量（简单版本）"""
        if not analysis:
            return 0.0
        
        quality_score = 0.0
        
        # 检查关键VPA术语
        vpa_terms = ['成交量', '量价', '支撑', '阻力', '趋势', '突破', '背离']
        found_terms = sum(1 for term in vpa_terms if term in analysis)
        quality_score += (found_terms / len(vpa_terms)) * 30
        
        # 检查技术分析术语
        tech_terms = ['MACD', 'RSI', 'MA', '均线', '布林', '指标']
        found_tech = sum(1 for term in tech_terms if term in analysis)
        quality_score += (found_tech / len(tech_terms)) * 20
        
        # 检查建议和结论
        advice_terms = ['建议', '风险', '目标', '止损', '入场', '出场']
        found_advice = sum(1 for term in advice_terms if term in analysis)
        quality_score += (found_advice / len(advice_terms)) * 25
        
        # 文本长度合理性
        length_score = min(len(analysis) / 1000, 1) * 25  # 期望1000字符以上
        quality_score += length_score
        
        return min(quality_score, 100.0)
    
    def run_comprehensive_test(self):
        """运行全面的模型对比测试"""
        logger.info("🚀 开始2025年最新模型综合测试...")
        
        # 获取测试数据
        logger.info("📊 获取ETH永续合约测试数据...")
        df = self.fetcher.get_ohlcv(symbol='ETH/USDT', limit=30)  # 使用较少数据节省成本
        
        if df is None:
            logger.error("❌ 无法获取测试数据")
            return None
        
        # 格式化为CSV格式（最经济）
        test_data = self.formatter.to_csv_format(df)
        token_estimate = len(test_data.split())
        
        logger.info(f"📝 测试数据准备完成，预估输入tokens: {token_estimate}")
        
        # 获取测试模型
        model_groups = self.get_test_models()
        
        results = {
            'test_time': datetime.now().isoformat(),
            'data_info': {
                'symbol': 'ETH/USDT',
                'timeframe': '1h',
                'bars': len(df),
                'estimated_tokens': token_estimate
            },
            'model_results': {},
            'summary': {}
        }
        
        # 按组测试模型
        for group_name, models in model_groups.items():
            logger.info(f"\\n🎯 测试模型组: {group_name.upper()}")
            results['model_results'][group_name] = []
            
            for model in models:
                if model in Settings.MODELS:
                    result = self.test_model_performance(model, test_data)
                    results['model_results'][group_name].append(result)
                    
                    # 添加延迟避免频率限制
                    time.sleep(2)
                else:
                    logger.warning(f"⚠️ 模型 {model} 不在配置中，跳过")
        
        # 生成测试总结
        results['summary'] = self._generate_summary(results['model_results'])
        
        return results
    
    def _generate_summary(self, model_results: dict) -> dict:
        """生成测试总结"""
        summary = {
            'total_models_tested': 0,
            'successful_models': 0,
            'failed_models': 0,
            'best_performance': {},
            'cost_analysis': {},
            'recommendations': []
        }
        
        all_results = []
        for group_results in model_results.values():
            all_results.extend(group_results)
        
        successful_results = [r for r in all_results if r.get('success', False)]
        
        summary['total_models_tested'] = len(all_results)
        summary['successful_models'] = len(successful_results)
        summary['failed_models'] = len(all_results) - len(successful_results)
        
        if successful_results:
            # 最佳性能模型
            fastest = min(successful_results, key=lambda x: x['response_time'])
            cheapest = min(successful_results, key=lambda x: x['cost_estimate']['estimated_cost'])
            highest_quality = max(successful_results, key=lambda x: x['analysis_quality_score'])
            
            summary['best_performance'] = {
                'fastest': {'model': fastest['model'], 'time': fastest['response_time']},
                'cheapest': {'model': cheapest['model'], 'cost': cheapest['cost_estimate']['estimated_cost']},
                'highest_quality': {'model': highest_quality['model'], 'score': highest_quality['analysis_quality_score']}
            }
            
            # 成本分析
            avg_cost = sum(r['cost_estimate']['estimated_cost'] for r in successful_results) / len(successful_results)
            total_cost = sum(r['cost_estimate']['estimated_cost'] for r in successful_results)
            
            summary['cost_analysis'] = {
                'average_cost_per_query': round(avg_cost, 6),
                'total_test_cost': round(total_cost, 6),
                'cost_range': {
                    'min': round(min(r['cost_estimate']['estimated_cost'] for r in successful_results), 6),
                    'max': round(max(r['cost_estimate']['estimated_cost'] for r in successful_results), 6)
                }
            }
        
        # 生成建议
        if successful_results:
            summary['recommendations'].append(f"✅ 成功测试 {len(successful_results)} 个模型")
            summary['recommendations'].append(f"💰 最经济选择: {cheapest['model']} (${cheapest['cost_estimate']['estimated_cost']:.6f})")
            summary['recommendations'].append(f"⚡ 最快响应: {fastest['model']} ({fastest['response_time']:.2f}秒)")
            summary['recommendations'].append(f"🎯 最高质量: {highest_quality['model']} (质量分: {highest_quality['analysis_quality_score']:.1f})")
        
        return summary
    
    def print_results(self, results: dict):
        """打印测试结果"""
        print("\\n" + "="*80)
        print("📊 2025年最新模型测试结果")
        print("="*80)
        
        print(f"\\n🕐 测试时间: {results['test_time']}")
        print(f"📈 测试数据: {results['data_info']['symbol']} {results['data_info']['bars']}根K线")
        print(f"💡 预估tokens: {results['data_info']['estimated_tokens']}")
        
        # 按组显示结果
        for group_name, group_results in results['model_results'].items():
            print(f"\\n🎯 {group_name.upper()} 模型组:")
            print("-" * 50)
            
            for result in group_results:
                if result['success']:
                    print(f"  ✅ {result['model']:15} | "
                          f"{result['response_time']:6.2f}s | "
                          f"${result['cost_estimate']['estimated_cost']:8.6f} | "
                          f"质量: {result['analysis_quality_score']:5.1f}")
                else:
                    print(f"  ❌ {result['model']:15} | 失败: {result.get('error', 'Unknown')}")
        
        # 显示总结
        summary = results['summary']
        print(f"\\n📋 测试总结:")
        print("-" * 50)
        print(f"总测试模型: {summary['total_models_tested']}")
        print(f"成功: {summary['successful_models']}, 失败: {summary['failed_models']}")
        
        if summary['best_performance']:
            print(f"\\n🏆 最佳表现:")
            bp = summary['best_performance']
            print(f"  最快: {bp['fastest']['model']} ({bp['fastest']['time']:.2f}s)")
            print(f"  最便宜: {bp['cheapest']['model']} (${bp['cheapest']['cost']:.6f})")
            print(f"  最高质量: {bp['highest_quality']['model']} ({bp['highest_quality']['score']:.1f}分)")
        
        if summary['cost_analysis']:
            ca = summary['cost_analysis']
            print(f"\\n💰 成本分析:")
            print(f"  平均成本: ${ca['average_cost_per_query']:.6f}")
            print(f"  总测试费用: ${ca['total_test_cost']:.6f}")
            print(f"  成本范围: ${ca['cost_range']['min']:.6f} - ${ca['cost_range']['max']:.6f}")
        
        print("\\n💡 建议:")
        for rec in summary['recommendations']:
            print(f"  {rec}")

def main():
    """主测试函数"""
    print("="*80)
    print("🧪 2025年最新LLM模型量价分析能力测试")
    print("="*80)
    
    try:
        tester = Model2025Tester()
        results = tester.run_comprehensive_test()
        
        if results:
            tester.print_results(results)
            
            print("\\n🎉 测试完成！建议基于以上结果选择最适合的模型进行量价分析。")
        else:
            print("\\n❌ 测试失败，请检查配置和网络连接。")
            
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\\n❌ 测试执行失败: {e}")

if __name__ == "__main__":
    main()