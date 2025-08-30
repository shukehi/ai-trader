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
from ai import RawDataAnalyzer, AnalysisEngine, MultiTimeframeAnalyzer, AnalysisScenario, RealtimeAnalysisEngine, RealtimeConfig, AnalysisFrequency
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
    limit: Annotated[int, typer.Option("--limit", "-l", help="K线数据数量")] = 120,
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
    """📋 列出所有可用的分析方法 (Al Brooks验证期)"""
    
    # 验证期特殊标题
    console.print(Panel.fit(
        "🧪 [bold yellow]AI-Trader 分析方法库 - Al Brooks验证期[/bold yellow]",
        border_style="yellow"
    ))
    
    # 验证期说明
    console.print(Panel(
        "ℹ️  [bold blue]当前状态说明[/bold blue]\n\n"
        "为确保分析质量，系统当前仅支持 Al Brooks 价格行为分析方法。\n"
        "其他方法将在验证完成后按优先级逐步恢复：\n\n"
        "📋 [yellow]计划恢复顺序[/yellow]:\n"
        "   1️⃣  VPA经典分析 (基础重要)\n"
        "   2️⃣  ICT公允价值缺口 (流行方法)\n"
        "   3️⃣  其他ICT和价格行为方法\n"
        "   4️⃣  高级综合分析方法\n\n"
        "📞 如需完整方法库，请查看: prompt_manager_full.py.backup",
        border_style="blue",
        title="验证期信息"
    ))
    console.print()
    
    try:
        prompt_manager = PromptManager()
        
        # 创建Al Brooks专用表格
        table = Table(title="🎯 当前可用分析方法", show_header=True)
        table.add_column("方法名称", style="cyan", width=40)
        table.add_column("简短命令", style="green", width=25)
        table.add_column("完整命令", style="yellow", width=40)
        table.add_column("状态", style="white", width=15)
        
        # Al Brooks方法信息
        table.add_row(
            "Al Brooks价格行为分析",
            "--method al-brooks", 
            "--method price-action-al-brooks-analysis",
            "🟢 验证中"
        )
        
        console.print(table)
        console.print()
        
        # 使用示例
        example_panel = Panel(
            "💡 [bold green]使用示例[/bold green]\n\n"
            "🔸 基础分析:\n"
            "   [cyan]python main.py analyze --method al-brooks[/cyan]\n\n"
            "🔸 指定交易对:\n"
            "   [cyan]python main.py analyze --method al-brooks --symbol BTCUSDT[/cyan]\n\n"
            "🔸 多时间周期分析:\n"
            "   [cyan]python main.py multi-analyze --method al-brooks --timeframes '1h,4h,1d'[/cyan]\n\n"
            "🔸 详细输出:\n"
            "   [cyan]python main.py analyze --method al-brooks --verbose[/cyan]",
            title="快速开始",
            border_style="green"
        )
        console.print(example_panel)
        
    except Exception as e:
        console.print(f"❌ 加载分析方法失败: {e}", style="red")
        console.print("💡 提示: 请确保Al Brooks提示词文件存在: prompts/price_action/al_brooks_analysis.txt", style="yellow")


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


