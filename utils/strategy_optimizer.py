#!/usr/bin/env python3
"""
策略优化器 - 基于历史数据的交易策略和AI模型优化
实现回测分析、参数调优、模型学习等高级功能
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
import re
from collections import defaultdict, Counter
# import matplotlib.pyplot as plt  # Optional visualization
# import seaborn as sns  # Optional for advanced plots

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """
    策略优化器
    
    功能特性:
    - AI提示词优化建议
    - 信号提取规则改进
    - 风险参数调优
    - 交易时间窗口分析
    """
    
    def __init__(self, db_path: str = "logs/trading_database.db"):
        """初始化策略优化器"""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
            
        logger.info(f"策略优化器初始化完成")
    
    def analyze_prompt_effectiveness(self) -> Dict[str, Any]:
        """
        分析不同AI提示词的有效性
        从分析文本中提取关键词和模式
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT 
                    a.model_used,
                    a.raw_analysis,
                    a.confidence_score,
                    t.realized_pnl,
                    t.side
                FROM ai_decisions a
                LEFT JOIN trades t ON a.decision_id = t.ai_decision_id
                WHERE a.raw_analysis IS NOT NULL
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # 分析成功和失败的分析文本特征
                success_keywords = Counter()
                failure_keywords = Counter()
                
                vpa_terms = [
                    'distribution', 'accumulation', 'markup', 'markdown',
                    'no supply', 'no demand', 'climax volume', 'upthrust', 'spring',
                    'wide spread', 'narrow spread', 'selling pressure', 'buying pressure',
                    'professional money', 'smart money', 'dumb money'
                ]
                
                analysis_results = {
                    'successful_patterns': defaultdict(int),
                    'failed_patterns': defaultdict(int),
                    'model_vpa_usage': defaultdict(lambda: {'total': 0, 'vpa_terms': 0}),
                    'confidence_correlation': []
                }
                
                for row in rows:
                    model, analysis, confidence, pnl, side = row
                    if not analysis:
                        continue
                        
                    analysis_lower = analysis.lower()
                    is_successful = pnl and pnl > 0
                    
                    # 统计VPA术语使用
                    vpa_count = sum(1 for term in vpa_terms if term in analysis_lower)
                    analysis_results['model_vpa_usage'][model]['total'] += 1
                    analysis_results['model_vpa_usage'][model]['vpa_terms'] += vpa_count
                    
                    # 提取关键模式
                    words = re.findall(r'\b[a-zA-Z]{4,}\b', analysis_lower)
                    for word in words:
                        if is_successful:
                            analysis_results['successful_patterns'][word] += 1
                        else:
                            analysis_results['failed_patterns'][word] += 1
                    
                    # 置信度相关性
                    if confidence:
                        analysis_results['confidence_correlation'].append({
                            'confidence': confidence,
                            'success': is_successful,
                            'vpa_terms': vpa_count
                        })
                
                # 计算VPA术语使用率
                vpa_usage_summary = {}
                for model, data in analysis_results['model_vpa_usage'].items():
                    if data['total'] > 0:
                        vpa_usage_summary[model] = {
                            'vpa_usage_rate': data['vpa_terms'] / data['total'],
                            'total_analyses': data['total']
                        }
                
                return {
                    'vpa_usage_by_model': vpa_usage_summary,
                    'top_success_words': dict(Counter(analysis_results['successful_patterns']).most_common(10)),
                    'top_failure_words': dict(Counter(analysis_results['failed_patterns']).most_common(10)),
                    'confidence_data': analysis_results['confidence_correlation']
                }
                
        except Exception as e:
            logger.error(f"提示词效果分析失败: {e}")
            return {'error': str(e)}
    
    def optimize_signal_extraction_rules(self) -> Dict[str, Any]:
        """
        优化信号提取的正则表达式规则
        基于成功和失败案例改进解析逻辑
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT 
                    a.raw_analysis,
                    a.extracted_signals,
                    t.realized_pnl,
                    t.side,
                    t.entry_price,
                    t.exit_price
                FROM ai_decisions a
                LEFT JOIN trades t ON a.decision_id = t.ai_decision_id
                WHERE a.raw_analysis IS NOT NULL AND a.extracted_signals IS NOT NULL
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # 分析信号提取的准确性
                extraction_analysis = {
                    'missed_signals': [],  # AI提到了但没提取到的信号
                    'incorrect_extractions': [],  # 提取错误的信号
                    'successful_extractions': [],  # 成功的提取
                    'suggested_patterns': []  # 建议的新正则表达式
                }
                
                # 定义一些应该被捕获的信号模式
                signal_patterns = {
                    'entry_price': [
                        r'入场价格?\s*[:：]\s*\$?(\d+\.?\d*)',
                        r'建议.*?(\d+\.?\d*)\s*附近.*?入场',
                        r'价格.*?(\d+\.?\d*)\s*做[多空]'
                    ],
                    'stop_loss': [
                        r'止损价格?\s*[:：]\s*\$?(\d+\.?\d*)',
                        r'止损.*?(\d+\.?\d*)',
                        r'停损.*?(\d+\.?\d*)'
                    ],
                    'take_profit': [
                        r'止盈价格?\s*[:：]\s*\$?(\d+\.?\d*)',
                        r'目标价格?\s*[:：]\s*\$?(\d+\.?\d*)',
                        r'获利了结.*?(\d+\.?\d*)'
                    ],
                    'direction': [
                        r'建议\s*(做多|做空|买入|卖出)',
                        r'(看多|看空|看涨|看跌)',
                        r'(bullish|bearish|买|卖)'
                    ]
                }
                
                for row in rows:
                    analysis, extracted_str, pnl, side, entry, exit = row
                    if not analysis:
                        continue
                        
                    try:
                        extracted = json.loads(extracted_str) if extracted_str else {}
                    except:
                        extracted = {}
                    
                    is_successful = pnl and pnl > 0
                    
                    # 检查每种信号类型的提取情况
                    for signal_type, patterns in signal_patterns.items():
                        found_in_text = False
                        extracted_value = extracted.get(signal_type)
                        
                        # 检查文本中是否有这类信号
                        for pattern in patterns:
                            if re.search(pattern, analysis, re.IGNORECASE):
                                found_in_text = True
                                break
                        
                        # 分析提取结果
                        if found_in_text and not extracted_value:
                            extraction_analysis['missed_signals'].append({
                                'signal_type': signal_type,
                                'analysis_text': analysis[:200] + '...',
                                'success': is_successful
                            })
                        elif found_in_text and extracted_value and is_successful:
                            extraction_analysis['successful_extractions'].append({
                                'signal_type': signal_type,
                                'extracted_value': extracted_value,
                                'analysis_text': analysis[:100] + '...'
                            })
                
                # 生成改进建议
                suggestions = []
                if extraction_analysis['missed_signals']:
                    suggestions.append({
                        'type': 'pattern_improvement',
                        'issue': f"发现 {len(extraction_analysis['missed_signals'])} 个漏提取信号",
                        'suggestion': '需要改进正则表达式匹配模式',
                        'implementation': 'signal_executor.py中的_extract_signals_from_text方法'
                    })
                
                return {
                    'extraction_analysis': extraction_analysis,
                    'optimization_suggestions': suggestions
                }
                
        except Exception as e:
            logger.error(f"信号提取规则优化失败: {e}")
            return {'error': str(e)}
    
    def analyze_optimal_parameters(self) -> Dict[str, Any]:
        """
        分析最优的交易参数设置
        包括风险比例、杠杆、持仓时间等
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT 
                    t.leverage,
                    t.margin_used,
                    t.holding_duration,
                    t.realized_pnl,
                    t.quantity,
                    t.entry_price,
                    t.exit_price,
                    a.confidence_score
                FROM trades t
                JOIN ai_decisions a ON t.ai_decision_id = a.decision_id
                WHERE t.realized_pnl IS NOT NULL
                """
                
                df = pd.read_sql_query(query, conn)
                
                if df.empty:
                    return {'message': '暂无已完成交易数据进行参数分析'}
                
                # 分析不同参数下的表现
                parameter_analysis = {
                    'leverage_performance': {},
                    'position_size_performance': {},
                    'holding_time_performance': {},
                    'confidence_threshold_analysis': {}
                }
                
                # 杠杆分析
                leverage_groups = df.groupby('leverage')
                for leverage, group in leverage_groups:
                    parameter_analysis['leverage_performance'][leverage] = {
                        'trade_count': len(group),
                        'win_rate': (group['realized_pnl'] > 0).mean(),
                        'avg_pnl': group['realized_pnl'].mean(),
                        'total_pnl': group['realized_pnl'].sum()
                    }
                
                # 仓位大小分析（按分位数分组）
                df['position_size_quantile'] = pd.qcut(df['quantity'], q=3, labels=['Small', 'Medium', 'Large'])
                size_groups = df.groupby('position_size_quantile')
                for size, group in size_groups:
                    parameter_analysis['position_size_performance'][str(size)] = {
                        'trade_count': len(group),
                        'win_rate': (group['realized_pnl'] > 0).mean(),
                        'avg_pnl': group['realized_pnl'].mean()
                    }
                
                # 持仓时间分析
                if df['holding_duration'].notna().any():
                    df['holding_hours'] = df['holding_duration'] / 3600
                    df['holding_category'] = pd.cut(df['holding_hours'], 
                                                   bins=[0, 1, 6, 24, float('inf')], 
                                                   labels=['<1h', '1-6h', '6-24h', '>24h'])
                    
                    time_groups = df.groupby('holding_category')
                    for time_cat, group in time_groups:
                        if len(group) > 0:
                            parameter_analysis['holding_time_performance'][str(time_cat)] = {
                                'trade_count': len(group),
                                'win_rate': (group['realized_pnl'] > 0).mean(),
                                'avg_pnl': group['realized_pnl'].mean()
                            }
                
                return parameter_analysis
                
        except Exception as e:
            logger.error(f"参数优化分析失败: {e}")
            return {'error': str(e)}
    
    def generate_optimization_plan(self) -> Dict[str, Any]:
        """
        生成综合优化计划
        整合所有分析结果，提供具体的改进步骤
        """
        try:
            prompt_analysis = self.analyze_prompt_effectiveness()
            signal_analysis = self.optimize_signal_extraction_rules()
            param_analysis = self.analyze_optimal_parameters()
            
            optimization_plan = {
                'immediate_actions': [],  # 立即可执行的改进
                'short_term_goals': [],   # 短期目标（1-2周）
                'long_term_strategy': [], # 长期策略（1个月+）
                'priority_score': {}
            }
            
            # 基于分析结果生成具体建议
            
            # 1. 提示词优化建议
            if 'vpa_usage_by_model' in prompt_analysis:
                for model, data in prompt_analysis['vpa_usage_by_model'].items():
                    if data['vpa_usage_rate'] < 0.5:  # VPA术语使用率低
                        optimization_plan['immediate_actions'].append({
                            'action': f'优化{model}的VPA提示词',
                            'reason': f'当前VPA术语使用率仅{data["vpa_usage_rate"]:.1%}',
                            'implementation': 'ai/trading_prompts.py中增加更多VPA专业术语',
                            'priority': 'high',
                            'effort': 'low'
                        })
            
            # 2. 信号提取改进
            if 'extraction_analysis' in signal_analysis:
                missed_count = len(signal_analysis['extraction_analysis'].get('missed_signals', []))
                if missed_count > 0:
                    optimization_plan['short_term_goals'].append({
                        'goal': '改进信号提取准确性',
                        'target': f'减少{missed_count}个漏提取信号',
                        'implementation': 'trading/signal_executor.py中的正则表达式优化',
                        'timeline': '1-2周',
                        'priority': 'medium'
                    })
            
            # 3. 参数优化建议
            if 'leverage_performance' in param_analysis:
                best_leverage = max(param_analysis['leverage_performance'].keys(),
                                  key=lambda k: param_analysis['leverage_performance'][k]['win_rate'])
                optimization_plan['immediate_actions'].append({
                    'action': f'调整默认杠杆到{best_leverage}x',
                    'reason': f'杠杆{best_leverage}x胜率最高',
                    'implementation': 'config/trading_config.py中的默认杠杆设置',
                    'priority': 'medium',
                    'effort': 'low'
                })
            
            # 4. 长期策略
            optimization_plan['long_term_strategy'].extend([
                {
                    'strategy': '建立AI模型A/B测试框架',
                    'description': '同时运行多个模型并对比表现',
                    'benefits': '持续优化模型选择',
                    'timeline': '1个月'
                },
                {
                    'strategy': '实现动态参数调整',
                    'description': '根据市场条件自动调整风险参数',
                    'benefits': '提高适应性和稳定性',
                    'timeline': '2个月'
                }
            ])
            
            # 计算优先级评分
            total_improvements = (len(optimization_plan['immediate_actions']) + 
                                len(optimization_plan['short_term_goals']) + 
                                len(optimization_plan['long_term_strategy']))
            
            optimization_plan['priority_score'] = {
                'total_improvements': total_improvements,
                'high_priority': len([a for a in optimization_plan['immediate_actions'] if a.get('priority') == 'high']),
                'quick_wins': len([a for a in optimization_plan['immediate_actions'] if a.get('effort') == 'low']),
                'optimization_potential': 'high' if total_improvements > 5 else 'medium' if total_improvements > 2 else 'low'
            }
            
            return optimization_plan
            
        except Exception as e:
            logger.error(f"优化计划生成失败: {e}")
            return {'error': str(e)}

def main():
    """演示策略优化功能"""
    try:
        optimizer = StrategyOptimizer()
        
        print("🎯 开始策略优化分析...")
        
        print("\n📝 分析提示词效果...")
        prompt_results = optimizer.analyze_prompt_effectiveness()
        if 'vpa_usage_by_model' in prompt_results:
            print("VPA术语使用率:")
            for model, data in prompt_results['vpa_usage_by_model'].items():
                print(f"  {model}: {data['vpa_usage_rate']:.1%}")
        
        print("\n🔍 分析信号提取规则...")
        signal_results = optimizer.optimize_signal_extraction_rules()
        if 'extraction_analysis' in signal_results:
            missed = len(signal_results['extraction_analysis'].get('missed_signals', []))
            print(f"发现 {missed} 个漏提取的信号")
        
        print("\n⚙️ 分析最优参数...")
        param_results = optimizer.analyze_optimal_parameters()
        
        print("\n📋 生成优化计划...")
        plan = optimizer.generate_optimization_plan()
        
        print(f"\n🏆 优化潜力: {plan['priority_score']['optimization_potential'].upper()}")
        print(f"总改进项: {plan['priority_score']['total_improvements']}")
        print(f"高优先级项: {plan['priority_score']['high_priority']}")
        print(f"快速实现项: {plan['priority_score']['quick_wins']}")
        
        print("\n💡 立即可执行的改进:")
        for action in plan['immediate_actions'][:3]:
            print(f"  • {action['action']}")
            print(f"    原因: {action['reason']}")
            print(f"    实施: {action['implementation']}")
        
    except Exception as e:
        print(f"❌ 策略优化分析失败: {e}")

if __name__ == "__main__":
    main()