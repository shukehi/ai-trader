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
