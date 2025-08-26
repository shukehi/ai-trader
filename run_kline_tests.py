#!/usr/bin/env python3
"""
原始K线数据分析测试 - 统一入口脚本
提供三种测试模式的快速访问
"""

import asyncio
import sys
from typing import Optional

# 设置项目路径
sys.path.append('/opt/ai-trader')

def show_menu():
    """显示测试选项菜单"""
    print("🚀 原始K线数据分析测试套件")
    print("="*50)
    print("请选择测试模式:")
    print()
    print("1. 🏃 快速测试 (简化版)")
    print("   - 单模型测试 (Gemini Flash)")
    print("   - 30秒完成，成本 ~$0.0003")
    print("   - 验证AI理解原始数据能力")
    print()
    print("2. 📊 完整评估 (标准版)")
    print("   - 多模型测试 (4个AI模型)")
    print("   - 专业4维度评估系统")
    print("   - 2-5分钟，成本 ~$0.01-0.05")
    print()
    print("3. 🎯 增强分析 (专业版)")
    print("   - 多时间框架分析 (1d/4h/1h/15m)")
    print("   - 批量模型对比测试")
    print("   - 5-10分钟，成本 ~$0.1-0.5")
    print()
    print("4. ❓ 查看帮助信息")
    print("0. 🚪 退出")
    print("="*50)

async def run_simple_test():
    """运行简化版测试"""
    print("🏃 启动快速测试...")
    
    try:
        # 动态导入避免循环依赖
        from test_raw_kline_simple import simple_raw_analysis_test
        success = await simple_raw_analysis_test()
        return success
    except Exception as e:
        print(f"❌ 快速测试失败: {e}")
        return False

async def run_complete_test():
    """运行完整评估测试"""
    print("📊 启动完整评估测试...")
    
    try:
        from test_raw_kline_analysis import test_raw_kline_analysis
        success = await test_raw_kline_analysis()
        return success
    except Exception as e:
        print(f"❌ 完整测试失败: {e}")
        return False

async def run_enhanced_test():
    """运行增强版测试"""
    print("🎯 启动增强分析测试...")
    
    try:
        from test_raw_kline_enhanced import main as enhanced_main
        success = await enhanced_main()
        return success
    except Exception as e:
        print(f"❌ 增强测试失败: {e}")
        return False

def show_help():
    """显示帮助信息"""
    print("\n📚 测试模式详细说明")
    print("="*60)
    
    print("\n🏃 快速测试 (test_raw_kline_simple.py)")
    print("   适用场景: 快速验证AI分析能力")
    print("   测试内容:")
    print("     - 获取30条ETH/USDT 1h数据")
    print("     - 使用Gemini Flash进行分析")
    print("     - 5项质量评估标准")
    print("   优势: 速度快、成本低、操作简单")
    print("   输出: 实时分析结果和质量评分")
    
    print("\n📊 完整评估 (test_raw_kline_analysis.py)")
    print("   适用场景: 系统性模型能力评估")
    print("   测试内容:")
    print("     - 获取100条ETH/USDT数据")
    print("     - 4个高级AI模型对比")
    print("     - 4维度专业评估体系")
    print("   优势: 全面评估、模型对比、详细报告")
    print("   输出: JSON格式详细测试报告")
    
    print("\n🎯 增强分析 (test_raw_kline_enhanced.py)")
    print("   适用场景: 专业级交易分析")
    print("   测试内容:")
    print("     - 多时间框架分析 (1d/4h/1h/15m)")
    print("     - 时间框架共识算法")
    print("     - 批量模型性能对比")
    print("   优势: 专业深度、多维分析、投资级质量")
    print("   输出: 多时间框架共识和模型对比报告")
    
    print("\n💡 使用建议:")
    print("   - 初次使用: 选择快速测试验证系统")
    print("   - 研究分析: 选择完整评估了解各模型表现")
    print("   - 交易应用: 选择增强分析获得专业信号")
    
    print("\n🔧 技术要求:")
    print("   - Python 3.8+")
    print("   - OPENROUTER_API_KEY 已配置")
    print("   - 网络连接稳定")
    print("   - results/ 目录存在")
    
    print("="*60)

async def main():
    """主函数"""
    while True:
        try:
            show_menu()
            
            choice = input("\n请选择 (1-4, 0退出): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "1":
                print()
                success = await run_simple_test()
                if success:
                    print("\n✅ 快速测试完成")
                else:
                    print("\n❌ 快速测试失败")
                    
            elif choice == "2":
                print()
                success = await run_complete_test()
                if success:
                    print("\n✅ 完整评估完成")
                else:
                    print("\n❌ 完整评估失败")
                    
            elif choice == "3":
                print()
                success = await run_enhanced_test()
                if success:
                    print("\n✅ 增强分析完成")
                else:
                    print("\n❌ 增强分析失败")
                    
            elif choice == "4":
                show_help()
                
            else:
                print("❌ 无效选择，请重新输入")
            
            if choice in ["1", "2", "3"]:
                input("\n按回车键继续...")
                print("\n" + "="*50 + "\n")
                
        except KeyboardInterrupt:
            print("\n👋 用户退出")
            break
        except Exception as e:
            print(f"\n❌ 程序异常: {e}")
            input("按回车键继续...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")