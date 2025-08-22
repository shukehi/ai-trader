# ⚡ AI Trader 快速部署命令

> **一页纸搞定 VPS 部署 - 复制粘贴即可完成**

## 🚀 VPS 一键部署 (5分钟完成)

### 步骤 1: 连接 VPS
```bash
# SSH 连接到您的 VPS (替换为实际 IP)
ssh root@YOUR_SERVER_IP
```

### 步骤 2: 执行自动部署
```bash
# 一键部署脚本
curl -fsSL https://raw.githubusercontent.com/shukehi/ai-trader/main/deployment/vps_deploy.sh | bash
```

### 步骤 3: 配置 API 密钥
```bash
# 编辑环境配置
cd /opt/ai-trader
sudo -u aitrader nano .env

# 添加您的 OpenRouter API 密钥:
# OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 步骤 4: 启动服务
```bash
# 启动 AI 交易系统
./manage.sh start

# 查看状态
./manage.sh status

# 查看实时日志
./manage.sh logs
```

## ✅ 验证部署

```bash
# 健康检查
./manage.sh health

# 查看监控面板 (浏览器访问)
echo "监控面板: http://$(curl -s ifconfig.me)/"

# 测试 API 连接
./venv/bin/python -c "from data.binance_fetcher import BinanceFetcher; print('✅ API 连接正常')"
```

---

## 🛠️ 管理命令大全

### 服务管理
```bash
cd /opt/ai-trader

# 启动服务
./manage.sh start

# 停止服务  
./manage.sh stop

# 重启服务
./manage.sh restart

# 查看状态
./manage.sh status

# 实时日志
./manage.sh logs

# 健康检查
./manage.sh health

# 更新代码
./manage.sh update
```

### 系统监控
```bash
# 查看系统资源
htop

# 查看服务进程
ps aux | grep ai-trader

# 查看端口占用
netstat -tlnp | grep 8080

# 查看磁盘空间
df -h

# 查看内存使用
free -h
```

### 日志查看
```bash
# 系统服务日志
sudo journalctl -u ai-trader -f

# 应用日志目录
ls -la /opt/ai-trader/logs/

# 交易日志
tail -f /opt/ai-trader/logs/trading/trades_*.json

# AI 决策日志
tail -f /opt/ai-trader/logs/ai/ai_decisions_*.json

# 系统性能日志
tail -f /opt/ai-trader/logs/system/performance_*.txt
```

---

## 🔧 故障排除一键命令

### API 连接问题
```bash
# 测试网络连接
curl -I https://api.binance.com
curl -I https://openrouter.ai

# 测试 Python 环境
cd /opt/ai-trader
./venv/bin/python -c "from config import Settings; Settings.validate()"

# 重启网络服务
sudo systemctl restart networking
```

### 服务启动失败
```bash
# 查看详细错误
sudo journalctl -u ai-trader --no-pager -l

# 检查权限
sudo chown -R aitrader:aitrader /opt/ai-trader

# 手动启动测试
cd /opt/ai-trader
sudo -u aitrader ./venv/bin/python main.py --help
```

### 性能问题
```bash
# 查看资源使用
top -p $(pgrep -f "main.py")

# 清理临时文件
find /opt/ai-trader -name "*.tmp" -delete
find /opt/ai-trader/logs -name "*.log" -mtime +7 -delete

# 重启服务释放内存
./manage.sh restart
```

---

## 📊 VPS 提供商快速配置

### DigitalOcean
```bash
# 推荐配置: $20/月
# CPU: 2 vCPU, RAM: 4GB, SSD: 80GB
# 操作系统: Ubuntu 22.04 LTS

# 一键安装命令 (登录后执行)
curl -fsSL https://github.com/YOUR_USERNAME/ai-trader/raw/main/deployment/vps_deploy.sh | bash
```

### 阿里云 ECS
```bash
# 推荐配置: ecs.t6-c1m2.large
# CPU: 2 vCPU, RAM: 4GB, SSD: 40GB
# 操作系统: Ubuntu 20.04 LTS

# 安装前准备 (中国大陆)
export DEBIAN_FRONTEND=noninteractive
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# 执行部署
curl -fsSL https://github.com/YOUR_USERNAME/ai-trader/raw/main/deployment/vps_deploy.sh | bash
```

### Vultr
```bash
# 推荐配置: $12/月  
# CPU: 2 vCPU, RAM: 4GB, SSD: 80GB
# 操作系统: Ubuntu 22.04 LTS

# 部署命令
curl -fsSL https://github.com/YOUR_USERNAME/ai-trader/raw/main/deployment/vps_deploy.sh | bash
```

---

## 🔐 安全加固一键脚本

### 基础安全设置
```bash
# SSH 安全加固
sudo sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# 防火墙配置
sudo ufw --force enable
sudo ufw allow 2222/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Fail2Ban 安装
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
```

### 系统优化
```bash
# 内存优化
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# 文件句柄限制
echo 'aitrader soft nofile 65536' | sudo tee -a /etc/security/limits.conf
echo 'aitrader hard nofile 65536' | sudo tee -a /etc/security/limits.conf

# 网络优化  
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf

# 应用配置
sudo sysctl -p
```

---

## 📱 移动端监控

### 手机查看状态
```bash
# 获取服务器 IP
curl -s ifconfig.me

# 访问监控面板 (手机浏览器)
# http://YOUR_SERVER_IP/

# SSH 移动端工具推荐:
# iOS: Termius, Prompt 3
# Android: JuiceSSH, Termux
```

### 微信/邮件告警设置
```bash
# 创建告警脚本
cat > /opt/ai-trader/scripts/alert.sh << 'EOF'
#!/bin/bash
MESSAGE="$1"
# 添加您的微信/邮件通知 API
curl -X POST "https://your-webhook-url" -d "text=$MESSAGE"
EOF

chmod +x /opt/ai-trader/scripts/alert.sh
```

---

## 🎯 生产环境清单

### 部署前检查 ✅
- [ ] VPS 已购买 (推荐 4GB+ 内存)
- [ ] OpenRouter API 密钥已获取
- [ ] GitHub 仓库已创建并公开
- [ ] SSH 连接已测试

### 部署后验证 ✅  
- [ ] 服务正常运行 (`./manage.sh status`)
- [ ] API 连接成功 (`./manage.sh health`)
- [ ] 监控面板可访问
- [ ] 日志正常记录
- [ ] 系统资源充足

### 安全检查 ✅
- [ ] SSH 端口已更改
- [ ] 防火墙已配置
- [ ] Root 登录已禁用
- [ ] SSL 证书已配置 (可选)

---

## 🆘 紧急恢复

### 服务异常停止
```bash
# 紧急重启
cd /opt/ai-trader
./manage.sh restart

# 如果重启失败
sudo systemctl reset-failed ai-trader
sudo systemctl start ai-trader
```

### 数据恢复
```bash
# 从备份恢复
cd /opt/ai-trader/backups
ls -la  # 查看可用备份

# 恢复最新备份
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz -C /
./manage.sh restart
```

### 系统重置
```bash
# 完整重新部署 (慎用!)
cd /opt
sudo rm -rf ai-trader
curl -fsSL https://github.com/YOUR_USERNAME/ai-trader/raw/main/deployment/vps_deploy.sh | bash
```

---

**🎉 恭喜！您的 AI 交易系统已成功部署到生产环境！**

**📞 需要帮助?** 
- GitHub Issues: https://github.com/YOUR_USERNAME/ai-trader/issues  
- 文档: https://github.com/YOUR_USERNAME/ai-trader/wiki