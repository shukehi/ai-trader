#!/usr/bin/env python3
"""
阶段2: 数据格式优化测试
系统性比较4种数据格式在VPA分析质量上的效果
"""

import os
import sys
import asyncio
import time
import json
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import BinanceFetcher
from formatters import DataFormatter
from ai import OpenRouterClient
from config import Settings

class FormatOptimizationTest:
    """数据格式优化测试类"""
    
    def __init__(self):
        self.fetcher = BinanceFetcher()
        self.formatter = DataFormatter()
        self.client = OpenRouterClient()
        
        # 测试配置
        self.test_symbol = 'ETH/USDT'
        self.test_timeframe = '1h'
        self.test_limit = 50  # K线数量
        
        # 测试模型（选择具有代表性的模型）
        self.test_models = [
            'gpt5-mini',        # GPT-5 Mini (推理版)
            'gpt4o-mini',       # GPT-4o mini (经济版)
            'claude-haiku',     # Claude Haiku (轻量版)
            'gemini-flash',     # Gemini Flash (快速版)
        ]
        
        # 数据格式
        self.formats = ['csv', 'text', 'json', 'pattern']
        
    def run_format_comparison(self) -> Dict[str, Any]:
        """运行格式对比测试"""
        print("🧪 开始阶段2: 数据格式优化测试")
        print(f"📊 测试配置: {self.test_symbol} {self.test_timeframe} {self.test_limit}条K线")
        print(f"🤖 测试模型: {', '.join(self.test_models)}")
        print(f"📝 测试格式: {', '.join(self.formats)}")
        print("="*80)
        
        # 获取测试数据
        print("📊 获取市场数据...")
        df = self.fetcher.get_ohlcv(
            symbol=self.test_symbol,
            timeframe=self.test_timeframe,
            limit=self.test_limit
        )
        
        # 生成所有格式的数据
        format_data = self._generate_format_data(df)
        
        # 运行测试矩阵
        results = self._run_test_matrix(format_data)
        
        # 分析结果
        analysis = self._analyze_results(results)
        
        # 保存结果
        self._save_results(results, analysis)
        
        return {
            'raw_results': results,
            'analysis': analysis,
            'test_config': {
                'symbol': self.test_symbol,
                'timeframe': self.test_timeframe,
                'limit': self.test_limit,
                'models': self.test_models,
                'formats': self.formats
            }
        }
    
    def _generate_format_data(self, df: pd.DataFrame) -> Dict[str, str]:
        """生成所有格式的数据"""
        print("📝 生成4种格式数据...")
        
        format_data = {}
        token_estimates = self.formatter.estimate_tokens_by_format(df)
        
        # CSV格式 (最省token)
        format_data['csv'] = self.formatter.to_csv_format(df)
        print(f"  📊 CSV格式: {token_estimates['csv']} tokens")
        
        # 文本格式 (最易理解)
        format_data['text'] = self.formatter.to_text_narrative(df)
        print(f"  📖 Text格式: {token_estimates['text']} tokens")
        
        # JSON格式 (最详细)
        format_data['json'] = self.formatter.to_structured_json(df)
        print(f"  🗂️ JSON格式: {token_estimates['json']} tokens")
        
        # Pattern格式 (最专业)
        format_data['pattern'] = self.formatter.to_pattern_description(df)
        print(f"  🎯 Pattern格式: {token_estimates['pattern']} tokens")
        
        return format_data
    
    def _run_test_matrix(self, format_data: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """运行测试矩阵 - 每种格式 x 每个模型"""
        results = {}
        total_tests = len(self.formats) * len(self.test_models)
        current_test = 0
        
        for format_name in self.formats:
            results[format_name] = {}
            
            for model_name in self.test_models:
                current_test += 1
                print(f"🔄 测试 {current_test}/{total_tests}: {format_name} x {model_name}")
                
                try:
                    # 运行VPA分析
                    result = self.client.analyze_market_data(
                        data=format_data[format_name],
                        model_name=model_name,
                        analysis_type='vpa'
                    )
                    
                    if result.get('error'):
                        print(f"  ❌ 失败: {result['error']}")
                        results[format_name][model_name] = {
                            'error': result['error'],
                            'success': False
                        }
                    else:
                        # 计算质量评分
                        quality_score = self._calculate_quality_score(result['analysis'])
                        
                        results[format_name][model_name] = {
                            'success': True,
                            'analysis': result['analysis'],
                            'usage': result.get('usage', {}),
                            'response_time': result.get('response_time', 0),
                            'quality_score': quality_score,
                            'model_id': result.get('model_id')
                        }
                        
                        print(f"  ✅ 成功: 质量评分 {quality_score:.1f}/100, "
                              f"耗时 {result.get('response_time', 0):.1f}s, "
                              f"tokens {result.get('usage', {}).get('total_tokens', 0)}")
                    
                    # 防止频率限制
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  ❌ 异常: {e}")
                    results[format_name][model_name] = {
                        'error': str(e),
                        'success': False
                    }
        
        return results
    
    def _calculate_quality_score(self, analysis: str) -> float:
        """计算VPA分析质量评分"""
        score = 0.0
        analysis_lower = analysis.lower()
        
        # VPA专业术语检查 (30分)
        vpa_terms = [
            '量价', '成交量', 'volume', 'accumulation', 'distribution',
            'markup', 'markdown', '背离', '异常成交量', '主力', '资金流'
        ]
        term_score = sum(1 for term in vpa_terms if term in analysis_lower)
        score += min(term_score * 3, 30)
        
        # 市场阶段判断 (25分)
        stage_terms = ['accumulation', 'distribution', 'markup', 'markdown', '吸筹', '派发', '拉升', '下跌']
        if any(term in analysis_lower for term in stage_terms):
            score += 25
        
        # 具体数据引用 (20分)
        if any(indicator in analysis for indicator in ['价格', '成交量', 'ohlc', '开盘', '收盘', '最高', '最低']):
            score += 20
        
        # 交易信号和建议 (15分)
        signal_terms = ['建议', '买入', '卖出', '止损', '目标', '支撑', '阻力', '突破']
        if any(term in analysis_lower for term in signal_terms):
            score += 15
        
        # 风险评估 (10分)
        risk_terms = ['风险', '谨慎', '注意', '警告', 'risk', 'caution']
        if any(term in analysis_lower for term in risk_terms):
            score += 10
        
        return min(score, 100.0)
    
    def _analyze_results(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """分析测试结果"""
        print("\n📊 分析测试结果...")
        
        analysis = {
            'format_performance': {},
            'model_performance': {},
            'cost_effectiveness': {},
            'recommendations': []
        }
        
        # 按格式分析
        for format_name in self.formats:
            format_results = results.get(format_name, {})
            successful_results = [r for r in format_results.values() if r.get('success')]
            
            if successful_results:
                avg_quality = sum(r['quality_score'] for r in successful_results) / len(successful_results)
                avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
                avg_tokens = sum(r['usage'].get('total_tokens', 0) for r in successful_results) / len(successful_results)
                
                analysis['format_performance'][format_name] = {
                    'avg_quality_score': round(avg_quality, 2),
                    'avg_response_time': round(avg_time, 2),
                    'avg_tokens': round(avg_tokens, 0),
                    'success_rate': len(successful_results) / len(self.test_models)
                }
        
        # 按模型分析
        for model_name in self.test_models:
            model_results = []
            for format_name in self.formats:
                result = results.get(format_name, {}).get(model_name, {})
                if result.get('success'):
                    model_results.append(result)
            
            if model_results:
                avg_quality = sum(r['quality_score'] for r in model_results) / len(model_results)
                avg_time = sum(r['response_time'] for r in model_results) / len(model_results)
                
                analysis['model_performance'][model_name] = {
                    'avg_quality_score': round(avg_quality, 2),
                    'avg_response_time': round(avg_time, 2),
                    'success_rate': len(model_results) / len(self.formats)
                }
        
        # 生成推荐
        self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]):
        """生成优化推荐"""
        recommendations = []
        
        # 找出最佳格式
        format_perf = analysis['format_performance']
        if format_perf:
            best_quality_format = max(format_perf.keys(), key=lambda x: format_perf[x]['avg_quality_score'])
            best_speed_format = min(format_perf.keys(), key=lambda x: format_perf[x]['avg_response_time'])
            best_token_format = min(format_perf.keys(), key=lambda x: format_perf[x]['avg_tokens'])
            
            recommendations.append(f"🏆 最佳分析质量格式: {best_quality_format} ({format_perf[best_quality_format]['avg_quality_score']:.1f}/100)")
            recommendations.append(f"⚡ 最快响应格式: {best_speed_format} ({format_perf[best_speed_format]['avg_response_time']:.1f}s)")
            recommendations.append(f"💰 最省Token格式: {best_token_format} ({format_perf[best_token_format]['avg_tokens']:.0f} tokens)")
        
        # 找出最佳模型
        model_perf = analysis['model_performance']
        if model_perf:
            best_model = max(model_perf.keys(), key=lambda x: model_perf[x]['avg_quality_score'])
            recommendations.append(f"🤖 最佳分析模型: {best_model} ({model_perf[best_model]['avg_quality_score']:.1f}/100)")
        
        analysis['recommendations'] = recommendations
    
    def _save_results(self, results: Dict[str, Any], analysis: Dict[str, Any]):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果
        results_file = f"results/format_optimization_test_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'test_config': {
                    'symbol': self.test_symbol,
                    'timeframe': self.test_timeframe,
                    'limit': self.test_limit,
                    'models': self.test_models,
                    'formats': self.formats
                },
                'results': results,
                'analysis': analysis
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 结果已保存: {results_file}")
        
        # 打印关键结果
        self._print_summary(analysis)
    
    def _print_summary(self, analysis: Dict[str, Any]):
        """打印测试总结"""
        print("\n" + "="*80)
        print("📊 阶段2数据格式优化测试结果总结")
        print("="*80)
        
        # 格式性能对比
        print("\n🎯 各格式性能对比:")
        format_perf = analysis['format_performance']
        for format_name, perf in format_perf.items():
            print(f"  {format_name:>8}: 质量 {perf['avg_quality_score']:>5.1f}/100 | "
                  f"速度 {perf['avg_response_time']:>5.1f}s | "
                  f"Token {perf['avg_tokens']:>6.0f} | "
                  f"成功率 {perf['success_rate']*100:>5.1f}%")
        
        # 模型性能对比
        print("\n🤖 各模型性能对比:")
        model_perf = analysis['model_performance']
        for model_name, perf in model_perf.items():
            print(f"  {model_name:>15}: 质量 {perf['avg_quality_score']:>5.1f}/100 | "
                  f"速度 {perf['avg_response_time']:>5.1f}s | "
                  f"成功率 {perf['success_rate']*100:>5.1f}%")
        
        # 推荐
        print("\n💡 优化推荐:")
        for rec in analysis['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "="*80)

def main():
    """主函数"""
    try:
        # 验证配置
        Settings.validate()
        
        # 创建测试实例
        test = FormatOptimizationTest()
        
        # 运行测试
        results = test.run_format_comparison()
        
        print("✅ 阶段2数据格式优化测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())