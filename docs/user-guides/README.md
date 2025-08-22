# ETH永续合约LLM量价分析助手

基于OpenRouter API的多模型加密货币技术分析工具，专门验证大语言模型直接分析原始K线数据的可行性。

## 项目特色

- 🔥 **2025旗舰模型**: GPT-5、Claude Opus 4.1、Gemini 2.5 Pro、Grok-4等最新顶级模型
- 📊 **VPA分析**: 基于Anna Coulling量价分析理论的专业分析
- 🎯 **ETH永续合约**: 专注以太坊永续合约市场
- 📝 **4种数据格式**: CSV、文本、JSON、模式描述等不同输入格式
- ⚡ **实时数据**: 通过Binance API获取最新市场数据
- 🧪 **科学测试**: 系统性验证LLM分析能力和限制

## 快速开始

### 1. 环境设置

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置API密钥
cp .env.example .env
# 编辑 .env 文件，添加你的 OPENROUTER_API_KEY
```

### 2. 获取OpenRouter API Key

1. 访问 [OpenRouter.ai](https://openrouter.ai)
2. 注册账户并获取API密钥
3. 将密钥添加到 `.env` 文件中

### 3. 基础测试

```bash
# 运行可行性测试
python tests/test_feasibility.py
```

### 4. 单次分析

```bash
# 🔥 使用2025旗舰模型进行顶级分析
python main.py --symbol ETHUSDT --model gpt5-chat     # GPT-5 Chat (旗舰版)
python main.py --symbol ETHUSDT --model gpt5-mini     # GPT-5 Mini (推理版)
python main.py --symbol ETHUSDT --model claude-opus-41 # Claude Opus 4.1
python main.py --symbol ETHUSDT --model gemini-25-pro  # Gemini 2.5 Pro
python main.py --symbol ETHUSDT --model grok4          # Grok-4

# 经济高效选择
python main.py --symbol ETHUSDT --model gpt5-nano     # GPT-5 Nano (超轻量)
python main.py --symbol ETHUSDT --model gpt4o-mini    # GPT-4o Mini
python main.py --symbol ETHUSDT --model claude-haiku  # Claude Haiku

# 专项测试
python tests/test_flagship_2025.py        # 2025旗舰模型专项测试
python tests/test_2025_models.py         # 全模型对比测试
```

## 测试阶段

### 阶段1: 基础可行性测试 ✅
验证LLM能否理解OHLCV数据格式，测试数据获取和基础分析功能。

### 阶段2: 格式优化测试 ✅
系统性比较4种数据格式在VPA分析质量上的效果：
- **Pattern**: 94.0/100分，3261 tokens（🏆最佳综合性能）
- **CSV**: 92.5/100分，3954 tokens  
- **JSON**: 92.5/100分，10297 tokens（最详细但耗token）
- **Text**: 91.8/100分，3424 tokens（最快响应18.8s）

**关键发现**：Pattern格式在保持专业分析质量的同时，token消耗最少，是最优选择。

### 阶段3: 滑动窗口策略 🔮
解决token限制问题，实现长时间序列分析。

### 阶段4: 混合分析模式 🔮
结合原始数据和预计算技术指标，多模型对比分析。

## 核心组件

### 数据获取 (`data/`)
- `BinanceFetcher`: Binance API数据获取
- `DataProcessor`: 技术指标计算和VPA分析

### AI分析 (`ai/`)
- `OpenRouterClient`: 多模型API客户端
- `AnalysisEngine`: 分析引擎和结果整合

### 数据格式化 (`formatters/`)
- `DataFormatter`: 4种LLM输入格式转换

## VPA分析支持

基于Anna Coulling的Volume Price Analysis理论：

- ✅ 量价关系验证
- ✅ 异常成交量识别  
- ✅ 市场操控迹象检测
- ✅ Accumulation/Distribution信号
- ✅ VPA蜡烛图形态分析

## 注意事项

⚠️ **这是一个实验性项目**，用于研究LLM在金融分析中的应用，不构成投资建议。

⚠️ **API费用**: 使用OpenRouter会产生费用，建议先进行小规模测试。

⚠️ **数据延迟**: 免费数据源可能有延迟，实盘交易需要考虑数据时效性。

## 开发状态

- [x] 项目架构设计
- [x] 数据获取模块  
- [x] OpenRouter API集成
- [x] 4种数据格式实现
- [x] 基础测试框架
- [x] **2025最新模型集成** (15+ models)
- [x] **性能和成本测试框架**
- [x] **阶段2格式优化测试** (Pattern格式获胜)
- [ ] 滑动窗口实现
- [ ] 混合分析模式
- [ ] 结果评估体系

## 贡献

欢迎提交Issue和Pull Request！特别是：

- 新的数据格式想法
- 更多LLM模型支持
- 分析准确性评估方法
- 性能优化建议

## 许可证

MIT License - 详见 LICENSE 文件