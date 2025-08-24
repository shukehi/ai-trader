#!/usr/bin/env python3
"""
远程开发环境验证脚本
验证VS Code远程SSH开发环境是否正确配置

使用方法:
    python scripts/verify_remote_setup.py
    python scripts/verify_remote_setup.py --detailed
"""

import os
import sys
import subprocess
import json
import pwd
import grp
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Any

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_colored(message: str, color: str = Colors.NC):
    """打印彩色消息"""
    print(f"{color}{message}{Colors.NC}")

def print_success(message: str):
    """打印成功消息"""
    print_colored(f"✅ {message}", Colors.GREEN)

def print_error(message: str):
    """打印错误消息"""
    print_colored(f"❌ {message}", Colors.RED)

def print_warning(message: str):
    """打印警告消息"""
    print_colored(f"⚠️  {message}", Colors.YELLOW)

def print_info(message: str):
    """打印信息消息"""
    print_colored(f"ℹ️  {message}", Colors.BLUE)

def print_header(message: str):
    """打印标题"""
    print_colored(f"\n{'='*60}", Colors.CYAN)
    print_colored(f" {message}", Colors.CYAN)
    print_colored(f"{'='*60}", Colors.CYAN)

class RemoteDevValidator:
    """远程开发环境验证器"""
    
    def __init__(self, project_dir: str = "/opt/ai-trader", dev_user: str = "ai-trader-dev"):
        self.project_dir = Path(project_dir)
        self.dev_user = dev_user
        self.current_user = pwd.getpwuid(os.getuid()).pw_name
        self.results: dict[str, bool] = {}
        
    def run_command(self, command: str, capture_output: bool = True) -> Tuple[bool, str]:
        """运行命令并返回结果"""
        try:
            if capture_output:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                return result.returncode == 0, result.stdout.strip()
            else:
                result = subprocess.run(command, shell=True, timeout=30)
                return result.returncode == 0, ""
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

    def check_user_existence(self) -> bool:
        """检查开发用户是否存在"""
        print_header("用户账户验证")
        
        try:
            pwd.getpwnam(self.dev_user)
            print_success(f"开发用户 '{self.dev_user}' 存在")
            self.results['user_exists'] = True
            return True
        except KeyError:
            print_error(f"开发用户 '{self.dev_user}' 不存在")
            print_info("请运行: sudo scripts/setup_remote_dev_user.sh")
            self.results['user_exists'] = False
            return False

    def check_user_groups(self) -> bool:
        """检查用户组配置"""
        if not self.results.get('user_exists', False):
            return False
            
        try:
            user_info = pwd.getpwnam(self.dev_user)
            user_groups = [g.gr_name for g in grp.getgrall() if self.dev_user in g.gr_mem]
            user_groups.append(grp.getgrgid(user_info.pw_gid).gr_name)
            
            required_groups = ['ai-trader', 'sudo']
            missing_groups = [group for group in required_groups if group not in user_groups]
            
            if not missing_groups:
                print_success(f"用户组配置正确: {', '.join(user_groups)}")
                self.results['user_groups'] = True
                return True
            else:
                print_warning(f"缺少用户组: {', '.join(missing_groups)}")
                print_info("当前用户组: " + ', '.join(user_groups))
                self.results['user_groups'] = False
                return False
                
        except Exception as e:
            print_error(f"检查用户组时出错: {e}")
            self.results['user_groups'] = False
            return False

    def check_project_directory(self) -> bool:
        """检查项目目录权限"""
        print_header("项目目录权限验证")
        
        if not self.project_dir.exists():
            print_error(f"项目目录不存在: {self.project_dir}")
            self.results['project_dir'] = False
            return False
            
        # 检查读权限
        if os.access(self.project_dir, os.R_OK):
            print_success("项目目录可读")
        else:
            print_error("项目目录不可读")
            self.results['project_dir'] = False
            return False
            
        # 检查写权限
        if os.access(self.project_dir, os.W_OK):
            print_success("项目目录可写")
        else:
            print_error("项目目录不可写")
            self.results['project_dir'] = False
            return False
            
        # 检查关键子目录
        critical_dirs = ['logs', 'data', 'venv', '.vscode']
        for dir_name in critical_dirs:
            dir_path = self.project_dir / dir_name
            if dir_path.exists():
                print_success(f"关键目录存在: {dir_name}")
            else:
                print_warning(f"关键目录缺失: {dir_name}")
                
        self.results['project_dir'] = True
        return True

    def check_python_environment(self) -> bool:
        """检查Python虚拟环境"""
        print_header("Python环境验证")
        
        venv_python = self.project_dir / "venv" / "bin" / "python"
        if not venv_python.exists():
            print_error("Python虚拟环境不存在")
            print_info("请运行: python3 -m venv venv")
            self.results['python_env'] = False
            return False
            
        # 检查Python版本
        success, output = self.run_command(f"{venv_python} --version")
        if success:
            print_success(f"Python版本: {output}")
        else:
            print_error("无法获取Python版本")
            self.results['python_env'] = False
            return False
            
        # 检查关键依赖
        success, _ = self.run_command(f"{venv_python} -c 'import ccxt, pandas, requests'")
        if success:
            print_success("关键Python依赖包可用")
        else:
            print_error("关键Python依赖包缺失")
            print_info("请运行: pip install -r requirements.txt")
            self.results['python_env'] = False
            return False
            
        # 检查AI交易系统配置
        config_check = f"{venv_python} -c 'from config import Settings; Settings.validate(); print(\"Config OK\")'"
        success, output = self.run_command(config_check)
        if success and "Config OK" in output:
            print_success("AI交易系统配置有效")
        else:
            print_warning("AI交易系统配置可能有问题")
            print_info("请检查.env文件和API密钥配置")
            
        self.results['python_env'] = True
        return True

    def check_ssh_configuration(self) -> bool:
        """检查SSH配置"""
        print_header("SSH配置验证")
        
        # 检查SSH目录
        if self.current_user == self.dev_user:
            ssh_dir = Path.home() / ".ssh"
            if ssh_dir.exists():
                print_success("SSH目录存在")
                
                # 检查authorized_keys
                auth_keys = ssh_dir / "authorized_keys"
                if auth_keys.exists() and auth_keys.stat().st_size > 0:
                    print_success("SSH公钥已配置")
                    self.results['ssh_config'] = True
                    return True
                else:
                    print_warning("SSH公钥未配置")
                    print_info("请将公钥添加到 ~/.ssh/authorized_keys")
            else:
                print_warning("SSH目录不存在")
        else:
            print_info(f"当前用户是 {self.current_user}，跳过SSH配置检查")
            
        self.results['ssh_config'] = False
        return False

    def check_vscode_configuration(self) -> bool:
        """检查VS Code配置"""
        print_header("VS Code配置验证")
        
        vscode_dir = self.project_dir / ".vscode"
        if not vscode_dir.exists():
            print_error(".vscode目录不存在")
            print_info("可运行: python scripts/fix_vscode_config.sh 自动修复")
            self.results['vscode_config'] = False
            return False
            
        # 检查配置文件
        config_files = {
            'settings.json': 'VS Code设置',
            'launch.json': '调试配置',
            'tasks.json': '任务配置',
            'extensions.json': '扩展推荐'
        }
        
        valid_files = 0
        total_files = len(config_files)
        
        for filename, description in config_files.items():
            file_path = vscode_dir / filename
            if file_path.exists():
                print_success(f"{description}文件存在: {filename}")
                
                # 验证JSON格式
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    print_success(f"{filename} JSON格式正确")
                    valid_files += 1
                except json.JSONDecodeError:
                    print_error(f"{filename} JSON格式错误")
                    print_info(f"可运行: python scripts/fix_vscode_config.sh 修复")
                except Exception as e:
                    print_warning(f"读取{filename}时出错: {e}")
            else:
                print_warning(f"{description}文件缺失: {filename}")
                print_info(f"可运行: python scripts/fix_vscode_config.sh 自动创建")
        
        # 根据有效文件比例判断
        success_rate = valid_files / total_files
        if success_rate >= 0.75:  # 75%以上文件有效
            self.results['vscode_config'] = True
            print_success(f"VS Code配置基本正常 ({valid_files}/{total_files} 文件有效)")
            return True
        else:
            self.results['vscode_config'] = False
            print_warning(f"VS Code配置需要修复 ({valid_files}/{total_files} 文件有效)")
            return False

    def check_git_configuration(self) -> bool:
        """检查Git配置和权限"""
        print_header("Git配置验证")
        
        if not (self.project_dir / ".git").exists():
            print_error("不是Git仓库")
            self.results['git_config'] = False
            return False
            
        # 测试Git命令
        try:
            result = subprocess.run(
                ['git', 'status'], 
                cwd=self.project_dir,
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                print_success("Git仓库状态正常")
            else:
                print_error("Git权限问题")
                if "dubious ownership" in result.stderr:
                    print_info("可运行: bash scripts/fix_git_permissions.sh --fix 修复")
                self.results['git_config'] = False
                return False
                
        except subprocess.TimeoutExpired:
            print_error("Git命令超时")
            self.results['git_config'] = False
            return False
        except Exception as e:
            print_error(f"Git测试失败: {e}")
            self.results['git_config'] = False
            return False
            
        # 检查安全目录配置
        try:
            result = subprocess.run(
                ['git', 'config', '--global', '--get-all', 'safe.directory'],
                capture_output=True, text=True, timeout=5
            )
            
            if str(self.project_dir) in result.stdout:
                print_success("Git安全目录已配置")
            else:
                print_warning("Git安全目录未配置")
                print_info("可运行: git config --global --add safe.directory " + str(self.project_dir))
                
        except Exception:
            print_info("无法检查Git安全目录配置")
            
        self.results['git_config'] = True
        return True

    def check_system_services(self) -> bool:
        """检查系统服务状态"""
        print_header("系统服务验证")
        
        # 检查管理脚本
        manage_script = self.project_dir / "manage.sh"
        if manage_script.exists():
            print_success("管理脚本存在")
            
            # 检查脚本权限
            if os.access(manage_script, os.X_OK):
                print_success("管理脚本可执行")
            else:
                print_warning("管理脚本不可执行")
                print_info(f"请运行: chmod +x {manage_script}")
        else:
            print_warning("管理脚本不存在")
            
        # 检查日志目录
        logs_dir = self.project_dir / "logs"
        if logs_dir.exists():
            subdirs = ['ai', 'trading', 'system']
            for subdir in subdirs:
                subdir_path = logs_dir / subdir
                if subdir_path.exists():
                    print_success(f"日志目录存在: {subdir}")
                else:
                    print_warning(f"日志目录缺失: {subdir}")
        
        self.results['system_services'] = True
        return True

    def check_api_connectivity(self) -> bool:
        """检查API连接"""
        print_header("API连接验证")
        
        venv_python = self.project_dir / "venv" / "bin" / "python"
        
        # 测试Binance API
        binance_test = f"{venv_python} -c 'from data.binance_fetcher import BinanceFetcher; fetcher = BinanceFetcher(); print(\"Binance OK\")'"
        success, output = self.run_command(binance_test)
        if success and "Binance OK" in output:
            print_success("Binance API连接正常")
        else:
            print_warning("Binance API连接可能有问题")
            print_info("这通常是由于网络限制或API配置问题")
            
        # 测试OpenRouter API（需要API密钥）
        openrouter_test = f"{venv_python} -c 'from ai.openrouter_client import OpenRouterClient; client = OpenRouterClient(); print(\"OpenRouter OK\")'"
        success, output = self.run_command(openrouter_test)
        if success and "OpenRouter OK" in output:
            print_success("OpenRouter API连接正常")
        else:
            print_warning("OpenRouter API连接可能有问题")
            print_info("请检查.env文件中的OPENROUTER_API_KEY")
            
        self.results['api_connectivity'] = True
        return True

    def run_comprehensive_test(self) -> bool:
        """运行综合功能测试"""
        print_header("综合功能测试")
        
        venv_python = self.project_dir / "venv" / "bin" / "python"
        
        # 运行基础可行性测试
        test_command = f"cd {self.project_dir} && {venv_python} tests/test_feasibility.py"
        print_info("运行基础功能测试...")
        success, output = self.run_command(test_command)
        
        if success:
            print_success("基础功能测试通过")
        else:
            print_warning("基础功能测试未通过")
            if output:
                print_info(f"错误详情: {output[-200:]}")  # 只显示最后200字符
                
        # 运行REST VPA测试
        rest_test = f"cd {self.project_dir} && {venv_python} test_rest_vpa.py"
        print_info("运行REST VPA测试...")
        success, output = self.run_command(rest_test)
        
        if success:
            print_success("REST VPA测试通过")
        else:
            print_warning("REST VPA测试未通过")
            
        self.results['comprehensive_test'] = True
        return True

    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        print_header("验证报告")
        
        total_checks = len(self.results)
        passed_checks = sum(1 for result in self.results.values() if result)
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print_info(f"总检查项目: {total_checks}")
        print_info(f"通过项目: {passed_checks}")
        
        if success_rate >= 80:
            print_success(f"成功率: {success_rate:.1f}% - 环境配置良好")
        elif success_rate >= 60:
            print_warning(f"成功率: {success_rate:.1f}% - 环境配置基本可用，建议优化")
        else:
            print_error(f"成功率: {success_rate:.1f}% - 环境配置有严重问题")
            
        # 详细结果
        print("\n详细结果:")
        for check, result in self.results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}")
            
        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'success_rate': success_rate,
            'results': self.results,
            'timestamp': subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
        }

    def show_recommendations(self):
        """显示改进建议"""
        print_header("改进建议")
        
        recommendations = []
        
        if not self.results.get('user_exists', True):
            recommendations.append("🔧 运行用户设置脚本: sudo scripts/setup_remote_dev_user.sh")
            
        if not self.results.get('python_env', True):
            recommendations.append("🐍 设置Python环境: python3 -m venv venv && source venv/bin/activate && pip install -r requirements-core.txt")
            
        if not self.results.get('ssh_config', True):
            recommendations.append("🔑 配置SSH密钥: ssh-keygen -t ed25519 -C 'ai-trader-dev' -f ~/.ssh/ai-trader-dev")
            
        if not self.results.get('vscode_config', True):
            recommendations.append("📝 修复VS Code配置: bash scripts/fix_vscode_config.sh")
            
        if not self.results.get('git_config', True):
            recommendations.append("📂 修复Git权限: bash scripts/fix_git_permissions.sh --fix")
            
        # 显示具体的修复建议
        if recommendations:
            for rec in recommendations:
                print_info(rec)
        else:
            print_success("🎉 环境配置完善，无需额外操作")
            
        print()
        print_info("📖 详细配置指南: docs/setup/REMOTE_SSH_SETUP.md")
        print_info("🛠️ 一键修复所有问题: bash scripts/fix_all_issues.sh")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='验证远程开发环境配置')
    parser.add_argument('--project-dir', default='/opt/ai-trader', help='项目目录路径')
    parser.add_argument('--dev-user', default='ai-trader-dev', help='开发用户名')
    parser.add_argument('--detailed', action='store_true', help='显示详细信息')
    parser.add_argument('--save-report', help='保存报告到指定文件')
    
    args = parser.parse_args()
    
    print_colored("🚀 AI交易系统远程开发环境验证工具", Colors.PURPLE)
    print_info(f"项目目录: {args.project_dir}")
    print_info(f"开发用户: {args.dev_user}")
    print_info(f"当前用户: {pwd.getpwuid(os.getuid()).pw_name}")
    
    validator = RemoteDevValidator(args.project_dir, args.dev_user)
    
    # 运行所有检查
    validator.check_user_existence()
    validator.check_user_groups()
    validator.check_project_directory()
    validator.check_python_environment()
    validator.check_ssh_configuration()
    validator.check_git_configuration()
    validator.check_vscode_configuration()
    validator.check_system_services()
    
    if args.detailed:
        validator.check_api_connectivity()
        validator.run_comprehensive_test()
    
    # 生成报告
    report = validator.generate_report()
    validator.show_recommendations()
    
    # 保存报告
    if args.save_report:
        try:
            with open(args.save_report, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print_success(f"报告已保存到: {args.save_report}")
        except Exception as e:
            print_error(f"保存报告失败: {e}")
    
    # 退出码
    sys.exit(0 if report['success_rate'] >= 60 else 1)

if __name__ == "__main__":
    main()