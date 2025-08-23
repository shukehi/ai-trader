#!/bin/bash

# VS Code配置验证和修复脚本
# 确保VS Code远程开发配置完整且格式正确

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

log_header() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# 配置变量
PROJECT_DIR="/opt/ai-trader"
VSCODE_DIR="$PROJECT_DIR/.vscode"
GITHUB_RAW_BASE="https://raw.githubusercontent.com/shukehi/ai-trader/main/.vscode"

log_header "VS Code配置验证和修复工具"
echo "项目目录: $PROJECT_DIR"
echo "配置目录: $VSCODE_DIR"
echo "============================================"

# 创建.vscode目录
create_vscode_directory() {
    log_info "创建VS Code配置目录..."
    
    if [[ ! -d "$VSCODE_DIR" ]]; then
        mkdir -p "$VSCODE_DIR"
        log_success "VS Code配置目录已创建"
    else
        log_success "VS Code配置目录已存在"
    fi
}

# 验证JSON格式
validate_json() {
    local file_path="$1"
    local file_name=$(basename "$file_path")
    
    if [[ -f "$file_path" ]]; then
        if python3 -m json.tool "$file_path" > /dev/null 2>&1; then
            log_success "✓ $file_name JSON格式正确"
            return 0
        else
            log_warning "✗ $file_name JSON格式错误"
            return 1
        fi
    else
        log_warning "✗ $file_name 文件不存在"
        return 1
    fi
}

# 下载配置文件
download_config_file() {
    local filename="$1"
    local url="$GITHUB_RAW_BASE/$filename"
    local target_path="$VSCODE_DIR/$filename"
    
    log_info "下载 $filename..."
    
    # 尝试使用curl下载
    if command -v curl >/dev/null 2>&1; then
        if curl -fsSL "$url" -o "$target_path"; then
            log_success "✓ $filename 下载成功"
            return 0
        else
            log_error "✗ $filename 下载失败 (curl)"
        fi
    fi
    
    # 备选：使用wget下载
    if command -v wget >/dev/null 2>&1; then
        if wget -q "$url" -O "$target_path"; then
            log_success "✓ $filename 下载成功"
            return 0
        else
            log_error "✗ $filename 下载失败 (wget)"
        fi
    fi
    
    return 1
}

# 创建嵌入式备份配置
create_embedded_config() {
    local filename="$1"
    local target_path="$VSCODE_DIR/$filename"
    
    log_info "创建嵌入式 $filename 配置..."
    
    case "$filename" in
        "settings.json")
            cat > "$target_path" << 'EOF'
{
    "python.defaultInterpreterPath": "/opt/ai-trader/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "terminal.integrated.cwd": "/opt/ai-trader",
    "files.watcherExclude": {
        "**/venv/**": true,
        "**/logs/**": true,
        "**/data/cache/**": true,
        "**/__pycache__/**": true
    },
    "editor.rulers": [120],
    "editor.tabSize": 4,
    "files.autoSave": "onFocusChange"
}
EOF
            ;;
        "extensions.json")
            cat > "$target_path" << 'EOF'
{
    "recommendations": [
        "ms-python.python",
        "ms-vscode-remote.remote-ssh",
        "ms-vscode-remote.remote-ssh-edit",
        "eamodio.gitlens",
        "rangav.vscode-thunder-client",
        "ms-vscode.vscode-json"
    ]
}
EOF
            ;;
        "launch.json")
            cat > "$target_path" << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "AI Trader - Quick Analysis",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "args": ["--symbol", "ETHUSDT", "--mode", "quick"],
            "console": "integratedTerminal",
            "cwd": "/opt/ai-trader"
        },
        {
            "name": "AI Trader - Trading Mode",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "args": ["--enable-trading", "--signal-only"],
            "console": "integratedTerminal",
            "cwd": "/opt/ai-trader"
        }
    ]
}
EOF
            ;;
        "tasks.json")
            cat > "$target_path" << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Validate System Configuration",
            "type": "shell",
            "command": "source venv/bin/activate && python -c \"from config import Settings; Settings.validate()\"",
            "group": "test",
            "options": {
                "cwd": "/opt/ai-trader"
            }
        },
        {
            "label": "Quick VPA Analysis",
            "type": "shell",
            "command": "source venv/bin/activate && python main.py --symbol ETHUSDT --mode quick",
            "group": "build",
            "options": {
                "cwd": "/opt/ai-trader"
            }
        }
    ]
}
EOF
            ;;
        *)
            log_error "未知的配置文件: $filename"
            return 1
            ;;
    esac
    
    log_success "✓ 嵌入式 $filename 创建成功"
    return 0
}

