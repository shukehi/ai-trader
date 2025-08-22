# 远程开发工作流程指南

## 概述

本指南详细介绍如何使用配置好的VS Code远程SSH环境进行AI交易系统的日常开发工作。

## 前提条件

- 已完成远程SSH环境配置（参考 `docs/setup/REMOTE_SSH_SETUP.md`）
- VS Code已安装Remote-SSH扩展
- SSH连接配置正确
- VPS上的开发环境已就绪

## 日常开发工作流程

### 1. 连接到远程开发环境

#### 启动VS Code远程连接
```bash
# 方法1：通过VS Code界面
# 1. 打开VS Code
# 2. 按 Ctrl+Shift+P (Windows/Linux) 或 Cmd+Shift+P (Mac)
# 3. 输入 "Remote-SSH: Connect to Host"
# 4. 选择 "ai-trader-vps"
# 5. 等待连接建立

# 方法2：通过命令行（如果配置了code命令）
code --remote ssh-remote+ai-trader-vps /opt/ai-trader
```

#### 验证连接状态
```bash
# 在VS Code终端中运行
pwd                          # 应显示 /opt/ai-trader
whoami                       # 应显示 ai-trader-dev
source venv/bin/activate     # 激活Python环境
python -c "from config import Settings; Settings.validate()"  # 验证配置
```

### 2. 代码开发和编辑

#### 项目结构导航
- **核心模块**: `ai/`, `data/`, `trading/`, `formatters/`
- **配置文件**: `config/`, `.env`, `trading_config.json`
- **测试代码**: `tests/`
- **示例脚本**: `examples/`
- **文档**: `docs/`
- **日志文件**: `logs/ai/`, `logs/trading/`, `logs/system/`

#### 实时代码编辑最佳实践
```python
# 1. 使用VS Code的IntelliSense和代码补全
# 2. 利用Python扩展的语法检查
# 3. 使用Git集成进行版本控制
# 4. 实时查看日志文件了解系统状态
```

### 3. 调试和测试工作流程

#### 使用VS Code调试器
```bash
# 1. 设置断点：在代码行号左侧点击
# 2. 选择调试配置：
#    - "AI Trader - Quick Analysis" - 快速VPA分析
#    - "AI Trader - Trading Mode" - 交易模式调试
#    - "Test Suite - Feasibility" - 运行可行性测试
# 3. 按F5启动调试
# 4. 使用调试控制台查看变量和执行状态
```

#### 运行测试套件
```bash
# 使用VS Code任务
# Ctrl+Shift+P -> "Tasks: Run Task" -> 选择测试任务

# 或直接在终端运行
source venv/bin/activate

# 基础功能测试
python tests/test_feasibility.py

# 多模型验证测试（不消耗API）
RUN_INTEGRATION_TESTS=false python tests/test_multi_model_validation.py

# VPA增强测试
python tests/test_vpa_enhancement.py

# 模拟交易测试
python tests/test_simulated_trading.py
```

### 4. 实时监控和日志分析

#### 多终端监控设置
```bash
# 终端1：系统状态监控
watch -n 5 './manage.sh status'

# 终端2：AI分析日志实时监控
tail -f logs/ai/analysis_$(date +%Y%m%d).log

# 终端3：交易日志实时监控（如果启用交易）
tail -f logs/trading/trades_$(date +%Y%m%d).csv

# 终端4：系统性能监控
tail -f logs/system/performance_*.txt
```

#### 日志分析工作流程
```bash
# 1. 实时查看最新日志
ls -la logs/ai/ | tail -5
ls -la logs/trading/ | tail -5

# 2. 分析特定时间段的日志
grep "2025-08-22 10:" logs/ai/analysis_20250822.log

# 3. 查看错误日志
grep -i "error\|exception" logs/ai/analysis_*.log

# 4. 分析交易性能
python examples/log_optimization.py
```

### 5. 功能开发和验证

