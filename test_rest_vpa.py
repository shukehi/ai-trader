#!/usr/bin/env python3
"""
REST VPA分析测试脚本
使用现有REST API进行Anna Coulling VSA分析测试
(绕过WebSocket连接问题)
"""

import asyncio
import logging
import sys
from datetime import datetime
import time

# 设置项目路径
sys.path.append('/Users/aries/Dve/ai_trader')

from data.binance_fetcher import BinanceFetcher
from ai.openrouter_client import OpenRouterClient
from ai.trading_prompts import TradingPromptTemplates
from formatters.data_formatter import DataFormatter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_rest_vpa_analysis():
    """测试REST API的VPA分析功能"""
    print("🧪 开始REST VPA分析测试")
    print("="*50)
    
    try:
        # 1. 验证API配置
        from config import Settings
        Settings.validate()
        print("✅ OpenRouter API配置验证通过")
        
        # 2. 创建组件
        fetcher = BinanceFetcher()
        client = OpenRouterClient()
        formatter = DataFormatter()
        
        print("✅ 核心组件初始化完成")
        
        # 3. 获取ETH永续合约数据
        print("\n📊 获取ETH/USDT永续合约数据...")
        df = fetcher.get_ohlcv('ETH/USDT', '1h', 50)
        
        if df.empty:
            print("❌ 获取数据失败")
            return False
        
        current_price = df['close'].iloc[-1]
        print(f"✅ 成功获取{len(df)}条数据")
        print(f"💰 当前价格: ${current_price:.2f}")
        print(f"📈 价格范围: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
        
        # 4. 格式化数据 (使用优化的Pattern格式)
        print("\n🔄 使用Anna Coulling优化格式化数据...")
        formatted_data = formatter.to_pattern_description(df)
        
        token_estimate = len(formatted_data.split()) * 1.3
        print(f"📝 格式化完成，估计{token_estimate:.0f} tokens")
        
        # 5. 获取Anna Coulling VSA提示词
        prompt_template = TradingPromptTemplates.get_trading_signal_prompt()
        full_prompt = prompt_template + "\n\n" + formatted_data
        
        print(f"📋 Anna Coulling VSA提示词已就绪")
        
        # 6. 执行VPA分析 (使用经济型模型)
        test_models = [
            ('gemini-flash', '⚡ Gemini Flash (最快)'),
            ('gpt4o-mini', '💰 GPT-4o Mini (经济)')
        ]
        
        results = []
        
        for model, description in test_models:
            print(f"\n🔍 {description} 分析中...")
            
            start_time = time.time()
            
            try:
                result = client.generate_response(full_prompt, model)
                analysis_time = time.time() - start_time
                
                if result.get('success'):
                    # 估算成本
                    cost_info = client.estimate_cost(
                        model, 
                        result['usage']['prompt_tokens'],
                        result['usage']['completion_tokens']
                    )
                    
                    print(f"✅ 分析成功:")
                    print(f"   ⏱️ 耗时: {analysis_time:.1f}秒")
                    print(f"   💰 成本: ${cost_info['estimated_cost']:.6f}")
                    print(f"   🔢 Tokens: {result['usage']['total_tokens']}")
                    
                    # 检查VSA关键词
                    analysis = result['analysis'].lower()
                    vsa_signals = []
                    
                    if 'accumulation' in analysis or '积累' in result['analysis']:
                        vsa_signals.append('积累阶段')
                    if 'distribution' in analysis or '分配' in result['analysis']:
                        vsa_signals.append('分配阶段')
                    if 'no demand' in analysis or '无需求' in result['analysis']:
                        vsa_signals.append('No Demand')
                    if 'no supply' in analysis or '无供应' in result['analysis']:
                        vsa_signals.append('No Supply')
                    if 'climax' in analysis or '高潮成交量' in result['analysis']:
                        vsa_signals.append('Climax Volume')
                    if 'upthrust' in analysis or '假突破' in result['analysis']:
                        vsa_signals.append('Upthrust')
                    if 'spring' in analysis or '弹簧' in result['analysis']:
                        vsa_signals.append('Spring')
                    
                    if vsa_signals:
                        print(f"   🎯 VSA信号: {', '.join(vsa_signals)}")
                    else:
                        print(f"   📊 一般分析 (未检测到特殊VSA信号)")
                    
                    # 显示分析摘要
                    summary = result['analysis'][:200] + "..." if len(result['analysis']) > 200 else result['analysis']
                    print(f"   📝 分析摘要: {summary}")
                    
                    results.append({
                        'model': model,
                        'success': True,
                        'cost': cost_info['estimated_cost'],
                        'time': analysis_time,
                        'vsa_signals': vsa_signals,
                        'tokens': result['usage']['total_tokens']
                    })
                    
                else:
                    print(f"❌ 分析失败: {result.get('error', 'Unknown error')}")
                    results.append({
                        'model': model,
                        'success': False,
                        'error': result.get('error')
                    })
                
            except Exception as e:
                print(f"❌ 分析异常: {e}")
                results.append({
                    'model': model,
                    'success': False,
                    'error': str(e)
                })
            
            # 避免API频率限制
            if model != test_models[-1][0]:  # 不是最后一个模型
                print("   ⏳ 等待1秒避免频率限制...")
                await asyncio.sleep(1)
        
        # 7. 测试结果汇总
        print("\n" + "="*60)
        print("📊 REST VPA分析测试结果汇总")
        print("="*60)
        
        successful_tests = [r for r in results if r.get('success', False)]
        total_cost = sum(r.get('cost', 0) for r in successful_tests)
        avg_time = sum(r.get('time', 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        
        print(f"✅ 成功测试: {len(successful_tests)}/{len(results)}")
        print(f"💰 总成本: ${total_cost:.6f}")
        print(f"⏱️ 平均耗时: {avg_time:.1f}秒")
        
        if successful_tests:
            print(f"\n🎯 VSA信号检测统计:")
            all_signals = []
            for r in successful_tests:
                all_signals.extend(r.get('vsa_signals', []))
            
            if all_signals:
                from collections import Counter
                signal_counts = Counter(all_signals)
                for signal, count in signal_counts.items():
                    print(f"   {signal}: {count}次")
            else:
                print("   未检测到专业VSA信号 (可能是正常的市场状态)")
        
        print(f"\n💡 系统评估:")
        if len(successful_tests) == len(results):
            print("🟢 优秀 - 所有分析成功，系统稳定")
        elif len(successful_tests) > 0:
            print("🟡 良好 - 部分分析成功，需要检查失败原因")
        else:
            print("🔴 失败 - 所有分析失败，需要检查配置和网络")
        
        print("="*60)
        return len(successful_tests) > 0
        
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🚀 REST VPA分析测试")
    print("基于Anna Coulling VSA理论 + OpenRouter API")
    print("(绕过WebSocket连接问题的简化测试)")
    print()
    
    success = await test_rest_vpa_analysis()
    
    if success:
        print("\n🎉 REST VPA测试通过！")
        print("💡 Anna Coulling VSA系统基础功能正常")
        print("📡 如需WebSocket实时功能，请检查网络连接")
    else:
        print("\n❌ REST VPA测试失败")
        print("🔍 请检查API配置和网络连接")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试程序异常: {e}")
        import traceback
        traceback.print_exc()