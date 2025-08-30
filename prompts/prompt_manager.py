#!/usr/bin/env python3
"""
提示词管理器 - 支持多种交易分析方法的提示词管理
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
    提示词管理器 - Al Brooks验证期版本
    
    当前支持的分析方法（验证期）：
    - Al Brooks 价格行为分析 (专业验证中)
    
    注意：为确保分析质量，当前仅支持Al Brooks方法。
    其他方法将在验证完成后逐步恢复。
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
            category: 分析类别 (volume_analysis, price_action, ict_concepts, composite)
            method: 具体方法名 (vpa_classic, liquidity_zones, etc.)
            
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
        # ==== Al Brooks 验证期方法映射 ====
        # 注意：为确保分析质量，当前仅支持Al Brooks价格行为分析方法
        # 其他方法已暂时禁用，将在验证完成后逐步恢复
        # 完整方法列表备份位于: prompt_manager_full.py.backup
        
        method_mapping = {
            # Al Brooks 价格行为分析方法（验证期唯一支持）
            'al-brooks': {'category': 'price_action', 'method': 'al_brooks_analysis', 'display_name': 'Al Brooks价格行为分析'},
            'price-action-al-brooks-analysis': {'category': 'price_action', 'method': 'al_brooks_analysis', 'display_name': 'Al Brooks价格行为分析'},
            
            # ==== 暂时禁用的方法 ====
            # 将在Al Brooks验证完成后按以下顺序恢复：
            # 1. VPA经典分析 (基础重要)
            # 2. ICT公允价值缺口 (流行方法) 
            # 3. 其他ICT和价格行为方法
            # 4. 高级综合分析方法
            
            # VPA分析方法 (暂时禁用)
            # 'vpa-classic': {'category': 'volume_analysis', 'method': 'vpa_classic', 'display_name': 'VPA经典分析'},
            # 'vsa-coulling': {'category': 'volume_analysis', 'method': 'vsa_coulling', 'display_name': 'Anna Coulling VSA'},
            # 'volume-profile': {'category': 'volume_analysis', 'method': 'volume_profile', 'display_name': '成交量分布分析'},
            
            # ICT概念方法 (暂时禁用)
            # 'ict-liquidity': {'category': 'ict_concepts', 'method': 'liquidity_zones', 'display_name': 'ICT流动性分析'},
            # 'ict-orderblocks': {'category': 'ict_concepts', 'method': 'order_blocks', 'display_name': 'ICT订单块分析'},
            # 'ict-fvg': {'category': 'ict_concepts', 'method': 'fair_value_gaps', 'display_name': 'ICT公允价值缺口'},
            
            # 其他价格行为分析 (暂时禁用)
            # 'pa-support-resistance': {'category': 'price_action', 'method': 'support_resistance', 'display_name': '支撑阻力分析'},
            # 'pa-trend': {'category': 'price_action', 'method': 'trend_analysis', 'display_name': '趋势分析'},
            
            # 综合分析 (暂时禁用)
            # 'multi-timeframe': {'category': 'composite', 'method': 'multi_timeframe', 'display_name': '多时间框架分析'},
            # 'perpetual-specific': {'category': 'composite', 'method': 'perpetual_specific', 'display_name': '永续合约专项分析'}
        }
        
        if full_method not in method_mapping:
            # Al Brooks验证期友好错误提示
            available_methods = list(method_mapping.keys())
            raise ValueError(f"\n❌ 当前验证期仅支持Al Brooks分析方法。\n" +
                           f"🔍 可用方法: {available_methods}\n" +
                           f"📝 请使用: --method price-action-al-brooks-analysis\n" +
                           f"ℹ️  其他方法将在Al Brooks验证完成后逐步恢复。")
        
        return method_mapping[full_method]
    
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
        
        # 根据分析类别返回对应的质量评估器
        if category == 'volume_analysis':
            return self._evaluate_vpa_quality
        elif category == 'ict_concepts':
            return self._evaluate_ict_quality  
        elif category == 'price_action':
            return self._evaluate_pa_quality
        elif category == 'composite':
            return self._evaluate_composite_quality
        else:
            return self._evaluate_general_quality
    
    def _evaluate_vpa_quality(self, analysis_text: str, df: Any) -> int:
        """VPA分析质量评估 (基于VSA/VPA理论)"""
        score = 0
        
        # 1. VPA专业术语 (25分)
        vpa_terms = ['VSA', 'VPA', 'Smart Money', 'Dumb Money', 'Accumulation', 'Distribution', 
                    'Markup', 'Markdown', 'Wide Spread', 'Narrow Spread', 'Volume Climax',
                    'No Demand', 'No Supply', 'Upthrust', 'Spring', 'Effort', 'Result']
        term_count = sum(1 for term in vpa_terms if term.lower() in analysis_text.lower())
        score += min(25, term_count * 3)
        
        # 2. 量价关系分析 (25分)
        volume_price_keywords = ['量价关系', '成交量配合', '放量', '缩量', '量价背离', '量价同步']
        if any(keyword in analysis_text for keyword in volume_price_keywords):
            score += 25
        
        # 3. 市场阶段识别 (25分) 
        stage_keywords = ['accumulation', 'distribution', 'markup', 'markdown', '吸筹', '派发', '拉升', '下跌']
        if any(keyword.lower() in analysis_text.lower() for keyword in stage_keywords):
            score += 25
        
        # 4. 具体数据引用 (15分)
        if any(str(round(price, 2)) in analysis_text for price in df['close'].values[-5:]):
            score += 15
        
        # 5. 交易建议 (10分)
        trading_keywords = ['建议', '入场', '出场', '止损', '目标']
        if any(keyword in analysis_text for keyword in trading_keywords):
            score += 10
        
        return min(100, score)
    
    def _evaluate_ict_quality(self, analysis_text: str, df: Any) -> int:
        """ICT概念分析质量评估"""
        score = 0
        
        # 1. ICT专业术语 (30分)
        ict_terms = ['Liquidity', 'Order Block', 'Fair Value Gap', 'FVG', 'Market Structure', 
                    'BOS', 'CHoCH', 'Displacement', 'Imbalance', 'Smart Money', 'Institutional',
                    'Manipulation', 'Accumulation', 'Distribution', 'PD Arrays', 'Optimal Trade Entry']
        term_count = sum(1 for term in ict_terms if term.lower() in analysis_text.lower())
        score += min(30, term_count * 4)
        
        # 2. 流动性分析 (20分)
        liquidity_keywords = ['流动性', 'liquidity', '止损猎取', 'stop hunt', '流动性区域']
        if any(keyword.lower() in analysis_text.lower() for keyword in liquidity_keywords):
            score += 20
        
        # 3. 市场结构分析 (20分)
        structure_keywords = ['市场结构', 'market structure', 'BOS', 'break of structure', 'CHoCH']
        if any(keyword.lower() in analysis_text.lower() for keyword in structure_keywords):
            score += 20
        
        # 4. 具体价位分析 (20分)
        if any(str(round(price, 2)) in analysis_text for price in df['close'].values[-5:]):
            score += 20
        
        # 5. 入场策略 (10分)
        entry_keywords = ['入场', 'entry', 'OTE', 'optimal trade entry', '最优入场']
        if any(keyword.lower() in analysis_text.lower() for keyword in entry_keywords):
            score += 10
        
        return min(100, score)
    
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
    
    def _evaluate_composite_quality(self, analysis_text: str, df: Any) -> int:
        """综合分析质量评估"""
        score = 0
        
        # 1. 多维度分析 (30分)
        dimensions = ['技术分析', '基本面', '情绪面', '资金面', 'technical', 'fundamental', 'sentiment']
        dimension_count = sum(1 for dim in dimensions if dim.lower() in analysis_text.lower())
        score += min(30, dimension_count * 6)
        
        # 2. 时间框架分析 (25分)
        timeframe_keywords = ['短期', '中期', '长期', '多时间框架', 'short term', 'medium term', 'long term']
        if any(keyword.lower() in analysis_text.lower() for keyword in timeframe_keywords):
            score += 25
        
        # 3. 风险管理 (25分)
        risk_keywords = ['风险管理', '止损', '资金管理', '仓位控制', 'risk management', 'position sizing']
        if any(keyword.lower() in analysis_text.lower() for keyword in risk_keywords):
            score += 25
        
        # 4. 数据引用 (20分)
        if any(str(round(price, 2)) in analysis_text for price in df['close'].values[-5:]):
            score += 20
        
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