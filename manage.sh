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
