#!/bin/bash

# 一键修复所有环境配置问题
# 自动检测和修复远程开发环境中的常见问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
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
    echo -e "${PURPLE}🚀 $1${NC}"
}

log_section() {
    echo -e "${CYAN}📋 $1${NC}"
}

# 配置变量
PROJECT_DIR="/opt/ai-trader"
CURRENT_USER=$(whoami)

# 显示启动横幅
show_banner() {
    echo -e "${PURPLE}"
    echo "=========================================="
    echo "🔧 AI交易系统环境一键修复工具"
    echo "=========================================="
    echo -e "${NC}"
    echo "项目目录: $PROJECT_DIR"
    echo "当前用户: $CURRENT_USER"
    echo "执行时间: $(date)"
    echo "=========================================="
}

# 检查运行环境
check_environment() {
    log_section "环境检查"
    
    # 检查项目目录
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        log_info "请先部署AI交易系统"
        exit 1
    fi
    
    # 检查是否在项目目录中
    cd "$PROJECT_DIR"
    log_success "项目目录检查通过"
    
    # 检查脚本是否存在
    local required_scripts=(
        "scripts/fix_git_permissions.sh"
        "scripts/fix_vscode_config.sh"
        "scripts/verify_remote_setup.py"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ -f "$script" ]]; then
            log_success "✓ $script"
        else
            log_warning "✗ $script (缺失，将跳过相关修复)"
        fi
    done
    
    echo
}

# 修复Git权限问题
fix_git_issues() {
    log_section "修复Git权限问题"
    
    if [[ -f "scripts/fix_git_permissions.sh" ]]; then
        if bash scripts/fix_git_permissions.sh --fix; then
            log_success "Git权限修复完成"
        else
            log_warning "Git权限修复部分完成"
        fi
    else
        log_info "手动修复Git权限..."
        
        # 基本的Git权限修复
        if [[ "$CURRENT_USER" == "root" ]]; then
            git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
            if [[ -d ".git" ]]; then
                chown -R aitrader:aitrader .git 2>/dev/null || true
                log_success "基础Git权限修复完成"
            fi
        else
            git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
            log_success "Git安全目录配置完成"
        fi
    fi
    
    echo
}

# 修复VS Code配置
fix_vscode_issues() {
    log_section "修复VS Code配置"
    
    if [[ -f "scripts/fix_vscode_config.sh" ]]; then
        if bash scripts/fix_vscode_config.sh; then
            log_success "VS Code配置修复完成"
        else
            log_warning "VS Code配置修复部分完成"
        fi
    else
        log_info "手动创建基础VS Code配置..."
        
        # 创建基础配置
        mkdir -p .vscode
        
        # 创建简化的settings.json
        cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "/opt/ai-trader/venv/bin/python",
    "terminal.integrated.cwd": "/opt/ai-trader",
    "files.autoSave": "onFocusChange"
}
EOF
        
        # 创建简化的extensions.json
        cat > .vscode/extensions.json << 'EOF'
{
    "recommendations": [
        "ms-python.python",
        "ms-vscode-remote.remote-ssh"
    ]
}
EOF
        
        log_success "基础VS Code配置创建完成"
    fi
    
    echo
}

# 修复Python环境
fix_python_environment() {
    log_section "修复Python环境"
    
    # 检查虚拟环境
    if [[ ! -d "venv" ]]; then
        log_info "创建Python虚拟环境..."
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境并安装核心依赖
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip setuptools wheel
    
    # 安装核心依赖
    if [[ -f "requirements-core.txt" ]]; then
        log_info "安装核心依赖..."
        if pip install -r requirements-core.txt; then
            log_success "核心依赖安装完成"
        else
            log_warning "核心依赖安装部分失败，尝试逐个安装"
            
            # 关键依赖逐个安装
            local core_packages=(
                "openai>=1.0.0"
                "python-dotenv>=1.0.0" 
                "requests>=2.31.0"
                "pandas>=2.0.0"
                "numpy>=1.24.0"
                "ccxt>=4.0.0"
            )
            
            for package in "${core_packages[@]}"; do
                if pip install "$package"; then
                    log_success "✓ $package"
                else
                    log_warning "✗ $package"
                fi
            done
        fi
    else
        log_warning "requirements-core.txt不存在，跳过依赖安装"
    fi
    
    # 验证核心模块
    if python -c "import pandas, numpy, ccxt, requests; print('Core modules OK')" 2>/dev/null; then
        log_success "Python环境验证通过"
    else
        log_warning "Python环境验证未通过"
    fi
    
    echo
}

# 修复用户权限
fix_user_permissions() {
    log_section "修复用户权限"
    
    # 如果是root用户，可以修复权限
    if [[ "$CURRENT_USER" == "root" ]]; then
        if [[ -f "scripts/setup_remote_dev_user.sh" ]]; then
            log_info "运行用户配置脚本..."
            bash scripts/setup_remote_dev_user.sh || true
        else
            log_info "手动配置基本权限..."
            
            # 确保基本权限
            chown -R aitrader:aitrader "$PROJECT_DIR" 2>/dev/null || true
            chmod -R 775 "$PROJECT_DIR" 2>/dev/null || true
            
            # 如果ai-trader-dev用户存在，添加权限
            if id "ai-trader-dev" &>/dev/null; then
                usermod -aG aitrader ai-trader-dev 2>/dev/null || true
                log_success "用户权限配置完成"
            fi
        fi
    else
        log_info "当前用户不是root，跳过用户权限修复"
    fi
    
    echo
}

