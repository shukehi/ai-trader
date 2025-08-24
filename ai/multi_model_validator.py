#!/usr/bin/env python3
"""
多模型验证引擎
防止单一模型幻觉，提供交叉验证和共识机制
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .openrouter_client import OpenRouterClient
from .consensus_calculator import ConsensusCalculator

logger = logging.getLogger(__name__)

@dataclass
class ValidationConfig:
    """验证配置 (优化版 - 对抗模型偏差)"""
    primary_models: Optional[List[str]] = None
    validation_models: Optional[List[str]] = None  
    consensus_threshold: float = 0.7      # 提高阈值确保质量
    enable_arbitration: bool = True       # 启用仲裁处理分歧
    max_models: int = 3                   # 专注于高质量模型
    timeout_seconds: int = 120
    # 偏差检测设置
    direction_bias_threshold: float = 0.8  # 检测方向偏差的阈值
    enable_bias_correction: bool = True    # 启用偏差纠正
    
    def __post_init__(self):
        if self.primary_models is None:
            # 实用的模型组合 - 对抗方向性偏差
            self.primary_models = ['gpt4o-mini', 'claude-haiku']
        if self.validation_models is None:
            # 平衡验证模型，提供不同视角
            self.validation_models = ['gemini-flash']

@dataclass 
class ValidationResult:
    """验证结果"""
    consensus_score: float
    confidence_level: str  # 'high', 'medium', 'low'
    primary_analysis: Dict[str, Any]
    validation_analyses: Dict[str, Any]
    disagreements: List[str]
    arbitration_result: Optional[Dict[str, Any]] = None
    total_cost: float = 0.0
    processing_time: float = 0.0

class MultiModelValidator:
    """
    多模型验证引擎
    
    功能：
    1. 并行调用多个LLM模型
    2. 交叉验证分析结果
    3. 计算共识得分
    4. 检测分歧并报警
    5. 智能仲裁机制
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[ValidationConfig] = None):
        self.client = OpenRouterClient(api_key)
        self.config = config or ValidationConfig()
        self.consensus_calc = ConsensusCalculator()
        
        logger.info(f"✅ MultiModelValidator初始化完成")
        logger.info(f"主要模型: {self.config.primary_models}")
        logger.info(f"验证模型: {self.config.validation_models}")
        logger.info(f"共识阈值: {self.config.consensus_threshold}")
    
    def validate_analysis(self, 
                         data: str, 
                         analysis_type: str = 'vpa',
                         enable_fast_mode: bool = False) -> ValidationResult:
        """
        执行多模型验证分析
        
        Args:
            data: 格式化的市场数据
            analysis_type: 分析类型
            enable_fast_mode: 是否启用快速模式（只用primary models）
            
        Returns:
            ValidationResult: 验证结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始多模型验证分析 (类型: {analysis_type})")
            
            # 确定要使用的模型
            models_to_use = self._select_models(enable_fast_mode)
            logger.info(f"🤖 使用模型: {models_to_use}")
            
            # 并行调用多个模型
            model_results = self._parallel_analyze(data, models_to_use, analysis_type)
            
            # 过滤成功的结果
            successful_results = {k: v for k, v in model_results.items() 
                                if v.get('success', False)}
            
            if len(successful_results) < 2:
                logger.warning(f"⚠️ 只有{len(successful_results)}个模型成功，无法进行有效验证")
                return self._create_fallback_result(model_results, start_time)
            
            # 计算共识得分
            consensus_score = self.consensus_calc.calculate_consensus(successful_results)
            
            # 确定置信度等级
            confidence_level = self._determine_confidence_level(consensus_score)
            
            # 检测分歧
            disagreements = self._detect_disagreements(successful_results, consensus_score)
            
            # 准备主要分析和验证分析
            primary_results = {k: v for k, v in successful_results.items() 
                             if self.config.primary_models and k in self.config.primary_models}
            validation_results = {k: v for k, v in successful_results.items() 
                                if self.config.validation_models and k in self.config.validation_models}
            
            # 执行仲裁（如果需要）
            arbitration_result = None
            if (consensus_score < self.config.consensus_threshold and 
                self.config.enable_arbitration and 
                len(disagreements) > 0):
                arbitration_result = self._execute_arbitration(data, analysis_type, disagreements)
            
            # 计算总成本
            total_cost = sum(r.get('cost_estimate', {}).get('estimated_cost', 0) 
                           for r in successful_results.values())
            
            processing_time = time.time() - start_time
            
            result = ValidationResult(
                consensus_score=consensus_score,
                confidence_level=confidence_level,
                primary_analysis=primary_results,
                validation_analyses=validation_results,
                disagreements=disagreements,
                arbitration_result=arbitration_result,
                total_cost=total_cost,
                processing_time=processing_time
            )
            
            self._log_validation_summary(result)
            return result
            
        except Exception as e:
            logger.error(f"❌ 多模型验证失败: {e}")
            processing_time = time.time() - start_time
            return ValidationResult(
                consensus_score=0.0,
                confidence_level='low',
                primary_analysis={},
                validation_analyses={},
                disagreements=[f"验证过程出错: {str(e)}"],
                processing_time=processing_time
            )
    
    def _select_models(self, enable_fast_mode: bool) -> List[str]:
        """选择要使用的模型"""
        if enable_fast_mode:
            return (self.config.primary_models or [])[:2]  # 只用前2个主要模型
        
        primary_models = self.config.primary_models or []
        validation_models = self.config.validation_models or []
        all_models = primary_models + validation_models
        return all_models[:self.config.max_models]
    
    def _get_model_timeout(self, model: str) -> int:
        """根据模型类型获取超时时间"""
        # Premium模型需要更长时间
        premium_models = ['gpt5-chat', 'claude-opus-41', 'gemini-25-pro', 'grok4']
        standard_models = ['gpt4o', 'claude', 'gemini']
        
        if model in premium_models:
            return 60  # Premium模型60秒
        elif model in standard_models:
            return 30  # 标准模型30秒
        else:
            return 20  # 经济模型20秒
    
    def _get_fallback_model(self, failed_model: str) -> Optional[str]:
        """获取失败模型的降级替代"""
        fallback_map = {
            'gpt5-chat': 'gpt5-mini',
            'gpt5-mini': 'gpt4o',
            'claude-opus-41': 'claude',
            'claude': 'claude-haiku',
            'gemini-25-pro': 'gemini',
            'gemini': 'gemini-flash',
            'grok4': 'grok'
        }
        return fallback_map.get(failed_model)
    
    def _parallel_analyze(self, data: str, models: List[str], analysis_type: str) -> Dict[str, Any]:
        """并行调用多个模型进行分析"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(models), 5)) as executor:
            # 提交所有任务
            future_to_model = {
                executor.submit(self._safe_analyze_with_fallback, data, model, analysis_type): model 
                for model in models
            }
            
            # 收集结果
            for future in as_completed(future_to_model, timeout=self.config.timeout_seconds):
                model = future_to_model[future]
                try:
                    # 使用模型特定的超时时间
                    model_timeout = self._get_model_timeout(model)
                    result = future.result(timeout=model_timeout)
                    results[model] = result
                    if result.get('success'):
                        logger.info(f"✅ {model} 分析完成")
                    else:
                        logger.warning(f"⚠️ {model} 分析失败，已尝试降级处理")
                except Exception as e:
                    logger.error(f"❌ {model} 分析失败: {e}")
                    results[model] = {
                        'success': False,
                        'error': str(e),
                        'model': model
                    }
        
        return results
    
    def _safe_analyze(self, data: str, model: str, analysis_type: str) -> Dict[str, Any]:
        """安全的单模型分析调用"""
        try:
            result = self.client.analyze_market_data(
                data=data,
                model_name=model,
                analysis_type=analysis_type
            )
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model': model
            }
    
    def _safe_analyze_with_fallback(self, data: str, model: str, analysis_type: str) -> Dict[str, Any]:
        """带降级重试的安全分析调用"""
        try:
            # 尝试原始模型
            result = self.client.analyze_market_data(
                data=data,
                model_name=model,
                analysis_type=analysis_type
            )
            return result
        except Exception as e:
            logger.warning(f"🔄 {model} 失败，尝试降级: {e}")
            
            # 尝试降级模型
            fallback_model = self._get_fallback_model(model)
            if fallback_model:
                try:
                    logger.info(f"🔄 使用降级模型 {fallback_model}")
                    result = self.client.analyze_market_data(
                        data=data,
                        model_name=fallback_model,
                        analysis_type=analysis_type
                    )
                    # 标记这是降级结果
                    result['fallback_used'] = True
                    result['original_model'] = model
                    result['fallback_model'] = fallback_model
                    return result
                except Exception as fallback_e:
                    logger.error(f"❌ 降级模型 {fallback_model} 也失败: {fallback_e}")
            
            return {
                'success': False,
                'error': str(e),
                'model': model,
                'fallback_attempted': fallback_model is not None
            }
    
    def _determine_confidence_level(self, consensus_score: float) -> str:
        """确定置信度等级"""
        if consensus_score >= 0.8:
            return 'high'
        elif consensus_score >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _detect_disagreements(self, results: Dict[str, Any], consensus_score: float) -> List[str]:
        """检测分歧点"""
        disagreements = []
        
        if consensus_score < self.config.consensus_threshold:
            disagreements.append(f"共识得分过低: {consensus_score:.2f} < {self.config.consensus_threshold}")
        
        # 检查具体分歧点
        disagreement_details = self.consensus_calc.identify_disagreements(results)
        disagreements.extend(disagreement_details)
        
        return disagreements
    
    def _execute_arbitration(self, data: str, analysis_type: str, disagreements: List[str]) -> Dict[str, Any]:
        """执行仲裁分析"""
        logger.info("🤔 检测到重大分歧，启动仲裁机制...")
        
        # 选择仲裁模型（通常选择与主要模型不同的模型）
        arbitrator = 'claude-haiku'  # 简洁专业的仲裁者
        
        # 构建仲裁提示
        arbitration_prompt = f"""
作为独立的第三方分析师，请对以下分歧进行仲裁：

分歧点：
{chr(10).join(disagreements)}

请基于数据进行独立分析，并对争议点给出明确判断。
        """
        
        try:
            arbitration_result = self.client.analyze_market_data(
                data=data,
                model_name=arbitrator,
                analysis_type=analysis_type,
                custom_prompt=arbitration_prompt
            )
            
            logger.info("✅ 仲裁分析完成")
            return arbitration_result
            
        except Exception as e:
            logger.error(f"❌ 仲裁分析失败: {e}")
            return {
                'success': False,
                'error': f"仲裁失败: {str(e)}"
            }
    
    def _create_fallback_result(self, model_results: Dict[str, Any], start_time: float) -> ValidationResult:
        """创建后备结果（当验证失败时）"""
        processing_time = time.time() - start_time
        
        # 尝试找到至少一个成功的结果
        successful_results = {k: v for k, v in model_results.items() if v.get('success', False)}
        
        return ValidationResult(
            consensus_score=0.0,
            confidence_level='low',
            primary_analysis=successful_results,
            validation_analyses={},
            disagreements=["验证模型数量不足，无法进行有效交叉验证"],
            processing_time=processing_time
        )
    
    def _log_validation_summary(self, result: ValidationResult):
        """记录验证摘要"""
        logger.info("="*60)
        logger.info("🔍 多模型验证结果摘要")
        logger.info(f"📊 共识得分: {result.consensus_score:.2f}")
        logger.info(f"🎯 置信度: {result.confidence_level.upper()}")
        logger.info(f"✅ 主要分析: {len(result.primary_analysis)}个模型")
        logger.info(f"🔄 验证分析: {len(result.validation_analyses)}个模型")
        logger.info(f"⚠️ 分歧数量: {len(result.disagreements)}")
        logger.info(f"💰 总成本: ${result.total_cost:.6f}")
        logger.info(f"⏱️ 处理时间: {result.processing_time:.2f}秒")
        
        if result.disagreements:
            logger.warning("⚠️ 检测到的分歧:")
            for i, disagreement in enumerate(result.disagreements, 1):
                logger.warning(f"  {i}. {disagreement}")
        
        if result.arbitration_result:
            logger.info("🤔 已执行仲裁分析")
            
        logger.info("="*60)

    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """获取验证结果摘要（用于前端展示）"""
        return {
            'consensus_score': result.consensus_score,
            'confidence_level': result.confidence_level,
            'model_count': {
                'primary': len(result.primary_analysis),
                'validation': len(result.validation_analyses),
                'total': len(result.primary_analysis) + len(result.validation_analyses)
            },
            'has_disagreements': len(result.disagreements) > 0,
            'disagreement_count': len(result.disagreements),
            'has_arbitration': result.arbitration_result is not None,
            'performance': {
                'total_cost': result.total_cost,
                'processing_time': result.processing_time
            },
            'recommendation': self._get_usage_recommendation(result)
        }
    
    def _get_usage_recommendation(self, result: ValidationResult) -> str:
        """获取使用建议"""
        if result.confidence_level == 'high':
            return "分析结果高度一致，可信度极高，建议直接使用"
        elif result.confidence_level == 'medium':
            return "分析结果基本一致，建议结合人工判断使用"
        else:
            return "模型间存在显著分歧，强烈建议人工复核后使用"