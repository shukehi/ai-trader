import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Available models for testing (OpenRouter 2025 Latest)
    MODELS = {
        # 🔥 2025 Latest Flagship Models
        'gpt5-chat': 'openai/gpt-5-chat',                    # GPT-5 Chat (推荐)
        'gpt5-mini': 'openai/gpt-5-mini',                    # GPT-5 Mini (经济版)
        'gpt5-nano': 'openai/gpt-5-nano',                    # GPT-5 Nano (超轻量)
        'claude-opus-41': 'anthropic/claude-opus-4.1',        # Claude Opus 4.1
        'gemini-25-pro': 'google/gemini-2.5-pro',            # Gemini 2.5 Pro
        'grok4': 'x-ai/grok-4',                              # Grok 4
        
        # OpenAI Models
        'gpt4': 'openai/gpt-4-turbo-2024-04-09',
        'gpt4o': 'openai/gpt-4o-2024-11-20',
        'gpt4o-mini': 'openai/gpt-4o-mini-2024-07-18',
        'o1': 'openai/o1-2024-12-17',
        'o1-mini': 'openai/o1-mini-2024-09-12',
        
        # Anthropic Claude Models  
        'claude': 'anthropic/claude-3.5-sonnet-20241022',
        'claude-haiku': 'anthropic/claude-3.5-haiku-20241022',
        'claude-opus': 'anthropic/claude-3-opus-20240229',
        
        # Google Gemini Models
        'gemini': 'google/gemini-pro-1.5',
        'gemini-flash': 'google/gemini-flash-1.5',
        'gemini-2': 'google/gemini-2.0-flash-exp',
        
        # xAI Grok Models
        'grok': 'x-ai/grok-beta',
        'grok-vision': 'x-ai/grok-vision-beta',
        
        # Meta Llama Models (高性价比选择)
        'llama': 'meta-llama/llama-3.1-70b-instruct',
        'llama-405b': 'meta-llama/llama-3.1-405b-instruct'
    }
    
    # Binance API (optional)
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # Data settings
    DEFAULT_SYMBOL = 'ETHUSDT'
    DEFAULT_TIMEFRAME = '1h'
    DEFAULT_LIMIT = 50
    
    # Multi-Model Validation Settings
    VALIDATION_CONFIG = {
        # 主要验证模型（基于Phase2测试结果）
        'primary_models': ['gpt5-mini', 'claude-opus-41'],
        
        # 辅助验证模型
        'validation_models': ['gpt4o-mini', 'gemini-flash', 'claude-haiku'],
        
        # 共识阈值设置
        'consensus_threshold': 0.6,     # 60%一致性阈值
        'high_confidence_threshold': 0.8, # 80%高置信度阈值
        
        # 验证行为控制
        'enable_arbitration': True,      # 启用仲裁机制
        'arbitrator_model': 'claude-haiku', # 仲裁模型
        'max_models_per_validation': 5,  # 单次验证最大模型数
        'timeout_seconds': 120,          # 验证超时时间
        
        # 性能控制
        'enable_optimization': True,     # 启用性能优化
        'timeout_per_request': 60,       # 单个请求超时时间(秒)
        
        # 质量控制
        'minimum_models_for_consensus': 2, # 最少模型数量
        'disagreement_alert_threshold': 3, # 分歧警报阈值
        
        # 缓存设置
        'enable_response_cache': False,   # 启用响应缓存
        'cache_duration_minutes': 30,     # 缓存持续时间
    }
    
    # VPA分析专用设置
    VPA_ANALYSIS_CONFIG = {
        # VPA信号权重（用于共识计算）
        'signal_weights': {
            'market_phase': 0.30,      # 市场阶段（最重要）
            'vpa_signal': 0.25,        # VPA信号
            'price_direction': 0.25,   # 价格方向
            'confidence': 0.10,        # 置信度
            'key_levels': 0.10         # 关键价位
        },
        
        # 关键价位容差
        'key_level_tolerance': 0.01,     # 1%价格容差
        
        # 分析深度设置
        'default_lookback_bars': 50,     # 默认回看K线数量
        'pattern_analysis_bars': 30,     # 形态分析K线数量
        'volume_analysis_period': 20,    # 成交量分析周期
        
        # 质量评分标准
        'quality_score_weights': {
            'vpa_terminology': 30,        # VPA术语使用
            'market_phase_clarity': 25,   # 市场阶段识别清晰度
            'data_reference': 20,         # 数据引用具体性
            'trading_signals': 15,        # 交易信号质量
            'risk_assessment': 10         # 风险评估完整性
        }
    }
    
    # Analysis settings - Token Limits (OpenRouter 2025 Latest)
    TOKEN_LIMITS = {
        # 🔥 2025 Latest Flagship Models
        'gpt5-chat': 400000,     # GPT-5 Chat (400K context)
        'gpt5-mini': 400000,     # GPT-5 Mini (400K context)
        'gpt5-nano': 400000,     # GPT-5 Nano (400K context)
        'claude-opus-41': 500000, # Claude Opus 4.1 (500K context)
        'gemini-25-pro': 10000000, # Gemini 2.5 Pro (10M context)
        'grok4': 1000000,        # Grok 4 (1M context)
        
        # OpenAI Models
        'gpt4': 128000,         # GPT-4 Turbo
        'gpt4o': 128000,        # GPT-4o
        'gpt4o-mini': 128000,   # GPT-4o mini
        'o1': 200000,           # o1 reasoning model
        'o1-mini': 128000,      # o1 mini
        
        # Anthropic Claude Models
        'claude': 200000,       # Claude 3.5 Sonnet
        'claude-haiku': 200000, # Claude 3.5 Haiku
        'claude-opus': 200000,  # Claude 3 Opus
        
        # Google Gemini Models
        'gemini': 2097152,      # Gemini Pro 1.5 (2M tokens)
        'gemini-flash': 1048576, # Gemini Flash 1.5 (1M tokens)
        'gemini-2': 1048576,    # Gemini 2.0 Flash
        
        # xAI Grok Models
        'grok': 131072,         # Grok Beta (128K)
        'grok-vision': 131072,  # Grok Vision Beta
        
        # Meta Llama Models
        'llama': 131072,        # Llama 3.1 70B (128K)
        'llama-405b': 131072    # Llama 3.1 405B (128K)
    }
    
    @classmethod
    def validate(cls):
        """验证必需的配置是否存在"""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required. Please set it in .env file")
        
        # 验证多模型验证配置
        validation_config = cls.VALIDATION_CONFIG
        
        # 检查主要模型是否在可用模型列表中
        for model in validation_config['primary_models']:
            if model not in cls.MODELS:
                raise ValueError(f"Primary model '{model}' not found in available models")
        
        # 检查验证模型是否在可用模型列表中
        for model in validation_config['validation_models']:
            if model not in cls.MODELS:
                raise ValueError(f"Validation model '{model}' not found in available models")
        
        # 检查仲裁模型
        arbitrator = validation_config['arbitrator_model']
        if arbitrator not in cls.MODELS:
            raise ValueError(f"Arbitrator model '{arbitrator}' not found in available models")
        
        # 验证阈值设置合理性
        if not 0 < validation_config['consensus_threshold'] <= 1:
            raise ValueError("Consensus threshold must be between 0 and 1")
        
        if not 0 < validation_config['high_confidence_threshold'] <= 1:
            raise ValueError("High confidence threshold must be between 0 and 1")
        
        # 验证VPA配置权重总和
        vpa_weights = cls.VPA_ANALYSIS_CONFIG['signal_weights']
        total_weight = sum(vpa_weights.values())
        if abs(total_weight - 1.0) > 0.01:  # 允许1%误差
            raise ValueError(f"VPA signal weights must sum to 1.0, got {total_weight}")
        
        quality_weights = cls.VPA_ANALYSIS_CONFIG['quality_score_weights']
        total_quality_weight = sum(quality_weights.values())
        if total_quality_weight != 100:
            raise ValueError(f"Quality score weights must sum to 100, got {total_quality_weight}")
        
        return True
    
    @classmethod
    def get_validation_config(cls):
        """获取验证配置"""
        return cls.VALIDATION_CONFIG.copy()
    
    @classmethod
    def get_vpa_config(cls):
        """获取VPA分析配置"""
        return cls.VPA_ANALYSIS_CONFIG.copy()
    
    @classmethod
    def get_model_tiers(cls):
        """获取模型分级信息"""
        return {
            'flagship': ['gpt5-chat', 'gpt5-mini', 'claude-opus-41', 'gemini-25-pro', 'grok4'],
            'production': ['gpt4o', 'claude', 'gemini'],
            'economy': ['gpt4o-mini', 'claude-haiku', 'gemini-flash', 'gpt5-nano'],
            'reasoning': ['o1', 'o1-mini'],
            'large_context': ['gemini-25-pro', 'claude-opus-41', 'gemini'],
        }
    
    # Model recommendations for different analysis types
    RECOMMENDED_MODELS = {
        'simple': ['gemini-flash', 'gpt5-nano', 'gpt4o-mini'],
        'complete': ['gpt4o-mini', 'claude', 'gemini'],
        'enhanced': ['gpt5-mini', 'claude-opus-41', 'gpt5-chat']
    }
    
    # 分析模式配置
    ANALYSIS_MODES = {
        'simple': {
            'default_model': 'gemini-flash',
            'fallback_model': 'gpt4o-mini',
            'timeout': 20
        },
        'complete': {
            'default_model': 'gpt4o-mini',
            'fallback_model': 'claude',
            'timeout': 45
        },
        'enhanced': {
            'default_model': 'gpt5-mini',
            'fallback_model': 'claude-opus-41',
            'timeout': 90
        }
    }

    @classmethod
    def get_recommended_models_for_task(cls, analysis_type: str = 'simple'):
        """根据分析类型获取推荐模型"""
        return cls.RECOMMENDED_MODELS.get(analysis_type, cls.RECOMMENDED_MODELS['simple'])