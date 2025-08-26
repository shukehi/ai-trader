#!/usr/bin/env python3
"""
增强版原始K线数据分析测试脚本
支持多时间框架分析和批量模型测试
"""

import asyncio
import logging
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, List

from data.binance_fetcher import BinanceFetcher
from ai.openrouter_client import OpenRouterClient
from formatters.data_formatter import DataFormatter
from config import Settings

# 设置项目路径
sys.path.append('/opt/ai-trader')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedKLineAnalyzer:
    """增强版K线分析器"""
    
    def __init__(self):
        self.fetcher = BinanceFetcher()
        self.client = OpenRouterClient()
        self.formatter = DataFormatter()
        
        # 多时间框架配置
        self.timeframes = {
            '1d': {'weight': 0.4, 'data_points': 30, 'priority': 'high'},
            '4h': {'weight': 0.3, 'data_points': 50, 'priority': 'high'},
            '1h': {'weight': 0.2, 'data_points': 100, 'priority': 'medium'},
            '15m': {'weight': 0.1, 'data_points': 200, 'priority': 'low'}
        }
    
    async def multi_timeframe_analysis(self, symbol: str = 'ETH/USDT', 
                                     model: str = 'gemini-flash') -> Dict[str, Any]:
        """多时间框架分析"""
        print(f"🔍 开始多时间框架分析: {symbol}")
        
        timeframe_results = {}
        total_cost = 0
        
        for tf, config in self.timeframes.items():
            print(f"\n⏰ 分析时间框架: {tf} (权重: {config['weight']:.1%})")
            
            try:
                # 获取数据
                df = self.fetcher.get_ohlcv(symbol, tf, config['data_points'])
                current_price = df['close'].iloc[-1]
                price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
                
                print(f"   📊 获取{len(df)}条{tf}数据, 当前价格: ${current_price:.2f}")
                print(f"   📈 区间涨跌: {price_change:+.2f}%")
                
                # 格式化数据
                raw_data = self.formatter.to_csv_format(df.tail(min(30, len(df))))
                
                # 构建提示词
                prompt = self._build_timeframe_prompt(tf, raw_data, symbol)
                
                # AI分析
                start_time = time.time()
                result = self.client.generate_response(prompt, model)
                analysis_time = time.time() - start_time
                
                if result.get('success'):
                    # 成本计算
                    cost = self.client.estimate_cost(
                        model,
                        result['usage']['prompt_tokens'],
                        result['usage']['completion_tokens']
                    )['estimated_cost']
                    
                    total_cost += cost
                    
                    print(f"   ✅ 分析完成: {analysis_time:.1f}s, ${cost:.6f}")
                    
                    # 存储结果
                    timeframe_results[tf] = {
                        'analysis': result['analysis'],
                        'weight': config['weight'],
                        'priority': config['priority'],
                        'cost': cost,
                        'time': analysis_time,
                        'market_data': {
                            'current_price': current_price,
                            'price_change': price_change,
                            'data_points': len(df)
                        }
                    }
                    
                    # 显示简要分析
                    summary = result['analysis'][:150] + "..." if len(result['analysis']) > 150 else result['analysis']
                    print(f"   📝 {summary}")
                    
                else:
                    print(f"   ❌ 分析失败: {result.get('error')}")
                    timeframe_results[tf] = {
                        'error': result.get('error'),
                        'weight': config['weight']
                    }
                
                # 避免频率限制
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   ❌ {tf}分析异常: {e}")
                timeframe_results[tf] = {
                    'error': str(e),
                    'weight': config['weight']
                }
        
        # 生成综合分析
        consensus = self._calculate_timeframe_consensus(timeframe_results)
        
        return {
            'timeframe_results': timeframe_results,
            'consensus': consensus,
            'total_cost': total_cost,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }
    
    def _build_timeframe_prompt(self, timeframe: str, raw_data: str, symbol: str) -> str:
        """构建时间框架特定的分析提示词"""
        
        timeframe_context = {
            '1d': "日线级别分析，重点关注主要趋势和长期市场阶段",
            '4h': "4小时级别分析，关注中期趋势确认和重要技术位",
            '1h': "小时级别分析，关注短期趋势和入场时机",
            '15m': "15分钟级别分析，关注精确入场和微观结构"
        }
        
        return f"""你是专业的{timeframe_context.get(timeframe, '')}分析师。

请分析以下{symbol} {timeframe}时间框架的原始K线数据：

{raw_data}

请提供专业的VPA分析，包括：
1. 该时间框架下的趋势方向和强度
2. 关键支撑阻力位识别  
3. 成交量与价格关系分析
4. Anna Coulling VSA信号识别
5. 针对{timeframe}时间框架的交易建议

注意：
- 使用专业VPA/VSA术语
- 引用具体价格数据
- 提供该时间框架下的风险评估
- 考虑{timeframe}级别的操作特点"""

    def _calculate_timeframe_consensus(self, timeframe_results: Dict) -> Dict[str, Any]:
        """计算多时间框架共识"""
        
        if not timeframe_results:
            return {'error': 'No valid timeframe results'}
        
        # 提取成功的分析结果
        valid_results = {tf: result for tf, result in timeframe_results.items() 
                        if 'analysis' in result}
        
        if not valid_results:
            return {'error': 'No successful analyses'}
        
        consensus = {
            'trend_signals': {},
            'vpa_signals': {},
            'confidence_score': 0,
            'weighted_recommendation': '',
            'timeframe_alignment': 0
        }
        
        # 分析趋势一致性
        trend_votes = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        
        for tf, result in valid_results.items():
            analysis = result['analysis'].lower()
            weight = result['weight']
            
            # 趋势投票
            if any(word in analysis for word in ['bullish', 'uptrend', '看涨', '上升']):
                trend_votes['bullish'] += weight
            elif any(word in analysis for word in ['bearish', 'downtrend', '看跌', '下降']):
                trend_votes['bearish'] += weight
            else:
                trend_votes['neutral'] += weight
        
        # 确定主导趋势
        dominant_trend = max(trend_votes, key=trend_votes.get)
        trend_strength = trend_votes[dominant_trend]
        
        consensus['trend_signals'] = {
            'dominant_trend': dominant_trend,
            'strength': trend_strength,
            'votes': trend_votes
        }
        
        # 计算时间框架对齐度
        alignment_score = trend_strength  # 主导趋势的权重总和
        consensus['timeframe_alignment'] = round(alignment_score * 100, 1)
        
        # 置信度评分
        if alignment_score >= 0.7:
            consensus['confidence_score'] = 90
        elif alignment_score >= 0.5:
            consensus['confidence_score'] = 75
        else:
            consensus['confidence_score'] = 60
        
        # 生成综合建议
        if dominant_trend == 'bullish' and alignment_score >= 0.6:
            consensus['weighted_recommendation'] = f"多时间框架看涨确认，建议逢低做多 (置信度: {alignment_score:.1%})"
        elif dominant_trend == 'bearish' and alignment_score >= 0.6:
            consensus['weighted_recommendation'] = f"多时间框架看跌确认，建议逢高做空 (置信度: {alignment_score:.1%})"
        else:
            consensus['weighted_recommendation'] = f"时间框架信号分歧，建议观望等待明确信号"
        
        return consensus

    async def batch_model_test(self, symbol: str = 'ETH/USDT', 
                              models: List[str] = None) -> Dict[str, Any]:
        """批量模型测试"""
        
        if models is None:
            models = ['gemini-flash', 'gpt4o-mini', 'claude-haiku', 'gpt5-mini']
        
        print(f"🚀 开始批量模型测试: {len(models)}个模型")
        
        # 获取测试数据
        df = self.fetcher.get_ohlcv(symbol, '1h', 50)
        raw_data = self.formatter.to_csv_format(df.tail(30))
        
        test_prompt = f"""请分析以下{symbol}原始K线数据，提供专业VPA分析：

{raw_data}

要求：
1. 识别当前趋势和市场阶段
2. 标识关键支撑阻力位  
3. 分析成交量价格关系
4. 提供具体交易建议和风险控制"""

        model_results = {}
        total_cost = 0
        
        for model in models:
            print(f"\n🔬 测试模型: {model}")
            
            try:
                start_time = time.time()
                result = self.client.generate_response(test_prompt, model)
                analysis_time = time.time() - start_time
                
                if result.get('success'):
                    cost = self.client.estimate_cost(
                        model,
                        result['usage']['prompt_tokens'],
                        result['usage']['completion_tokens']
                    )['estimated_cost']
                    
                    total_cost += cost
                    
                    print(f"   ✅ 成功: {analysis_time:.1f}s, ${cost:.6f}")
                    
                    model_results[model] = {
                        'analysis': result['analysis'],
                        'cost': cost,
                        'time': analysis_time,
                        'tokens': result['usage']['total_tokens'],
                        'success': True
                    }
                    
                    # 显示分析摘要
                    summary = result['analysis'][:120] + "..." if len(result['analysis']) > 120 else result['analysis']
                    print(f"   📝 {summary}")
                    
                else:
                    print(f"   ❌ 失败: {result.get('error')}")
                    model_results[model] = {
                        'error': result.get('error'),
                        'success': False
                    }
                
                # 避免频率限制
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   ❌ 异常: {e}")
                model_results[model] = {
                    'error': str(e),
                    'success': False
                }
        
        # 生成对比报告
        comparison = self._generate_model_comparison(model_results, total_cost)
        
        return {
            'model_results': model_results,
            'comparison': comparison,
            'total_cost': total_cost,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_model_comparison(self, model_results: Dict, total_cost: float) -> Dict[str, Any]:
        """生成模型对比报告"""
        
        successful_models = {model: result for model, result in model_results.items() 
                           if result.get('success', False)}
        
        if not successful_models:
            return {'error': 'No successful model tests'}
        
        comparison = {
            'performance_ranking': [],
            'cost_ranking': [],
            'speed_ranking': [],
            'summary': {}
        }
        
        # 性能排名 (按响应时间)
        speed_sorted = sorted(successful_models.items(), key=lambda x: x[1]['time'])
        comparison['speed_ranking'] = [(model, f"{result['time']:.1f}s") 
                                     for model, result in speed_sorted]
        
        # 成本排名
        cost_sorted = sorted(successful_models.items(), key=lambda x: x[1]['cost'])
        comparison['cost_ranking'] = [(model, f"${result['cost']:.6f}") 
                                    for model, result in cost_sorted]
        
        # 质量评估 (按分析长度和专业术语)
        quality_scores = {}
        for model, result in successful_models.items():
            analysis = result['analysis'].lower()
            
            # 基础质量评分
            quality_score = 0
            
            # 长度评分 (合理长度)
            length = len(result['analysis'])
            if 500 <= length <= 2000:
                quality_score += 30
            elif length > 300:
                quality_score += 20
            
            # VPA术语评分
            vpa_terms = ['vsa', 'volume', 'support', 'resistance', 'trend', 'bullish', 'bearish']
            vpa_count = sum(1 for term in vpa_terms if term in analysis)
            quality_score += min(vpa_count * 10, 40)
            
            # 数值引用评分
            import re
            price_mentions = len(re.findall(r'\d+[\.,]?\d*', result['analysis']))
            quality_score += min(price_mentions * 2, 30)
            
            quality_scores[model] = quality_score
        
        quality_sorted = sorted(quality_scores.items(), key=lambda x: x[1], reverse=True)
        comparison['performance_ranking'] = [(model, f"{score}/100") 
                                          for model, score in quality_sorted]
        
        # 综合评分
        comparison['summary'] = {
            'total_models_tested': len(model_results),
            'successful_tests': len(successful_models),
            'success_rate': len(successful_models) / len(model_results) * 100,
            'total_cost': total_cost,
            'fastest_model': speed_sorted[0][0] if speed_sorted else None,
            'cheapest_model': cost_sorted[0][0] if cost_sorted else None,
            'highest_quality': quality_sorted[0][0] if quality_sorted else None
        }
        
        return comparison


async def main():
    """主函数"""
    print("🚀 增强版原始K线数据分析测试")
    print("支持多时间框架分析和批量模型测试")
    print("="*60)
    
    try:
        # 验证API配置
        Settings.validate()
        print("✅ API配置验证通过")
        
        # 初始化分析器
        analyzer = EnhancedKLineAnalyzer()
        
        # 选择测试模式
        print("\n请选择测试模式:")
        print("1. 多时间框架分析")
        print("2. 批量模型测试")
        print("3. 完整测试 (两种模式)")
        
        # 默认执行完整测试
        choice = "3"
        
        results = {}
        
        if choice in ["1", "3"]:
            print("\n" + "="*40)
            print("📊 执行多时间框架分析")
            print("="*40)
            
            mtf_result = await analyzer.multi_timeframe_analysis('ETH/USDT', 'gemini-flash')
            results['multi_timeframe'] = mtf_result
            
            # 显示共识结果
            consensus = mtf_result.get('consensus', {})
            if 'error' not in consensus:
                print(f"\n🎯 多时间框架共识结果:")
                print(f"   主导趋势: {consensus['trend_signals']['dominant_trend']}")
                print(f"   时间框架对齐度: {consensus['timeframe_alignment']}%")
                print(f"   置信度: {consensus['confidence_score']}/100")
                print(f"   综合建议: {consensus['weighted_recommendation']}")
        
        if choice in ["2", "3"]:
            print("\n" + "="*40)
            print("🔬 执行批量模型测试")
            print("="*40)
            
            batch_result = await analyzer.batch_model_test('ETH/USDT')
            results['batch_models'] = batch_result
            
            # 显示对比结果
            comparison = batch_result.get('comparison', {})
            if 'error' not in comparison:
                summary = comparison['summary']
                print(f"\n📈 批量测试结果汇总:")
                print(f"   成功率: {summary['success_rate']:.1f}%")
                print(f"   总成本: ${summary['total_cost']:.6f}")
                print(f"   最快模型: {summary['fastest_model']}")
                print(f"   最省钱模型: {summary['cheapest_model']}")
                print(f"   最高质量: {summary['highest_quality']}")
        
        # 保存详细报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/opt/ai-trader/results/enhanced_analysis_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细报告已保存: {report_file}")
        print("="*60)
        print("🎉 增强版测试完成！")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback  # pylint: disable=import-outside-toplevel
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        logger.error("❌ 程序异常: %s", e)
        import traceback  # pylint: disable=import-outside-toplevel
        traceback.print_exc()