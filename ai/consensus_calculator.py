#!/usr/bin/env python3
"""
共识算法模块
计算多模型分析结果的一致性和共识得分
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import Counter
import logging

logger = logging.getLogger(__name__)

@dataclass
class VPASignal:
    """增强的VPA信号提取结果"""
    market_phase: Optional[str] = None  # Accumulation, Distribution, Markup, Markdown
    vpa_signal: Optional[str] = None    # bullish, bearish, neutral
    price_direction: Optional[str] = None  # up, down, sideways
    confidence: Optional[str] = None    # high, medium, low
    vsa_signals: Optional[List[str]] = None       # VSA专业信号 (新增)
    timeframe_consistency: Optional[str] = None  # 时间框架一致性 (新增)
    perpetual_factors: Optional[List[str]] = None          # 永续合约因素 (新增)
    key_levels: Optional[List[float]] = None      # 关键价位

    def __post_init__(self):
        if self.key_levels is None:
            self.key_levels = []
        if self.vsa_signals is None:
            self.vsa_signals = []
        if self.perpetual_factors is None:
            self.perpetual_factors = []

class ConsensusCalculator:
    """
    共识计算器
    
    功能：
    1. 从分析文本中提取关键指标
    2. 计算模型间一致性得分
    3. 识别具体分歧点
    4. 生成共识摘要
    """
    
    def __init__(self):
        # 增强的VPA权重配置 (优化后7维度)
        self.weights = {
            'market_phase': 0.25,      # 市场阶段 (降低以平衡其他维度)
            'vpa_signal': 0.20,        # VPA信号
            'price_direction': 0.20,   # 价格方向
            'vsa_signals': 0.15,       # VSA专业信号 (新增)
            'timeframe_consistency': 0.10,  # 时间框架一致性 (新增)
            'perpetual_factors': 0.05,      # 永续合约特殊因素 (新增)
            'confidence': 0.05         # 置信度 (降低权重)
        }
        
        # 模式匹配规则
        self._init_patterns()
        
        logger.info("✅ ConsensusCalculator初始化完成")
    
    def _init_patterns(self):
        """初始化文本模式匹配规则"""
        
        # 市场阶段关键词
        self.market_phase_patterns = {
            'accumulation': [
                r'accumulation', r'吸筹', r'收集', r'建仓', r'买入累积',
                r'wyckoff.*accumulation', r'smart.*money.*buying'
            ],
            'distribution': [
                r'distribution', r'派发', r'分配', r'出货', r'获利了结',
                r'wyckoff.*distribution', r'smart.*money.*selling'
            ],
            'markup': [
                r'markup', r'拉升', r'上涨阶段', r'牛市', r'推升',
                r'bullish.*trend', r'upward.*movement'
            ],
            'markdown': [
                r'markdown', r'下跌阶段', r'熊市', r'回调', r'下降',
                r'bearish.*trend', r'downward.*movement'
            ]
        }
        
        # VPA信号关键词
        self.vpa_signal_patterns = {
            'bullish': [
                r'bullish', r'看涨', r'买入', r'做多', r'上涨信号',
                r'positive.*signal', r'buy.*signal', r'健康.*上涨'
            ],
            'bearish': [
                r'bearish', r'看跌', r'卖出', r'做空', r'下跌信号',
                r'negative.*signal', r'sell.*signal', r'健康.*下跌'
            ],
            'neutral': [
                r'neutral', r'中性', r'震荡', r'盘整', r'观望',
                r'sideways', r'range.*bound', r'wait.*and.*see'
            ]
        }
        
        # 价格方向关键词
        self.price_direction_patterns = {
            'up': [
                r'上涨', r'上升', r'突破', r'冲高', r'反弹',
                r'upward', r'rising', r'breakout', r'rally'
            ],
            'down': [
                r'下跌', r'下降', r'跳水', r'回落', r'暴跌',
                r'downward', r'falling', r'decline', r'dump'
            ],
            'sideways': [
                r'横盘', r'震荡', r'盘整', r'窄幅', r'整理',
                r'sideways', r'consolidation', r'range'
            ]
        }
        
        # 置信度关键词
        self.confidence_patterns = {
            'high': [
                r'高度确信', r'强烈', r'明确', r'确定', r'肯定', r'非常', r'十分',
                r'明显', r'显著', r'清晰', r'毫无疑问', r'绝对',
                r'strongly', r'clearly', r'definitely', r'confident', r'certain',
                r'obvious', r'significant', r'clear', r'absolutely', r'very'
            ],
            'medium': [
                r'可能', r'倾向', r'倾向于', r'有可能', r'较为', r'相对',
                r'预计', r'预期', r'估计', r'大概', r'或许',
                r'likely', r'probably', r'tends.*to', r'appears', r'seems',
                r'expected', r'estimated', r'perhaps', r'moderate'
            ],
            'low': [
                r'不确定', r'谨慎', r'需要观察', r'存在风险', r'建议等待',
                r'存疑', r'待观察', r'需谨慎', r'不明确', r'有待验证',
                r'uncertain', r'cautious', r'risky', r'wait.*and.*see',
                r'unclear', r'questionable', r'need.*verification', r'weak'
            ]
        }
        
        # VSA专业信号关键词 (新增)
        self.vsa_signal_patterns = {
            'no_demand': [
                r'no.*demand', r'需求不足', r'无量上涨', r'可疑.*上涨', r'假突破',
                r'upthrust', r'诱多', r'weak.*rally'
            ],
            'no_supply': [
                r'no.*supply', r'供给不足', r'无量下跌', r'可疑.*下跌', r'假跌破',
                r'spring', r'洗盘', r'weak.*decline'
            ],
            'climax_volume': [
                r'climax.*volume', r'成交量高潮', r'放量', r'巨量', r'异常.*量',
                r'selling.*climax', r'buying.*climax', r'极端.*成交量'
            ],
            'wide_spread': [
                r'wide.*spread', r'宽.*价差', r'大幅波动', r'高波动', r'剧烈.*波动'
            ],
            'narrow_spread': [
                r'narrow.*spread', r'窄.*价差', r'小幅波动', r'低波动', r'温和.*波动'
            ]
        }
        
        # 永续合约专业术语 (新增)
        self.perpetual_patterns = {
            'funding_rate_positive': [
                r'正.*资金费率', r'多头.*费率', r'funding.*rate.*positive', r'多头.*支付'
            ],
            'funding_rate_negative': [
                r'负.*资金费率', r'空头.*费率', r'funding.*rate.*negative', r'空头.*支付'
            ],
            'open_interest_increase': [
                r'持仓量.*增加', r'OI.*增长', r'open.*interest.*increase', r'持仓.*上升'
            ],
            'open_interest_decrease': [
                r'持仓量.*减少', r'OI.*下降', r'open.*interest.*decrease', r'持仓.*下降'
            ],
            'leverage_effect': [
                r'杠杆.*效应', r'强平', r'爆仓', r'cascade', r'liquidation', r'margin.*call'
            ]
        }
    
    def calculate_consensus(self, results: Dict[str, Any]) -> float:
        """
        计算模型间共识得分
        
        Args:
            results: {model_name: analysis_result} 字典
            
        Returns:
            float: 0-1之间的共识得分
        """
        try:
            logger.info(f"🔄 开始计算 {len(results)} 个模型的共识得分...")
            
            # 提取所有模型的VPA信号
            model_signals = {}
            for model_name, result in results.items():
                if result.get('success') and result.get('analysis'):
                    signal = self._extract_vpa_signals(result['analysis'], model_name)
                    model_signals[model_name] = signal
                else:
                    logger.warning(f"⚠️ 跳过模型 {model_name}: 分析失败或无内容")
            
            if len(model_signals) < 2:
                logger.warning("⚠️ 有效模型少于2个，无法计算共识")
                return 0.0
            
            # 计算各维度的一致性
            dimension_scores = {}
            for dimension, weight in self.weights.items():
                score = self._calculate_dimension_consensus(model_signals, dimension)
                dimension_scores[dimension] = score
                logger.info(f"  📊 {dimension}: {score:.3f} (权重: {weight})")
            
            # 计算加权总分
            consensus_score = sum(
                score * self.weights[dimension] 
                for dimension, score in dimension_scores.items()
            )
            
            logger.info(f"🎯 最终共识得分: {consensus_score:.3f}")
            return consensus_score
            
        except Exception as e:
            logger.error(f"❌ 计算共识得分失败: {e}")
            return 0.0
    
    def _extract_vpa_signals(self, analysis_text: str, model_name: str) -> VPASignal:
        """从分析文本中提取增强的VPA信号"""
        text = analysis_text.lower()
        
        # 提取传统VPA信号
        market_phase = self._extract_category(text, self.market_phase_patterns)
        vpa_signal = self._extract_category(text, self.vpa_signal_patterns)
        price_direction = self._extract_category(text, self.price_direction_patterns)
        confidence = self._extract_category(text, self.confidence_patterns)
        key_levels = self._extract_key_levels(text)
        
        # 提取VSA专业信号 (新增)
        vsa_signals = self._extract_multiple_categories(text, self.vsa_signal_patterns)
        
        # 提取时间框架一致性信号 (新增)
        timeframe_consistency = self._infer_timeframe_consistency(text)
        
        # 提取永续合约因素 (新增) 
        perpetual_factors = self._extract_multiple_categories(text, self.perpetual_patterns)
        
        signal = VPASignal(
            market_phase=market_phase,
            vpa_signal=vpa_signal,
            price_direction=price_direction,
            confidence=confidence,
            vsa_signals=vsa_signals,
            timeframe_consistency=timeframe_consistency,
            perpetual_factors=perpetual_factors,
            key_levels=key_levels
        )
        
        logger.debug(f"📍 {model_name} 增强VPA信号: {signal}")
        return signal
    
    def _extract_category(self, text: str, patterns: Dict[str, List[str]]) -> Optional[str]:
        """从文本中提取分类信息"""
        scores = {}
        text_lower = text.lower()  # 转换为小写进行匹配
        
        for category, pattern_list in patterns.items():
            score = 0
            for pattern in pattern_list:
                # 使用大小写无关的正则匹配
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            scores[category] = score
        
        # 返回得分最高的分类
        if scores and max(scores.values()) > 0:
            return max(scores.keys(), key=lambda k: scores[k])
        
        # 如果是置信度模式，提供智能默认值
        if patterns == self.confidence_patterns:
            # 基于文本长度和内容复杂度推断置信度
            if len(text) > 500 and ('分析' in text or 'analysis' in text_lower):
                return 'medium'
            elif '?' in text or '？' in text or 'maybe' in text_lower or '或许' in text:
                return 'low'
            else:
                return 'medium'  # 默认中等置信度
        
        return None
    
    def _extract_key_levels(self, text: str) -> List[float]:
        """提取关键价位"""
        # 匹配价格数字（ETH通常在1000-10000范围）
        price_patterns = [
            r'(\d{4}\.\d{1,2})',  # 4位.2位小数
            r'(\d{4})',           # 4位整数
            r'支撑.*?(\d{4})',     # 中文支撑位
            r'阻力.*?(\d{4})',     # 中文阻力位
            r'support.*?(\d{4})',  # 英文支撑位
            r'resistance.*?(\d{4})' # 英文阻力位
        ]
        
        levels = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    level = float(match)
                    if 1000 <= level <= 10000:  # ETH价格合理范围
                        levels.append(level)
                except ValueError:
                    continue
        
        # 去重并排序
        return sorted(list(set(levels)))
    
    def _extract_multiple_categories(self, text: str, patterns: Dict[str, List[str]]) -> List[str]:
        """从文本中提取多个匹配的分类 (用于VSA信号和永续合约因素)"""
        matched_categories = []
        text_lower = text.lower()
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched_categories.append(category)
                    break  # 找到一个匹配就够了，避免重复
        
        return matched_categories
    
    def _infer_timeframe_consistency(self, text: str) -> Optional[str]:
        """推断时间框架一致性"""
        text_lower = text.lower()
        
        # 检查是否提到多时间框架分析
        timeframe_indicators = [
            r'多.*时间.*框架', r'不同.*周期', r'日线.*小时', r'长.*短.*周期',
            r'multi.*timeframe', r'different.*timeframes', r'daily.*hourly',
            r'higher.*lower.*timeframe'
        ]
        
        has_timeframe_analysis = any(
            re.search(pattern, text_lower, re.IGNORECASE) 
            for pattern in timeframe_indicators
        )
        
        if has_timeframe_analysis:
            # 检查一致性描述
            consistency_patterns = {
                'consistent': [
                    r'一致', r'同向', r'支持', r'确认', r'吻合',
                    r'consistent', r'aligned', r'confirm', r'support'
                ],
                'conflicting': [
                    r'冲突', r'矛盾', r'分歧', r'不一致', r'背离',
                    r'conflict', r'diverge', r'inconsistent', r'contradict'
                ],
                'mixed': [
                    r'混合', r'部分', r'有限', r'局部',
                    r'mixed', r'partial', r'limited', r'some'
                ]
            }
            
            for category, pattern_list in consistency_patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        return category
        
        return None
    
    def _calculate_dimension_consensus(self, model_signals: Dict[str, VPASignal], dimension: str) -> float:
        """计算某个维度的一致性得分 (支持新的VPA维度)"""
        if dimension == 'vsa_signals':
            return self._calculate_list_consensus(model_signals, dimension)
        elif dimension == 'perpetual_factors':
            return self._calculate_list_consensus(model_signals, dimension)
        elif dimension == 'timeframe_consistency':
            return self._calculate_categorical_consensus(model_signals, dimension)
        elif dimension == 'key_levels':
            return self._calculate_key_levels_consensus(model_signals)
        else:
            # 传统的分类维度
            return self._calculate_categorical_consensus(model_signals, dimension)
    
    def _calculate_categorical_consensus(self, model_signals: Dict[str, VPASignal], dimension: str) -> float:
        """计算分类维度的一致性"""
        values = []
        
        for signal in model_signals.values():
            value = getattr(signal, dimension, None)
            if value is not None:
                values.append(value)
        
        if not values:
            return 0.0
        
        # 对于分类变量，计算最频繁值的占比
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]
        consensus_ratio = most_common_count / len(values)
        
        return consensus_ratio
    
    def _calculate_list_consensus(self, model_signals: Dict[str, VPASignal], dimension: str) -> float:
        """计算列表类型维度的一致性 (VSA信号、永续合约因素等)"""
        all_values: List[str] = []
        model_count = 0
        
        for signal in model_signals.values():
            value_list = getattr(signal, dimension, [])
            if value_list:
                all_values.extend(value_list)
                model_count += 1
        
        if not all_values or model_count == 0:
            return 0.0
        
        # 计算各类别的出现频率
        counter = Counter(all_values)
        total_mentions = len(all_values)
        
        # 计算加权一致性：考虑最频繁项目的占比和模型覆盖率
        if counter:
            most_common_count = counter.most_common(1)[0][1]
            frequency_consensus = most_common_count / total_mentions
            coverage_bonus = min(model_count / len(model_signals), 1.0) * 0.2
            
            return min(frequency_consensus + coverage_bonus, 1.0)
        
        return 0.0
    
    def _calculate_key_levels_consensus(self, model_signals: Dict[str, VPASignal]) -> float:
        """计算关键价位的一致性"""
        all_levels = []
        for signal in model_signals.values():
            if signal.key_levels:
                all_levels.extend(signal.key_levels)
        
        if len(all_levels) < 2:
            return 0.0
        
        # 计算价位聚类的一致性
        # 这里使用简单的范围匹配：价位相差<1%认为一致
        consensus_groups: List[List[float]] = []
        tolerance = 0.01  # 1%容差
        
        for level in all_levels:
            matched = False
            for group in consensus_groups:
                avg_group_level = sum(group) / len(group)
                if abs(level - avg_group_level) / avg_group_level <= tolerance:
                    group.append(level)
                    matched = True
                    break
            
            if not matched:
                consensus_groups.append([level])
        
        # 找到最大的一致组
        max_group_size = max(len(group) for group in consensus_groups) if consensus_groups else 0
        consensus_ratio = max_group_size / len(all_levels) if all_levels else 0
        
        return consensus_ratio
    
    def identify_disagreements(self, results: Dict[str, Any]) -> List[str]:
        """识别具体的分歧点"""
        disagreements: List[str] = []
        
        # 提取信号
        model_signals = {}
        for model_name, result in results.items():
            if result.get('success') and result.get('analysis'):
                signal = self._extract_vpa_signals(result['analysis'], model_name)
                model_signals[model_name] = signal
        
        if len(model_signals) < 2:
            return disagreements
        
        # 检查各维度分歧
        for dimension in ['market_phase', 'vpa_signal', 'price_direction']:
            values = []
            model_values = {}
            
            for model_name, signal in model_signals.items():
                value = getattr(signal, dimension, None)
                if value:
                    values.append(value)
                    model_values[model_name] = value
            
            if len(set(values)) > 1:  # 存在分歧
                disagreement_desc = f"{dimension}分歧: "
                value_groups: Dict[str, List[str]] = {}
                for model, value in model_values.items():
                    if value not in value_groups:
                        value_groups[value] = []
                    value_groups[value].append(model)
                
                parts = []
                for value, models in value_groups.items():
                    parts.append(f"{value}({', '.join(models)})")
                
                disagreement_desc += " vs ".join(parts)
                disagreements.append(disagreement_desc)
        
        return disagreements
    
    def generate_consensus_summary(self, results: Dict[str, Any], consensus_score: float) -> Dict[str, Any]:
        """生成共识摘要"""
        # 提取所有信号
        model_signals = {}
        for model_name, result in results.items():
            if result.get('success') and result.get('analysis'):
                signal = self._extract_vpa_signals(result['analysis'], model_name)
                model_signals[model_name] = signal
        
        # 找到各维度的主流观点
        consensus_view = {}
        for dimension in ['market_phase', 'vpa_signal', 'price_direction', 'confidence']:
            values = [getattr(signal, dimension) for signal in model_signals.values() 
                     if getattr(signal, dimension) is not None]
            
            if values:
                counter = Counter(values)
                most_common = counter.most_common(1)[0]
                consensus_view[dimension] = {
                    'value': most_common[0],
                    'support_count': most_common[1],
                    'total_count': len(values),
                    'confidence': most_common[1] / len(values)
                }
        
        # 汇总关键价位
        all_levels: List[float] = []
        for signal in model_signals.values():
            if signal.key_levels is not None:
                all_levels.extend(signal.key_levels)
        
        # 聚类价位
        if all_levels:
            consensus_levels = self._cluster_key_levels(all_levels)
        else:
            consensus_levels = []
        
        return {
            'consensus_score': consensus_score,
            'model_count': len(model_signals),
            'consensus_view': consensus_view,
            'consensus_levels': consensus_levels,
            'reliability': 'high' if consensus_score >= 0.8 else 'medium' if consensus_score >= 0.6 else 'low'
        }
    
    def _cluster_key_levels(self, levels: List[float], tolerance: float = 0.01) -> List[Dict[str, Any]]:
        """聚类关键价位"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters: List[Dict[str, Any]] = []
        
        for level in sorted_levels:
            matched = False
            for cluster in clusters:
                avg_level = sum(cluster['levels']) / len(cluster['levels'])
                if abs(level - avg_level) / avg_level <= tolerance:
                    cluster['levels'].append(level)
                    cluster['support_count'] += 1
                    matched = True
                    break
            
            if not matched:
                clusters.append({
                    'levels': [level],
                    'support_count': 1
                })
        
        # 计算每个聚类的代表价位和置信度
        result_clusters = []
        total_levels = len(levels)
        
        for cluster in clusters:
            avg_level = sum(cluster['levels']) / len(cluster['levels'])
            confidence = cluster['support_count'] / total_levels
            
            result_clusters.append({
                'level': round(avg_level, 2),
                'support_count': cluster['support_count'],
                'confidence': confidence,
                'type': self._classify_level_type(avg_level, sorted_levels)
            })
        
        # 按支持度排序
        return sorted(result_clusters, key=lambda x: x['support_count'], reverse=True)
    
    def _classify_level_type(self, level: float, all_levels: List[float]) -> str:
        """分类价位类型（支撑/阻力）"""
        # 简单的分类逻辑：低于中位数的是支撑，高于的是阻力
        median = sorted(all_levels)[len(all_levels) // 2] if all_levels else level
        
        if level < median:
            return 'support'
        else:
            return 'resistance'