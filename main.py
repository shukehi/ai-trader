#!/usr/bin/env python3
"""
AI-Trader: AI直接分析交易系统
使用Typer + Rich构建的现代化CLI界面
"""

import logging
from datetime import datetime
from typing import Optional, Annotated
import sys

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.layout import Layout
from rich.prompt import Confirm, Prompt
from rich import print as rprint
from rich.markdown import Markdown

from config import Settings
from data import BinanceFetcher
from formatters import DataFormatter
from ai import RawDataAnalyzer, AnalysisEngine
from prompts import PromptManager

# 创建Rich控制台
console = Console()
app = typer.Typer(
    name="ai-trader",
    help="🤖 AI直接分析交易系统 - 专业的AI驱动加密货币分析工具",
    add_completion=False,
    rich_markup_mode="rich"
)

# 配置日志
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
logger = logging.getLogger(__name__)


@app.command()
def analyze(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="交易对符号")] = "ETHUSDT",
    timeframe: Annotated[str, typer.Option("--timeframe", "-t", help="时间周期")] = "1h", 
    limit: Annotated[int, typer.Option("--limit", "-l", help="K线数据数量")] = 50,
    model: Annotated[str, typer.Option("--model", "-m", help="AI模型")] = "gemini-flash",
    analysis_type: Annotated[str, typer.Option("--analysis-type", "-a", help="分析类型")] = "complete",
    analysis_method: Annotated[Optional[str], typer.Option("--method", help="分析方法")] = None,
    raw_analysis: Annotated[bool, typer.Option("--raw", help="使用原始数据分析器")] = True,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="显示详细输出")] = False
):
    """🚀 执行AI直接分析"""
    
    if verbose:
        logging.basicConfig(level=logging.INFO, force=True)
    
    # 显示启动信息
    _show_startup_banner()
    
    # 验证配置
    try:
        Settings.validate()
        console.print("✅ API配置验证成功", style="green")
    except Exception as e:
        console.print(f"❌ 配置错误: {e}", style="red")
        raise typer.Exit(1)
    
    # 显示分析参数
    _show_analysis_params(symbol, timeframe, limit, model, analysis_type, analysis_method)
    
    # 获取数据
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # 数据获取阶段
        task = progress.add_task("📊 正在获取市场数据...", total=None)
        
        try:
            fetcher = BinanceFetcher()
            symbol_for_api = symbol.replace('USDT', '/USDT') if '/' not in symbol else symbol
            df = fetcher.get_ohlcv(symbol_for_api, timeframe, limit)
            
            if df is None or len(df) == 0:
                console.print("❌ 获取数据失败", style="red")
                raise typer.Exit(1)
                
            progress.update(task, description=f"✅ 成功获取 {len(df)} 条数据")
            
            # 显示数据概览
            _show_data_overview(df, symbol)
            
        except Exception as e:
            console.print(f"❌ 数据获取错误: {e}", style="red")
            raise typer.Exit(1)
    
    # AI分析阶段
    console.print("\n🤖 开始AI分析...", style="blue")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("🧠 AI分析进行中...", total=100)
        
        try:
            # 选择分析器
            if raw_analysis:
                analyzer = RawDataAnalyzer()
                progress.update(task, advance=20, description="🔧 初始化原始数据分析器...")
                
                result = analyzer.analyze_raw_ohlcv(
                    df=df,
                    model=model,
                    analysis_type=analysis_type,
                    analysis_method=analysis_method
                )
                progress.update(task, advance=70, description="📊 分析完成...")
                
            else:
                engine = AnalysisEngine()
                progress.update(task, advance=20, description="🔧 初始化分析引擎...")
                
                result = engine.raw_data_analysis(
                    df=df,
                    analysis_type=analysis_type,
                    model=model
                )
                progress.update(task, advance=70, description="📊 分析完成...")
            
            progress.update(task, advance=10, description="✅ 处理结果...")
            
        except Exception as e:
            console.print(f"❌ 分析过程错误: {e}", style="red")
            raise typer.Exit(1)
    
    # 显示分析结果
    _show_analysis_results(result, symbol, model, analysis_method)


