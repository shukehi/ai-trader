#!/usr/bin/env python3
"""
ETH永续合约AI直接分析助手
专注API数据获取和AI分析原始K线数据
"""

import argparse
import logging
from config import Settings
from data import BinanceFetcher
from formatters import DataFormatter
from ai import RawDataAnalyzer, OpenRouterClient, AnalysisEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='ETH永续合约AI直接分析助手')
    parser.add_argument('--symbol', default='ETHUSDT', help='交易对符号')
    parser.add_argument('--timeframe', default='1h', help='时间周期')
    parser.add_argument('--limit', type=int, default=50, help='K线数据数量')
    parser.add_argument('--model', choices=[
        'gpt5-chat', 'gpt5-mini', 'gpt5-nano', 'claude-opus-41', 'gemini-25-pro',
        'gpt4', 'gpt4o', 'gpt4o-mini', 'claude', 'gemini', 'gemini-flash'
    ], default='gemini-flash', help='使用的LLM模型')
    
    # AI直接分析模式
    parser.add_argument('--raw-analysis', action='store_true', help='AI直接分析原始数据（推荐）')
    parser.add_argument('--analysis-type', choices=['simple', 'complete', 'enhanced'], 
                       default='simple', help='AI分析类型')
    parser.add_argument('--batch-models', action='store_true', help='使用多个模型进行对比')
    
    args = parser.parse_args()
    
    try:
        # 验证配置
        Settings.validate()
        
        print(f"🚀 启动AI直接分析助手...")
        print(f"📊 分析参数: {args.symbol} {args.timeframe} 最近{args.limit}条数据")
        print(f"🤖 使用模型: {args.model}")
        
        # 获取数据
        fetcher = BinanceFetcher()
        symbol_for_api = args.symbol.replace('USDT', '/USDT') if '/' not in args.symbol else args.symbol
        
        print(f"📊 获取 {symbol_for_api} 数据...")
        df = fetcher.get_ohlcv(
            symbol=symbol_for_api,
            timeframe=args.timeframe,
            limit=args.limit
        )
        
        if df is None or len(df) == 0:
            print("❌ 获取数据失败")
            return 1
            
        print(f"✅ 获取到 {len(df)} 条数据")
        print(f"💰 最新价格: ${df.iloc[-1]['close']:.2f}")
        
        if args.raw_analysis:
            # AI直接分析模式
            print("🤖 开始AI直接分析...")
            analyzer = RawDataAnalyzer()
            
            if args.batch_models:
                # 多模型对比
                models = ['gemini-flash', 'gpt4o-mini', 'claude']
                print(f"🔄 使用多模型对比: {', '.join(models)}")
                
                for model in models:
                    print(f"\n--- 📊 {model} 分析结果 ---")
                    result = analyzer.analyze_raw_ohlcv(
                        df=df,
                        model=model,
                        analysis_type=args.analysis_type
                    )
                    
                    if result.get('success'):
                        print(result['analysis'])
                    else:
                        print(f"❌ 分析失败: {result.get('analysis', '未知错误')}")
            else:
                # 单模型分析
                result = analyzer.analyze_raw_ohlcv(
                    df=df,
                    model=args.model,
                    analysis_type=args.analysis_type
                )
                
                if result.get('success'):
                    print("\n--- 📊 AI分析结果 ---")
                    print(result['analysis'])
                    print(f"\n📈 数据点数: {result.get('data_points', len(df))}")
                else:
                    print(f"❌ AI分析失败: {result.get('analysis', '未知错误')}")
        else:
            # 使用分析引擎
            print("🤖 使用分析引擎...")
            engine = AnalysisEngine()
            
            result = engine.raw_data_analysis(
                df=df,
                analysis_type=args.analysis_type,
                model=args.model
            )
            
            if result.get('success'):
                print("\n--- 📊 分析结果 ---")
                print(result['analysis'])
            else:
                print(f"❌ 分析失败: {result.get('analysis', '未知错误')}")
            
    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        return 0
    except Exception as e:
        logger.error(f"程序执行错误: {e}")
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())