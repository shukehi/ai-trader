#!/usr/bin/env python3
"""
提示词管理器 - Al Brooks价格行为分析专用
"""

import os
import logging
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Al Brooks术语映射系统 - 解决提示词与评估器术语不匹配问题
BROOKS_TERM_MAPPING = {
    # 核心Brooks概念及其同义词
    'always_in_concepts': [
        'always in', 'always in long', 'always in short', 'transitioning',
        'market state', '市场状态'
    ],
    
    'bar_patterns': [
        # 提示词使用的术语 → 评估器可接受的术语
        'reversal bar with long tail', 'pin bar', 'reversal bar',
        'outside bar', 'engulfing bar', 
        'inside bar', 'ii', 'ioi',
        'trend bar', 'follow through', 'follow-through'
    ],
    
    'structure_analysis': [
        'H1', 'H2', 'L1', 'L2', 'high 1', 'high 2', 'low 1', 'low 2',
        'first entry', 'second entry',
        'swing point', 'swing high', 'swing low',
        'pullback', 'two-legged', 'two-legged pullback'
    ],
    
    'brooks_concepts': [
        'breakout mode', 'tight trading range', 'TTR',
        'measured move', 'magnet', 'micro channel',
        'spike and channel', 'wedge', 'flag',
        'trend strength', 'strong', 'medium', 'weak'
    ],
    
    'risk_management': [
        'stop', 'stop loss', 'target', 'entry', 'exit',
        'structural stop', 'position size', 'risk management'
    ]
}

