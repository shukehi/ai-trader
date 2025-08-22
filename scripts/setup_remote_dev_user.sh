#!/bin/bash

# VPS远程开发用户配置脚本
# 用于设置AI交易系统的VS Code远程开发环境

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
DEV_USERNAME="ai-trader-dev"
PROJECT_DIR="/opt/ai-trader"
MAIN_USERNAME="ai-trader"

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        echo "使用命令: sudo $0"
        exit 1
    fi
}

# 创建开发用户
create_dev_user() {
    log_info "创建开发用户: $DEV_USERNAME"
    
    if id "$DEV_USERNAME" &>/dev/null; then
        log_warning "用户 $DEV_USERNAME 已存在，跳过创建"
    else
        # 创建用户（不创建家目录，使用系统默认shell）
        useradd -m -s /bin/bash "$DEV_USERNAME"
        
        # 设置临时密码（可选）
        echo "是否为用户 $DEV_USERNAME 设置密码？(y/n)"
        read -r -t 10 set_password || set_password="n"  # 10秒超时，默认跳过
        if [[ $set_password == "y" || $set_password == "Y" ]]; then
            if ! passwd "$DEV_USERNAME"; then
                log_warning "密码设置失败，将使用SSH密钥认证"
                log_info "请确保稍后配置SSH密钥"
            fi
        else
            log_info "跳过密码设置，将使用SSH密钥认证（推荐）"
        fi
        
        log_success "用户 $DEV_USERNAME 创建成功"
    fi
}

# 配置用户组权限
setup_user_groups() {
    log_info "配置用户组权限"
    
    # 添加到sudo组（可选的管理权限）
    usermod -aG sudo "$DEV_USERNAME"
    log_success "用户 $DEV_USERNAME 已添加到sudo组"
    
    # 添加到ai-trader组（如果存在）
    if getent group "$MAIN_USERNAME" > /dev/null 2>&1; then
        usermod -aG "$MAIN_USERNAME" "$DEV_USERNAME"
        log_success "用户 $DEV_USERNAME 已添加到 $MAIN_USERNAME 组"
    else
        log_warning "组 $MAIN_USERNAME 不存在，将创建并配置"
        groupadd "$MAIN_USERNAME"
        usermod -aG "$MAIN_USERNAME" "$DEV_USERNAME"
        
        # 如果ai-trader用户存在，也添加到组中
        if id "$MAIN_USERNAME" &>/dev/null; then
            usermod -aG "$MAIN_USERNAME" "$MAIN_USERNAME"
        fi
    fi
}

# 配置项目目录权限
setup_project_permissions() {
    log_info "配置项目目录权限: $PROJECT_DIR"
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log_error "项目目录 $PROJECT_DIR 不存在"
        log_info "请先部署AI交易系统到VPS"
        exit 1
    fi
    
    # 设置目录所有者为ai-trader用户和组
    chown -R "$MAIN_USERNAME:$MAIN_USERNAME" "$PROJECT_DIR"
    log_success "目录所有者设置完成"
    
    # 设置目录权限（775：所有者和组可读写执行，其他用户只读执行）
    chmod -R 775 "$PROJECT_DIR"
    log_success "目录权限设置完成"
    
    # 配置ACL权限（如果系统支持）
    if command -v setfacl >/dev/null 2>&1; then
        log_info "配置ACL权限"
        setfacl -R -m u:"$DEV_USERNAME":rwx "$PROJECT_DIR"
        setfacl -R -d -m u:"$DEV_USERNAME":rwx "$PROJECT_DIR"
        log_success "ACL权限配置完成"
    else
        log_warning "系统不支持ACL，使用传统权限管理"
    fi
    
    # 确保日志目录权限
    if [[ -d "$PROJECT_DIR/logs" ]]; then
        chmod -R 775 "$PROJECT_DIR/logs"
        chown -R "$MAIN_USERNAME:$MAIN_USERNAME" "$PROJECT_DIR/logs"
    fi
    
    # 确保缓存目录权限
    if [[ -d "$PROJECT_DIR/data/cache" ]]; then
        chmod -R 775 "$PROJECT_DIR/data/cache"
        chown -R "$MAIN_USERNAME:$MAIN_USERNAME" "$PROJECT_DIR/data/cache"
    fi
}