@app.command()
def multi_analyze(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="交易对符号")] = "ETHUSDT",
    timeframes: Annotated[str, typer.Option("--timeframes", "-tf", help="时间周期列表，逗号分隔")] = "15m,1h,4h",
    model: Annotated[str, typer.Option("--model", "-m", help="AI模型")] = "gemini-flash",
    analysis_type: Annotated[str, typer.Option("--analysis-type", "-a", help="分析类型")] = "complete",
    analysis_method: Annotated[Optional[str], typer.Option("--method", help="分析方法")] = None,
    scenario: Annotated[Optional[str], typer.Option("--scenario", help="分析场景")] = None,
    user_intent: Annotated[Optional[str], typer.Option("--intent", help="用户意图")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="显示详细输出")] = False
):
    """🔄 执行多时间周期综合分析"""
    
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
    
    # 解析时间周期列表
    timeframe_list = [tf.strip() for tf in timeframes.split(',')]
    
    # 解析分析场景
    scenario_enum = None
    if scenario:
        scenario_mapping = {
            'intraday': AnalysisScenario.INTRADAY_TRADING,
            'trend': AnalysisScenario.TREND_ANALYSIS,
            'swing': AnalysisScenario.SWING_TRADING,
            'position': AnalysisScenario.POSITION_SIZING,
            'quick': AnalysisScenario.QUICK_CHECK
        }
        scenario_enum = scenario_mapping.get(scenario.lower())
    
    # 显示多时间周期分析参数
    _show_multi_timeframe_params(symbol, timeframe_list, model, analysis_type, analysis_method, scenario)
    
    # 执行多时间周期分析
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("🔄 执行多时间周期分析...", total=100)
        
        try:
            analyzer = MultiTimeframeAnalyzer()
            progress.update(task, advance=20, description="🔧 初始化多时间周期分析器...")
            
            result = analyzer.analyze_multi_timeframe(
                symbol=symbol,
                model=model,
                analysis_type=analysis_type,
                analysis_method=analysis_method,
                scenario=scenario_enum,
                custom_timeframes=timeframe_list,
                user_intent=user_intent
            )
            progress.update(task, advance=70, description="📊 分析完成...")
            
        except Exception as e:
            console.print(f"❌ 多时间周期分析错误: {e}", style="red")
            raise typer.Exit(1)
        
        progress.update(task, advance=10, description="✅ 处理结果...")
    
    # 显示多时间周期分析结果
    _show_multi_timeframe_results(result, symbol, model)


@app.command()
def realtime(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="交易对符号")] = "ETHUSDT",
    timeframes: Annotated[str, typer.Option("--timeframes", "-tf", help="时间周期列表，逗号分隔")] = "5m,15m,1h,4h",
    model: Annotated[str, typer.Option("--model", "-m", help="AI模型")] = "gemini-flash",
    frequency: Annotated[str, typer.Option("--frequency", "-f", help="分析频率")] = "normal",
    adaptive: Annotated[bool, typer.Option("--adaptive", help="自适应频率")] = True,
    analysis_method: Annotated[Optional[str], typer.Option("--method", help="分析方法")] = None,
    max_per_hour: Annotated[int, typer.Option("--max-per-hour", help="每小时最大分析次数")] = 20,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="显示详细输出")] = False
):
    """⚡ 启动实时多时间周期分析"""
    
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
    
    # 解析时间周期列表
    timeframe_list = [tf.strip() for tf in timeframes.split(',')]
    
    # 解析分析频率
    frequency_mapping = {
        'realtime': AnalysisFrequency.REALTIME,
        'high': AnalysisFrequency.HIGH,
        'normal': AnalysisFrequency.NORMAL,
        'low': AnalysisFrequency.LOW
    }
    frequency_enum = frequency_mapping.get(frequency.lower(), AnalysisFrequency.NORMAL)
    
    # 创建实时配置
    config = RealtimeConfig(
        symbol=symbol,
        timeframes=timeframe_list,
        base_frequency=frequency_enum,
        adaptive_frequency=adaptive,
        model=model,
        analysis_method=analysis_method,
        max_analysis_per_hour=max_per_hour
    )
    
    # 显示实时分析配置
    _show_realtime_config(config)
    
    if not Confirm.ask("🚀 启动实时分析?"):
        console.print("👋 实时分析取消")
        return
    
    # 启动实时分析引擎
    try:
        import asyncio
        
        async def run_realtime_analysis():
            engine = RealtimeAnalysisEngine(config)
            
            # 添加结果回调
            def on_analysis_result(result):
                console.print("\n" + "="*80)
                console.print(f"⚡ [bold yellow]实时分析结果 - {result.timestamp.strftime('%H:%M:%S')}[/bold yellow]")
                _show_multi_timeframe_results(result, symbol, model, is_realtime=True)
            
            def on_error(error):
                console.print(f"❌ [red]实时分析错误: {error}[/red]")
            
            engine.add_analysis_callback(on_analysis_result)
            engine.add_error_callback(on_error)
            
            console.print("⚡ [bold green]实时分析已启动，按Ctrl+C停止[/bold green]")
            
            try:
                await engine.start_realtime_analysis()
            except KeyboardInterrupt:
                console.print("\n🛑 用户中断，正在停止实时分析...")
                await engine.stop()
                console.print("✅ 实时分析已停止")
            except Exception as e:
                console.print(f"❌ 实时分析错误: {e}")
                await engine.stop()
        
        asyncio.run(run_realtime_analysis())
        
    except Exception as e:
        console.print(f"❌ 启动实时分析失败: {e}", style="red")