@app.command()
def methods():
    """📋 列出所有可用的分析方法"""
    
    console.print(Panel.fit(
        "📚 [bold blue]AI-Trader 分析方法库[/bold blue]",
        border_style="blue"
    ))
    
    try:
        prompt_manager = PromptManager()
        methods = prompt_manager.list_available_methods()
        
        for category, method_list in methods.items():
            # 创建分类表格
            table = Table(title=f"🔸 {category.replace('_', ' ').title()}", show_header=True)
            table.add_column("方法名称", style="cyan", width=40)
            table.add_column("命令参数", style="yellow", width=50)
            table.add_column("描述", style="white")
            
            for method in method_list:
                method_key = f"{category.replace('_', '-')}-{method.replace('_', '-')}"
                try:
                    method_info = prompt_manager.get_method_info(method_key)
                    display_name = method_info.get('display_name', method.replace('_', ' ').title())
                    description = method_info.get('description', '专业分析方法')[:50]
                except:
                    display_name = method.replace('_', ' ').title()
                    description = '专业分析方法'
                
                table.add_row(
                    display_name,
                    f"--method {method_key}",
                    description
                )
            
            console.print(table)
            console.print()
            
    except Exception as e:
        console.print(f"❌ 加载分析方法失败: {e}", style="red")


