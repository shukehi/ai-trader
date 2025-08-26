#!/usr/bin/env python3
"""
简化版原始K线数据分析测试
快速测试AI模型直接分析原始OHLCV数据的能力
"""

import asyncio
import sys
import time
sys.path.append('/opt/ai-trader')

from data.binance_fetcher import BinanceFetcher
from ai.openrouter_client import OpenRouterClient
from formatters.data_formatter import DataFormatter
from config import Settings

async def simple_raw_analysis_test():
    """简化版原始数据分析测试"""
    print("🧪 简化版原始K线数据分析测试")
    print("="*50)
    
    try:
        # 1. 验证配置
        Settings.validate()
        print("✅ API配置验证通过")
        
        # 2. 初始化组件
        fetcher = BinanceFetcher()
        client = OpenRouterClient()
        formatter = DataFormatter()
        
        # 3. 获取数据
        print("\n📊 获取ETH/USDT数据...")
        df = fetcher.get_ohlcv('ETH/USDT', '1h', 30)  # 只获取30条数据
        
        current_price = df['close'].iloc[-1]
        price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
        
        print(f"✅ 获取{len(df)}条数据")
        print(f"💰 当前价格: ${current_price:.2f}")
        print(f"📈 涨跌幅: {price_change:+.2f}%")
        
        # 4. 格式化原始数据
        raw_data = formatter.to_csv_format(df.tail(20))  # 只使用最近20条
        
        # 5. 原始分析提示词
        prompt = f"""你是专业的量价分析师，请分析以下ETH/USDT原始K线数据：

{raw_data}

请回答：
1. 当前趋势方向是什么？
2. 最近的价格行为有什么特点？
3. 成交量变化说明什么？
4. 有哪些关键支撑阻力位？
5. 给出简要的交易建议

请直接引用数据中的具体价格和成交量数值。"""
        
        # 6. 使用快速模型测试
        print("\n🔍 使用Gemini Flash进行分析...")
        
        start_time = time.time()
        result = client.generate_response(prompt, 'gemini-flash')
        analysis_time = time.time() - start_time
        
        if result.get('success'):
            # 计算成本
            cost_info = client.estimate_cost(
                'gemini-flash',
                result['usage']['prompt_tokens'],
                result['usage']['completion_tokens']
            )
            
            print(f"✅ 分析完成:")
            print(f"   ⏱️ 耗时: {analysis_time:.1f}秒")
            print(f"   💰 成本: ${cost_info['estimated_cost']:.6f}")
            print(f"   🔢 Tokens: {result['usage']['total_tokens']}")
            
            print(f"\n📝 分析结果:")
            print("-" * 50)
            print(result['analysis'])
            print("-" * 50)
            
            # 7. 简单评估
            analysis_text = result['analysis'].lower()
            
            evaluation_score = 0
            max_score = 100
            
            # 评估标准
            criteria = {
                '引用具体价格': ['$', 'price', '价格'],
                '分析趋势': ['trend', 'bullish', 'bearish', '上升', '下降', '趋势'],
                '成交量分析': ['volume', '成交量', '放量', '缩量'],
                '技术位识别': ['support', 'resistance', '支撑', '阻力'],
                '交易建议': ['buy', 'sell', 'long', 'short', '买入', '卖出']
            }
            
            print(f"\n🎯 分析质量评估:")
            
            for criterion, keywords in criteria.items():
                found = any(keyword in analysis_text for keyword in keywords)
                points = 20 if found else 0
                evaluation_score += points
                status = "✅" if found else "❌"
                print(f"   {status} {criterion}: {points}/20分")
            
            grade = "优秀" if evaluation_score >= 80 else "良好" if evaluation_score >= 60 else "一般" if evaluation_score >= 40 else "较差"
            
            print(f"\n📊 总体评分: {evaluation_score}/{max_score} ({grade})")
            
            # 8. 结果验证
            print(f"\n🔍 数据理解验证:")
            
            # 检查是否正确理解了数据格式
            if any(str(int(current_price)) in result['analysis'] for _ in [1]):  # 检查是否提到当前价格附近的数值
                print("✅ 正确理解了价格数据")
            else:
                print("❓ 可能未充分利用价格数据")
                
            # 检查是否提到具体的数值范围
            high_price = df['high'].max()
            low_price = df['low'].min()
            
            if any(str(int(high_price))[:3] in result['analysis'] or str(int(low_price))[:3] in result['analysis'] for _ in [1]):
                print("✅ 引用了具体的价格数据")
            else:
                print("❓ 较少引用具体数值")
            
            print(f"\n💡 测试结论:")
            if evaluation_score >= 60:
                print("🟢 AI模型能够较好地理解和分析原始K线数据")
                print("🎯 展现了直接处理数值数据进行VPA分析的能力")
            else:
                print("🟡 AI模型对原始数据的理解有限")
                print("💭 可能需要更好的提示词或数据格式")
            
            return True
            
        else:
            print(f"❌ 分析失败: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🚀 简化版原始K线数据分析测试")
    print("验证AI模型直接理解原始OHLCV数据的能力")
    print()
    
    success = await simple_raw_analysis_test()
    
    if success:
        print("\n🎉 测试完成！AI展现了分析原始数据的能力")
    else:
        print("\n❌ 测试失败，请检查配置")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")