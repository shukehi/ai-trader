#!/bin/bash
# AI Trader VPS 部署脚本 - 完整自动化部署
# 适用系统: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
# 使用方法: bash deployment/vps_deploy.sh

set -e  # 出错时退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量
PROJECT_NAME="ai-trader"
PROJECT_DIR="/opt/ai-trader"
SERVICE_USER="aitrader"
PYTHON_VERSION="3.9"
GITHUB_REPO="https://github.com/shukehi/ai-trader.git"

echo "🚀 AI Trader VPS 部署开始..."
echo "时间: $(date)"
echo "系统: $(uname -a)"
echo "用户: $(whoami)"
echo "============================================"

# 1. 检查系统兼容性
log_info "检查系统兼容性..."

if command -v apt-get &> /dev/null; then
    OS="ubuntu"
    PACKAGE_MANAGER="apt-get"
elif command -v yum &> /dev/null; then
    OS="centos"
    PACKAGE_MANAGER="yum"
else
    log_error "不支持的操作系统。支持 Ubuntu/Debian 和 CentOS/RHEL"
    exit 1
fi

log_success "操作系统: $OS"

# 2. 更新系统
log_info "更新系统包管理器..."

if [ "$OS" = "ubuntu" ]; then
    sudo apt-get update -y
    sudo apt-get upgrade -y
    sudo apt-get install -y software-properties-common
elif [ "$OS" = "centos" ]; then
    sudo yum update -y
    sudo yum groupinstall -y "Development Tools"
fi

log_success "系统更新完成"

# 3. 安装系统依赖
log_info "安装系统依赖..."

if [ "$OS" = "ubuntu" ]; then
    sudo apt-get install -y \
        python3 python3-pip python3-venv python3-dev \
        git curl wget vim htop \
        build-essential libssl-dev libffi-dev \
        nginx supervisor redis-server \
        ufw fail2ban logrotate
elif [ "$OS" = "centos" ]; then
    sudo yum install -y \
        python39 python39-pip python39-devel \
        git curl wget vim htop \
        gcc gcc-c++ make openssl-devel libffi-devel \
        nginx supervisor redis \
        firewalld fail2ban logrotate
    
    # 创建 python3 软链接
    sudo ln -sf /usr/bin/python3.9 /usr/bin/python3 || true
fi

log_success "系统依赖安装完成"

# 4. 创建服务用户
log_info "创建服务用户..."

if ! id "$SERVICE_USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d /home/$SERVICE_USER $SERVICE_USER
    sudo mkdir -p /home/$SERVICE_USER
    sudo chown $SERVICE_USER:$SERVICE_USER /home/$SERVICE_USER
    log_success "创建用户: $SERVICE_USER"
else
    log_warning "用户 $SERVICE_USER 已存在"
fi

# 5. 创建项目目录
log_info "创建项目目录..."

sudo mkdir -p $PROJECT_DIR
sudo chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

# 6. 克隆项目代码
log_info "克隆项目代码..."

if [ -d "$PROJECT_DIR/.git" ]; then
    log_warning "项目已存在，执行更新..."
    cd $PROJECT_DIR
    sudo -u $SERVICE_USER git pull origin main
else
    log_info "首次克隆项目..."
    sudo -u $SERVICE_USER git clone $GITHUB_REPO $PROJECT_DIR
    cd $PROJECT_DIR
fi

log_success "代码克隆/更新完成"

# 6.5. 修复Git权限问题
log_info "修复Git权限配置..."
cd $PROJECT_DIR

# 添加安全目录配置
git config --global --add safe.directory $PROJECT_DIR 2>/dev/null || true
sudo -u $SERVICE_USER git config --global --add safe.directory $PROJECT_DIR 2>/dev/null || true

# 确保Git目录权限正确
chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/.git
log_success "Git权限修复完成"

# 7. 设置 Python 虚拟环境
log_info "设置 Python 虚拟环境..."

sudo -u $SERVICE_USER python3 -m venv $PROJECT_DIR/venv
sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install --upgrade pip setuptools wheel

log_success "虚拟环境创建完成"

# 8. 安装 Python 依赖
log_info "安装 Python 依赖..."

# 升级pip和基础工具
log_info "升级pip和基础安装工具..."
sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install --upgrade pip setuptools wheel

# 清理可能存在的临时文件
log_info "清理临时文件..."
sudo -u $SERVICE_USER find $PROJECT_DIR -name "=*" -type f -delete 2>/dev/null || true

# 阶段1: 安装核心依赖（必须成功）
log_info "安装核心依赖（第1阶段）..."
if sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements-core.txt; then
    log_success "核心依赖安装成功"
