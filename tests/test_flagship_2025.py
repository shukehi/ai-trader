#!/usr/bin/env python3
"""
2025年旗舰模型专项测试
专门测试GPT-5、Claude Opus 4.1、Gemini 2.5 Pro、Grok-4的量价分析能力
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
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FlagshipModelTester:
    """2025年旗舰模型测试器"""
    
    def __init__(self):
        try:
            Settings.validate()
            self.fetcher = BinanceFetcher()
            self.formatter = DataFormatter()
            self.client = OpenRouterClient()
            
            # 2025旗舰模型列表
            self.flagship_models = {
                'gpt5': {
                    'name': 'GPT-5',
                    'provider': 'OpenAI',
                    'speciality': '通用推理和分析',
                    'context': '1M tokens'
                },
                'claude-opus-41': {
                    'name': 'Claude Opus 4.1',
                    'provider': 'Anthropic',
                    'speciality': '深度分析和推理',
                    'context': '500K tokens'
                },
                'gemini-25-pro': {
                    'name': 'Gemini 2.5 Pro',
                    'provider': 'Google',
                    'speciality': '多模态和长上下文',
                    'context': '10M tokens'
                },
                'grok4': {
                    'name': 'Grok-4',
                    'provider': 'xAI',
                    'speciality': '实时信息和创新思考',
                    'context': '1M tokens'
                }
            }
            
            logger.info("🚀 2025旗舰模型测试器初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise
    
    def test_vpa_analysis_depth(self, model_name: str, data: str) -> dict:
        """测试VPA分析深度和专业性"""
        logger.info(f"🧪 测试 {model_name} 的VPA分析深度...")
        
        # 专门的VPA深度分析提示
        vpa_expert_prompt = """
你是一位世界级的VPA(Volume Price Analysis)专家，深谙Anna Coulling的理论体系。
请对提供的ETH永续合约数据进行最专业深入的VPA分析：

核心分析要求：
1. 【市场阶段判断】- 当前处于Accumulation, Distribution, Markup还是Markdown阶段？
2. 【量价关系验证】- 每个重要价格变化是否得到成交量确认？识别量价背离
3. 【专业资金行为】- 分析大资金的进出痕迹，识别Smart Money vs Dumb Money
4. 【关键VPA信号】- 识别Stopping Volume, Testing Volume, Climax Volume等
5. 【永续合约特色】- 结合资金费率变化分析市场情绪和持仓结构

分析框架：
- 使用Wyckoff理论的Supply/Demand分析
- 识别Cause and Effect原理在价格行为中的体现
- 判断当前是否存在No Demand或No Supply的迹象
- 分析Volume Spread Analysis (VSA) 的核心原理

请提供：
1. 市场当前阶段的明确判断（含置信度）
2. 最关键的3个VPA信号及其交易含义
3. 基于VPA的具体操作建议（进场位、止损位、目标位）
4. 风险评估和仓位管理建议

