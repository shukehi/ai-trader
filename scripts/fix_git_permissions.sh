#!/bin/bash

# Git权限管理和修复脚本
# 解决"detected dubious ownership"和权限问题

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
CURRENT_USER=$(whoami)

log_header "Git权限管理和修复工具"
echo "项目目录: $PROJECT_DIR"
echo "当前用户: $CURRENT_USER"
echo "============================================"

# 检查Git仓库状态
check_git_status() {
    log_info "检查Git仓库状态..."
    
    if [[ ! -d "$PROJECT_DIR/.git" ]]; then
        log_error "不是Git仓库: $PROJECT_DIR"
        return 1
    fi
    
    # 尝试执行Git命令
    cd "$PROJECT_DIR"
    
    if git status >/dev/null 2>&1; then
        log_success "Git仓库状态正常"
        return 0
    else
        log_warning "Git仓库存在权限问题"
        return 1
    fi
}

# 修复Git安全配置
fix_git_safe_directory() {
    log_info "修复Git安全目录配置..."
    
    # 添加安全目录到用户配置
    if git config --global --get safe.directory | grep -q "$PROJECT_DIR"; then
        log_success "安全目录已配置"
    else
        git config --global --add safe.directory "$PROJECT_DIR"
        log_success "已添加安全目录: $PROJECT_DIR"
    fi
    
    # 如果是root用户，也为系统配置
    if [[ "$CURRENT_USER" == "root" ]]; then
        if git config --system --get safe.directory | grep -q "$PROJECT_DIR" 2>/dev/null; then
            log_success "系统级安全目录已配置"
        else
            git config --system --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
            log_success "已添加系统级安全目录"
        fi
    fi
}

# 修复Git目录权限
fix_git_ownership() {
    log_info "修复Git目录权限..."
    
    # 检测项目目录的实际所有者
    local dir_owner=$(stat -c '%U' "$PROJECT_DIR" 2>/dev/null || stat -f '%Su' "$PROJECT_DIR" 2>/dev/null)
    local dir_group=$(stat -c '%G' "$PROJECT_DIR" 2>/dev/null || stat -f '%Sg' "$PROJECT_DIR" 2>/dev/null)
    
    log_info "项目目录所有者: $dir_owner:$dir_group"
    
    # 如果当前用户是root，可以修复权限
    if [[ "$CURRENT_USER" == "root" ]]; then
        log_info "使用root权限修复Git目录权限..."
        
        # 修复.git目录权限
        if [[ -d "$PROJECT_DIR/.git" ]]; then
            chown -R "$dir_owner:$dir_group" "$PROJECT_DIR/.git"
            log_success ".git目录权限已修复"
        fi
        
        # 确保当前用户可以访问
        if [[ "$CURRENT_USER" != "$dir_owner" ]]; then
            # 添加ACL权限（如果支持）
            if command -v setfacl >/dev/null 2>&1; then
                setfacl -R -m u:"$CURRENT_USER":rwx "$PROJECT_DIR/.git" 2>/dev/null || true
                log_success "已添加当前用户的访问权限"
            fi
        fi
    else
        log_warning "需要root权限才能修复目录所有者"
        log_info "当前只能配置Git安全目录"
    fi
}

# 修复Git配置权限
fix_git_config_permissions() {
    log_info "修复Git配置权限..."
    
    # 修复用户Git配置文件权限
    local git_config="$HOME/.gitconfig"
    if [[ -f "$git_config" ]]; then
        chmod 644 "$git_config" 2>/dev/null || true
        log_success "用户Git配置权限已修复"
    fi
    
    # 如果是root用户，修复系统Git配置
    if [[ "$CURRENT_USER" == "root" ]]; then
        local system_git_config="/etc/gitconfig"
        if [[ -f "$system_git_config" ]]; then
            chmod 644 "$system_git_config" 2>/dev/null || true
            log_success "系统Git配置权限已修复"
        fi
    fi
}