else
    log_error "核心依赖安装失败，尝试逐个安装..."
    
    # 核心依赖逐个安装，确保关键组件可用
    CORE_PACKAGES=(
        "openai>=1.0.0"
        "python-dotenv>=1.0.0"
        "requests>=2.31.0"
        "pandas>=2.0.0"
        "numpy>=1.24.0"
        "ccxt>=4.0.0"
        "python-binance>=1.0.17"
        "websockets>=11.0.0"
        "aiohttp>=3.8.0"
        "python-dateutil>=2.8.0"
        "pytz>=2023.3"
    )
    
    for package in "${CORE_PACKAGES[@]}"; do
        if sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install "$package"; then
            log_success "✓ $package"
        else
            log_warning "✗ $package - 将影响系统功能"
        fi
    done
fi

# 阶段2: 安装可选依赖（允许失败）
log_info "安装可选依赖（第2阶段）..."
if sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements-optional.txt; then
    log_success "可选依赖安装成功"
else
    log_warning "部分可选依赖安装失败，核心功能不受影响"
    
    # 尝试安装最重要的可选依赖
    OPTIONAL_PACKAGES=(
        "ta>=0.10.0"
        "matplotlib>=3.7.0"
        "sqlalchemy>=2.0.0"
    )
    
    for package in "${OPTIONAL_PACKAGES[@]}"; do
        if sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install "$package"; then
            log_success "✓ $package (可选)"
        else
            log_info "✗ $package (可选，跳过)"
        fi
    done
fi

# 验证核心功能
log_info "验证核心依赖..."
if sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/python -c "
import sys, importlib
required_modules = ['pandas', 'numpy', 'ccxt', 'requests', 'openai', 'dotenv']
missing = []
for module in required_modules:
    try:
        importlib.import_module(module.replace('-', '_'))
    except ImportError:
        missing.append(module)
        
if missing:
    print(f'Missing critical modules: {missing}')
    sys.exit(1)
else:
    print('All critical modules available')
"; then
    log_success "核心依赖验证通过"
else
    log_error "核心依赖验证失败，系统可能无法正常运行"
fi

# 再次清理临时文件
sudo -u $SERVICE_USER find $PROJECT_DIR -name "=*" -type f -delete 2>/dev/null || true

log_success "Python 依赖安装完成"

# 9. 创建配置文件
log_info "创建配置文件..."

if [ ! -f "$PROJECT_DIR/.env" ]; then
    sudo -u $SERVICE_USER cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env
    log_warning "⚠️  请配置 $PROJECT_DIR/.env 文件中的 API 密钥！"
    log_warning "    编辑命令: sudo -u $SERVICE_USER nano $PROJECT_DIR/.env"
else
    log_success "配置文件已存在"
fi

# 10. 创建日志目录
log_info "创建日志和数据目录..."

sudo -u $SERVICE_USER mkdir -p $PROJECT_DIR/logs/{trading,ai,system}
sudo -u $SERVICE_USER mkdir -p $PROJECT_DIR/results/production
sudo -u $SERVICE_USER mkdir -p $PROJECT_DIR/backups

log_success "目录结构创建完成"

# 11. 设置系统服务
log_info "设置系统服务..."

# 创建 systemd 服务文件
sudo tee /etc/systemd/system/ai-trader.service > /dev/null <<EOF
[Unit]
Description=AI Trader System
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python main.py --enable-trading --auto-trade --enable-validation
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 创建监控服务
sudo tee /etc/systemd/system/ai-trader-monitor.service > /dev/null <<EOF
[Unit]
Description=AI Trader Monitor
After=ai-trader.service
Wants=ai-trader.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python monitoring/production_monitor.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd
sudo systemctl daemon-reload

log_success "系统服务配置完成"

# 12. 配置防火墙
log_info "配置防火墙..."

if [ "$OS" = "ubuntu" ]; then
    sudo ufw --force enable
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
elif [ "$OS" = "centos" ]; then
    sudo systemctl enable firewalld
    sudo systemctl start firewalld
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
fi

log_success "防火墙配置完成"

# 13. 配置 Nginx (可选 - 用于监控面板)
log_info "配置 Nginx..."

sudo tee /etc/nginx/sites-available/ai-trader > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /logs {
        alias $PROJECT_DIR/logs;
        autoindex on;
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
EOF

if [ "$OS" = "ubuntu" ]; then
    sudo ln -sf /etc/nginx/sites-available/ai-trader /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
fi

sudo systemctl enable nginx
sudo systemctl restart nginx

log_success "Nginx 配置完成"

# 14. 配置日志轮转
log_info "配置日志轮转..."

sudo tee /etc/logrotate.d/ai-trader > /dev/null <<EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl restart ai-trader
    endscript
}
EOF

