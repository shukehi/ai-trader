#!/bin/bash
# ETH永续合约AI分析助手 - 备份和容灾系统
# 功能：配置备份、日志备份、结果备份、系统恢复

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS=30

echo "🛡️ ETH永续合约AI分析助手 - 备份系统"
echo "时间: $(date)"
echo "备份目录: $BACKUP_DIR"
echo "============================================"

# 1. 创建备份目录
echo "📁 创建备份目录..."
mkdir -p "$BACKUP_DIR"/{config,logs,results,scripts}

# 2. 备份配置文件
echo "⚙️ 备份配置文件..."
cp -r config/* "$BACKUP_DIR/config/" 2>/dev/null || echo "   注意: config目录为空或不存在"
cp .env "$BACKUP_DIR/config/.env.backup" 2>/dev/null || echo "   注意: .env文件不存在"
cp requirements.txt "$BACKUP_DIR/config/" 2>/dev/null
cp CLAUDE.md "$BACKUP_DIR/config/" 2>/dev/null || true
cp README.md "$BACKUP_DIR/config/" 2>/dev/null || true

# 3. 备份重要脚本
echo "🔧 备份脚本文件..."
cp -r deployment "$BACKUP_DIR/scripts/" 2>/dev/null || true
cp -r monitoring "$BACKUP_DIR/scripts/" 2>/dev/null || true
cp -r utils "$BACKUP_DIR/scripts/" 2>/dev/null || true
cp start_production.sh "$BACKUP_DIR/scripts/" 2>/dev/null || true

# 4. 备份日志文件
echo "📝 备份日志文件..."
if [ -d "logs" ]; then
    # 只备份最近7天的日志
    find logs -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
    find logs -name "*.jsonl" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
    echo "   ✅ 已备份最近7天的日志文件"
else
    echo "   注意: logs目录不存在"
fi

# 5. 备份分析结果
echo "📊 备份分析结果..."
if [ -d "results" ]; then
    # 只备份最近30天的结果
    find results -name "*.json" -mtime -30 -exec cp {} "$BACKUP_DIR/results/" \; 2>/dev/null || true
    echo "   ✅ 已备份最近30天的分析结果"
else
    echo "   注意: results目录不存在"
fi

# 6. 创建系统状态快照
echo "📸 创建系统状态快照..."
cat > "$BACKUP_DIR/system_snapshot.txt" << EOF
# ETH永续合约AI分析助手 - 系统快照
备份时间: $(date)
备份脚本: $0
操作用户: $(whoami)
系统信息: $(uname -a)
Python版本: $(python3 --version 2>/dev/null || echo "Python not found")
工作目录: $(pwd)

# 虚拟环境状态
虚拟环境: $([ -d "venv" ] && echo "存在" || echo "不存在")

# 目录结构
EOF

ls -la >> "$BACKUP_DIR/system_snapshot.txt"

# 7. 测试核心组件（如果可能）
echo "🧪 测试核心组件..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from config import Settings
    Settings.validate()
    print('   ✅ 配置验证通过')
    
    with open('$BACKUP_DIR/component_test.txt', 'w') as f:
        f.write('配置验证: 通过\\n')
        f.write('备份时间: $(date)\\n')
except Exception as e:
    print(f'   ⚠️ 配置验证失败: {e}')
    with open('$BACKUP_DIR/component_test.txt', 'w') as f:
        f.write('配置验证: 失败\\n')
        f.write(f'错误: {e}\\n')
" 2>/dev/null || echo "   ⚠️ 组件测试跳过"
else
    echo "   ⚠️ 虚拟环境不存在，跳过组件测试"
fi

# 8. 压缩备份
echo "🗜️ 压缩备份文件..."
cd backups
tar -czf "$(basename $BACKUP_DIR).tar.gz" "$(basename $BACKUP_DIR)"
rm -rf "$(basename $BACKUP_DIR)"
cd ..

COMPRESSED_SIZE=$(du -h "backups/$(basename $BACKUP_DIR).tar.gz" | cut -f1)
echo "   ✅ 备份压缩完成: $COMPRESSED_SIZE"

# 9. 清理旧备份
echo "🧹 清理旧备份..."
find backups -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
OLD_COUNT=$(find backups -name "*.tar.gz" | wc -l)
echo "   📊 保留备份文件: $OLD_COUNT 个"

# 10. 生成备份报告
echo "📋 生成备份报告..."
cat > "backups/latest_backup_report.txt" << EOF
# ETH永续合约AI分析助手 - 备份报告

备份时间: $(date)
备份文件: $(basename $BACKUP_DIR).tar.gz  
备份大小: $COMPRESSED_SIZE
保留期限: $RETENTION_DAYS 天

备份内容:
- 配置文件 (config/, .env, requirements.txt, 文档)
- 脚本文件 (deployment/, monitoring/, utils/)
- 日志文件 (最近7天)
- 分析结果 (最近30天)
- 系统快照

总备份数: $OLD_COUNT 个
磁盘使用: $(du -sh backups | cut -f1)

状态: ✅ 备份成功完成
EOF

echo ""
echo "🎯 备份完成!"
echo "============================================"
echo "📊 备份统计:"
echo "   备份文件: backups/$(basename $BACKUP_DIR).tar.gz"
echo "   备份大小: $COMPRESSED_SIZE"
echo "   保留数量: $OLD_COUNT 个"
echo "   磁盘使用: $(du -sh backups 2>/dev/null | cut -f1 || echo "未知")"
echo ""
echo "📋 快速恢复命令:"
echo "   tar -xzf backups/$(basename $BACKUP_DIR).tar.gz -C restore/"
echo "   # 然后手动恢复配置文件和脚本"
echo ""
echo "✅ 备份系统执行完成"