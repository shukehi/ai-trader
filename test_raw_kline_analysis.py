#!/usr/bin/env python3
"""
原始K线数据分析测试脚本
测试AI模型（包括Claude Opus 4.1）直接分析原始OHLCV数据的能力
评估分析结果的正确性和专业性
"""

import asyncio
import logging
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any
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



class KLineAnalysisEvaluator:
    """K线分析结果评估器"""
    
    def __init__(self):
        self.evaluation_criteria = {
            # 技术分析正确性 (40%)
            'technical_accuracy': {
                'weight': 0.40,
                'indicators': [
                    'trend_identification',      # 趋势识别
                    'support_resistance',        # 支撑阻力
                    'volume_analysis',           # 成交量分析
                    'price_action'               # 价格行动
                ]
            },
            # VPA专业性 (30%)
            'vpa_professionalism': {
                'weight': 0.30,
                'indicators': [
                    'anna_coulling_terminology', # Anna Coulling术语
                    'vsa_signals',              # VSA信号识别
                    'market_phases',            # 市场阶段分析
                    'smart_money_detection'     # 聪明钱识别
                ]
            },
            # 数据理解能力 (20%)
            'data_comprehension': {
                'weight': 0.20,
                'indicators': [
                    'ohlcv_interpretation',     # OHLCV数据解释
                    'pattern_recognition',      # 模式识别
                    'numerical_accuracy',       # 数值准确性
                    'timeframe_awareness'       # 时间框架意识
                ]
            },
            # 交易实用性 (10%)
            'trading_practicality': {
                'weight': 0.10,
                'indicators': [
                    'actionable_signals',       # 可操作信号
                    'risk_assessment',          # 风险评估
                    'entry_exit_points',        # 进出场点位
                    'position_sizing'           # 仓位建议
                ]
            }
        }
    
    def evaluate_analysis(self, analysis_text: str, market_data: Dict) -> Dict[str, Any]:
        """评估分析结果"""
        analysis_lower = analysis_text.lower()
        evaluation_result = {
            'total_score': 0,
            'category_scores': {},
            'detailed_feedback': {},
            'strengths': [],
            'weaknesses': []
        }
        
        total_weighted_score = 0
        
        for category, config in self.evaluation_criteria.items():
            category_score = self._evaluate_category(analysis_text, analysis_lower, category, config, market_data)
            evaluation_result['category_scores'][category] = category_score
            total_weighted_score += category_score * config['weight']
        
        evaluation_result['total_score'] = round(total_weighted_score, 2)
        evaluation_result['grade'] = self._get_grade(evaluation_result['total_score'])
        
        return evaluation_result
    
    def _evaluate_category(self, analysis_text: str, analysis_lower: str,
                          category: str, config: Dict, market_data: Dict) -> float:
        """评估单个类别"""
        score = 0
        max_score = len(config['indicators']) * 25  # 每个指标最高25分
        
        if category == 'technical_accuracy':
            score = self._evaluate_technical_accuracy(analysis_lower, market_data)
        elif category == 'vpa_professionalism':
            score = self._evaluate_vpa_professionalism(analysis_lower)
        elif category == 'data_comprehension':
            score = self._evaluate_data_comprehension(analysis_text, market_data)
        elif category == 'trading_practicality':
            score = self._evaluate_trading_practicality(analysis_lower)
        
        return min(score, max_score)  # 确保不超过最大分数
    
    def _evaluate_technical_accuracy(self, analysis_lower: str, market_data: Dict) -> float:
        """评估技术分析准确性"""
        score = 0
        
        # 趋势识别 (25分)
        trend_keywords = ['uptrend', 'downtrend', 'sideways', 'bullish', 'bearish', 
                         '上升趋势', '下降趋势', '横盘', '看涨', '看跌']
        if any(keyword in analysis_lower for keyword in trend_keywords):
            score += 25
        
        # 支撑阻力 (25分)
        sr_keywords = ['support', 'resistance', 'key level', 'breakout', 'breakdown',
                      '支撑', '阻力', '关键位', '突破', '跌破']
        if any(keyword in analysis_lower for keyword in sr_keywords):
            score += 25
        
        # 成交量分析 (25分)
        volume_keywords = ['volume', 'high volume', 'low volume', 'volume spike',
                          '成交量', '放量', '缩量', '量价']
        if any(keyword in analysis_lower for keyword in volume_keywords):
            score += 25
        
        # 价格行动 (25分)
        price_action_keywords = ['price action', 'candlestick', 'doji', 'hammer', 'engulfing',
                                '价格行动', 'K线', '十字星', '锤子线', '包络']
        if any(keyword in analysis_lower for keyword in price_action_keywords):
            score += 25
        
        return score
    
    def _evaluate_vpa_professionalism(self, analysis_lower: str) -> float:
        """评估VPA专业性"""
        score = 0
        
        # Anna Coulling术语 (25分) - 扩展专业词汇
        anna_coulling_terms = [
            'no demand', 'no supply', 'climax volume', 'wide spread',
            'narrow spread', 'professional money', 'smart money', 'wyckoff',
            'vsa', 'composite operator', 'composite man', 'market maker',
            'weakness on strength', 'strength on weakness', 'effort vs result',
            'stopping volume', 'pseudo upthrust', 'bag holding',
            'selling climax', 'buying climax', 'churning', 'distribution day',
            '无需求', '无供应', '高潮成交量', '宽幅', '窄幅',
            '专业资金', '聪明钱', '复合操作者', '做市商', '强势中的弱点',
            '弱势中的强势', '努力与结果', '止跌成交量', '伪假突破'
        ]
        if any(term in analysis_lower for term in anna_coulling_terms):
            score += 25
        
        # VSA信号识别 (25分) - 扩展VSA信号词汇
        vsa_signals = [
            'upthrust', 'spring', 'test', 'absorption', 'stopping volume',
            'shakeout', 'markdown', 'markup', 'last point of supply',
            'sign of strength', 'sign of weakness', 'end of rising market',
            'selling pressure', 'buying pressure', 'professional interest',
            'retail sentiment', 'volume dry up', 'no demand bar',
            '假突破', '弹簧', '测试', '吸收', '止跌成交量',
            '震仓', '标记下跌', '标记上涨', '最后供应点',
            '强势信号', '弱势信号', '上升市场结束', '专业兴趣'
        ]
        if any(signal in analysis_lower for signal in vsa_signals):
            score += 25
        
        # 市场阶段分析 (25分)
        market_phases = [
            'accumulation', 'markup', 'distribution', 'markdown',
            '积累', '拉升', '分配', '下跌'
        ]
        if any(phase in analysis_lower for phase in market_phases):
            score += 25
        
        # 聪明钱识别 (25分)
        smart_money_keywords = [
            'institutional', 'whale', 'composite man', 'market maker',
            '机构', '大户', '复合人', '做市商'
        ]
        if any(keyword in analysis_lower for keyword in smart_money_keywords):
            score += 25
        
        return score
    
    def _evaluate_data_comprehension(self, analysis_text: str, market_data: Dict) -> float:
        """评估数据理解能力"""
        score = 0
        
        # OHLCV数据解释 (25分)
        ohlcv_keywords = [
            'open', 'high', 'low', 'close', 'volume', 'ohlc',
            '开盘', '最高', '最低', '收盘', '成交量', '四价'
        ]
        analysis_lower = analysis_text.lower()
        if any(keyword in analysis_lower for keyword in ohlcv_keywords):
            score += 25
        
        # 模式识别 (25分)
        pattern_keywords = [
            'pattern', 'formation', 'triangle', 'flag', 'pennant',
            'head and shoulders', '形态', '三角形', '旗形',
            '楔形', '头肩'
        ]
        if any(keyword in analysis_lower for keyword in pattern_keywords):
            score += 25
        
        # 数值准确性 (25分)
        # 检查是否提到具体价格或数值
        import re  # pylint: disable=import-outside-toplevel
        price_mentions = re.findall(r'\$?\d+[\.,]?\d*', analysis_text)
        if price_mentions:
            score += 25
        
        # 时间框架意识 (25分)
        timeframe_keywords = [
            'hourly', 'daily', '1h', '4h', '1d', 'timeframe',
            '小时', '日线', '时间框架', '周期'
        ]
        if any(keyword in analysis_lower for keyword in timeframe_keywords):
            score += 25
        
        return score
    
    def _evaluate_trading_practicality(self, analysis_lower: str) -> float:
        """评估交易实用性 - 增强版"""
        score = 0
        
        # 可操作信号 (25分) - 增强信号识别
        signal_keywords = [
            'buy', 'sell', 'long', 'short', 'entry', 'exit',
            'bullish signal', 'bearish signal', 'trade setup',
            'go long', 'go short', 'enter position', 'close position',
            '买入', '卖出', '做多', '做空', '进场', '出场',
            '看涨信号', '看跌信号', '交易设置', '建仓', '平仓'
        ]
        signal_count = sum(1 for keyword in signal_keywords 
                          if keyword in analysis_lower)
        if signal_count >= 2:  # 需要至少2个相关词汇
            score += 25
        elif signal_count >= 1:
            score += 15
        
        # 风险评估 (25分) - 增强风险管理评估
        risk_keywords = [
            'risk', 'stop loss', 'risk reward', 'position size',
            'risk management', 'drawdown', 'max loss', 'money management',
            'leverage', 'margin', 'conservative', 'aggressive',
            '风险', '止损', '风险回报', '仓位', '风险管理',
            '回撤', '最大损失', '资金管理', '杠杆', '保证金'
        ]
        risk_count = sum(1 for keyword in risk_keywords 
                        if keyword in analysis_lower)
        if risk_count >= 3:  # 需要至少3个风险相关词汇
            score += 25
        elif risk_count >= 2:
            score += 15
        elif risk_count >= 1:
            score += 10
        
        # 具体价位和点位 (25分) - 增强具体性要求
        import re  # pylint: disable=import-outside-toplevel
        
        # 检查具体价格提及
        price_patterns = [
            r'\$\d+[\.,]?\d*',  # $4600.50格式
            r'\d+[\.,]\d+',     # 4600.50格式  
            r'at \d+',          # at 4600格式
            r'above \d+',       # above 4600格式
            r'below \d+',       # below 4600格式
            r'target.*\d+',     # target 4700格式
            r'stop.*\d+',       # stop 4500格式
        ]
        
        price_mentions = 0
        for pattern in price_patterns:
            if re.search(pattern, analysis_lower):
                price_mentions += 1
        
        if price_mentions >= 3:  # 需要至少3个具体价格提及
            score += 25
        elif price_mentions >= 2:
            score += 15
        elif price_mentions >= 1:
            score += 10
        
        # 交易计划完整性 (25分) - 新增评估维度
        plan_keywords = [
            'plan', 'strategy', 'approach', 'method',
            'timeframe', 'holding period', 'profit target', 'exit strategy',
            'portfolio', 'allocation', 'diversification',
            '计划', '策略', '方法', '时间框架', '持有期',
            '盈利目标', '退出策略', '投资组合', '配置'
        ]
        plan_count = sum(1 for keyword in plan_keywords 
                        if keyword in analysis_lower)
        if plan_count >= 2:  # 需要至少2个计划相关词汇
            score += 25
        elif plan_count >= 1:
            score += 15
        
        return min(score, 100)  # 确保不超过100分
    
    def _get_grade(self, score: float) -> str:
        """根据分数获取等级"""
        if score >= 90:
            return 'A+ (优秀)'
        elif score >= 80:
            return 'A (良好)'
        elif score >= 70:
            return 'B+ (中上)'
        elif score >= 60:
            return 'B (中等)'
        elif score >= 50:
            return 'C+ (中下)'
        elif score >= 40:
            return 'C (较差)'
        else:
            return 'D (不合格)'

