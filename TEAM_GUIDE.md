# AI-Trader 团队协作开发指南

**版本**: v1.3.0  
**更新日期**: 2025-08-30  
**适用对象**: 新加入的开发团队成员

---

## 🏗️ 项目当前状态

### 系统概况
AI-Trader 是一个专业的AI驱动加密货币分析系统，当前处于 **v1.3.0 生产就绪状态**。

**核心特色**:
- ✅ 直接分析原始OHLCV数据，无需传统技术指标
- ✅ 智能Token管理，自动模型降级机制  
- ✅ 4个高端AI模型：GPT-5, Claude-Opus-41, Gemini-25-Pro, Grok4
- ✅ Al Brooks价格行为分析，质量评分80+/100
- ✅ 完整的质量验证和测试框架

### 最新重要更新 (v1.3.0)
- **智能Token管理**: 解决Token超限问题，98%+分析成功率
- **模型精简**: 从20+模型精简至4个顶级模型
- **架构优化**: 增强错误处理和自动恢复机制
- **文档完善**: 全面的开发和架构文档

---

## 🚀 快速开始

### 1. 环境设置
```bash
# 克隆项目
git clone https://github.com/shukehi/ai-trader.git
cd ai-trader

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置API密钥
cp .env.example .env
# 编辑 .env 添加 OPENROUTER_API_KEY
```

### 2. 系统验证
```bash
# 验证配置
python -c "from config import Settings; Settings.validate()"

# 测试核心组件  
python -c "from ai import RawDataAnalyzer; print('✅ AI分析器就绪')"
python -c "from data import BinanceFetcher; print('✅ 数据获取就绪')"

# 运行质量测试
pytest -q
```

### 3. 基础使用测试
```bash
# 快速分析测试
python main.py analyze --symbol ETHUSDT --limit 50

# 查看可用功能
python main.py methods
python main.py config
```

---

## 🏛️ 核心架构理解

### 数据流架构
```
Binance API → BinanceFetcher → RawDataAnalyzer → OpenRouterClient → AI模型
    ↓              ↓                ↓               ↓            ↓
  实时数据       格式化处理        智能分析       Token管理    分析结果
```

### 关键组件职责

#### 1. AI分析层 (`ai/`)
- **RawDataAnalyzer**: 主分析引擎，质量评分系统
- **OpenRouterClient**: LLM API客户端，智能Token管理
- **MultiTimeframeAnalyzer**: 多时间框架并行分析
- **AnalysisEngine**: 传统分析接口（部分流程仍在使用）

#### 2. 数据层 (`data/`)
- **BinanceFetcher**: 市场数据获取，自动格式转换
- **BinanceWebSocket**: 实时数据流
- **DataFormatter**: 数据格式化和优化

