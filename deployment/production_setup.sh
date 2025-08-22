#!/bin/bash
# ETH永续合约AI分析助手 - 生产环境部署脚本
# 使用方法: bash deployment/production_setup.sh

set -e  # 出错时退出

echo "🚀 开始生产环境部署..."
echo "时间: $(date)"
echo "用户: $(whoami)"
echo "系统: $(uname -a)"
echo "============================================"

# 1. 环境准备
echo "📦 1. 环境准备"
echo "检查Python版本..."
python_version=$(python3 --version)
echo "   ✅ $python_version"

echo "创建生产目录结构..."
mkdir -p logs
mkdir -p results/production
mkdir -p backups
mkdir -p monitoring
echo "   ✅ 目录结构创建完成"

# 2. 依赖安装
echo "📚 2. 安装生产依赖"
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "   ✅ 依赖安装完成"

# 3. 配置文件检查
echo "⚙️ 3. 配置文件检查"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ⚠️ 已创建.env文件，请配置OPENROUTER_API_KEY"
        echo "   编辑命令: nano .env"
    else
        echo "   ❌ 缺少.env.example文件"
        exit 1
    fi
else
    echo "   ✅ .env文件存在"
fi

# 4. 系统健康检查
echo "🔧 4. 系统健康检查"
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from config import Settings
    Settings.validate()
    print('   ✅ 配置验证通过')
except Exception as e:
    print(f'   ❌ 配置验证失败: {e}')
    sys.exit(1)
"

# 5. 测试核心功能
echo "🧪 5. 核心功能测试"
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from data import BinanceFetcher, DataProcessor
    from ai import OpenRouterClient, AnalysisEngine, MultiModelValidator
    from formatters import DataFormatter
    print('   ✅ 所有核心模块导入成功')
except Exception as e:
    print(f'   ❌ 模块导入失败: {e}')
    sys.exit(1)
"

# 6. 创建生产配置
echo "📝 6. 创建生产配置文件"
cat > config/production.py << 'EOF'
"""
生产环境专用配置
"""
import os
from .settings import Settings

class ProductionSettings(Settings):
    # 生产环境日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/production.log')
    
    # 生产环境限制
    MAX_DAILY_COST = float(os.getenv('MAX_DAILY_COST', '50.0'))  # 每日最大成本
    MAX_HOURLY_REQUESTS = int(os.getenv('MAX_HOURLY_REQUESTS', '100'))  # 每小时最大请求数
    
    # 生产环境模型配置
    PRODUCTION_MODELS = {
        'primary': os.getenv('PRIMARY_MODEL', 'gpt5-mini'),
        'validation': os.getenv('VALIDATION_MODEL', 'gpt4o-mini'), 
        'economy': os.getenv('ECONOMY_MODEL', 'gemini-flash')
    }
    
    # 监控配置
    ENABLE_MONITORING = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '300'))  # 5分钟
    
    # 备份配置
    ENABLE_BACKUP = os.getenv('ENABLE_BACKUP', 'true').lower() == 'true'
    BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', '3600'))  # 1小时
EOF

echo "   ✅ 生产配置文件创建完成"

# 7. 创建启动脚本
echo "🚀 7. 创建生产启动脚本"
cat > start_production.sh << 'EOF'
#!/bin/bash
# ETH永续合约AI分析助手 - 生产启动脚本

# 激活虚拟环境
source venv/bin/activate

# 设置生产环境变量
export ENV=production
export LOG_LEVEL=INFO
export MAX_DAILY_COST=50.0

# 启动主程序
echo "🚀 启动ETH永续合约AI分析助手 (生产模式)"
echo "时间: $(date)"
echo "PID: $$"

# 记录启动日志
echo "$(date): 生产服务启动" >> logs/production.log

# 运行主程序
python3 main.py \
    --symbol ETHUSDT \
    --enable-validation \
    --fast-validation \
    --limit 50 \
    2>&1 | tee -a logs/production.log
EOF

chmod +x start_production.sh
echo "   ✅ 生产启动脚本创建完成"

# 8. 创建监控脚本
echo "📊 8. 创建监控脚本"
cat > monitoring/health_check.sh << 'EOF'
#!/bin/bash
# 系统健康检查脚本

echo "🔍 ETH永续合约AI分析助手健康检查"
echo "时间: $(date)"

# 检查进程
if pgrep -f "main.py" > /dev/null; then
    echo "✅ 主程序运行中"
else
    echo "❌ 主程序未运行"
fi

# 检查日志文件
if [ -f "logs/production.log" ]; then
    echo "📝 日志文件正常"
    tail_lines=$(tail -n 10 logs/production.log | wc -l)
    echo "   最近10行日志: $tail_lines 行"
else
    echo "⚠️ 日志文件不存在"
fi

# 检查磁盘空间
disk_usage=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
echo "💾 磁盘使用率: $disk_usage%"
if [ $disk_usage -gt 90 ]; then
    echo "⚠️ 磁盘空间不足"
fi

# 检查配置文件
if [ -f ".env" ]; then
    echo "⚙️ 配置文件存在"
else
    echo "❌ 配置文件缺失"
fi
EOF

chmod +x monitoring/health_check.sh
echo "   ✅ 监控脚本创建完成"

echo ""
echo "🎯 生产环境部署完成!"
echo "============================================"
echo "📋 下一步操作:"
echo "1. 配置API密钥: nano .env"
echo "2. 设置生产参数: nano config/production.py" 
echo "3. 启动生产服务: ./start_production.sh"
echo "4. 运行健康检查: ./monitoring/health_check.sh"
echo ""
echo "📖 生产运行命令:"
echo "# 标准生产分析"
echo "./start_production.sh"
echo ""
echo "# 经济模式分析"  
echo "python3 main.py --model gemini-flash --symbol ETHUSDT --limit 50"
echo ""
echo "# 高质量分析"
echo "python3 main.py --model gpt5-mini --symbol ETHUSDT --enable-validation"
echo ""
echo "✅ 部署脚本执行完成"