log_success "日志轮转配置完成"

# 15. 系统优化
log_info "系统优化..."

# 增加文件句柄限制
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
$SERVICE_USER soft nofile 65536
$SERVICE_USER hard nofile 65536
EOF

# 内核参数优化
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
# AI Trader 优化
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 65536 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
EOF

sudo sysctl -p

log_success "系统优化完成"

# 16. 健康检查脚本
log_info "创建健康检查脚本..."

sudo -u $SERVICE_USER tee $PROJECT_DIR/scripts/health_check.sh > /dev/null <<'EOF'
#!/bin/bash
# AI Trader 健康检查脚本

cd "$(dirname "$0")/.."

# 检查服务状态
if ! systemctl is-active --quiet ai-trader; then
    echo "❌ AI Trader 服务未运行"
    exit 1
fi

# 检查 Python 进程
if ! pgrep -f "main.py" > /dev/null; then
    echo "❌ AI Trader 进程未找到"
    exit 1
fi

# 检查 API 连接
if ! ./venv/bin/python -c "
from config import Settings
from data import BinanceFetcher
try:
    Settings.validate()
    fetcher = BinanceFetcher()
    fetcher.get_ohlcv('ETH/USDT', '1h', 1)
    print('✅ API 连接正常')
except Exception as e:
    print(f'❌ API 连接失败: {e}')
    exit(1)
"; then
    echo "✅ 系统健康检查通过"
else
    echo "❌ 系统健康检查失败"
    exit 1
fi
EOF

chmod +x $PROJECT_DIR/scripts/health_check.sh

log_success "健康检查脚本创建完成"

# 17. 创建启动脚本
log_info "创建便捷管理脚本..."

sudo -u $SERVICE_USER tee $PROJECT_DIR/manage.sh > /dev/null <<'EOF'
#!/bin/bash
# AI Trader 管理脚本

cd "$(dirname "$0")"

case "$1" in
    start)
        echo "启动 AI Trader..."
        sudo systemctl start ai-trader
        sudo systemctl start ai-trader-monitor
        echo "✅ 服务已启动"
        ;;
    stop)
        echo "停止 AI Trader..."
        sudo systemctl stop ai-trader
        sudo systemctl stop ai-trader-monitor
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "重启 AI Trader..."
        sudo systemctl restart ai-trader
        sudo systemctl restart ai-trader-monitor
        echo "✅ 服务已重启"
        ;;
    status)
        echo "=== AI Trader 状态 ==="
        sudo systemctl status ai-trader --no-pager
        echo -e "\n=== 监控器状态 ==="
        sudo systemctl status ai-trader-monitor --no-pager
        ;;
    logs)
        echo "=== 最新日志 ==="
        sudo journalctl -u ai-trader -f
        ;;
    health)
        echo "=== 健康检查 ==="
        ./scripts/health_check.sh
        ;;
    update)
        echo "更新代码..."
        git pull origin main
        ./venv/bin/pip install -r requirements.txt
        sudo systemctl restart ai-trader
        echo "✅ 更新完成"
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs|health|update}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看状态"
        echo "  logs    - 查看实时日志"
        echo "  health  - 健康检查"
        echo "  update  - 更新代码"
        exit 1
        ;;
esac
EOF

chmod +x $PROJECT_DIR/manage.sh

log_success "管理脚本创建完成"

echo ""
echo "🎉 AI Trader VPS 部署完成！"
echo "============================================"
log_success "项目目录: $PROJECT_DIR"
log_success "服务用户: $SERVICE_USER"
log_warning "⚠️  下一步操作："
echo ""
echo "1. 配置 API 密钥:"
echo "   sudo -u $SERVICE_USER nano $PROJECT_DIR/.env"
echo ""
echo "2. 启动服务:"
echo "   cd $PROJECT_DIR"
echo "   ./manage.sh start"
echo ""
echo "3. 查看状态:"
echo "   ./manage.sh status"
echo ""
echo "4. 查看日志:"
echo "   ./manage.sh logs"
echo ""
echo "5. 健康检查:"
echo "   ./manage.sh health"
echo ""
log_info "访问监控面板: http://$(curl -s ifconfig.me)/"
log_info "日志目录: $PROJECT_DIR/logs/"
echo ""
echo "🚀 享受 AI 交易系统吧！"