# 清理临时文件
cleanup_temp_files() {
    log_section "清理临时文件"
    
    # 清理pip安装产生的临时文件
    find "$PROJECT_DIR" -name "=*" -type f -delete 2>/dev/null || true
    
    # 清理Python缓存
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理其他临时文件
    find "$PROJECT_DIR" -name "*.tmp" -delete 2>/dev/null || true
    find "$PROJECT_DIR" -name ".DS_Store" -delete 2>/dev/null || true
    
    log_success "临时文件清理完成"
    echo
}

# 运行环境验证
run_verification() {
    log_section "运行环境验证"
    
    if [[ -f "scripts/verify_remote_setup.py" ]]; then
        if python3 scripts/verify_remote_setup.py; then
            log_success "环境验证通过"
        else
            log_warning "环境验证发现问题，但已执行修复"
        fi
    else
        log_info "验证脚本不存在，进行基础验证"
        
        # 基础验证
        local checks_passed=0
        local total_checks=4
        
        # 检查项目目录
        if [[ -d "$PROJECT_DIR" ]]; then
            log_success "✓ 项目目录存在"
            ((checks_passed++))
        fi
        
        # 检查Python环境
        if [[ -f "venv/bin/python" ]]; then
            log_success "✓ Python虚拟环境存在"
            ((checks_passed++))
        fi
        
        # 检查Git仓库
        if [[ -d ".git" ]]; then
            log_success "✓ Git仓库存在"
            ((checks_passed++))
        fi
        
        # 检查VS Code配置
        if [[ -d ".vscode" ]]; then
            log_success "✓ VS Code配置存在"
            ((checks_passed++))
        fi
        
        local success_rate=$((checks_passed * 100 / total_checks))
        echo
        log_info "基础验证完成: $checks_passed/$total_checks ($success_rate%)"
    fi
    
    echo
}

# 显示修复总结
show_summary() {
    log_header "修复总结"
    
    echo "修复操作已完成，包括："
    echo "  🔧 Git权限配置"
    echo "  📝 VS Code配置"
    echo "  🐍 Python环境"
    echo "  👤 用户权限"
    echo "  🧹 临时文件清理"
    echo
    
    log_info "下一步操作："
    echo "1. 重新验证环境: python3 scripts/verify_remote_setup.py"
    echo "2. 测试AI功能: python3 main.py --symbol ETHUSDT --mode quick"
    echo "3. 重启VS Code远程连接"
    echo
    
    log_success "🎉 环境修复完成！"
}

# 显示使用帮助
show_help() {
    echo "AI交易系统环境一键修复工具"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help        显示此帮助信息"
    echo "  -q, --quiet       静默模式，减少输出"
    echo "  --git-only        仅修复Git权限问题"
    echo "  --vscode-only     仅修复VS Code配置问题"
    echo "  --python-only     仅修复Python环境问题"
    echo "  --verify-only     仅运行环境验证"
    echo
    echo "功能:"
    echo "  - 自动检测和修复常见环境配置问题"
    echo "  - Git权限和安全目录配置"
    echo "  - VS Code远程开发配置"
    echo "  - Python虚拟环境和依赖"
    echo "  - 用户权限和目录访问"
    echo "  - 临时文件清理"
    echo
    echo "示例:"
    echo "  $0                # 执行完整修复"
    echo "  sudo $0           # 以root权限执行(推荐)"
    echo "  $0 --git-only     # 只修复Git问题"
}

# 主函数
main() {
    local git_only=false
    local vscode_only=false
    local python_only=false
    local verify_only=false
    local quiet=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quiet)
                quiet=true
                shift
                ;;
            --git-only)
                git_only=true
                shift
                ;;
            --vscode-only)
                vscode_only=true
                shift
                ;;
            --python-only)
                python_only=true
                shift
                ;;
            --verify-only)
                verify_only=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示横幅（静默模式下跳过）
    if [[ "$quiet" != "true" ]]; then
        show_banner
        echo
    fi
    
    # 环境检查
    check_environment
    
    # 根据参数执行相应修复
    if [[ "$verify_only" == "true" ]]; then
        run_verification
    elif [[ "$git_only" == "true" ]]; then
        fix_git_issues
    elif [[ "$vscode_only" == "true" ]]; then
        fix_vscode_issues
    elif [[ "$python_only" == "true" ]]; then
        fix_python_environment
    else
        # 执行完整修复流程
        fix_git_issues
        fix_vscode_issues
        fix_python_environment
        fix_user_permissions
        cleanup_temp_files
        run_verification
        
        if [[ "$quiet" != "true" ]]; then
            show_summary
        fi
    fi
    
    log_success "修复操作完成"
}

# 执行主函数
main "$@"