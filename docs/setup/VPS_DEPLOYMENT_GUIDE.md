# 🚀 AI Trader VPS 部署完整指南

> **完整的 VPS 生产环境部署教程 - 从零开始到 7x24 稳定运行**

## 📋 部署概览

### 🎯 部署目标
- ✅ **生产级部署**: 7x24 稳定运行的 AI 交易系统
- ✅ **自动化部署**: 一键完成环境配置和服务启动
- ✅ **安全加固**: 防火墙、用户权限、日志监控
- ✅ **监控告警**: 实时健康检查和异常通知
- ✅ **便捷管理**: 简单的启停和维护命令

### 🖥️ 系统要求

| 组件 | 最低配置 | 推荐配置 | 说明 |
|------|----------|----------|------|
| **CPU** | 1 vCPU | 2+ vCPU | AI 分析需要计算资源 |
| **内存** | 2GB | 4GB+ | Python 多进程运行 |
| **存储** | 20GB SSD | 50GB+ SSD | 日志和数据存储 |
| **网络** | 10Mbps | 100Mbps+ | 实时数据获取 |
| **操作系统** | Ubuntu 20.04+ | Ubuntu 22.04 LTS | 或 CentOS 8+ |

### 🌐 支持的 VPS 提供商
- **推荐**: DigitalOcean, Vultr, Linode, AWS EC2
- **国内**: 阿里云, 腾讯云, 华为云, UCloud
- **要求**: 支持 Docker 或完整 Linux 系统访问权限

---

## 🔧 方法一：一键自动化部署 (推荐)

### 步骤 1: 购买和配置 VPS

1. **选择 VPS 提供商** (以 DigitalOcean 为例):
   ```bash
   # 推荐配置: 2GB RAM, 1 vCPU, 50GB SSD
   # 操作系统: Ubuntu 22.04 LTS
   # 区域: 选择距离您最近的数据中心
   ```

2. **获取服务器信息**:
   ```bash
   # 记录以下信息:
   - 服务器 IP 地址
   - root 密码或 SSH 密钥
   - SSH 端口 (默认 22)
   ```

### 步骤 2: 连接到 VPS

```bash
# SSH 连接到服务器 (替换为您的 IP)
ssh root@YOUR_SERVER_IP

# 或使用密钥连接
ssh -i ~/.ssh/your_key.pem root@YOUR_SERVER_IP
```

### 步骤 3: 执行一键部署

```bash
# 1. 下载部署脚本
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-trader/main/deployment/vps_deploy.sh -o vps_deploy.sh

# 2. 修改脚本中的 GitHub 仓库地址
sed -i 's/YOUR_USERNAME/your_actual_username/g' vps_deploy.sh

# 3. 执行部署 (约 5-10 分钟)
bash vps_deploy.sh
```

### 步骤 4: 配置 API 密钥

```bash
# 切换到项目目录
cd /opt/ai-trader

# 配置环境变量 (重要!)
sudo -u aitrader nano .env

# 编辑以下内容:
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 步骤 5: 启动服务

```bash
# 使用便捷管理脚本
cd /opt/ai-trader
./manage.sh start

# 查看服务状态
./manage.sh status

# 查看实时日志
./manage.sh logs
```

### 🎉 部署完成！

访问 `http://YOUR_SERVER_IP/` 查看监控面板

---

## 🛠️ 方法二：手动部署 (高级用户)

### 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3 python3-pip python3-venv git curl wget

# 创建项目目录
sudo mkdir -p /opt/ai-trader
cd /opt/ai-trader

# 克隆项目
git clone https://github.com/YOUR_USERNAME/ai-trader.git .
```

### Python 环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env
nano .env  # 添加 API 密钥
```

### 系统服务

```bash
# 创建系统用户
sudo useradd -r -s /bin/bash aitrader
sudo chown -R aitrader:aitrader /opt/ai-trader

# 创建 systemd 服务
sudo nano /etc/systemd/system/ai-trader.service
```

服务配置内容：
```ini
[Unit]
Description=AI Trader System
After=network.target

[Service]
Type=simple
User=aitrader
WorkingDirectory=/opt/ai-trader
Environment=PATH=/opt/ai-trader/venv/bin
ExecStart=/opt/ai-trader/venv/bin/python main.py --enable-trading --auto-trade
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-trader
sudo systemctl start ai-trader
```

---

## 🔒 安全配置

### 防火墙设置

```bash
# Ubuntu UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 检查状态
sudo ufw status
```

### SSH 安全加固

```bash
# 编辑 SSH 配置
sudo nano /etc/ssh/sshd_config

# 推荐设置:
Port 2222                    # 更改默认端口
PermitRootLogin no          # 禁用 root 登录
PasswordAuthentication no   # 仅允许密钥登录
MaxAuthTries 3              # 限制登录尝试
```

### Fail2Ban 保护

```bash
# 安装 Fail2Ban
sudo apt install -y fail2ban

# 配置规则
sudo nano /etc/fail2ban/jail.local
```

Fail2Ban 配置：
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 2222
```

---

## 📊 监控和运维

### 系统监控

```bash
# 查看系统资源
htop

# 查看服务状态  
./manage.sh status

# 健康检查
./manage.sh health

# 查看日志
./manage.sh logs
```

### 日志管理

```bash
# 日志位置
/opt/ai-trader/logs/
├── trading/     # 交易日志
├── ai/         # AI 决策日志
└── system/     # 系统日志

# 查看特定日志
tail -f /opt/ai-trader/logs/trading/trades_*.json
```

### 性能优化

```bash
# 内存优化
echo 'vm.swappiness=10' >> /etc/sysctl.conf

