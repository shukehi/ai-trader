# VS Code远程SSH开发环境配置指南

## 概述

本指南详细说明如何配置VS Code远程SSH开发环境，实现直接在VPS上进行AI交易系统的开发和调试。

## 配置优势

- **实时日志分析**：直接访问生产环境日志文件
- **即时问题修复**：在真实环境中调试和验证
- **无环境差异**：避免本地与生产环境不一致
- **Claude Code集成**：支持AI助手直接访问远程文件系统

## 前置条件

- 本地安装VS Code
- VPS已部署AI交易系统
- VPS具有SSH访问权限
- 基本的Linux命令行操作知识

## 阶段1：VPS SSH环境配置

### 1.1 创建开发专用用户

在VPS上执行以下命令创建开发用户：

```bash
# 创建开发用户
sudo adduser ai-trader-dev

# 添加到必要的用户组
sudo usermod -aG sudo ai-trader-dev
sudo usermod -aG ai-trader ai-trader-dev

# 设置用户密码（可选，推荐使用密钥认证）
sudo passwd ai-trader-dev
```

### 1.2 配置项目目录权限

```bash
# 设置项目目录权限
sudo chown -R ai-trader:ai-trader /opt/ai-trader
sudo chmod -R 775 /opt/ai-trader

# 为开发用户添加ACL权限（如果系统支持）
sudo setfacl -R -m u:ai-trader-dev:rwx /opt/ai-trader
sudo setfacl -R -d -m u:ai-trader-dev:rwx /opt/ai-trader

# 或者简单地将用户添加到ai-trader组
sudo usermod -aG ai-trader ai-trader-dev
```

### 1.3 验证权限设置

```bash
# 切换到开发用户验证权限
sudo -u ai-trader-dev ls -la /opt/ai-trader/
sudo -u ai-trader-dev touch /opt/ai-trader/test_write_permission.txt
sudo -u ai-trader-dev rm /opt/ai-trader/test_write_permission.txt
```

## 阶段2：SSH密钥配置

### 2.1 生成SSH密钥对（本地）

在本地机器上生成SSH密钥：

```bash
# 生成ED25519密钥对（推荐）
ssh-keygen -t ed25519 -C "ai-trader-remote-dev" -f ~/.ssh/ai-trader-dev

# 或使用RSA密钥（兼容性更好）
ssh-keygen -t rsa -b 4096 -C "ai-trader-remote-dev" -f ~/.ssh/ai-trader-dev
```

### 2.2 上传公钥到VPS

```bash
# 方法1：使用ssh-copy-id（推荐）
ssh-copy-id -i ~/.ssh/ai-trader-dev.pub ai-trader-dev@YOUR_VPS_IP

# 方法2：手动上传
cat ~/.ssh/ai-trader-dev.pub | ssh ai-trader-dev@YOUR_VPS_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 2.3 测试SSH连接

```bash
# 测试密钥认证连接
ssh -i ~/.ssh/ai-trader-dev ai-trader-dev@YOUR_VPS_IP

# 验证可以访问项目目录
ssh -i ~/.ssh/ai-trader-dev ai-trader-dev@YOUR_VPS_IP "ls -la /opt/ai-trader/"
```

## 阶段3：VS Code Remote-SSH配置

### 3.1 安装必要扩展

在VS Code中安装以下扩展：

- **Remote - SSH**
- **Remote - SSH: Editing Configuration Files**
- **Remote Explorer**

### 3.2 配置SSH连接

创建或编辑SSH配置文件（~/.ssh/config）：

```
Host ai-trader-vps
    HostName YOUR_VPS_IP
    User ai-trader-dev
    IdentityFile ~/.ssh/ai-trader-dev
    Port 22
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ConnectTimeout 30
```

### 3.3 建立远程连接

1. 打开VS Code
2. 按 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (Mac)
3. 输入 "Remote-SSH: Connect to Host"
4. 选择 "ai-trader-vps"
5. 选择平台类型：Linux
6. 等待连接建立

### 3.4 打开项目目录

连接成功后：

1. 点击 "Open Folder"
2. 输入路径：`/opt/ai-trader`
3. 点击 "OK"

## 阶段4：远程开发环境优化

### 4.1 安装远程扩展

在远程环境中安装以下扩展：

- **Python** (Microsoft)
- **Pylint**
- **GitLens**
- **Thunder Client** (用于API测试)
- **JSON** (内置但确保启用)

### 4.2 配置Python解释器

1. 按 `Ctrl+Shift+P`
2. 输入 "Python: Select Interpreter"
3. 选择 `/opt/ai-trader/venv/bin/python`

### 4.3 验证环境

在远程终端中执行：

```bash
# 激活虚拟环境
cd /opt/ai-trader
source venv/bin/activate