# 修复配置文件
fix_config_file() {
    local filename="$1"
    local target_path="$VSCODE_DIR/$filename"
    
    log_info "修复 $filename..."
    
    # 首先尝试从GitHub下载
    if download_config_file "$filename"; then
        if validate_json "$target_path"; then
            return 0
        else
            log_warning "$filename 下载的文件格式有问题，使用嵌入式配置"
        fi
    fi
    
    # 如果下载失败或格式错误，使用嵌入式配置
    if create_embedded_config "$filename"; then
        if validate_json "$target_path"; then
            return 0
        else
            log_error "$filename 嵌入式配置也有问题"
            return 1
        fi
    fi
    
    return 1
}

# 验证和修复所有配置文件
fix_all_configs() {
    local config_files=("settings.json" "extensions.json" "launch.json" "tasks.json")
    local success_count=0
    local total_count=${#config_files[@]}
    
    log_header "验证和修复VS Code配置文件"
    
    for config_file in "${config_files[@]}"; do
        echo
        if validate_json "$VSCODE_DIR/$config_file"; then
            ((success_count++))
        else
            if fix_config_file "$config_file"; then
                ((success_count++))
            fi
        fi
    done
    
    echo
    log_info "修复完成: $success_count/$total_count 文件正常"
    
    if [[ $success_count -eq $total_count ]]; then
        log_success "所有VS Code配置文件都已就绪！"
        return 0
    else
        log_warning "部分配置文件仍有问题，但基本功能应该可用"
        return 1
    fi
}

# 设置权限
set_permissions() {
    log_info "设置配置文件权限..."
    
    # 确保配置文件可读写
    if [[ -d "$VSCODE_DIR" ]]; then
        find "$VSCODE_DIR" -type f -name "*.json" -exec chmod 644 {} \;
        log_success "权限设置完成"
    fi
}

# 验证配置完整性
verify_configuration() {
    log_header "验证VS Code配置完整性"
    
    local required_files=("settings.json" "extensions.json" "launch.json" "tasks.json")
    local valid_files=0
    
    for file in "${required_files[@]}"; do
        if validate_json "$VSCODE_DIR/$file"; then
            ((valid_files++))
        fi
    done
    
    echo
    if [[ $valid_files -eq ${#required_files[@]} ]]; then
        log_success "✅ VS Code配置验证通过 ($valid_files/${#required_files[@]})"
        
        echo
        log_info "配置文件列表:"
        ls -la "$VSCODE_DIR/"
        
        echo
        log_info "下一步:"
        echo "1. 重启VS Code远程连接"
        echo "2. 安装推荐扩展"
        echo "3. 使用调试配置和任务"
        
        return 0
    else
        log_warning "⚠️ VS Code配置部分有问题 ($valid_files/${#required_files[@]})"
        return 1
    fi
}

# 主函数
main() {
    # 检查项目目录
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    # 执行修复流程
    create_vscode_directory
    fix_all_configs
    set_permissions
    verify_configuration
    
    local exit_code=$?
    
    echo
    if [[ $exit_code -eq 0 ]]; then
        log_success "🎉 VS Code配置修复完成！"
    else
        log_warning "⚠️ VS Code配置修复完成，但可能存在问题"
    fi
    
    exit $exit_code
}

# 显示使用帮助
show_help() {
    echo "VS Code配置验证和修复脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help    显示此帮助信息"
    echo "  -f, --force   强制重新创建所有配置文件"
    echo
    echo "功能:"
    echo "  - 验证VS Code配置文件JSON格式"
    echo "  - 自动下载缺失或损坏的配置文件"
    echo "  - 提供嵌入式备份配置"
    echo "  - 设置正确的文件权限"
}

# 解析命令行参数
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_RECREATE=true
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 如果强制重建，先删除现有配置
if [[ "$FORCE_RECREATE" == "true" ]]; then
    log_warning "强制重建模式：删除现有配置"
    rm -rf "$VSCODE_DIR"
fi

# 执行主函数
main