#### 新功能开发工作流程
```bash
# 1. 创建功能分支（可选）
git checkout -b feature/new-functionality

# 2. 开发新功能
# - 编辑相关模块
# - 添加测试用例
# - 更新文档

# 3. 本地验证
python -c "from your_module import YourClass; test = YourClass(); print('功能正常')"

# 4. 运行相关测试
python -m pytest tests/test_your_module.py -v

# 5. 集成测试
python main.py --symbol ETHUSDT --mode quick  # 快速验证
```

#### AI模型测试和优化
```bash
# 测试不同AI模型性能
python main.py --symbol ETHUSDT --model gpt5-mini --enable-validation
python main.py --symbol ETHUSDT --model gemini-flash --fast-validation
python main.py --symbol ETHUSDT --model gpt4o-mini --ultra-economy

# 成本分析
python utils/cost_controller.py

# 性能基准测试
python tests/test_format_optimization.py  # 格式优化测试
python tests/test_flagship_2025.py        # 旗舰模型测试
```

### 6. 生产部署和监控

#### 部署前验证
```bash
# 1. 运行完整测试套件
python tests/test_feasibility.py
python tests/test_multi_model_validation.py
python tests/test_vpa_enhancement.py

# 2. 验证配置
python scripts/verify_remote_setup.py --detailed

# 3. 系统健康检查
python monitoring/production_monitor.py --once
```

#### 生产监控工作流程
```bash
# 1. 启动生产监控
python monitoring/production_monitor.py &

# 2. 定期健康检查
./manage.sh health

# 3. 查看系统状态
./manage.sh status

# 4. 备份关键数据
bash scripts/backup_system.sh
```

### 7. Claude Code协作工作流程

#### 协作场景1：问题诊断
```bash
# 1. Claude读取日志文件
# Claude可以直接: Read logs/ai/analysis_20250822.log
# 2. 分析问题原因
# 3. 提供解决方案
# 4. 直接修改代码: Edit affected_file.py
# 5. 验证修复效果
```

#### 协作场景2：功能开发
```bash
# 1. Claude分析需求
# Read main.py, config/settings.py
# 2. 设计实现方案
# 3. 编写代码: Edit/MultiEdit相关文件
# 4. 创建测试用例
# 5. 运行验证: Bash python tests/test_new_feature.py
```

#### 协作场景3：性能优化
```bash
# 1. Claude分析性能日志
# Read logs/system/performance_*.txt
# 2. 识别瓶颈
# 3. 优化代码
# 4. 基准测试验证
# 5. 更新文档
```

### 8. Git版本控制工作流程

#### 标准Git工作流程
```bash
# 1. 同步最新代码
git status
git pull origin main

# 2. 创建功能分支（可选）
git checkout -b feature/optimization-improvements

# 3. 进行开发工作
# 编辑代码、测试、调试

# 4. 提交更改
git add .
git commit -m "feat: 优化VPA分析性能

- 改进VSA计算算法效率
- 优化多时间框架分析
- 增加缓存机制减少API调用

Tested: ✅ 通过所有VPA增强测试
Performance: ⚡ 分析速度提升35%"

# 5. 推送到远程
git push origin feature/optimization-improvements

# 或直接推送到main（小改动）
git push origin main
```

#### Git协作最佳实践
- **提交消息规范**: 使用feat/fix/docs/test等前缀
- **频繁提交**: 小改动及时提交
- **描述清晰**: 包含测试结果和性能影响
- **分支管理**: 大功能使用单独分支开发

### 9. 环境维护和更新

#### 定期维护任务
```bash
# 每日维护
./manage.sh health                    # 系统健康检查
python utils/cost_controller.py      # 检查API使用成本
git pull origin main                  # 同步最新代码

# 每周维护
pip list --outdated                   # 检查过期依赖
bash scripts/backup_system.sh        # 创建系统备份
python scripts/verify_remote_setup.py --detailed  # 完整环境验证

# 每月维护
pip install --upgrade -r requirements.txt  # 更新依赖
./manage.sh update                    # 系统更新
```