#### 3. 提示系统 (`prompts/`)
- **PromptManager**: 外部提示词管理
- **price_action/**: Al Brooks方法论提示词
- 术语映射和质量评估系统

#### 4. 配置系统 (`config/`)
- **Settings**: 核心配置管理
- 4个高端模型配置
- Token限制和验证规则

---

## 🛠️ 开发工作流

### 代码修改流程

1. **功能开发前**:
```bash
git checkout -b feature/your-feature-name
python main.py config  # 验证当前配置
pytest -q  # 确保现有测试通过
```

2. **开发过程中**:
```bash
# 测试单个组件
python -c "from ai import RawDataAnalyzer; # your test code"

# 测试分析功能
python main.py analyze --verbose --symbol ETHUSDT --limit 50

# Token使用监控
python main.py analyze --verbose | grep -E "(token|Token)"
```

3. **提交前验证**:
```bash
pytest -q  # Brooks质量合规测试
python -c "from config import Settings; Settings.validate()"  # 配置验证
python main.py methods  # 功能完整性检查
```

### 分支策略
- **main**: 生产就绪代码，所有提交必须通过测试
- **feature/**: 新功能开发分支
- **hotfix/**: 紧急修复分支
- **docs/**: 文档更新分支

### 提交规范
```bash
# 功能提交
git commit -m "feat: 简短描述

详细说明:
- 具体变更内容
- 影响的组件
- 测试验证情况"

# 修复提交
git commit -m "fix: 问题描述

- 问题根源分析
- 解决方案
- 验证方法"
```

---

## 🔧 常见开发任务

### 1. 添加新的AI模型

```python
# 1. 在 config/settings.py 中添加模型
MODELS = {
    'new-model': 'provider/model-id',  # 添加到这里
    # ... 其他模型
}

TOKEN_LIMITS = {
    'new-model': 128000,  # 添加Token限制
    # ... 其他限制
}

# 2. 更新降级层次 (ai/openrouter_client.py)
def _get_fallback_models(self, current_model: str) -> List[str]:
    model_capacities = [
        ('new-model', 256000),  # 根据容量插入正确位置
        ('gemini-25-pro', 2097152),
        # ... 其他模型
    ]

# 3. 测试验证
python main.py analyze --model new-model --limit 50
```

### 2. 优化Token使用

当分析失败或Token使用过高时:

```python
# 检查Token计算逻辑 (ai/openrouter_client.py)
def _estimate_tokens(self, text: str) -> int:
    # 调整估算算法
    pass

# 调整安全边距
safe_model_limit = int(max_model_tokens * 0.8)  # 可调整比例

# 优化响应空间分配
response_ratios = {
    'complete': 0.30,  # 可调整比例
    # ...
}
```

### 3. 改进分析质量

```python
# 1. 更新提示词 (prompts/price_action/)
# 编辑相应的 .txt 文件

# 2. 调整质量评分 (prompts/prompt_manager.py)
def _evaluate_al_brooks_quality(self, analysis: str) -> int:
    # 修改评分逻辑
    pass

# 3. 更新术语映射
BROOKS_TERM_MAPPING = {
    # 添加新的术语映射
}

# 4. 测试质量改进
pytest tests/test_brooks_quality.py -v
```

### 4. 添加新的分析方法

```bash
# 1. 创建提示词文件
mkdir prompts/new_method/
echo "新方法的提示词内容" > prompts/new_method/analysis.txt

# 2. 更新PromptManager (prompts/prompt_manager.py)
def get_method_info(self, method_name: str):
    # 添加新方法的映射
    pass

# 3. 添加质量评估器
def _evaluate_new_method_quality(self, analysis: str) -> int:
    # 实现质量评估逻辑
    pass

# 4. 更新测试
# 在 tests/ 目录添加相应测试文件
```

---

## 🐛 故障排查指南

### Token相关问题

**问题**: "maximum context length exceeded"
```bash
# 1. 检查Token限制配置
python -c "from config import Settings; print(Settings.TOKEN_LIMITS)"

# 2. 监控Token使用
python main.py analyze --verbose --symbol ETHUSDT --limit 50

# 3. 测试降级机制
python main.py analyze --symbol ETHUSDT --limit 200 --verbose
```

**解决思路**:
- 检查模型的实际Token限制
- 验证Token估算算法准确性
- 测试自动降级是否正常工作

### 分析质量问题

**问题**: 质量评分低于预期
```bash
# 1. 详细分析输出
python main.py analyze --verbose --method al-brooks

# 2. 检查术语映射
python -c "from prompts import PromptManager; pm = PromptManager(); print(pm.BROOKS_TERM_MAPPING)"

# 3. 运行质量测试
pytest tests/test_brooks_quality.py -v -s
```

### API连接问题

**问题**: OpenRouter API调用失败
```bash
# 1. 验证API密钥
python -c "from config import Settings; print('Key exists:', bool(Settings.OPENROUTER_API_KEY))"

# 2. 测试网络连接
python -c "import requests; r = requests.get('https://openrouter.ai/api/v1/models'); print(r.status_code)"

# 3. 检查模型可用性
python -c "from ai import OpenRouterClient; client = OpenRouterClient(); print(client.models)"
```

---

## 📊 性能监控

### 关键指标监控

**分析成功率**:
```bash
# 运行批量测试统计成功率
for i in {1..10}; do python main.py analyze --symbol ETHUSDT --limit 50; done
```

**Token使用效率**:
```bash
# 监控Token使用情况
python main.py analyze --verbose 2>&1 | grep -E "输入token|最大响应token|总计"
```

**分析质量**:
```bash
# 质量评分统计
python main.py analyze --method al-brooks --verbose | grep "质量评分"
```

### 性能基准
- **目标成功率**: >98%
- **Token使用率**: <50% (安全边际)
- **响应时间**: 5-15秒
- **质量评分**: >70/100

---

## 📋 测试策略

### 单元测试
```bash
pytest tests/test_brooks_quality.py -v  # Brooks质量测试
```

### 集成测试
```bash
python main.py analyze --symbol ETHUSDT --limit 120  # 完整流程测试
python main.py multi-analyze --symbol ETHUSDT --timeframes "1h,4h"  # 多时间框架测试
```

### 回归测试
```bash
# 每次重要更新后运行
pytest -q  # 全部测试
python -c "from config import Settings; Settings.validate()"  # 配置验证
```

---

## 📚 重要文档

### 必读文档
- **CLAUDE.md**: 完整架构和开发指南
- **CHANGELOG_v1.3.0.md**: 最新版本详细变更
- **README.md**: 项目概览和快速开始

### 技术文档
- **CLI_USAGE.md**: 命令行使用指南
- **.env.example**: 配置模板
- **prompts/**: 分析方法提示词库

### API文档
- [OpenRouter API](https://openrouter.ai/docs)
- [Binance API](https://binance-docs.github.io/apidocs/)

---

## ⚠️ 注意事项

### 安全相关
- **API密钥**: 绝对不能提交到代码库
- **敏感信息**: 使用环境变量管理
- **网络安全**: 注意API调用频率限制

### 代码质量
- **测试覆盖**: 新功能必须包含测试
- **文档更新**: 重要变更必须更新文档
- **代码审查**: 重要提交需要审查

### 版本管理
- **语义版本**: 遵循 semver 规范
- **向后兼容**: 谨慎处理破坏性变更
- **发布流程**: 标签 + 文档 + 测试

---

## 🤝 团队协作

### 沟通渠道
- **代码审查**: GitHub Pull Request
- **问题跟踪**: GitHub Issues
- **技术讨论**: 代码注释和文档

### 贡献流程
1. Fork 项目
2. 创建功能分支
3. 开发和测试
4. 提交 Pull Request
5. 代码审查
6. 合并到主分支

### 获取帮助
- 查看 GitHub Issues 中的已知问题
- 阅读详细的错误日志和堆栈跟踪
- 参考 CLAUDE.md 中的故障排查部分

---

**祝开发愉快！** 🚀

*如有任何问题，请随时创建 GitHub Issue 或查阅相关文档。*