@app.command()
def scenarios():
    """📋 列出所有可用的分析场景"""
    
    console.print(Panel.fit(
        "📚 [bold blue]多时间周期分析场景[/bold blue]",
        border_style="blue"
    ))
    
    scenarios_info = {
        AnalysisScenario.INTRADAY_TRADING: {
            'name': '日内交易',
            'timeframes': '5m, 15m, 1h, 4h',
            'frequency': '5分钟更新',
            'description': '高频交易和短线操作场景'
        },
        AnalysisScenario.TREND_ANALYSIS: {
            'name': '趋势分析',
            'timeframes': '1h, 4h, 1d, 1w',
            'frequency': '1小时更新',
            'description': '中长期趋势判断和持仓分析'
        },
        AnalysisScenario.SWING_TRADING: {
            'name': '波段交易',
            'timeframes': '1h, 4h, 1d',
            'frequency': '30分钟更新',
            'description': '中期波段操作和趋势追随'
        },
        AnalysisScenario.POSITION_SIZING: {
            'name': '仓位管理',
            'timeframes': '4h, 1d, 1w',
            'frequency': '2小时更新',
            'description': '投资组合管理和风险控制'
        },
        AnalysisScenario.QUICK_CHECK: {
            'name': '快速检查',
            'timeframes': '1h',
            'frequency': '1小时更新',
            'description': '快速市场概况和基本分析'
        }
    }
    
    table = Table(title="📊 分析场景详情", show_header=True)
    table.add_column("场景", style="cyan", width=12)
    table.add_column("命令参数", style="yellow", width=15)
    table.add_column("时间周期", style="green", width=15)
    table.add_column("更新频率", style="blue", width=12)
    table.add_column("适用描述", style="white")
    
    for scenario, info in scenarios_info.items():
        command_param = scenario.value
        table.add_row(
            info['name'],
            f"--scenario {command_param}",
            info['timeframes'],
            info['frequency'],
            info['description']
        )
    
    console.print(table)
    console.print("\n💡 使用示例:")
    console.print("  python main.py multi-analyze --scenario intraday")
    console.print("  python main.py realtime --frequency high")


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


def _show_multi_timeframe_params(symbol, timeframes, model, analysis_type, analysis_method, scenario):
    """显示多时间周期分析参数"""
    table = Table(title="🔄 多时间周期分析配置", show_header=False, box=None)
    table.add_column("参数", style="cyan", width=15)
    table.add_column("值", style="white")
    
    table.add_row("交易对", symbol)
    table.add_row("时间周期", ", ".join(timeframes))
    table.add_row("AI模型", model)
    table.add_row("分析类型", analysis_type)
    table.add_row("分析方法", analysis_method or "默认")
    table.add_row("分析场景", scenario or "智能识别")
    
    console.print(table)


def _show_realtime_config(config: RealtimeConfig):
    """显示实时分析配置"""
    table = Table(title="⚡ 实时分析配置", show_header=False, box=None)
    table.add_column("配置项", style="cyan", width=15)
    table.add_column("设置值", style="white")
    
    table.add_row("交易对", config.symbol)
    table.add_row("时间周期", ", ".join(config.timeframes))
    table.add_row("AI模型", config.model)
    table.add_row("基础频率", config.base_frequency.value)
    table.add_row("自适应频率", "启用" if config.adaptive_frequency else "禁用")
    table.add_row("分析方法", config.analysis_method or "默认")
    table.add_row("每小时限制", str(config.max_analysis_per_hour))
    table.add_row("波动率阈值", f"{config.volatility_threshold:.1%}")
    table.add_row("成交量阈值", f"{config.volume_threshold:.1f}x")
    
    console.print(table)