# 配置SSH目录
setup_ssh_directory() {
    log_info "配置SSH目录"
    
    DEV_HOME="/home/$DEV_USERNAME"
    SSH_DIR="$DEV_HOME/.ssh"
    
    # 创建SSH目录
    mkdir -p "$SSH_DIR"
    chown "$DEV_USERNAME:$DEV_USERNAME" "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    
    # 创建authorized_keys文件
    touch "$SSH_DIR/authorized_keys"
    chown "$DEV_USERNAME:$DEV_USERNAME" "$SSH_DIR/authorized_keys"
    chmod 600 "$SSH_DIR/authorized_keys"
    
    log_success "SSH目录配置完成"
    log_info "请将公钥添加到: $SSH_DIR/authorized_keys"
}

# 验证配置
verify_setup() {
    log_info "验证配置"
    
    # 检查用户是否存在
    if id "$DEV_USERNAME" &>/dev/null; then
        log_success "✓ 用户 $DEV_USERNAME 存在"
    else
        log_error "✗ 用户 $DEV_USERNAME 不存在"
        return 1
    fi
    
    # 检查用户组
    if groups "$DEV_USERNAME" | grep -q "$MAIN_USERNAME"; then
        log_success "✓ 用户在 $MAIN_USERNAME 组中"
    else
        log_error "✗ 用户不在 $MAIN_USERNAME 组中"
        return 1
    fi
    
    if groups "$DEV_USERNAME" | grep -q "sudo"; then
        log_success "✓ 用户具有sudo权限"
    else
        log_warning "⚠ 用户没有sudo权限"
    fi
    
    # 检查项目目录权限
    if sudo -u "$DEV_USERNAME" test -r "$PROJECT_DIR"; then
        log_success "✓ 用户可读取项目目录"
    else
        log_error "✗ 用户无法读取项目目录"
        return 1
    fi
    
    if sudo -u "$DEV_USERNAME" test -w "$PROJECT_DIR"; then
        log_success "✓ 用户可写入项目目录"
    else
        log_error "✗ 用户无法写入项目目录"
        return 1
    fi
    
    # 检查Python环境
    if sudo -u "$DEV_USERNAME" test -f "$PROJECT_DIR/venv/bin/python"; then
        log_success "✓ Python虚拟环境存在"
    else
        log_warning "⚠ Python虚拟环境不存在"
    fi
    
    log_success "配置验证完成"
}

# 显示下一步操作
show_next_steps() {
    echo
    log_info "=== 配置完成 ==="
    echo
    log_info "下一步操作："
    echo "1. 在本地生成SSH密钥："
    echo "   ssh-keygen -t ed25519 -C 'ai-trader-remote-dev' -f ~/.ssh/ai-trader-dev"
    echo
    echo "2. 上传公钥到VPS："
    echo "   ssh-copy-id -i ~/.ssh/ai-trader-dev.pub $DEV_USERNAME@$(hostname -I | awk '{print $1}')"
    echo
    echo "3. 测试SSH连接："
    echo "   ssh -i ~/.ssh/ai-trader-dev $DEV_USERNAME@$(hostname -I | awk '{print $1}')"
    echo
    echo "4. 配置VS Code SSH连接："
    echo "   参考文档: docs/setup/REMOTE_SSH_SETUP.md"
    echo
    log_info "用户信息："
    echo "   用户名: $DEV_USERNAME"
    echo "   项目目录: $PROJECT_DIR"
    echo "   SSH目录: /home/$DEV_USERNAME/.ssh"
    echo
}

# 主函数
main() {
    log_info "开始配置VPS远程开发环境"
    log_info "目标用户: $DEV_USERNAME"
    log_info "项目目录: $PROJECT_DIR"
    echo
    
    check_root
    create_dev_user
    setup_user_groups
    setup_project_permissions
    setup_ssh_directory
    
    echo
    verify_setup
    
    if [[ $? -eq 0 ]]; then
        show_next_steps
    else
        log_error "配置验证失败，请检查上述错误"
        exit 1
    fi
}

# 显示使用帮助
show_help() {
    echo "VPS远程开发用户配置脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help           显示此帮助信息"
    echo "  -u, --username USER  指定开发用户名 (默认: ai-trader-dev)"
    echo "  -d, --dir DIR        指定项目目录 (默认: /opt/ai-trader)"
    echo
    echo "示例:"
    echo "  $0                                    # 使用默认配置"
    echo "  $0 -u mydev -d /home/user/ai-trader   # 自定义配置"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--username)
            DEV_USERNAME="$2"
            shift 2
            ;;
        -d|--dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行主函数
main

log_success "VPS远程开发环境配置完成！"