要求专业术语准确，逻辑清晰，可操作性强。
        """.strip()
        
        try:
            start_time = time.time()
            
            response = self.client.client.chat.completions.create(
                model=Settings.MODELS[model_name],
                messages=[
                    {"role": "system", "content": vpa_expert_prompt},
                    {"role": "user", "content": data}
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            
            end_time = time.time()
            
            analysis = response.choices[0].message.content
            usage = response.usage
            
            # 分析质量评分
            quality_score = self._evaluate_vpa_analysis_quality(analysis)
            
            return {
                'model': model_name,
                'success': True,
                'analysis': analysis,
                'response_time': end_time - start_time,
                'token_usage': {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                },
                'quality_metrics': quality_score,
                'cost_estimate': self.client.estimate_cost(
                    model_name, usage.prompt_tokens, usage.completion_tokens
                )
            }
            
        except Exception as e:
            logger.error(f"❌ {model_name} VPA测试失败: {e}")
            return {
                'model': model_name,
                'success': False,
                'error': str(e),
                'response_time': time.time() - start_time
            }
    
    def _evaluate_vpa_analysis_quality(self, analysis: str) -> dict:
        """评估VPA分析质量"""
        scores = {
            'vpa_terminology': 0,      # VPA专业术语使用
            'market_stage_clarity': 0,  # 市场阶段判断清晰度
            'actionable_advice': 0,     # 可操作的建议
            'risk_management': 0,       # 风险管理要素
            'professional_depth': 0,    # 专业深度
            'total_score': 0
        }
        
        if not analysis:
            return scores
        
        analysis_lower = analysis.lower()
        
        # VPA专业术语 (30分)
        vpa_terms = [
            'accumulation', 'distribution', 'markup', 'markdown',
            'stopping volume', 'testing volume', 'climax',
            'supply', 'demand', 'wyckoff', 'smart money',
            'volume spread', 'no demand', 'no supply'
        ]
        found_vpa = sum(1 for term in vpa_terms if term in analysis_lower)
        scores['vpa_terminology'] = min(found_vpa / len(vpa_terms) * 30, 30)
        
        # 市场阶段判断 (25分)
        stage_indicators = ['阶段', '当前', '判断', '置信度', 'phase']
        found_stage = sum(1 for term in stage_indicators if term in analysis_lower)
        scores['market_stage_clarity'] = min(found_stage / len(stage_indicators) * 25, 25)
        
        # 可操作建议 (25分)
        action_terms = ['建议', '进场', '止损', '目标', '操作', '买入', '卖出']
        found_action = sum(1 for term in action_terms if term in analysis)
        scores['actionable_advice'] = min(found_action / len(action_terms) * 25, 25)
        
        # 风险管理 (10分)
        risk_terms = ['风险', '仓位', '管理', 'risk', '止损']
        found_risk = sum(1 for term in risk_terms if term in analysis)
        scores['risk_management'] = min(found_risk / len(risk_terms) * 10, 10)
        
        # 专业深度 (10分) - 基于分析长度和结构
        if len(analysis) > 1000:
            scores['professional_depth'] += 5
        if '1.' in analysis or '2.' in analysis:  # 结构化分析
            scores['professional_depth'] += 5
        
        scores['total_score'] = sum(scores.values()) - scores['total_score']  # 排除total_score自身
        
        return scores
    
    def run_flagship_comparison(self, limit: int = 30):
        """运行2025旗舰模型对比测试"""
        logger.info("🚀 开始2025旗舰模型VPA分析对比测试...")
        
        # 获取测试数据
        logger.info("📊 获取ETH永续合约数据...")
        df = self.fetcher.get_ohlcv(symbol='ETH/USDT', limit=limit)
        
        if df is None:
            logger.error("❌ 无法获取测试数据")
            return None
        
        # 添加技术指标以提供更丰富的分析数据
        df_with_indicators = DataProcessor.add_basic_indicators(df)
        df_with_vpa = DataProcessor.analyze_volume_price_relationship(df_with_indicators)
        
        # 格式化为VPA专用数据格式
        test_data = self._prepare_vpa_test_data(df_with_vpa)
        
        logger.info(f"📝 VPA测试数据准备完成，数据量: {len(df)}根K线")
        
        results = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'symbol': 'ETH/USDT',
                'timeframe': '1h',
                'data_points': len(df),
                'test_type': 'VPA Professional Analysis'
            },
            'flagship_results': {},
            'comparison': {}
        }
        
        # 测试每个旗舰模型
        for model_key, model_info in self.flagship_models.items():
            if model_key in Settings.MODELS:
                logger.info(f"\\n🎯 测试 {model_info['name']} ({model_info['provider']})...")
                
                result = self.test_vpa_analysis_depth(model_key, test_data)
                results['flagship_results'][model_key] = {
                    'model_info': model_info,
                    'test_result': result
                }
                
                # 防止API频率限制
                time.sleep(3)
            else:
                logger.warning(f"⚠️ 模型 {model_key} 未在配置中找到")
        
        # 生成对比分析
        results['comparison'] = self._generate_flagship_comparison(results['flagship_results'])
        
        return results
    
    def _prepare_vpa_test_data(self, df) -> str:
        """准备VPA专用测试数据格式"""
        lines = [f"# ETH/USDT 永续合约 VPA 专业分析数据\\n"]
        
        # 数据概览
        lines.append("## 市场概况")
        lines.append(f"时间范围: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")
        lines.append(f"价格变化: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f} ({((df['close'].iloc[-1]/df['close'].iloc[0]-1)*100):+.2f}%)")
        lines.append(f"成交量总计: {df['volume'].sum():,.0f}")
        lines.append("")
        
        # 详细K线数据含技术指标
        lines.append("## K线数据 (含VPA关键指标)")
        header = "时间,开盘,最高,最低,收盘,成交量,量比,RSI,MACD,布林上轨,VPA信号"
        lines.append(header)
        
        for _, row in df.tail(20).iterrows():  # 最近20根K线
            vpa_signals = []
            if row.get('bullish_volume', False):
                vpa_signals.append('健康上涨')
            if row.get('bearish_volume', False):
                vpa_signals.append('健康下跌')
            if row.get('suspicious_rally', False):
                vpa_signals.append('可疑上涨')
            if row.get('high_volume_no_progress', False):
                vpa_signals.append('高量无进展')
            
            vpa_signal_str = ','.join(vpa_signals) if vpa_signals else '正常'
            
            line = (f"{row['datetime']},{row['open']:.2f},{row['high']:.2f},"
                   f"{row['low']:.2f},{row['close']:.2f},{row['volume']:.0f},"
                   f"{row.get('volume_ratio', 1.0):.2f},"
                   f"{row.get('rsi', 0):.1f},{row.get('macd', 0):.4f},"
                   f"{row.get('bb_upper', row['close']):.2f},{vpa_signal_str}")
            lines.append(line)
        
        return "\\n".join(lines)
    
    def _generate_flagship_comparison(self, results: dict) -> dict:
        """生成旗舰模型对比分析"""
        comparison = {
            'performance_ranking': {},
            'cost_analysis': {},
            'quality_analysis': {},
            'recommendations': {}
        }
        
        successful_results = {k: v for k, v in results.items() 
                            if v['test_result'].get('success', False)}
        
        if not successful_results:
            return comparison
        
        # 性能排名
        by_speed = sorted(successful_results.items(), 
                         key=lambda x: x[1]['test_result']['response_time'])
        by_cost = sorted(successful_results.items(), 
                        key=lambda x: x[1]['test_result']['cost_estimate']['estimated_cost'])
        by_quality = sorted(successful_results.items(), 
                          key=lambda x: x[1]['test_result']['quality_metrics']['total_score'], 
                          reverse=True)
        
        comparison['performance_ranking'] = {
            'fastest': {
                'model': by_speed[0][0],
                'name': by_speed[0][1]['model_info']['name'],
                'time': by_speed[0][1]['test_result']['response_time']
            },
            'most_economical': {
                'model': by_cost[0][0], 
                'name': by_cost[0][1]['model_info']['name'],
                'cost': by_cost[0][1]['test_result']['cost_estimate']['estimated_cost']
            },
            'highest_quality': {
                'model': by_quality[0][0],
                'name': by_quality[0][1]['model_info']['name'], 
                'score': by_quality[0][1]['test_result']['quality_metrics']['total_score']
            }
        }
        
        # 成本分析
        total_cost = sum(r['test_result']['cost_estimate']['estimated_cost'] 
                        for r in successful_results.values())
        avg_cost = total_cost / len(successful_results)
        
        comparison['cost_analysis'] = {
            'total_test_cost': round(total_cost, 6),
            'average_cost': round(avg_cost, 6),
            'cost_range': {
                'min': by_cost[0][1]['test_result']['cost_estimate']['estimated_cost'],
                'max': by_cost[-1][1]['test_result']['cost_estimate']['estimated_cost']
            }
        }
        
        return comparison
    
    def print_flagship_results(self, results: dict):
        """打印旗舰模型测试结果"""
        print("\\n" + "="*100)
        print("🔥 2025年旗舰模型VPA分析能力对比测试结果")
        print("="*100)
        
        test_info = results['test_info']
        print(f"\\n📊 测试信息:")
        print(f"  时间: {test_info['timestamp']}")
        print(f"  标的: {test_info['symbol']}")
        print(f"  数据: {test_info['data_points']}根K线")
        print(f"  类型: {test_info['test_type']}")
        
        # 各模型详细结果
        print(f"\\n🎯 模型测试结果:")
        print("-" * 100)
        
        for model_key, result_data in results['flagship_results'].items():
            model_info = result_data['model_info']
            test_result = result_data['test_result']
            
            print(f"\\n🤖 {model_info['name']} ({model_info['provider']})")
            print(f"   特长: {model_info['speciality']}")
            print(f"   上下文: {model_info['context']}")
            
            if test_result.get('success'):
                quality = test_result['quality_metrics']
                cost = test_result['cost_estimate']
                
                print(f"   ✅ 状态: 成功")
                print(f"   ⏱️  响应时间: {test_result['response_time']:.2f}秒")
                print(f"   💰 成本: ${cost['estimated_cost']:.6f}")
                print(f"   📊 质量评分: {quality['total_score']:.1f}/100")
                print(f"   🎯 VPA专业度: {quality['vpa_terminology']:.1f}/30")
                print(f"   📈 阶段判断: {quality['market_stage_clarity']:.1f}/25")
                print(f"   💡 可操作性: {quality['actionable_advice']:.1f}/25")
                
                # 显示分析预览
                analysis_preview = test_result['analysis'][:300] + "..."
                print(f"   📝 分析预览: {analysis_preview}")
                
            else:
                print(f"   ❌ 状态: 失败 - {test_result.get('error', 'Unknown error')}")
        
        # 对比总结
        if results['comparison']:
            comp = results['comparison']
            print(f"\\n🏆 综合对比:")
            print("-" * 50)
            
            if 'performance_ranking' in comp:
                pr = comp['performance_ranking']
                print(f"🚀 最快响应: {pr['fastest']['name']} ({pr['fastest']['time']:.2f}秒)")
                print(f"💰 最经济: {pr['most_economical']['name']} (${pr['most_economical']['cost']:.6f})")
                print(f"🎯 最高质量: {pr['highest_quality']['name']} ({pr['highest_quality']['score']:.1f}分)")
            
            if 'cost_analysis' in comp:
                ca = comp['cost_analysis']
                print(f"\\n💸 成本分析:")
                print(f"  总测试费用: ${ca['total_test_cost']:.6f}")
                print(f"  平均费用: ${ca['average_cost']:.6f}")
                print(f"  费用区间: ${ca['cost_range']['min']:.6f} - ${ca['cost_range']['max']:.6f}")

def main():
    """主测试函数"""
    print("="*100)
    print("🔥 2025年AI旗舰模型量价分析专业能力测试")
    print("🎯 测试模型: GPT-5 | Claude Opus 4.1 | Gemini 2.5 Pro | Grok-4")
    print("="*100)
    
    try:
        tester = FlagshipModelTester()
        results = tester.run_flagship_comparison(limit=30)
        
        if results:
            tester.print_flagship_results(results)
            
            # 保存详细结果到文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flagship_test_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\\n💾 详细测试结果已保存到: {filename}")
            print("\\n🎉 2025旗舰模型测试完成！")
            
        else:
            print("\\n❌ 测试失败，请检查配置和网络连接。")
            
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\\n❌ 测试执行失败: {e}")

if __name__ == "__main__":
    main()