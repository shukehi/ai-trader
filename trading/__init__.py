#!/usr/bin/env python3
"""
ETH永续合约AI交易助手 - 模拟交易模块
提供完整的模拟交易环境，包括订单管理、持仓管理、风险控制和交易日志
"""

from .simulated_exchange import SimulatedExchange
from .order_manager import OrderManager
from .position_manager import PositionManager
from .trade_logger import TradeLogger
from .signal_executor import SignalExecutor
from .risk_manager import RiskManager
from .monitor import TradingMonitor

__all__ = [
    'SimulatedExchange',
    'OrderManager', 
    'PositionManager',
    'TradeLogger',
    'SignalExecutor',
    'RiskManager',
    'TradingMonitor'
]

__version__ = '1.0.0'