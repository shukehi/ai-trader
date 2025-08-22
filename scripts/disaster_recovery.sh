#!/bin/bash
# ETH永续合约AI分析助手 - 灾难恢复系统
# 功能：系统恢复、配置恢复、数据恢复

set -e

echo "🚨 ETH永续合约AI分析助手 - 灾难恢复系统"
echo "时间: $(date)"
echo "============================================"

# 检查参数
if [ $# -eq 0 ]; then
    echo "使用方法:"
    echo "  $0 <备份文件>     # 从指定备份恢复"
    echo "  $0 --latest       # 从最新备份恢复"
    echo "  $0 --list         # 列出可用备份"
    echo "  $0 --check        # 检查系统状态"
    exit 1
fi

# 列出可用备份
if [ "$1" = "--list" ]; then
    echo "📋 可用备份文件:"
    if [ -d "backups" ]; then
        ls -la backups/*.tar.gz 2>/dev/null || echo "   没有找到备份文件"
    else
        echo "   backups目录不存在"
    fi
    exit 0
fi

# 检查系统状态
if [ "$1" = "--check" ]; then
    echo "🔍 系统状态检查:"
    
    # 检查关键文件
    echo "📁 关键文件检查:"
    files=(".env" "requirements.txt" "main.py" "config/settings.py")
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            echo "   ✅ $file"
        else
            echo "   ❌ $file (缺失)"
        fi
    done
    
    # 检查目录结构
    echo "📂 目录结构检查:"
    dirs=("venv" "config" "data" "ai" "formatters" "tests")
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "   ✅ $dir/"
        else
            echo "   ❌ $dir/ (缺失)"
        fi
    done
    
    # 检查虚拟环境
    echo "🐍 Python环境检查:"
    if [ -f "venv/bin/activate" ]; then
        echo "   ✅ 虚拟环境存在"
        source venv/bin/activate
        if python3 -c "import sys; sys.path.insert(0, '.'); from config import Settings; Settings.validate()" 2>/dev/null; then
            echo "   ✅ 配置验证通过"
        else
            echo "   ❌ 配置验证失败"
        fi
    else
        echo "   ❌ 虚拟环境不存在"
    fi
    
    exit 0
fi

# 确定备份文件
if [ "$1" = "--latest" ]; then
    if [ ! -d "backups" ]; then
        echo "❌ backups目录不存在"
        exit 1
    fi
    
    BACKUP_FILE=$(ls -t backups/*.tar.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ 没有找到备份文件"
        exit 1
    fi
    echo "📦 使用最新备份: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "❌ 备份文件不存在: $BACKUP_FILE"
        exit 1
    fi
    echo "📦 使用指定备份: $BACKUP_FILE"
fi

# 创建恢复目录
RESTORE_DIR="restore_$(date +%Y%m%d_%H%M%S)"
echo "📁 创建恢复目录: $RESTORE_DIR"
mkdir -p "$RESTORE_DIR"

# 解压备份
echo "📦 解压备份文件..."
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# 找到解压的目录
BACKUP_CONTENT_DIR=$(find "$RESTORE_DIR" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "$BACKUP_CONTENT_DIR" ]; then
    echo "❌ 无法找到备份内容目录"
    exit 1
fi

echo "📂 备份内容目录: $BACKUP_CONTENT_DIR"

# 确认恢复操作
echo ""
echo "⚠️ 警告: 此操作将覆盖现有配置文件!"
echo "即将恢复的内容:"
echo "   - 配置文件 (.env, config/)"
echo "   - 脚本文件 (deployment/, monitoring/)"
echo "   - 历史日志和结果"
echo ""
read -p "确认继续恢复？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 用户取消恢复操作"
    rm -rf "$RESTORE_DIR"
    exit 1
fi

# 备份当前配置
echo "💾 备份当前配置..."
CURRENT_BACKUP="current_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_BACKUP"
cp .env "$CURRENT_BACKUP/" 2>/dev/null || true
cp -r config "$CURRENT_BACKUP/" 2>/dev/null || true
echo "   ✅ 当前配置已备份到: $CURRENT_BACKUP"

# 恢复配置文件
echo "⚙️ 恢复配置文件..."
if [ -d "$BACKUP_CONTENT_DIR/config" ]; then
    # 恢复配置目录
    if [ -f "$BACKUP_CONTENT_DIR/config/.env.backup" ]; then
        cp "$BACKUP_CONTENT_DIR/config/.env.backup" .env
        echo "   ✅ 恢复 .env 文件"
    fi
    
    # 恢复其他配置文件
    cp "$BACKUP_CONTENT_DIR/config/requirements.txt" . 2>/dev/null || true
    cp -r "$BACKUP_CONTENT_DIR/config" . 2>/dev/null || true
    echo "   ✅ 配置文件恢复完成"
else
    echo "   ⚠️ 备份中没有找到config目录"
fi

# 恢复脚本文件
echo "🔧 恢复脚本文件..."
if [ -d "$BACKUP_CONTENT_DIR/scripts" ]; then
    cp -r "$BACKUP_CONTENT_DIR/scripts/deployment" . 2>/dev/null || true
    cp -r "$BACKUP_CONTENT_DIR/scripts/monitoring" . 2>/dev/null || true
    cp -r "$BACKUP_CONTENT_DIR/scripts/utils" . 2>/dev/null || true
    cp "$BACKUP_CONTENT_DIR/scripts/start_production.sh" . 2>/dev/null || true
    chmod +x start_production.sh 2>/dev/null || true
    echo "   ✅ 脚本文件恢复完成"
else
    echo "   ⚠️ 备份中没有找到scripts目录"
fi

# 恢复日志文件
echo "📝 恢复日志文件..."
if [ -d "$BACKUP_CONTENT_DIR/logs" ]; then
    mkdir -p logs
    cp -r "$BACKUP_CONTENT_DIR/logs"/* logs/ 2>/dev/null || true
    echo "   ✅ 日志文件恢复完成"
else
    echo "   ⚠️ 备份中没有找到logs目录"
fi

# 恢复分析结果
echo "📊 恢复分析结果..."
if [ -d "$BACKUP_CONTENT_DIR/results" ]; then
    mkdir -p results
    cp -r "$BACKUP_CONTENT_DIR/results"/* results/ 2>/dev/null || true
    echo "   ✅ 分析结果恢复完成"
else
    echo "   ⚠️ 备份中没有找到results目录"
fi

# 检查虚拟环境
echo "🐍 检查Python环境..."
if [ ! -d "venv" ]; then
    echo "   ⚠️ 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "   ✅ 虚拟环境创建并安装依赖完成"
    fi
else
    echo "   ✅ 虚拟环境存在"
fi

# 验证恢复
echo "🔍 验证恢复结果..."
source venv/bin/activate 2>/dev/null || true
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from config import Settings
    Settings.validate()
    print('   ✅ 系统验证通过')
except Exception as e:
    print(f'   ❌ 系统验证失败: {e}')
    exit(1)
" 2>/dev/null; then
    RECOVERY_STATUS="SUCCESS"
else
    RECOVERY_STATUS="PARTIAL"
    echo "   ⚠️ 系统验证部分失败，可能需要手动配置"
fi

# 生成恢复报告
echo "📋 生成恢复报告..."
cat > "recovery_report_$(date +%Y%m%d_%H%M%S).txt" << EOF
# ETH永续合约AI分析助手 - 恢复报告

恢复时间: $(date)
备份文件: $BACKUP_FILE
恢复目录: $RESTORE_DIR
当前备份: $CURRENT_BACKUP
恢复状态: $RECOVERY_STATUS

恢复内容:
- 配置文件: $([ -f ".env" ] && echo "✅" || echo "❌")
- 脚本文件: $([ -f "start_production.sh" ] && echo "✅" || echo "❌")  
- 日志文件: $([ -d "logs" ] && echo "✅" || echo "❌")
- 分析结果: $([ -d "results" ] && echo "✅" || echo "❌")
- 虚拟环境: $([ -d "venv" ] && echo "✅" || echo "❌")

系统验证: $([ "$RECOVERY_STATUS" = "SUCCESS" ] && echo "✅ 通过" || echo "⚠️ 部分失败")

后续步骤:
1. 检查 .env 文件中的API密钥
2. 运行系统健康检查: $0 --check  
3. 测试核心功能: ./start_production.sh --test
4. 如有问题，从当前备份恢复: $CURRENT_BACKUP
EOF

# 清理临时文件
echo "🧹 清理临时文件..."
rm -rf "$RESTORE_DIR"

echo ""
echo "🎯 恢复操作完成!"
echo "============================================"
echo "📊 恢复状态: $RECOVERY_STATUS"
echo "📋 恢复报告: recovery_report_*.txt"
echo "💾 当前备份: $CURRENT_BACKUP (如需回滚)"
echo ""
echo "📝 后续步骤:"
echo "1. 检查配置: nano .env"
echo "2. 验证系统: $0 --check"
echo "3. 启动服务: ./start_production.sh"
echo ""
echo "✅ 灾难恢复系统执行完成"