# 测试Git操作
test_git_operations() {
    log_info "测试Git操作..."
    
    cd "$PROJECT_DIR"
    
    # 测试基本Git命令
    local test_commands=(
        "git status"
        "git log --oneline -n 1"
        "git branch"
        "git remote -v"
    )
    
    local success_count=0
    local total_count=${#test_commands[@]}
    
    for cmd in "${test_commands[@]}"; do
        if eval "$cmd" >/dev/null 2>&1; then
            log_success "✓ $cmd"
            ((success_count++))
        else
            log_warning "✗ $cmd"
        fi
    done
    
    echo
    if [[ $success_count -eq $total_count ]]; then
        log_success "所有Git操作测试通过 ($success_count/$total_count)"
        return 0
    else
        log_warning "部分Git操作测试失败 ($success_count/$total_count)"
        return 1
    fi
}

# 显示当前Git配置
show_git_config() {
    log_info "当前Git配置:"
    echo
    
    # 显示安全目录配置
    log_info "安全目录配置:"
    git config --global --get-all safe.directory 2>/dev/null || echo "  (无全局安全目录配置)"
    
    if [[ "$CURRENT_USER" == "root" ]]; then
        git config --system --get-all safe.directory 2>/dev/null || echo "  (无系统安全目录配置)"
    fi
    
    echo
    
    # 显示基本Git配置
    log_info "基本Git配置:"
    git config --global user.name 2>/dev/null && echo "  用户名: $(git config --global user.name)" || true
    git config --global user.email 2>/dev/null && echo "  邮箱: $(git config --global user.email)" || true
    
    echo
    
    # 显示仓库状态
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        cd "$PROJECT_DIR"
        log_info "仓库状态:"
        echo "  分支: $(git branch --show-current 2>/dev/null || echo '未知')"
        echo "  远程仓库: $(git remote get-url origin 2>/dev/null || echo '未配置')"
        echo "  最后提交: $(git log --oneline -n 1 2>/dev/null || echo '无提交记录')"
    fi
}

# 执行完整的Git权限修复
perform_full_fix() {
    log_header "执行完整的Git权限修复"
    
    local fix_functions=(
        "fix_git_safe_directory"
        "fix_git_ownership"
        "fix_git_config_permissions"
    )
    
    for func in "${fix_functions[@]}"; do
        echo
        if $func; then
            log_success "✓ $func 完成"
        else
            log_warning "⚠ $func 部分完成或失败"
        fi
    done
    
    echo
    log_header "测试修复结果"
    test_git_operations
}

# 显示使用建议
show_recommendations() {
    log_header "使用建议"
    
    echo "1. 权限修复:"
    echo "   sudo $0 --fix     # 以root权限执行完整修复"
    echo
    
    echo "2. 如果仍有问题，尝试:"
    echo "   sudo chown -R \$(whoami):\$(whoami) $PROJECT_DIR/.git"
    echo "   git config --global --add safe.directory $PROJECT_DIR"
    echo
    
    echo "3. 对于开发用户权限问题:"
    echo "   sudo scripts/setup_remote_dev_user.sh"
    echo
    
    echo "4. 验证修复结果:"
    echo "   $0 --test"
}

# 主函数
main() {
    local action="${1:-check}"
    
    case "$action" in
        "--check"|"check")
            if check_git_status; then
                show_git_config
                log_success "Git权限检查完成：无问题"
            else
                show_git_config
                echo
                log_warning "Git权限检查完成：发现问题"
                show_recommendations
                exit 1
            fi
            ;;
        "--fix"|"fix")
            perform_full_fix
            ;;
        "--test"|"test")
            test_git_operations
            ;;
        "--config"|"config")
            show_git_config
            ;;
        "--help"|"help"|"-h")
            show_help
            ;;
        *)
            log_error "未知操作: $action"
            show_help
            exit 1
            ;;
    esac
}

# 显示帮助信息
show_help() {
    echo "Git权限管理和修复脚本"
    echo
    echo "用法: $0 [操作]"
    echo
    echo "操作:"
    echo "  check, --check     检查Git权限状态 (默认)"
    echo "  fix, --fix         执行完整的权限修复"
    echo "  test, --test       测试Git操作"
    echo "  config, --config   显示当前Git配置"
    echo "  help, --help, -h   显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                 # 检查权限状态"
    echo "  sudo $0 --fix      # 修复权限问题"
    echo "  $0 --test          # 测试Git操作"
}

# 检查项目目录
if [[ ! -d "$PROJECT_DIR" ]]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 执行主函数
main "$@"