# 文件句柄限制
echo 'aitrader soft nofile 65536' >> /etc/security/limits.conf

# 应用设置
sudo sysctl -p
```

---

## 🚨 常见问题和解决方案

### API 连接问题

**问题**: `Binance API 连接失败`
```bash
# 解决方案:
# 1. 检查网络连接
curl -I https://api.binance.com

# 2. 检查防火墙
sudo ufw status

# 3. 测试 API
cd /opt/ai-trader
./venv/bin/python -c "from data.binance_fetcher import BinanceFetcher; print('测试通过')"
```

### 服务启动失败

**问题**: `ai-trader.service 启动失败`
```bash
# 解决方案:
# 1. 查看详细错误
sudo journalctl -u ai-trader -f

# 2. 检查权限
sudo chown -R aitrader:aitrader /opt/ai-trader

# 3. 检查 Python 环境
sudo -u aitrader /opt/ai-trader/venv/bin/python --version
```

### 内存不足

**问题**: `内存使用过高`
```bash
# 解决方案:
# 1. 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 优化 Python 设置
export PYTHONOPTIMIZE=1

# 3. 限制并发分析
# 编辑 main.py 减少并发数
```

### 网络延迟高

**问题**: `数据获取延迟高`
```bash
# 解决方案:
# 1. 测试网络延迟
ping api.binance.com

# 2. 更换 DNS
echo 'nameserver 8.8.8.8' > /etc/resolv.conf

# 3. 优化网络参数
echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.conf
```

---

## 🔄 维护和更新

### 代码更新

```bash
# 更新代码
cd /opt/ai-trader
./manage.sh update

# 手动更新
git pull origin main
./venv/bin/pip install -r requirements.txt
./manage.sh restart
```

### 备份数据

```bash
# 创建备份脚本
sudo nano /opt/ai-trader/scripts/backup.sh
```

备份脚本内容：
```bash
#!/bin/bash
BACKUP_DIR="/opt/ai-trader/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份配置和数据
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
    /opt/ai-trader/.env \
    /opt/ai-trader/logs/ \
    /opt/ai-trader/trading_config.json

# 保留最近 30 天的备份
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "备份完成: backup_$DATE.tar.gz"
```

### 系统监控脚本

```bash
# 创建监控脚本
sudo nano /opt/ai-trader/scripts/monitor.sh
```

监控脚本内容：
```bash
#!/bin/bash
# AI Trader 系统监控

# 检查服务状态
if ! systemctl is-active --quiet ai-trader; then
    echo "警告: AI Trader 服务未运行" | mail -s "系统警告" admin@yourdomain.com
    systemctl restart ai-trader
fi

# 检查磁盘空间
DISK_USAGE=$(df /opt/ai-trader | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "警告: 磁盘使用率超过 80%" | mail -s "磁盘警告" admin@yourdomain.com
fi

# 检查内存使用
MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ $MEM_USAGE -gt 90 ]; then
    echo "警告: 内存使用率超过 90%" | mail -s "内存警告" admin@yourdomain.com
fi
```

### 定时任务

```bash
# 设置定时任务
sudo -u aitrader crontab -e

# 添加以下内容:
# 每 5 分钟检查系统状态
*/5 * * * * /opt/ai-trader/scripts/health_check.sh

# 每天凌晨 2 点备份数据  
0 2 * * * /opt/ai-trader/scripts/backup.sh

# 每小时清理临时日志
0 * * * * find /opt/ai-trader/logs -name "*.tmp" -mtime +1 -delete
```

---

## 🎯 高级配置

### 负载均衡 (多实例)

```bash
# 部署多个实例
for i in {1..3}; do
    sudo cp /etc/systemd/system/ai-trader.service /etc/systemd/system/ai-trader-$i.service
    sudo sed -i "s/ai-trader/ai-trader-$i/g" /etc/systemd/system/ai-trader-$i.service
    sudo systemctl enable ai-trader-$i
done
```

### SSL/HTTPS 配置

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 申请 SSL 证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 数据库集成

```bash
# 安装 PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 创建数据库
sudo -u postgres createdb aitrader
sudo -u postgres createuser aitrader

# 配置连接
echo "DATABASE_URL=postgresql://aitrader:password@localhost/aitrader" >> .env
```

---

## 📞 技术支持

### 获取帮助

1. **项目文档**: [GitHub Wiki](https://github.com/YOUR_USERNAME/ai-trader/wiki)
2. **问题报告**: [GitHub Issues](https://github.com/YOUR_USERNAME/ai-trader/issues)
3. **社区讨论**: [GitHub Discussions](https://github.com/YOUR_USERNAME/ai-trader/discussions)

### 紧急联系

- **系统故障**: 检查日志 `./manage.sh logs`
- **性能问题**: 运行健康检查 `./manage.sh health`  
- **安全问题**: 立即停止服务 `./manage.sh stop`

---

## ✅ 部署检查清单

完成部署后，请确认以下项目：

- [ ] **VPS 系统**: Ubuntu/CentOS 正确安装
- [ ] **代码部署**: GitHub 代码成功克隆
- [ ] **Python 环境**: 虚拟环境和依赖安装完成
- [ ] **API 配置**: OpenRouter API 密钥配置正确
- [ ] **系统服务**: ai-trader.service 正常运行
- [ ] **防火墙**: 必要端口开放，安全规则配置
- [ ] **监控系统**: 健康检查和日志监控正常
- [ ] **备份机制**: 自动备份脚本配置完成
- [ ] **性能测试**: 系统负载和响应时间正常
- [ ] **安全加固**: SSH、Fail2Ban 等安全措施生效

🎉 **恭喜！AI Trader 已成功部署到生产环境！**