#### 问题排查工作流程
```bash
# 1. 检查系统状态
./manage.sh status
python scripts/verify_remote_setup.py

# 2. 查看错误日志
grep -i "error\|exception" logs/*/*.log | tail -20

# 3. 测试基础功能
python -c "from config import Settings; Settings.validate()"
python tests/test_feasibility.py

# 4. 网络连接测试
python test_rest_vpa.py

# 5. 恢复策略
bash scripts/disaster_recovery.sh --check
```

## 高级工作流程

### 多环境开发
```bash
# 开发环境配置
Host ai-trader-dev
    HostName DEV_SERVER_IP
    User ai-trader-dev

# 测试环境配置  
Host ai-trader-test
    HostName TEST_SERVER_IP
    User ai-trader-test

# 生产环境配置
Host ai-trader-prod
    HostName PROD_SERVER_IP
    User ai-trader
```

### 自动化工作流程
```bash
# 自动化测试脚本
#!/bin/bash
echo "🚀 启动自动化测试流程"
source venv/bin/activate
python tests/test_feasibility.py
python tests/test_multi_model_validation.py
python tests/test_vpa_enhancement.py
echo "✅ 所有测试完成"

# 自动化部署脚本（集成到VS Code任务）
{
    "label": "Auto Deploy",
    "type": "shell",
    "command": "./scripts/auto_deploy.sh",
    "group": "build"
}
```

### 性能监控和优化
```bash
# 实时性能监控
python -m cProfile -o profile_output.prof main.py --symbol ETHUSDT --mode quick
python -c "import pstats; p = pstats.Stats('profile_output.prof'); p.sort_stats('cumulative').print_stats(10)"

# 内存使用监控
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

## 故障排除指南

### 常见问题和解决方案

#### SSH连接问题
```bash
# 问题：连接超时
# 解决：检查网络和防火墙设置
ping YOUR_VPS_IP
telnet YOUR_VPS_IP 22

# 问题：权限被拒绝
# 解决：重新配置SSH密钥
ssh-keygen -t ed25519 -C "ai-trader-dev" -f ~/.ssh/ai-trader-dev
ssh-copy-id -i ~/.ssh/ai-trader-dev.pub ai-trader-dev@YOUR_VPS_IP
```

#### VS Code远程扩展问题
```bash
# 清除VS Code远程缓存
rm -rf ~/.vscode-server/
# 重新连接VS Code

# 重新安装远程扩展
# VS Code -> Extensions -> Remote - SSH -> Reload
```

#### Python环境问题
```bash
# 重建虚拟环境
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### API连接问题
```bash
# 检查API密钥配置
cat .env | grep OPENROUTER_API_KEY

# 测试API连接
python -c "
from ai.openrouter_client import OpenRouterClient
client = OpenRouterClient()
print('API连接正常' if client else 'API连接失败')
"
```

## 最佳实践总结

### 开发效率优化
- **多终端使用**: 同时监控不同类型的日志
- **快捷键熟练**: 提高VS Code操作效率
- **模板复用**: 使用调试配置和任务模板
- **增量开发**: 小步快跑，频繁测试验证

### 安全性考虑
- **定期密钥轮换**: 每月更新SSH密钥
- **权限最小化**: 只给必要的系统权限
- **代码审查**: 重要更改前进行代码审查
- **备份策略**: 定期备份配置和代码

### 性能优化
- **资源监控**: 定期检查CPU、内存使用
- **网络优化**: 使用compression和连接复用
- **缓存策略**: 合理使用数据缓存
- **并行处理**: 利用多线程和异步处理

### 协作效率
- **文档同步**: 及时更新开发文档
- **问题记录**: 记录和分享解决方案
- **知识分享**: 定期分享最佳实践
- **工具标准化**: 统一开发环境和工具

## 总结

通过遵循这个工作流程，你可以：
- 🚀 **高效开发**: 利用远程环境的强大计算资源
- 🔍 **实时调试**: 直接在生产环境中调试问题
- 📊 **数据洞察**: 实时访问交易和分析日志
- 🤖 **AI协作**: 与Claude Code无缝协作开发
- 🛡️ **风险控制**: 在真实环境中测试和验证

记住，远程开发的核心优势是能够直接在生产环境中工作，这既是优势也是责任。始终保持代码质量和系统稳定性的高标准。