class PromptManager:
    """
    提示词管理器 - Al Brooks价格行为分析专用版本
    
    专注于Al Brooks价格行为分析方法：
    - Al Brooks 价格行为分析 (生产就绪)
    
    系统已优化为专门支持Al Brooks方法论。
    """
    
    def __init__(self, prompts_dir: str = None):
        """初始化提示词管理器"""
        if prompts_dir is None:
            # 默认使用当前文件所在目录
            self.prompts_dir = Path(__file__).parent
        else:
            self.prompts_dir = Path(prompts_dir)
        
        self._prompt_cache = {}
        self._available_methods = None
        
        logger.info(f"✅ 提示词管理器初始化完成，目录: {self.prompts_dir}")
    
    def load_prompt(self, category: str, method: str) -> str:
        """
        加载指定分析方法的提示词
        
        Args:
            category: 分析类别 (仅支持 price_action)
            method: 具体方法名 (仅支持 al_brooks_analysis)
            
        Returns:
            提示词内容
        """
        cache_key = f"{category}/{method}"
        
        # 检查缓存
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        # 构建文件路径
        prompt_file = self.prompts_dir / category / f"{method}.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 缓存提示词
            self._prompt_cache[cache_key] = content
            logger.info(f"📄 加载提示词: {cache_key}")
            
            return content
            
        except Exception as e:
            logger.error(f"❌ 加载提示词失败: {cache_key}, 错误: {e}")
            raise
    
    def list_available_methods(self) -> Dict[str, List[str]]:
        """
        获取所有可用的分析方法
        
        Returns:
            {category: [method1, method2, ...]}
        """
        if self._available_methods is not None:
            return self._available_methods
        
        methods = {}
        
        # 扫描所有分类目录
        for category_dir in self.prompts_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                category_name = category_dir.name
                category_methods = []
                
                # 扫描每个分类下的提示词文件
                for prompt_file in category_dir.glob('*.txt'):
                    method_name = prompt_file.stem
                    category_methods.append(method_name)
                
                if category_methods:
                    methods[category_name] = sorted(category_methods)
        
        self._available_methods = methods
        logger.info(f"🔍 发现分析方法: {dict(methods)}")
        
        return methods
    
    def get_method_info(self, full_method: str) -> Dict[str, str]:
        """
        解析完整方法名并返回信息
        
        Args:
            full_method: 格式如 "vpa-classic" 或 "ict-liquidity"
            
        Returns:
            {'category': 'volume_analysis', 'method': 'vpa_classic', 'display_name': 'VPA经典分析'}
        """
        # ==== Al Brooks 价格行为分析方法映射 ====
        method_mapping = {
            'al-brooks': {
                'category': 'price_action',
                'method': 'al_brooks_analysis',
                'display_name': 'Al Brooks价格行为分析',
                'requires_metadata': True
            },
            'price-action-al-brooks-analysis': {
                'category': 'price_action',
                'method': 'al_brooks_analysis',
                'display_name': 'Al Brooks价格行为分析',
                'requires_metadata': True
            }
        }
        
        if full_method not in method_mapping:
            available_methods = list(method_mapping.keys())
            raise ValueError(f"\n❌ 系统仅支持Al Brooks分析方法。\n" +
                           f"🔍 可用方法: {available_methods}\n" +
                           f"📝 请使用: --method al-brooks 或 --method price-action-al-brooks-analysis")
        
        return method_mapping[full_method]

    def get_required_metadata_fields(self) -> List[str]:
        """需要传递到分析器/输出的元数据字段。禁止Unknown/Unspecified。"""
        return ['venue', 'timezone', 'tick_size', 'fees_bps', 'slippage_ticks']
    
    def get_quality_evaluator(self, full_method: str) -> Callable:
        """
        获取指定分析方法的质量评估函数
        
        Args:
            full_method: 完整方法名
            
        Returns:
            质量评估函数
        """
        method_info = self.get_method_info(full_method)
        category = method_info['category']
        
        # Al Brooks专用质量评估器
        if category == 'price_action':
            return self._evaluate_pa_quality
        else:
            return self._evaluate_general_quality
    
    def _evaluate_pa_quality(self, analysis_text: str, df: Any) -> int:
        """价格行为分析质量评估（优化Al Brooks支持）- 新权重分配"""
        score = 0
        text_lower = analysis_text.lower()
        
        # === 优化权重分配：分析质量60分 + 术语准确40分 ===
        
        # 1. 结构分析深度 (30分) - 提高权重
        structure_score = 0
        # Always In状态分析
        always_in_terms = BROOKS_TERM_MAPPING['always_in_concepts']
        if any(term.lower() in text_lower for term in always_in_terms):
            structure_score += 15
        
        # 结构识别 (swing points, H1/H2等)
        structure_terms = BROOKS_TERM_MAPPING['structure_analysis']
        structure_count = sum(1 for term in structure_terms if term.lower() in text_lower)
        structure_score += min(15, structure_count * 3)
        score += min(30, structure_score)
        
        # 2. 交易计划完整性 (20分) - 提高权重
        plan_score = 0
        risk_terms = BROOKS_TERM_MAPPING['risk_management']
        plan_count = sum(1 for term in risk_terms if term.lower() in text_lower)
        plan_score = min(20, plan_count * 4)
        score += plan_score
        
        # 3. Brooks概念应用 (10分) - 概念深度
        concept_terms = BROOKS_TERM_MAPPING['brooks_concepts']
        concept_count = sum(1 for term in concept_terms if term.lower() in text_lower)
        score += min(10, concept_count * 2)
        
        # 4. Brooks术语准确性 (25分) - 使用映射表
        term_score = 0
        bar_patterns = BROOKS_TERM_MAPPING['bar_patterns']
        pattern_count = sum(1 for pattern in bar_patterns if pattern.lower() in text_lower)
        term_score = min(25, pattern_count * 3)
        score += term_score
        
        # 5. 具体价位引用 (15分) - 提高权重，体现数据结合
        price_score = 0
        # 检查最近5个价位的引用
        recent_prices = df['close'].values[-5:]
        price_matches = sum(1 for price in recent_prices 
                          if str(round(float(price), 2)) in analysis_text)
        price_score += price_matches * 5
        
        # 检查关键价位（支撑阻力）的数值引用
        if any(keyword in text_lower for keyword in ['support', '支撑', 'resistance', '阻力']):
            price_score += 5
        
        score += min(15, price_score)
        
        # === 质量加分项 ===
        # JSON格式完整性奖励 (额外5分)
        if 'schema_version' in text_lower and 'always_in_state' in text_lower:
            score += 5
            
        # 风险管理细节奖励 (额外5分)
        if any(term in text_lower for term in ['structural stop', 'measured move', 'magnet']):
            score += 5
        
        return min(100, score)
    
    def _evaluate_general_quality(self, analysis_text: str, df: Any) -> int:
        """通用质量评估 (后备方案)"""
        score = 0
        
        # 基础评估标准
        if len(analysis_text) > 200:
            score += 20
        if any(str(round(price, 2)) in analysis_text for price in df['close'].values[-5:]):
            score += 30
        
        general_keywords = ['分析', '建议', '趋势', '支撑', '阻力', '成交量']
        keyword_count = sum(1 for kw in general_keywords if kw in analysis_text)
        score += min(50, keyword_count * 10)
        
        return min(100, score)
    
    def clear_cache(self):
        """清空提示词缓存"""
        self._prompt_cache.clear()
        self._available_methods = None
        logger.info("🗑️ 提示词缓存已清空")
    
    def reload_prompts(self):
        """重新加载所有提示词"""
        self.clear_cache()
        self.list_available_methods()
        logger.info("🔄 提示词已重新加载")
