from .openrouter_client import OpenRouterClient
from .analysis_engine import AnalysisEngine
from .raw_data_analyzer import RawDataAnalyzer

# 按需导入可选组件；若依赖缺失，提供占位符以避免导入失败

__all__ = ['OpenRouterClient', 'AnalysisEngine', 'RawDataAnalyzer']

# analysis_context（通常不引入额外第三方依赖）
try:
    from .analysis_context import AnalysisContext, MultiTimeframeContext, SignalStrength, ContextPriority
    __all__ += ['AnalysisContext', 'MultiTimeframeContext', 'SignalStrength', 'ContextPriority']
except Exception as _e_ctx:  # 安全降级
    pass

# multi_timeframe_analyzer（可能引入更多内部依赖）
try:
    from .multi_timeframe_analyzer import MultiTimeframeAnalyzer, AnalysisScenario, MultiTimeframeResult
except Exception as _e_mtf:
    class _UnavailableMTF:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"MultiTimeframeAnalyzer unavailable: {_e_mtf}")
    class MultiTimeframeAnalyzer(_UnavailableMTF):
        pass
    class AnalysisScenario:  # 占位枚举
        pass
    class MultiTimeframeResult(dict):
        pass
finally:
    __all__ += ['MultiTimeframeAnalyzer', 'AnalysisScenario', 'MultiTimeframeResult']

# realtime_analysis_engine（依赖 websockets/aiohttp 等，可缺失）
try:
    from .realtime_analysis_engine import RealtimeAnalysisEngine, RealtimeConfig, AnalysisFrequency, MarketCondition
except Exception as _e_rt:
    class _UnavailableRT:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"RealtimeAnalysisEngine unavailable: {_e_rt}")
    class RealtimeAnalysisEngine(_UnavailableRT):
        pass
    class RealtimeConfig(dict):
        pass
    class AnalysisFrequency:  # 占位枚举
        pass
    class MarketCondition:  # 占位枚举
        pass
finally:
    __all__ += ['RealtimeAnalysisEngine', 'RealtimeConfig', 'AnalysisFrequency', 'MarketCondition']