async def test_raw_kline_analysis():
    """测试原始K线数据分析"""
    print("🧪 开始原始K线数据分析测试")
    print("="*60)
    
    try:
        # 1. 验证API配置
        Settings.validate()
        print("✅ OpenRouter API配置验证通过")
        
        # 2. 初始化组件
        fetcher = BinanceFetcher()
        client = OpenRouterClient()
        formatter = DataFormatter()
        evaluator = KLineAnalysisEvaluator()
        
        print("✅ 测试组件初始化完成")
        
        # 3. 获取ETH/USDT原始数据
        print("\n📊 获取ETH/USDT永续合约原始数据...")
        df = fetcher.get_ohlcv('ETH/USDT', '1h', 100)  # 获取更多数据用于分析
        
        if df.empty:
            print("❌ 获取数据失败")
            return False
        
        # 数据统计
        current_price = df['close'].iloc[-1]
        price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
        avg_volume = df['volume'].mean()
        
        print(f"✅ 成功获取{len(df)}条原始OHLCV数据")
        print(f"💰 当前价格: ${current_price:.2f}")
        print(f"📈 区间涨跌幅: {price_change:+.2f}%")
        print(f"📊 平均成交量: {avg_volume:.0f}")
        
        # 4. 准备测试模型
        test_models = [
            ('claude-opus-41', '🧠 Claude Opus 4.1 (最新旗舰)'),
            ('gpt5-mini', '⚡ GPT-5 Mini (高性价比)'),
            ('gemini-25-pro', '🚀 Gemini 2.5 Pro (大容量)'),
            ('gpt4o', '🎯 GPT-4o (均衡型)')
        ]
        
        # 5. 原始数据分析提示词
        raw_analysis_prompt = f"""
你是一位专业的量价分析(VPA)专家，请直接分析以下原始K线数据：

数据格式：每行包含 [时间, 开盘价, 最高价, 最低价, 收盘价, 成交量]

原始OHLCV数据：
{formatter.to_csv_format(df.tail(50))}  # 使用最近50条数据

请基于以上原始数据进行专业的VPA分析，包括：
1. 市场趋势识别和阶段分析
2. 关键支撑阻力位识别
3. 成交量与价格关系分析
4. Anna Coulling VSA信号识别
5. 交易信号和风险评估

要求：
- 直接引用具体的价格和成交量数据
- 使用专业的VPA/VSA术语
- 提供具体的交易建议和风险控制
- 分析应基于数据事实，避免主观臆测
"""
        
        results = []
        
        # 6. 执行多模型分析
        for model, description in test_models:
            print(f"\n🔍 {description} 分析中...")
            
            start_time = time.time()
            
            try:
                # 检查模型是否可用
                if model not in Settings.MODELS:
                    print(f"❌ 模型 {model} 不可用，跳过")
                    continue
                
                result = client.generate_response(raw_analysis_prompt, model)
                analysis_time = time.time() - start_time
                
                if result.get('success'):
                    # 估算成本
                    cost_info = client.estimate_cost(
                        model, 
                        result['usage']['prompt_tokens'],
                        result['usage']['completion_tokens']
                    )
                    
                    # 评估分析质量
                    market_data = {
                        'current_price': current_price,
                        'price_change': price_change,
                        'avg_volume': avg_volume,
                        'data_points': len(df)
                    }
                    
                    evaluation = evaluator.evaluate_analysis(result['analysis'], market_data)
                    
                    print(f"✅ 分析完成:")
                    print(f"   ⏱️ 耗时: {analysis_time:.1f}秒")
                    print(f"   💰 成本: ${cost_info['estimated_cost']:.6f}")
                    print(f"   🔢 Tokens: {result['usage']['total_tokens']}")
                    print(f"   🎯 质量评分: {evaluation['total_score']}/100 ({evaluation['grade']})")
                    
                    # 显示分类得分
                    print(f"   📊 分类得分:")
                    for category, score in evaluation['category_scores'].items():
                        category_name = {
                            'technical_accuracy': '技术分析准确性',
                            'vpa_professionalism': 'VPA专业性',
                            'data_comprehension': '数据理解能力',
                            'trading_practicality': '交易实用性'
                        }.get(category, category)
                        print(f"      {category_name}: {score:.0f}/100")
                    
                    # 显示分析摘要
                    summary = result['analysis'][:300] + "..." if len(result['analysis']) > 300 else result['analysis']
                    print(f"   📝 分析摘要: {summary}")
                    
                    results.append({
                        'model': model,
                        'description': description,
                        'success': True,
                        'cost': cost_info['estimated_cost'],
                        'time': analysis_time,
                        'tokens': result['usage']['total_tokens'],
                        'evaluation': evaluation,
                        'analysis': result['analysis']
                    })
                    
                else:
                    print(f"❌ 分析失败: {result.get('error', 'Unknown error')}")
                    results.append({
                        'model': model,
                        'description': description,
                        'success': False,
                        'error': result.get('error')
                    })
            
            except Exception as e:
                print(f"❌ 分析异常: {e}")
                results.append({
                    'model': model,
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
            
            # 避免API频率限制
            if model != test_models[-1][0]:
                print("   ⏳ 等待2秒避免频率限制...")
                await asyncio.sleep(2)
        
        # 7. 生成测试报告
        print("\n" + "="*80)
        print("📊 原始K线数据分析测试报告")
        print("="*80)
        
        successful_tests = [r for r in results if r.get('success', False)]
        
        if not successful_tests:
            print("❌ 所有测试都失败了")
            return False
        
        # 总体统计
        total_cost = sum(r.get('cost', 0) for r in successful_tests)
        avg_time = sum(r.get('time', 0) for r in successful_tests) / len(successful_tests)
        avg_score = sum(r['evaluation']['total_score'] for r in successful_tests) / len(successful_tests)
        
        print(f"✅ 成功测试: {len(successful_tests)}/{len(results)}")
        print(f"💰 总成本: ${total_cost:.6f}")
        print(f"⏱️ 平均耗时: {avg_time:.1f}秒")
        print(f"🎯 平均质量得分: {avg_score:.1f}/100")
        
        # 排行榜
        print(f"\n🏆 模型性能排行榜:")
        sorted_results = sorted(successful_tests, key=lambda x: x['evaluation']['total_score'], reverse=True)
        
        for i, result in enumerate(sorted_results, 1):
            evaluation = result['evaluation']
            print(f"{i}. {result['description']}")
            print(f"   质量得分: {evaluation['total_score']}/100 ({evaluation['grade']})")
            print(f"   成本: ${result['cost']:.6f}, 耗时: {result['time']:.1f}秒")
        
        # 最佳分析展示
        if sorted_results:
            best_result = sorted_results[0]
            print(f"\n🥇 最佳分析结果 ({best_result['description']}):")
            print("-" * 60)
            print(best_result['analysis'][:1000] + "..." if len(best_result['analysis']) > 1000 else best_result['analysis'])
            print("-" * 60)
        
        # 保存详细报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/opt/ai-trader/results/raw_kline_analysis_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_time': timestamp,
                'market_data': market_data,
                'results': results,
                'summary': {
                    'success_rate': len(successful_tests) / len(results),
                    'total_cost': total_cost,
                    'average_time': avg_time,
                    'average_score': avg_score
                }
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细报告已保存到: {report_file}")
        print("="*80)
        
        return len(successful_tests) > 0
        
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🚀 原始K线数据分析测试")
    print("测试AI模型直接理解和分析原始OHLCV数据的能力")
    print("评估分析结果的技术准确性和VPA专业性")
    print()
    
    success = await test_raw_kline_analysis()
    
    if success:
        print("\n🎉 原始K线数据分析测试完成！")
        print("💡 AI模型展现了直接理解原始数据的能力")
    else:
        print("\n❌ 原始K线数据分析测试失败")
        print("🔍 请检查API配置和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        logger.error("❌ 测试程序异常: %s", e)
        import traceback  # pylint: disable=import-outside-toplevel
        traceback.print_exc()