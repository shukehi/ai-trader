#!/usr/bin/env python3
"""
交易配置管理器 - 统一管理所有交易相关配置
支持JSON配置文件、环境变量和命令行参数覆盖
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExchangeSettings:
    """交易所设置"""
    maker_fee: float = 0.0002
    taker_fee: float = 0.0004
    slippage_factor: float = 0.0001
    default_leverage: float = 10.0

@dataclass
class RiskLevel:
    """风险等级设置"""
    max_single_trade_risk: float
    max_total_risk: float
    max_positions: int
    max_leverage: float
    drawdown_limit: float

@dataclass
class RiskManagement:
    """风险管理设置"""
    default_risk_level: str = "moderate"
    max_single_trade_risk: float = 0.02
    max_total_risk: float = 0.06
    max_positions: int = 5
    max_daily_trades: int = 10
    emergency_stop_drawdown: float = 0.15
    
    # 各风险等级设置
    conservative: RiskLevel = None
    moderate: RiskLevel = None
    aggressive: RiskLevel = None
    
    def __post_init__(self):
        if self.conservative is None:
            self.conservative = RiskLevel(0.01, 0.03, 3, 5.0, 0.05)
        if self.moderate is None:
            self.moderate = RiskLevel(0.02, 0.06, 5, 10.0, 0.10)
        if self.aggressive is None:
            self.aggressive = RiskLevel(0.03, 0.10, 8, 20.0, 0.15)

@dataclass
class SignalExecution:
    """信号执行设置"""
    default_execution_mode: str = "confirm"  # auto, confirm, signal_only
    min_signal_strength: int = 2
    min_confidence_score: float = 0.6
    min_risk_reward_ratio: float = 1.5
    price_deviation_threshold: float = 0.02

@dataclass
class AIAnalysis:
    """AI分析设置 (优化版 - 对抗模型偏差)"""
    default_model: str = "gpt4o-mini"
    enable_validation: bool = True        # 默认启用多模型验证
    fast_validation: bool = False         # 使用完整验证以确保质量
    analysis_timeout: int = 90            # 增加超时以适应多模型
    retry_attempts: int = 3
    # 模型偏差对抗设置
    primary_models: list = None           # 主要分析模型
    validation_models: list = None        # 验证模型
    consensus_threshold: float = 0.7      # 提高共识阈值确保质量
    
    def __post_init__(self):
        if self.primary_models is None:
            # 选择互补的模型组合，减少方向性偏差
            self.primary_models = ['gpt4o-mini', 'claude-haiku']
        if self.validation_models is None:
            # 验证模型应该与主要模型有不同的特性
            self.validation_models = ['gemini-flash']

@dataclass
class Monitoring:
    """监控设置"""
    refresh_interval: float = 1.0
    max_history_length: int = 3600
    enable_real_time: bool = True
    balance_drop_percent: float = 0.05
    unrealized_loss_percent: float = 0.10
    position_count_max: int = 8
    risk_utilization_high: float = 0.85

@dataclass
class Logging:
    """日志设置"""
    log_directory: str = "logs"
    enable_trade_logging: bool = True
    enable_ai_decision_logging: bool = True
    enable_risk_event_logging: bool = True
    log_retention_days: int = 90
    export_formats: list = None
    auto_backup: bool = True
    
    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ["json", "csv", "sqlite"]

class TradingConfig:
    """
    交易配置管理器
    
    功能特性:
    - JSON配置文件加载
    - 环境变量覆盖
    - 命令行参数覆盖
    - 配置验证和默认值
    - 动态配置更新
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 trading_config.json
        """
        # 设置默认配置文件路径
        if config_path is None:
            config_path = Path(__file__).parent.parent / "trading_config.json"
        
        self.config_path = Path(config_path)
        
        # 基础配置
        self.description = "ETH永续合约AI交易助手"
        self.version = "1.0.0"
        self.initial_balance = 10000.0
        self.default_symbol = "ETHUSDT"
        self.default_timeframe = "1h"
        
        # 各模块配置
        self.exchange_settings = ExchangeSettings()
        self.risk_management = RiskManagement()
        self.signal_execution = SignalExecution()
        self.ai_analysis = AIAnalysis()
        self.monitoring = Monitoring()
        self.logging = Logging()
        
        # 加载配置
        self.load_config()
        
        logger.info(f"交易配置已加载: {self.config_path}")
    
    def load_config(self) -> bool:
        """从JSON文件加载配置"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self._create_default_config()
                return True
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 解析配置数据
            trading_config = config_data.get('trading_config', {})
            
            # 基础设置
            self.description = trading_config.get('description', self.description)
            self.version = trading_config.get('version', self.version)
            self.initial_balance = trading_config.get('initial_balance', self.initial_balance)
            self.default_symbol = trading_config.get('default_symbol', self.default_symbol)
            self.default_timeframe = trading_config.get('default_timeframe', self.default_timeframe)
            
            # 交易所设置
            exchange_data = trading_config.get('exchange_settings', {})
            self.exchange_settings = ExchangeSettings(**{
                k: v for k, v in exchange_data.items() 
                if k in ExchangeSettings.__dataclass_fields__
            })
            
            # 风险管理设置
            risk_data = trading_config.get('risk_management', {})
            risk_levels = risk_data.get('risk_levels', {})
            
            self.risk_management = RiskManagement(
                **{k: v for k, v in risk_data.items() if k != 'risk_levels'},
                conservative=RiskLevel(**risk_levels.get('conservative', {})) if risk_levels.get('conservative') else None,
                moderate=RiskLevel(**risk_levels.get('moderate', {})) if risk_levels.get('moderate') else None,
                aggressive=RiskLevel(**risk_levels.get('aggressive', {})) if risk_levels.get('aggressive') else None
            )
            
            # 信号执行设置
            signal_data = trading_config.get('signal_execution', {})
            self.signal_execution = SignalExecution(**{
                k: v for k, v in signal_data.items()
                if k in SignalExecution.__dataclass_fields__
            })
            
            # AI分析设置
            ai_data = trading_config.get('ai_analysis', {})
            self.ai_analysis = AIAnalysis(**{
                k: v for k, v in ai_data.items()
                if k in AIAnalysis.__dataclass_fields__
            })
            
            # 监控设置
            monitor_data = trading_config.get('monitoring', {})
            alert_thresholds = monitor_data.get('alert_thresholds', {})
            
            self.monitoring = Monitoring(
                **{k: v for k, v in monitor_data.items() if k != 'alert_thresholds'},
                **alert_thresholds
            )
            
            # 日志设置
            log_data = trading_config.get('logging', {})
            self.logging = Logging(**{
                k: v for k, v in log_data.items()
                if k in Logging.__dataclass_fields__
            })
            
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("使用默认配置")
            return False
    
    def save_config(self) -> bool:
        """保存配置到JSON文件"""
        try:
            config_data = {
                "trading_config": {
                    "description": self.description,
                    "version": self.version,
                    "initial_balance": self.initial_balance,
                    "default_symbol": self.default_symbol,
                    "default_timeframe": self.default_timeframe,
                    
                    "exchange_settings": asdict(self.exchange_settings),
                    
                    "risk_management": {
                        **{k: v for k, v in asdict(self.risk_management).items() 
                           if k not in ['conservative', 'moderate', 'aggressive']},
                        "risk_levels": {
                            "conservative": asdict(self.risk_management.conservative),
                            "moderate": asdict(self.risk_management.moderate),
                            "aggressive": asdict(self.risk_management.aggressive)
                        }
                    },
                    
                    "signal_execution": asdict(self.signal_execution),
                    "ai_analysis": asdict(self.ai_analysis),
                    
                    "monitoring": {
                        **{k: v for k, v in asdict(self.monitoring).items()
                           if not k.endswith('_percent') and not k.endswith('_max') and not k.endswith('_high')},
                        "alert_thresholds": {
                            "balance_drop_percent": self.monitoring.balance_drop_percent,
                            "unrealized_loss_percent": self.monitoring.unrealized_loss_percent,
                            "position_count_max": self.monitoring.position_count_max,
                            "risk_utilization_high": self.monitoring.risk_utilization_high
                        }
                    },
                    
                    "logging": asdict(self.logging)
                }
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        try:
            self.save_config()
            logger.info(f"已创建默认配置文件: {self.config_path}")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")
    
    def override_from_env(self) -> None:
        """从环境变量覆盖配置"""
        try:
            # 基础配置
            self.initial_balance = float(os.getenv('TRADING_INITIAL_BALANCE', self.initial_balance))
            self.default_symbol = os.getenv('TRADING_DEFAULT_SYMBOL', self.default_symbol)
            self.default_timeframe = os.getenv('TRADING_DEFAULT_TIMEFRAME', self.default_timeframe)
            
            # 风险管理
            max_risk = os.getenv('TRADING_MAX_RISK')
            if max_risk:
                self.risk_management.max_single_trade_risk = float(max_risk)
            
            risk_level = os.getenv('TRADING_RISK_LEVEL')
            if risk_level and risk_level in ['conservative', 'moderate', 'aggressive']:
                self.risk_management.default_risk_level = risk_level
            
            # AI模型
            model = os.getenv('TRADING_DEFAULT_MODEL')
            if model:
                self.ai_analysis.default_model = model
            
            # 执行模式
            exec_mode = os.getenv('TRADING_EXECUTION_MODE')
            if exec_mode and exec_mode in ['auto', 'confirm', 'signal_only']:
                self.signal_execution.default_execution_mode = exec_mode
            
            logger.info("已从环境变量覆盖配置")
            
        except Exception as e:
            logger.error(f"从环境变量覆盖配置失败: {e}")
    
    def override_from_args(self, args) -> None:
        """从命令行参数覆盖配置"""
        try:
            if hasattr(args, 'initial_balance') and args.initial_balance:
                self.initial_balance = args.initial_balance
            
            if hasattr(args, 'symbol') and args.symbol:
                self.default_symbol = args.symbol
            
            if hasattr(args, 'timeframe') and args.timeframe:
                self.default_timeframe = args.timeframe
            
            if hasattr(args, 'max_risk') and args.max_risk:
                self.risk_management.max_single_trade_risk = args.max_risk
            
            if hasattr(args, 'risk_level') and args.risk_level:
                self.risk_management.default_risk_level = args.risk_level
            
            if hasattr(args, 'model') and args.model:
                self.ai_analysis.default_model = args.model
            
            if hasattr(args, 'enable_validation'):
                self.ai_analysis.enable_validation = args.enable_validation
            
            if hasattr(args, 'fast_validation'):
                self.ai_analysis.fast_validation = args.fast_validation
            
            # 执行模式判断
            if hasattr(args, 'auto_trade') and args.auto_trade:
                self.signal_execution.default_execution_mode = 'auto'
            elif hasattr(args, 'signal_only') and args.signal_only:
                self.signal_execution.default_execution_mode = 'signal_only'
            
            logger.info("已从命令行参数覆盖配置")
            
        except Exception as e:
            logger.error(f"从命令行参数覆盖配置失败: {e}")
    
    def get_risk_level_settings(self, level: str = None) -> RiskLevel:
        """获取指定风险等级设置"""
        if level is None:
            level = self.risk_management.default_risk_level
        
        level_map = {
            'conservative': self.risk_management.conservative,
            'moderate': self.risk_management.moderate,
            'aggressive': self.risk_management.aggressive
        }
        
        return level_map.get(level, self.risk_management.moderate)
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        issues = []
        
        # 基础验证
        if self.initial_balance <= 0:
            issues.append("初始资金必须大于0")
        
        # 风险管理验证
        risk = self.risk_management
        if risk.max_single_trade_risk <= 0 or risk.max_single_trade_risk > 0.1:
            issues.append("单笔交易风险应在0-10%之间")
        
        if risk.max_total_risk <= risk.max_single_trade_risk:
            issues.append("总风险应大于单笔风险")
        
        if risk.max_positions <= 0:
            issues.append("最大持仓数量必须大于0")
        
        # 信号执行验证
        signal = self.signal_execution
        if signal.default_execution_mode not in ['auto', 'confirm', 'signal_only']:
            issues.append("无效的执行模式")
        
        if signal.min_signal_strength < 1 or signal.min_signal_strength > 4:
            issues.append("信号强度应在1-4之间")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'description': self.description,
            'version': self.version,
            'initial_balance': self.initial_balance,
            'default_symbol': self.default_symbol,
            'default_timeframe': self.default_timeframe,
            'exchange_settings': asdict(self.exchange_settings),
            'risk_management': asdict(self.risk_management),
            'signal_execution': asdict(self.signal_execution),
            'ai_analysis': asdict(self.ai_analysis),
            'monitoring': asdict(self.monitoring),
            'logging': asdict(self.logging)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"TradingConfig(balance=${self.initial_balance}, risk={self.risk_management.default_risk_level})"