# 验证Python环境
which python
python --version
pip list | grep ccxt

# 验证项目可以运行
python -c "from config import Settings; Settings.validate()"
```

## 阶段5：开发调试配置

### 5.1 VS Code调试配置

创建 `.vscode/launch.json` 文件：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "AI Trader - Quick Analysis",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "args": [
                "--symbol", "ETHUSDT",
                "--model", "gpt5-mini",
                "--mode", "quick"
            ],
            "console": "integratedTerminal",
            "cwd": "/opt/ai-trader",
            "env": {
                "PYTHONPATH": "/opt/ai-trader"
            }
        },
        {
            "name": "AI Trader - Trading Mode",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "args": [
                "--enable-trading",
                "--signal-only",
                "--symbol", "ETHUSDT"
            ],
            "console": "integratedTerminal",
            "cwd": "/opt/ai-trader"
        },
        {
            "name": "Test Suite",
            "type": "python",
            "request": "launch",
            "program": "-m",
            "args": ["pytest", "tests/", "-v"],
            "console": "integratedTerminal",
            "cwd": "/opt/ai-trader"
        }
    ]
}
```

### 5.2 VS Code工作区配置

创建 `.vscode/settings.json` 文件：

```json
{
    "python.defaultInterpreterPath": "/opt/ai-trader/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "files.watcherExclude": {
        "**/venv/**": true,
        "**/logs/**": true,
        "**/data/cache/**": true
    },
    "terminal.integrated.cwd": "/opt/ai-trader"
}
```

## 阶段6：实际使用工作流

### 6.1 日常开发流程

```bash
# 1. 连接到远程环境
# VS Code -> Remote-SSH: Connect to Host -> ai-trader-vps

# 2. 打开项目终端
cd /opt/ai-trader
source venv/bin/activate

# 3. 拉取最新代码
git pull origin main

# 4. 进行开发工作
# 编辑代码、调试、测试等

# 5. 提交更改
git add .
git commit -m "远程开发：修复XXX问题"
git push origin main
```

### 6.2 实时监控设置

在VS Code终端中设置多个面板：

```bash
# 终端1：系统监控
watch -n 5 './manage.sh status'

# 终端2：日志监控
tail -f logs/ai/analysis_$(date +%Y%m%d).log

# 终端3：交易监控（如果启用交易）
tail -f logs/trading/trades_$(date +%Y%m%d).csv

# 终端4：开发调试
python main.py --enable-validation --symbol ETHUSDT
```

### 6.3 Claude Code协作

配置完成后，Claude Code可以：

- 直接读取远程日志文件分析问题
- 实时修改代码并验证
- 执行远程命令进行调试
- 监控系统状态和交易情况

## 安全考虑

### 访问控制

- 使用专门的开发用户，不共享root权限
- 定期轮换SSH密钥
- 限制SSH访问IP（可选）

### 网络安全

```bash
# 配置防火墙（可选）
sudo ufw allow from YOUR_IP_ADDRESS to any port 22

# 禁用密码认证（仅使用密钥）
sudo nano /etc/ssh/sshd_config
# 设置：PasswordAuthentication no
sudo systemctl restart ssh
```

### 数据备份

```bash
# 开发前备份重要配置
cp -r /opt/ai-trader/.env /opt/ai-trader/.env.backup
cp -r /opt/ai-trader/logs /tmp/logs_backup
```

## 故障排除

### 常见问题

**连接超时**
```bash
# 检查VPS SSH服务状态
sudo systemctl status ssh
sudo systemctl start ssh

# 检查防火墙设置
sudo ufw status
```

**权限问题**
```bash
# 重新设置目录权限
sudo chown -R ai-trader:ai-trader /opt/ai-trader
sudo chmod -R 775 /opt/ai-trader
```

**Python环境问题**
```bash
# 重新创建虚拟环境
cd /opt/ai-trader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 验证配置

使用验证脚本确认配置成功：

```bash
# 下载并运行验证脚本
curl -o verify_remote_setup.py https://raw.githubusercontent.com/shukehi/ai-trader/main/scripts/verify_remote_setup.py
python verify_remote_setup.py
```

## 下一步

配置完成后，参考以下文档：
- `docs/user-guides/README.md` - 基本使用指南
- `docs/technical/cli.md` - 命令行参考
- `docs/user-guides/TRADING_README.md` - 交易系统使用