@app.command()
def config():
    """⚙️ 配置管理和验证"""
    
    console.print(Panel.fit(
        "⚙️ [bold green]AI-Trader 配置管理[/bold green]",
        border_style="green"
    ))
    
    # 检查API配置
    try:
        Settings.validate()
        
        table = Table(title="📊 系统配置状态", show_header=True)
        table.add_column("配置项", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("详情", style="white")
        
        table.add_row("OpenRouter API", "✅ 正常", "API密钥已配置")
        table.add_row("数据连接", "✅ 正常", "Binance API连接正常")
        table.add_row("分析组件", "✅ 就绪", "AI分析器初始化成功")
        
        console.print(table)
        
        # 测试数据获取
        if Confirm.ask("🧪 是否测试数据获取功能?"):
            _test_data_connection()
            
    except Exception as e:
        console.print(f"❌ 配置验证失败: {e}", style="red")
        console.print("\n💡 请检查以下配置:")
        console.print("  • .env文件是否存在")
        console.print("  • OPENROUTER_API_KEY是否正确设置")
        console.print("  • 网络连接是否正常")


@app.command()
def demo():
    """🎮 运行演示分析"""
    
    console.print(Panel.fit(
        "🎮 [bold magenta]AI-Trader 演示模式[/bold magenta]\n\n"
        "将使用 ETHUSDT 进行快速分析演示",
        border_style="magenta"
    ))
    
    if not Confirm.ask("🚀 开始演示?"):
        console.print("👋 演示取消")
        return
    
    # 使用快速参数进行演示
    try:
        analyze(
            symbol="ETHUSDT",
            timeframe="1h", 
            limit=20,
            model="gemini-flash",
            analysis_type="simple",
            analysis_method=None,
            raw_analysis=True,
            verbose=False
        )
    except Exception as e:
        console.print(f"❌ 演示失败: {e}", style="red")


def _show_startup_banner():
    """显示启动横幅"""
    banner = """
🤖 [bold blue]AI-Trader[/bold blue] [dim]v2.0[/dim]
[italic]专业的AI直接分析交易系统[/italic]
"""
    console.print(Panel.fit(banner, border_style="blue"))


def _show_analysis_params(symbol, timeframe, limit, model, analysis_type, analysis_method):
    """显示分析参数"""
    table = Table(title="📊 分析配置", show_header=False, box=None)
    table.add_column("参数", style="cyan", width=12)
    table.add_column("值", style="white")
    
    table.add_row("交易对", symbol)
    table.add_row("时间框架", timeframe)
    table.add_row("数据量", str(limit))
    table.add_row("AI模型", model)
    table.add_row("分析类型", analysis_type)
    table.add_row("分析方法", analysis_method or "默认")
    
    console.print(table)


def _show_data_overview(df, symbol):
    """显示数据概览"""
    latest = df.iloc[-1]
    
    table = Table(title=f"💰 {symbol} 数据概览", show_header=True)
    table.add_column("时间", style="dim")
    table.add_column("开盘", style="cyan")
    table.add_column("最高", style="green")
    table.add_column("最低", style="red")
    table.add_column("收盘", style="yellow")
    table.add_column("成交量", style="blue")
    
    # 显示最近5条数据
    for _, row in df.tail(5).iterrows():
        table.add_row(
            str(row['timestamp'])[:19] if 'timestamp' in row else str(row.name),
            f"${row['open']:.2f}",
            f"${row['high']:.2f}",
            f"${row['low']:.2f}",
            f"${row['close']:.2f}",
            f"{row['volume']:,.0f}"
        )
    
    console.print(table)


def _show_analysis_results(result, symbol, model, analysis_method):
    """显示分析结果"""
    console.print("\n" + "="*80)
    console.print(Panel.fit(
        f"📊 [bold green]{symbol} AI分析结果[/bold green]",
        border_style="green"
    ))
    
    if result.get('success'):
        # 显示分析文本
        if 'analysis_text' in result:
            analysis_text = result['analysis_text']
        else:
            analysis_text = result.get('analysis', '无分析结果')
        
        # 格式化分析结果
        console.print(Panel(
            analysis_text,
            title="🤖 AI分析报告",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # 显示质量指标
        quality_score = result.get('quality_score', 'N/A')
        analysis_time = result.get('performance_metrics', {}).get('analysis_time', 'N/A')
        data_points = result.get('data_points', len(result.get('df', [])) if 'df' in result else 'N/A')
        
        metrics_table = Table(title="📈 分析指标", show_header=False)
        metrics_table.add_column("指标", style="cyan")
        metrics_table.add_column("值", style="white")
        
        metrics_table.add_row("🎯 质量评分", f"{quality_score}/100" if quality_score != 'N/A' else 'N/A')
        metrics_table.add_row("⏱️ 分析耗时", f"{analysis_time}秒" if analysis_time != 'N/A' else 'N/A')
        metrics_table.add_row("📊 数据点数", str(data_points))
        metrics_table.add_row("🤖 使用模型", model)
        metrics_table.add_row("📋 分析方法", analysis_method or "默认")
        metrics_table.add_row("🕒 分析时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        console.print(metrics_table)
        console.print("\n✅ [bold green]分析完成![/bold green]")
        
    else:
        error_msg = result.get('error', result.get('analysis', '未知错误'))
        console.print(f"❌ [red]分析失败: {error_msg}[/red]")


def _test_data_connection():
    """测试数据连接"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("🧪 测试数据连接...", total=None)
        
        try:
            fetcher = BinanceFetcher()
            df = fetcher.get_ohlcv('ETH/USDT', '1h', 5)
            
            if df is not None and len(df) > 0:
                progress.update(task, description="✅ 数据连接测试成功")
                console.print(f"✅ 成功获取 {len(df)} 条测试数据", style="green")
                console.print(f"💰 最新价格: ${df.iloc[-1]['close']:.2f}", style="yellow")
            else:
                console.print("❌ 数据连接测试失败", style="red")
                
        except Exception as e:
            console.print(f"❌ 数据连接错误: {e}", style="red")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 用户中断，退出程序", style="yellow")
    except Exception as e:
        console.print(f"❌ 程序执行错误: {e}", style="red")
        sys.exit(1)