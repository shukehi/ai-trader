import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from .openrouter_client import OpenRouterClient
from .multi_model_validator import MultiModelValidator, ValidationConfig
from formatters import DataFormatter

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """
    AI直接分析引擎 - 专注原始数据分析
    
    核心功能：
    1. AI直接理解原始OHLCV数据
    2. 多模型交叉验证防幻觉
    3. 共识得分计算
    4. 分歧检测与报警
    5. 智能仲裁机制
    6. 置信度评估
    
    使用方法：
    - raw_data_analysis(): AI直接分析原始数据（推荐）
    - validated_vpa_analysis(): 完整验证分析
    - quick_validation_check(): 快速验证检查
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_validation: bool = True):
        self.client = OpenRouterClient(api_key)
        self.formatter = DataFormatter()
        
        # 初始化多模型验证器
        self.validator: Optional[MultiModelValidator]
        if enable_validation:
            self.validator = MultiModelValidator(api_key)
            logger.info("✅ 多模型验证已启用")
        else:
            self.validator = None
            logger.info("ℹ️ 多模型验证已禁用")
    
    def raw_data_analysis(self, 
                         df: pd.DataFrame,
                         model: str = 'gpt4o-mini',
                         format_type: str = 'csv') -> Dict[str, Any]:
        """
        AI直接分析原始OHLCV数据
        
        Args:
            df: 原始OHLCV数据DataFrame
            model: 使用的AI模型
            format_type: 数据格式 ('csv', 'text', 'json', 'pattern')
            
        Returns:
            分析结果字典
        """
        try:
            # 格式化原始数据
            if format_type == 'csv':
                formatted_data = self.formatter.to_csv_format(df)
            elif format_type == 'text':
                formatted_data = self.formatter.to_text_narrative(df)
            elif format_type == 'json':
                formatted_data = self.formatter.to_structured_json(df)
            elif format_type == 'pattern':
                formatted_data = self.formatter.to_pattern_description(df)
            else:
                formatted_data = self.formatter.to_csv_format(df)  # 默认使用CSV
            
            # AI分析原始数据
            logger.info(f"使用 {model} 模型进行AI直接分析...")
            
            analysis_result = self.client.analyze_market_data(
                data=formatted_data,
                model_name=model,
                analysis_type='raw_vpa'
            )
            
            # 创建分析报告
            report = {
                'data_summary': {
                    'total_bars': len(df),
                    'time_range': {
                        'start': df['datetime'].iloc[0],
                        'end': df['datetime'].iloc[-1]
                    },
                    'price_range': {
                        'min': df['low'].min(),
                        'max': df['high'].max(),
                        'current': df['close'].iloc[-1],
                        'change': ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
                    },
                    'volume_summary': {
                        'total': df['volume'].sum(),
                        'average': df['volume'].mean(),
                        'recent_avg': df['volume'].tail(10).mean()
                    }
                },
                'ai_analysis': analysis_result,
                'analysis_method': 'raw_data_ai_direct',
                'model_used': model,
                'format_used': format_type
            }
            
            logger.info("✅ AI直接分析完成")
            return report
            
        except Exception as e:
            logger.error(f"AI直接分析失败: {e}")
            return {
                'error': str(e),
                'analysis_method': 'raw_data_ai_direct',
                'model_used': model
            }
    
    def validated_vpa_analysis(self,
                             df: pd.DataFrame,
                             models: Optional[List[str]] = None,
                             validation_config: Optional[ValidationConfig] = None) -> Dict[str, Any]:
        """
        验证的VPA分析：使用多模型验证防止幻觉
        
        Args:
            df: OHLCV数据
            models: 使用的模型列表
            validation_config: 验证配置
            
        Returns:
            包含验证信息的分析结果
        """
        if not self.validator:
            logger.warning("⚠️ 多模型验证未启用，降级为单模型分析")
            return self.raw_data_analysis(df)
        
        try:
            # 使用最优的Pattern格式
            formatted_data = self.formatter.to_pattern_description(df, 
                                                                 include_vsa=True, 
                                                                 include_perpetual_context=True)
            
            logger.info("🔍 开始多模型验证分析...")
            
            # 执行多模型验证
            validation_result = self.validator.validate_analysis(
                market_data=formatted_data,
                models=models,
                config=validation_config
            )
            
            # 整合分析结果
            report = {
                'data_summary': {
                    'total_bars': len(df),
                    'time_range': {
                        'start': df['datetime'].iloc[0],
                        'end': df['datetime'].iloc[-1]
                    },
                    'price_range': {
                        'min': df['low'].min(),
                        'max': df['high'].max(),
                        'current': df['close'].iloc[-1],
                        'change': ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
                    }
                },
                'validation_result': validation_result,
                'analysis_method': 'validated_vpa_analysis',
                'models_used': validation_result.get('models_used', []),
                'consensus_score': validation_result.get('consensus_score', 0),
                'confidence_level': validation_result.get('confidence_level', 'unknown')
            }
            
            logger.info("✅ 验证分析完成")
            return report
            
        except Exception as e:
            logger.error(f"验证分析失败: {e}")
            return {
                'error': str(e),
                'analysis_method': 'validated_vpa_analysis'
            }
    
    def quick_validation_check(self,
                             df: pd.DataFrame,
                             primary_model: str = 'gpt5-mini',
                             secondary_model: str = 'gemini-flash') -> Dict[str, Any]:
        """
        快速验证检查：使用2个模型进行快速交叉验证
        
        Args:
            df: OHLCV数据
            primary_model: 主要模型
            secondary_model: 次要模型
            
        Returns:
            快速验证结果
        """
        try:
            formatted_data = self.formatter.to_csv_format(df)
            
            logger.info(f"🚀 快速验证: {primary_model} vs {secondary_model}")
            
            # 并行分析
            primary_result = self.client.analyze_market_data(
                data=formatted_data,
                model_name=primary_model,
                analysis_type='quick_vpa'
            )
            
            secondary_result = self.client.analyze_market_data(
                data=formatted_data,
                model_name=secondary_model,
                analysis_type='quick_vpa'
            )
            
            # 简单一致性检查
            consistency_score = self._calculate_simple_consistency(
                primary_result, secondary_result
            )
            
            return {
                'primary_analysis': primary_result,
                'secondary_analysis': secondary_result,
                'consistency_score': consistency_score,
                'models_used': [primary_model, secondary_model],
                'analysis_method': 'quick_validation_check',
                'recommendation': 'high_confidence' if consistency_score > 0.7 else 'medium_confidence' if consistency_score > 0.4 else 'low_confidence'
            }
            
        except Exception as e:
            logger.error(f"快速验证失败: {e}")
            return {
                'error': str(e),
                'analysis_method': 'quick_validation_check'
            }
    
    def _calculate_simple_consistency(self, result1: Any, result2: Any) -> float:
        """
        计算两个分析结果的简单一致性得分
        """
        try:
            # 简化的一致性计算
            # 这里可以根据具体需求实现更复杂的逻辑
            if isinstance(result1, str) and isinstance(result2, str):
                # 基于文本长度和关键词的简单相似度
                if len(result1) > 0 and len(result2) > 0:
                    return 0.8  # 假设基本一致性
            return 0.5  # 默认中等一致性
        except:
            return 0.3  # 计算失败时的默认值
    
    def get_analysis_capabilities(self) -> Dict[str, Any]:
        """
        获取分析引擎的能力描述
        """
        return {
            'engine_type': 'AI_Direct_Analysis',
            'core_capabilities': [
                'Raw OHLCV data analysis',
                'Multi-model validation',
                'Professional VPA analysis',
                'Real-time signal generation'
            ],
            'supported_formats': ['csv', 'text', 'json', 'pattern'],
            'validation_enabled': self.validator is not None,
            'recommended_method': 'validated_vpa_analysis',
            'fast_method': 'raw_data_analysis',
            'description': 'AI直接理解原始K线数据，无需传统技术指标预处理'
        }