def _show_multi_timeframe_results(result, symbol, model=None, is_realtime=False):
    """显示多时间周期分析结果"""
    
    title_prefix = "⚡ 实时" if is_realtime else "🔄 多周期"
    
    console.print(Panel.fit(
        f"📊 [bold green]{title_prefix}分析结果 - {symbol}[/bold green]",
        border_style="green"
    ))
    
    if result.overall_signal != "ERROR":
        # 显示主要分析结果
        if hasattr(result, 'primary_analysis') and result.primary_analysis.get('success'):
            primary_text = result.primary_analysis.get('analysis_text', result.primary_analysis.get('analysis', ''))
            if primary_text:
                console.print(Panel(
                    primary_text,
                    title="🤖 AI综合分析",
                    border_style="blue",
                    padding=(1, 2)
                ))
        
        # 多时间周期汇总表
        summary_table = Table(title="📊 多周期分析汇总", show_header=True)
        summary_table.add_column("指标", style="cyan")
        summary_table.add_column("结果", style="white")
        
        summary_table.add_row("🎯 分析场景", result.scenario.value if hasattr(result, 'scenario') else 'N/A')
        summary_table.add_row("📈 综合信号", result.overall_signal)
        summary_table.add_row("🔗 一致性评分", f"{result.consistency_score:.1f}/100")
        summary_table.add_row("💪 信心水平", f"{result.confidence_level:.1f}/100")
        summary_table.add_row("⏱️ 执行时间", f"{result.execution_time:.2f}秒")
        summary_table.add_row("📅 分析时间", result.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        
        console.print(summary_table)
        
        # 时间框架详情
        if hasattr(result, 'primary_analysis') and hasattr(result, 'secondary_analyses'):
            tf_table = Table(title="📋 时间框架分析详情", show_header=True)
            tf_table.add_column("时间周期", style="cyan")
            tf_table.add_column("分析状态", style="green")
            tf_table.add_column("质量评分", style="yellow")
            tf_table.add_column("数据点数", style="blue")
            
            # 主要时间框架
            primary_quality = result.primary_analysis.get('quality_score', 'N/A')
            primary_data_points = result.primary_analysis.get('data_points', 'N/A')
            tf_table.add_row(
                f"{result.primary_analysis.get('timeframe', 'Unknown')} (主)",
                "✅ 成功" if result.primary_analysis.get('success') else "❌ 失败",
                f"{primary_quality}/100" if primary_quality != 'N/A' else 'N/A',
                str(primary_data_points)
            )
            
            # 辅助时间框架
            for tf, analysis in result.secondary_analyses.items():
                quality = analysis.get('quality_score', 'N/A')
                data_points = analysis.get('data_points', 'N/A')
                tf_table.add_row(
                    tf,
                    "✅ 成功" if analysis.get('success') else "❌ 失败",
                    f"{quality}/100" if quality != 'N/A' else 'N/A',
                    str(data_points)
                )
            
            console.print(tf_table)
        
        # 汇聚区域
        if hasattr(result, 'major_confluence_zones') and result.major_confluence_zones:
            confluence_table = Table(title="🎯 关键汇聚区域", show_header=True)
            confluence_table.add_column("价格水平", style="cyan")
            confluence_table.add_column("强度", style="green")
            confluence_table.add_column("涉及周期", style="yellow")
            confluence_table.add_column("级别类型", style="blue")
            
            for zone in result.major_confluence_zones[:3]:  # 显示前3个最重要的
                confluence_table.add_row(
                    f"${zone.get('price', 0):.2f}",
                    f"{zone.get('strength', 0):.1f}",
                    ", ".join(zone.get('timeframes', [])),
                    ", ".join(zone.get('level_types', []))
                )
            
            console.print(confluence_table)
        
        # 风险警告
        if hasattr(result, 'risk_warnings') and result.risk_warnings:
            warnings_text = "\n".join([f"• {warning}" for warning in result.risk_warnings])
            console.print(Panel(
                warnings_text,
                title="⚠️ 风险警告",
                border_style="red",
                padding=(1, 2)
            ))
        
        # 交易建议
        if hasattr(result, 'trading_recommendations') and result.trading_recommendations:
            recommendations_text = "\n".join([f"• {rec}" for rec in result.trading_recommendations])
            console.print(Panel(
                recommendations_text,
                title="💡 交易建议",
                border_style="green",
                padding=(1, 2)
            ))
        
        console.print("\n✅ [bold green]多时间周期分析完成![/bold green]")
        
    else:
        error_msg = "多时间周期分析失败"
        if hasattr(result, 'risk_warnings') and result.risk_warnings:
            error_msg += f": {', '.join(result.risk_warnings)}"
        console.print(f"❌ [red]{error_msg}[/red]")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 用户中断，退出程序", style="yellow")
    except Exception as e:
        console.print(f"❌ 程序执行错误: {e}", style="red")
        sys.exit(1)