# AI-Trader CLI Usage Guide (Typer + Rich)

现代化的命令行界面，使用 Typer + Rich 构建，提供美观和用户友好的交互体验。

## 🚀 主要命令

### 分析命令
```bash
# 基本分析
python main.py analyze

# 自定义参数分析
python main.py analyze --symbol BTCUSDT --model claude --analysis-type enhanced

# 使用短参数
python main.py analyze -s ETHUSDT -m gemini-flash -a complete -l 100

# 专业分析方法
python main.py analyze --method volume-analysis-vpa-classic
python main.py analyze --method ict-concepts-fair-value-gaps
python main.py analyze --method price-action-trend-analysis
```

### 工具命令
```bash
# 查看所有分析方法
python main.py methods

# 配置管理和测试
python main.py config

# 快速演示
python main.py demo

# 查看帮助
python main.py --help
python main.py analyze --help
```

## 🎨 Rich CLI 特性

### 美观的显示效果
- ✅ **彩色输出**: 成功(绿色)、错误(红色)、信息(蓝色)
- 📊 **格式化表格**: 数据以表格形式展示，易于阅读
- 🎯 **面板显示**: 重要信息以面板形式突出显示
- ⏳ **进度条**: 实时显示分析进度和耗时

### 交互体验
- 🤖 **智能提示**: 用户友好的交互式确认
- 📋 **结构化输出**: 清晰的信息层次和布局
- 🎮 **演示模式**: 一键体验完整功能

## 📊 输出示例

### 分析过程显示
```
🤖 AI-Trader v2.0
专业的AI直接分析交易系统
┌─────────────────────────────────────┐
│ ✅ API配置验证成功                    │
└─────────────────────────────────────┘

📊 分析配置
┌──────────┬────────────┐
│ 参数     │ 值         │
├──────────┼────────────┤
│ 交易对   │ ETHUSDT    │
│ 时间框架 │ 1h         │
│ AI模型   │ claude     │
└──────────┴────────────┘

📊 正在获取市场数据... ⠋
✅ 成功获取 50 条数据

🧠 AI分析进行中... ━━━━━━━━━━ 100% 0:00:15
✅ 处理结果...
```

### 结果展示
```
📊 ETHUSDT AI分析结果
┌────────────────────────────────────────┐
│ 🤖 AI分析报告                           │
│                                        │
│ 基于当前ETHUSDT价格行为和成交量分析...   │
│ [详细的AI分析内容]                      │
└────────────────────────────────────────┘

📈 分析指标
┌─────────┬──────────┐
│ 指标    │ 值       │
├─────────┼──────────┤
│ 质量评分 │ 85/100   │
│ 分析耗时 │ 12.3秒   │
│ 数据点数 │ 50       │
└─────────┴──────────┘

✅ 分析完成!
```

## 🔧 参数说明

### analyze 命令参数
- `--symbol, -s`: 交易对符号 (默认: ETHUSDT)
- `--timeframe, -t`: 时间周期 (默认: 1h)
- `--limit, -l`: K线数据数量 (默认: 50)
- `--model, -m`: AI模型 (默认: gemini-flash)
- `--analysis-type, -a`: 分析类型 (默认: complete)
- `--method`: 专业分析方法 (可选)
- `--raw`: 使用原始数据分析器 (默认: True)
- `--verbose, -v`: 显示详细日志

### 可用的分析方法
- **Volume Analysis**: `volume-analysis-vpa-classic`, `volume-analysis-vsa-coulling`
- **ICT Concepts**: `ict-concepts-fair-value-gaps`, `ict-concepts-liquidity-zones`, `ict-concepts-order-blocks`
- **Price Action**: `price-action-support-resistance`, `price-action-trend-analysis`

## 💡 使用建议

1. **首次使用**: 运行 `python main.py config` 验证配置
2. **快速体验**: 使用 `python main.py demo` 进行演示
3. **查看方法**: 使用 `python main.py methods` 了解所有分析方法
4. **生产使用**: 使用 `claude` 或 `gpt4o-mini` 模型获得最佳分析质量
5. **开发测试**: 使用 `gemini-flash` 模型快速测试

---
🤖 **AI-Trader** - 现代化CLI界面让AI直接分析更加美观和易用！