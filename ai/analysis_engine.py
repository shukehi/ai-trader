import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from .openrouter_client import OpenRouterClient
from .multi_model_validator import MultiModelValidator, ValidationConfig
from data import DataProcessor

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """
    增强分析引擎 - 集成多模型验证机制
    
    新功能：
    1. 多模型交叉验证防幻觉
    2. 共识得分计算
    3. 分歧检测与报警
    4. 智能仲裁机制
    5. 置信度评估
    
    使用方法：
    - validated_vpa_analysis(): 完整验证分析（推荐）
    - quick_validation_check(): 快速验证检查
    - comprehensive_analysis(): 原有的综合分析（向后兼容）
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_validation: bool = True):
        self.client = OpenRouterClient(api_key)
        self.processor = DataProcessor()
        
        # 初始化多模型验证器
        if enable_validation:
            self.validator = MultiModelValidator(api_key)
            logger.info("✅ 多模型验证已启用")
        else:
            self.validator = None
            logger.info("ℹ️ 多模型验证已禁用")
    
    def comprehensive_analysis(self, 
                             df: pd.DataFrame,
                             models: List[str] = ['gpt4'],
                             include_indicators: bool = True,
                             include_patterns: bool = True) -> Dict[str, Any]:
        """
        综合分析：使用多个模型分析同一数据
        """
        try:
            # 数据预处理
            if include_indicators:
                df = self.processor.add_basic_indicators(df)
            
            if include_patterns:
                df = self.processor.detect_candlestick_patterns(df)
                df = self.processor.analyze_volume_price_relationship(df)
            
            # 获取关键水平
            key_levels = self.processor.get_key_levels(df)
            
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
                'key_levels': key_levels,
                'ai_analysis': {}
            }
            
            # 使用不同模型进行分析
            for model in models:
                logger.info(f"使用 {model} 模型进行分析...")
                
                # VPA分析
                vpa_data = self._prepare_vpa_data(df)
                vpa_result = self.client.analyze_market_data(
                    data=vpa_data,
                    model_name=model,
                    analysis_type='vpa'
                )
                
                # 技术分析
                technical_data = self._prepare_technical_data(df, key_levels)
                technical_result = self.client.analyze_market_data(
                    data=technical_data,
                    model_name=model,
                    analysis_type='technical'
                )
                
                # 形态分析
                pattern_data = self._prepare_pattern_data(df)
                pattern_result = self.client.analyze_market_data(
                    data=pattern_data,
                    model_name=model,
                    analysis_type='pattern'
                )
                
                report['ai_analysis'][model] = {
                    'vpa_analysis': vpa_result,
                    'technical_analysis': technical_result,
                    'pattern_analysis': pattern_result,
                    'total_tokens': (
                        vpa_result.get('usage', {}).get('total_tokens', 0) +
                        technical_result.get('usage', {}).get('total_tokens', 0) +
                        pattern_result.get('usage', {}).get('total_tokens', 0)
                    )
                }
            
            return report
            
        except Exception as e:
            logger.error(f"综合分析失败: {e}")
            return {'error': str(e)}
    
    def _prepare_vpa_data(self, df: pd.DataFrame, last_n: int = 50) -> str:
        """
        为VPA分析准备数据格式
        """
        recent_df = df.tail(last_n).copy()
        
        # 基础OHLCV数据
        data_lines = ["# ETH/USDT 1小时K线数据 (VPA分析)\\n"]
        data_lines.append("时间,开盘价,最高价,最低价,收盘价,成交量,成交量比率,价格变化")
        
        for _, row in recent_df.iterrows():
            volume_ratio = row.get('volume_ratio', 1.0) if 'volume_ratio' in row else 1.0
            price_change = row.get('price_change', 0) * 100 if 'price_change' in row else 0
            
            line = f"{row['datetime']},{row['open']:.2f},{row['high']:.2f},{row['low']:.2f},{row['close']:.2f},{row['volume']:.0f},{volume_ratio:.2f},{price_change:+.2f}%"
            data_lines.append(line)
        
        # 添加VPA信号总结
        if 'bullish_volume' in recent_df.columns:
            bullish_signals = recent_df['bullish_volume'].sum()
            bearish_signals = recent_df['bearish_volume'].sum()
            suspicious_rallies = recent_df['suspicious_rally'].sum()
            suspicious_declines = recent_df['suspicious_decline'].sum()
            
            data_lines.append(f"\\n# VPA信号统计 (最近{last_n}根K线)")
            data_lines.append(f"健康上涨信号: {bullish_signals}")
            data_lines.append(f"健康下跌信号: {bearish_signals}")
            data_lines.append(f"可疑上涨信号: {suspicious_rallies}")
            data_lines.append(f"可疑下跌信号: {suspicious_declines}")
        
        return "\\n".join(data_lines)
    
    def _prepare_technical_data(self, df: pd.DataFrame, key_levels: Dict, last_n: int = 50) -> str:
        """
        为技术分析准备数据格式
        """
        recent_df = df.tail(last_n).copy()
        
        data_lines = ["# ETH/USDT 技术分析数据\\n"]
        
        # 关键水平
        data_lines.append("## 关键技术水平")
        data_lines.append(f"阻力位: {key_levels.get('resistance_levels', [])}")
        data_lines.append(f"支撑位: {key_levels.get('support_levels', [])}")
        data_lines.append("")
        
        # 带技术指标的OHLCV数据
        data_lines.append("## K线数据与技术指标")
        header = "时间,开盘,最高,最低,收盘,成交量"
        
        # 添加可用的技术指标列
        indicators = ['sma_20', 'rsi', 'macd', 'bb_upper', 'bb_lower', 'vwap']
        available_indicators = [ind for ind in indicators if ind in recent_df.columns]
        if available_indicators:
            header += "," + ",".join(available_indicators)
        
        data_lines.append(header)
        
        for _, row in recent_df.iterrows():
            line = f"{row['datetime']},{row['open']:.2f},{row['high']:.2f},{row['low']:.2f},{row['close']:.2f},{row['volume']:.0f}"
            
            for indicator in available_indicators:
                value = row.get(indicator, 0)
                if pd.isna(value):
                    value = 0
                line += f",{value:.2f}"
            
            data_lines.append(line)
        
        return "\\n".join(data_lines)
    
    def _prepare_pattern_data(self, df: pd.DataFrame, last_n: int = 30) -> str:
        """
        为形态分析准备数据格式
        """
        recent_df = df.tail(last_n).copy()
        
        data_lines = ["# ETH/USDT K线形态数据\\n"]
        data_lines.append("时间,开盘价,最高价,最低价,收盘价,成交量,K线描述")
        
        for _, row in recent_df.iterrows():
            # 基础K线描述
            body_color = "阳线" if row['close'] > row['open'] else "阴线" if row['close'] < row['open'] else "十字"
            body_size = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            
            description_parts = [body_color]
            
            # 添加形态信息
            if 'is_doji' in row and row['is_doji']:
                description_parts.append("十字星")
            if 'is_hammer' in row and row['is_hammer']:
                description_parts.append("锤子线")
            if 'is_shooting_star' in row and row['is_shooting_star']:
                description_parts.append("流星线")
            if 'bullish_engulfing' in row and row['bullish_engulfing']:
                description_parts.append("看涨吞没")
            if 'bearish_engulfing' in row and row['bearish_engulfing']:
                description_parts.append("看跌吞没")
            
            # 实体大小描述
            if total_range > 0:
                body_ratio = body_size / total_range
                if body_ratio < 0.1:
                    description_parts.append("小实体")
                elif body_ratio > 0.7:
                    description_parts.append("大实体")
            
            description = ",".join(description_parts)
            
            line = f"{row['datetime']},{row['open']:.2f},{row['high']:.2f},{row['low']:.2f},{row['close']:.2f},{row['volume']:.0f},{description}"
            data_lines.append(line)
        
        return "\\n".join(data_lines)
    
    def validated_vpa_analysis(self, 
                              df: pd.DataFrame,
                              enable_fast_mode: bool = False,
                              validation_config: Optional[ValidationConfig] = None) -> Dict[str, Any]:
        """
        带验证的VPA分析 - 多模型交叉验证防幻觉
        
        Args:
            df: K线数据
            enable_fast_mode: 快速模式（只用主要模型）
            validation_config: 验证配置
            
        Returns:
            包含验证结果的完整分析报告
        """
        try:
            if not self.validator:
                logger.warning("⚠️ 验证器未启用，回退到单模型分析")
                return self._fallback_single_analysis(df)
            
            logger.info("🔍 开始带验证的VPA分析...")
            
            # 使用最优的Pattern格式准备数据
            from formatters import DataFormatter
            formatter = DataFormatter()
            
            # 基于阶段2测试结果，Pattern格式最优
            formatted_data = formatter.to_pattern_description(df)
            
            # 执行多模型验证分析
            validation_result = self.validator.validate_analysis(
                data=formatted_data,
                analysis_type='vpa',
                enable_fast_mode=enable_fast_mode
            )
            
            # 准备数据摘要
            data_summary = {
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
            }
            
            # 构建验证分析报告
            validated_report = {
                'analysis_type': 'validated_vpa',
                'data_summary': data_summary,
                'validation_summary': self.validator.get_validation_summary(validation_result),
                'consensus_analysis': self._extract_consensus_analysis(validation_result),
                'model_analyses': {
                    'primary': validation_result.primary_analysis,
                    'validation': validation_result.validation_analyses
                },
                'quality_indicators': {
                    'consensus_score': validation_result.consensus_score,
                    'confidence_level': validation_result.confidence_level,
                    'model_agreement': len(validation_result.disagreements) == 0,
                    'has_arbitration': validation_result.arbitration_result is not None
                },
                'risk_assessment': self._generate_risk_assessment(validation_result),
                'performance_metrics': {
                    'total_cost': validation_result.total_cost,
                    'processing_time': validation_result.processing_time,
                    'models_used': len(validation_result.primary_analysis) + len(validation_result.validation_analyses)
                }
            }
            
            # 如果存在分歧，添加详细分歧报告
            if validation_result.disagreements:
                validated_report['disagreement_analysis'] = {
                    'disagreements': validation_result.disagreements,
                    'arbitration_available': validation_result.arbitration_result is not None,
                    'recommendation': self._get_disagreement_recommendation(validation_result)
                }
            
            logger.info(f"✅ 验证分析完成 - 共识得分: {validation_result.consensus_score:.2f}")
            return validated_report
            
        except Exception as e:
            logger.error(f"❌ 验证分析失败: {e}")
            return {
                'error': f"验证分析失败: {str(e)}",
                'fallback_analysis': self._fallback_single_analysis(df)
            }
    
    def _fallback_single_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """后备单模型分析"""
        logger.info("🔄 执行后备单模型分析")
        
        try:
            from formatters import DataFormatter
            formatter = DataFormatter()
            data = formatter.to_pattern_description(df)
            
            # 使用最佳模型进行分析
            result = self.client.analyze_market_data(
                data=data,
                model_name='gpt5-mini',  # 基于Phase2测试的最佳模型
                analysis_type='vpa'
            )
            
            return {
                'analysis_type': 'single_model_fallback',
                'model_used': 'gpt5-mini',
                'analysis': result,
                'warning': '由于验证器不可用，使用单模型分析，请注意潜在的幻觉风险'
            }
            
        except Exception as e:
            logger.error(f"❌ 后备分析也失败: {e}")
            return {'error': f"所有分析方法都失败: {str(e)}"}
    
    def _extract_consensus_analysis(self, validation_result) -> Dict[str, Any]:
        """从验证结果中提取共识分析"""
        if not validation_result.primary_analysis:
            return {}
        
        # 使用共识计算器生成摘要
        all_results = {**validation_result.primary_analysis, **validation_result.validation_analyses}
        
        if hasattr(self.validator, 'consensus_calc'):
            consensus_summary = self.validator.consensus_calc.generate_consensus_summary(
                all_results, validation_result.consensus_score
            )
            return consensus_summary
        
        return {'consensus_score': validation_result.consensus_score}
    
    def _generate_risk_assessment(self, validation_result) -> Dict[str, Any]:
        """生成风险评估"""
        risk_level = 'low'
        risk_factors = []
        
        # 基于共识得分评估风险
        if validation_result.consensus_score < 0.4:
            risk_level = 'high'
            risk_factors.append('模型间存在严重分歧')
        elif validation_result.consensus_score < 0.6:
            risk_level = 'medium'
            risk_factors.append('模型间存在一定分歧')
        
        # 检查其他风险因素
        if len(validation_result.primary_analysis) < 2:
            risk_factors.append('主要分析模型数量不足')
        
        if validation_result.disagreements:
            risk_factors.append(f'发现{len(validation_result.disagreements)}个具体分歧点')
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'confidence_score': validation_result.consensus_score,
            'reliability_rating': validation_result.confidence_level
        }
    
    def _get_disagreement_recommendation(self, validation_result) -> str:
        """获取分歧处理建议"""
        if validation_result.consensus_score < 0.4:
            return "强烈建议人工复核，模型间存在重大分歧，直接使用结果风险很高"
        elif validation_result.consensus_score < 0.6:
            return "建议谨慎使用，结合人工判断和额外信息源进行决策"
        else:
            return "分歧较小，可以参考主流观点，但建议关注少数派意见"
    
    def quick_validation_check(self, data: str, analysis_type: str = 'vpa') -> Dict[str, Any]:
        """
        快速验证检查 - 只用2个主要模型进行快速交叉验证
        
        适用场景：
        - 实时交易决策
        - 成本敏感的分析
        - 快速验证需求
        """
        if not self.validator:
            return {'error': '验证器未启用'}
        
        try:
            logger.info("⚡ 执行快速验证检查...")
            
            # 使用快速模式，只调用主要模型
            validation_result = self.validator.validate_analysis(
                data=data,
                analysis_type=analysis_type,
                enable_fast_mode=True
            )
            
            return {
                'quick_validation': True,
                'consensus_score': validation_result.consensus_score,
                'confidence_level': validation_result.confidence_level,
                'has_disagreements': len(validation_result.disagreements) > 0,
                'processing_time': validation_result.processing_time,
                'cost': validation_result.total_cost,
                'recommendation': self.validator._get_usage_recommendation(validation_result)
            }
            
        except Exception as e:
            logger.error(f"❌ 快速验证失败: {e}")
            return {'error': f'快速验证失败: {str(e)}'}