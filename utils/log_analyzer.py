#!/usr/bin/env python3
"""
交易日志分析器 - 基于历史数据的AI模型和策略优化
从交易日志和AI分析日志中提取有价值的改进建议
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class TradingLogAnalyzer:
    """
    交易日志分析器
    
    功能特性:
    - AI模型性能评估和对比
    - 交易策略效果统计
    - 信号质量分析和优化建议
    - 市场条件与AI表现的关联分析
    """
    
    def __init__(self, db_path: str = "logs/trading_database.db"):
        """
        初始化日志分析器
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
            
        logger.info(f"交易日志分析器初始化完成 - 数据库: {db_path}")
    
    def get_model_performance_comparison(self) -> Dict[str, Any]:
        """
        获取不同AI模型的性能对比
        
        Returns:
            模型性能对比结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取每个模型的决策和相关交易统计
                query = """
                SELECT 
                    a.model_used,
                    COUNT(DISTINCT a.decision_id) as total_decisions,
                    COUNT(DISTINCT t.trade_id) as executed_trades,
                    AVG(a.confidence_score) as avg_confidence,
                    AVG(CASE WHEN t.realized_pnl > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
                    AVG(t.realized_pnl) as avg_pnl,
                    SUM(t.realized_pnl) as total_pnl,
                    COUNT(CASE WHEN t.side = 'long' THEN 1 END) as long_trades,
                    COUNT(CASE WHEN t.side = 'short' THEN 1 END) as short_trades
                FROM ai_decisions a
                LEFT JOIN trades t ON a.decision_id = t.ai_decision_id
                GROUP BY a.model_used
                ORDER BY total_decisions DESC
                """
                
                df = pd.read_sql_query(query, conn)
                
                # 计算额外的性能指标
                results = {}
                for _, row in df.iterrows():
                    model = row['model_used']
                    results[model] = {
                        'total_decisions': int(row['total_decisions']),
                        'executed_trades': int(row['executed_trades']) if row['executed_trades'] else 0,
                        'execution_rate': (row['executed_trades'] / row['total_decisions']) if row['total_decisions'] > 0 else 0,
                        'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0,
                        'win_rate': float(row['win_rate']) if row['win_rate'] else 0,
                        'avg_pnl': float(row['avg_pnl']) if row['avg_pnl'] else 0,
                        'total_pnl': float(row['total_pnl']) if row['total_pnl'] else 0,
                        'long_trades': int(row['long_trades']) if row['long_trades'] else 0,
                        'short_trades': int(row['short_trades']) if row['short_trades'] else 0,
                        'direction_bias': 'long' if (row['long_trades'] or 0) > (row['short_trades'] or 0) else 'short' if (row['short_trades'] or 0) > 0 else 'neutral'
                    }
                
                return {
                    'models': results,
                    'summary': {
                        'total_models_analyzed': len(results),
                        'best_execution_rate': max([m['execution_rate'] for m in results.values()]) if results else 0,
                        'best_win_rate': max([m['win_rate'] for m in results.values()]) if results else 0,
                        'most_profitable': max(results.keys(), key=lambda k: results[k]['total_pnl']) if results else None
                    }
                }
                
        except Exception as e:
            logger.error(f"模型性能对比分析失败: {e}")
            return {'error': str(e)}
    
    def analyze_signal_quality(self) -> Dict[str, Any]:
        """
        分析AI信号的质量和准确性
        
        Returns:
            信号质量分析结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取信号数据
                query = """
                SELECT 
                    a.decision_id,
                    a.model_used,
                    a.raw_analysis,
                    a.extracted_signals,
                    a.confidence_score,
                    t.side,
                    t.realized_pnl,
                    t.entry_price,
                    t.exit_price,
                    t.holding_duration
                FROM ai_decisions a
                LEFT JOIN trades t ON a.decision_id = t.ai_decision_id
                WHERE a.extracted_signals IS NOT NULL AND a.extracted_signals != '{}'
                """
                
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # 解析信号数据
                signal_analysis = {
                    'total_signals': 0,
                    'by_strength': defaultdict(list),
                    'by_direction': defaultdict(list),
                    'by_confidence': defaultdict(list),
                    'success_patterns': [],
                    'failure_patterns': []
                }
                
                for row in rows:
                    try:
                        signals = json.loads(row[3]) if row[3] else {}
                        if not signals:
                            continue
                            
                        signal_analysis['total_signals'] += 1
                        
                        # 按信号强度分组
                        strength = signals.get('strength', 0)
                        direction = signals.get('direction', 'unknown')
                        entry_price = signals.get('entry_price', 0)
                        confidence = row[4] if row[4] else 0
                        
                        realized_pnl = row[6] if row[6] else 0
                        is_successful = realized_pnl > 0
                        
                        signal_data = {
                            'model': row[1],
                            'strength': strength,
                            'direction': direction,
                            'confidence': confidence,
                            'entry_price': entry_price,
                            'realized_pnl': realized_pnl,
                            'successful': is_successful
                        }
                        
                        signal_analysis['by_strength'][strength].append(signal_data)
                        signal_analysis['by_direction'][direction].append(signal_data)
                        
                        # 分析成功和失败模式
                        if is_successful:
                            signal_analysis['success_patterns'].append(signal_data)
                        else:
                            signal_analysis['failure_patterns'].append(signal_data)
                            
                    except json.JSONDecodeError:
                        continue
                
                # 计算统计数据
                summary = {}
                for strength, signals in signal_analysis['by_strength'].items():
                    if signals:
                        successful = [s for s in signals if s['successful']]
                        summary[f'strength_{strength}'] = {
                            'count': len(signals),
                            'win_rate': len(successful) / len(signals),
                            'avg_pnl': np.mean([s['realized_pnl'] for s in signals if s['realized_pnl']])
                        }
                
                signal_analysis['strength_summary'] = summary
                
                return signal_analysis
                
        except Exception as e:
            logger.error(f"信号质量分析失败: {e}")
            return {'error': str(e)}
    
    def analyze_market_timing(self) -> Dict[str, Any]:
        """
        分析AI在不同市场条件下的表现
        
        Returns:
            市场时机分析结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取带时间的交易数据
                query = """
                SELECT 
                    t.entry_time,
                    t.exit_time,
                    t.side,
                    t.entry_price,
                    t.exit_price,
                    t.realized_pnl,
                    a.model_used,
                    a.raw_analysis
                FROM trades t
                JOIN ai_decisions a ON t.ai_decision_id = a.decision_id
                ORDER BY t.entry_time
                """
                
                df = pd.read_sql_query(query, conn)
                
                if df.empty:
                    return {'message': '暂无交易数据进行市场时机分析'}
                
                # 转换时间戳
                df['entry_datetime'] = pd.to_datetime(df['entry_time'], unit='s', utc=True)
                df['hour'] = df['entry_datetime'].dt.hour
                df['weekday'] = df['entry_datetime'].dt.weekday
                
                # 按时间段分析
                timing_analysis = {
                    'by_hour': {},
                    'by_weekday': {},
                    'by_model_timing': {}
                }
                
                # 按小时分析
                for hour in range(24):
                    hour_trades = df[df['hour'] == hour]
                    if not hour_trades.empty:
                        timing_analysis['by_hour'][hour] = {
                            'trade_count': len(hour_trades),
                            'win_rate': (hour_trades['realized_pnl'] > 0).mean(),
                            'avg_pnl': hour_trades['realized_pnl'].mean()
                        }
                
                # 按星期分析
                weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                for day_idx in range(7):
                    day_trades = df[df['weekday'] == day_idx]
                    if not day_trades.empty:
                        timing_analysis['by_weekday'][weekdays[day_idx]] = {
                            'trade_count': len(day_trades),
                            'win_rate': (day_trades['realized_pnl'] > 0).mean(),
                            'avg_pnl': day_trades['realized_pnl'].mean()
                        }
                
                return timing_analysis
                
        except Exception as e:
            logger.error(f"市场时机分析失败: {e}")
            return {'error': str(e)}
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """
        基于历史数据生成优化建议
        
        Returns:
            优化建议
        """
        try:
            # 获取各项分析结果
            model_performance = self.get_model_performance_comparison()
            signal_quality = self.analyze_signal_quality()
            market_timing = self.analyze_market_timing()
            
            recommendations = {
                'model_recommendations': [],
                'signal_optimization': [],
                'timing_suggestions': [],
                'risk_management': [],
                'overall_score': 0
            }
            
            # 模型建议
            if 'models' in model_performance:
                models = model_performance['models']
                if models:
                    best_model = max(models.keys(), key=lambda k: models[k]['execution_rate'] * models[k]['win_rate'])
                    recommendations['model_recommendations'].append({
                        'priority': 'high',
                        'suggestion': f'优先使用 {best_model} 模型',
                        'reason': f'执行率: {models[best_model]["execution_rate"]:.1%}, 胜率: {models[best_model]["win_rate"]:.1%}',
                        'implementation': f'在main.py中设置 --model {best_model} 作为默认'
                    })
                    
                    # 检查方向性偏差
                    for model, data in models.items():
                        if data['direction_bias'] != 'neutral':
                            recommendations['model_recommendations'].append({
                                'priority': 'medium',
                                'suggestion': f'{model} 模型存在{data["direction_bias"]}方向偏差',
                                'reason': f'Long交易: {data["long_trades"]}, Short交易: {data["short_trades"]}',
                                'implementation': '考虑在prompt中增加平衡性指导或使用多模型验证'
                            })
            
            # 信号优化建议
            if 'strength_summary' in signal_quality:
                strength_data = signal_quality['strength_summary']
                if strength_data:
                    best_strength = max(strength_data.keys(), 
                                      key=lambda k: strength_data[k]['win_rate'] if strength_data[k]['count'] > 0 else 0)
                    recommendations['signal_optimization'].append({
                        'priority': 'high',
                        'suggestion': f'提高信号强度阈值，重点关注{best_strength}级别信号',
                        'reason': f'{best_strength}信号胜率: {strength_data[best_strength]["win_rate"]:.1%}',
                        'implementation': '在signal_executor.py中调整min_signal_strength参数'
                    })
            
            # 计算总体评分
            total_trades = sum([model_performance.get('models', {}).get(m, {}).get('executed_trades', 0) 
                              for m in model_performance.get('models', {})])
            if total_trades > 10:
                recommendations['overall_score'] = 85  # 数据充足
            elif total_trades > 5:
                recommendations['overall_score'] = 70  # 数据适中
            else:
                recommendations['overall_score'] = 50  # 数据不足
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return {'error': str(e)}
    
    def generate_performance_report(self) -> str:
        """
        生成完整的性能分析报告
        
        Returns:
            格式化的报告文本
        """
        try:
            model_perf = self.get_model_performance_comparison()
            signal_qual = self.analyze_signal_quality()
            market_time = self.analyze_market_timing()
            recommendations = self.get_optimization_recommendations()
            
            report = []
            report.append("🎯 ETH永续合约AI交易系统 - 性能分析报告")
            report.append("=" * 60)
            report.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 模型性能部分
            if 'models' in model_perf:
                report.append("📊 AI模型性能对比:")
                report.append("-" * 30)
                for model, data in model_perf['models'].items():
                    report.append(f"🤖 {model}:")
                    report.append(f"  总决策数: {data['total_decisions']}")
                    report.append(f"  执行交易: {data['executed_trades']} (执行率: {data['execution_rate']:.1%})")
                    report.append(f"  平均置信度: {data['avg_confidence']:.1%}")
                    report.append(f"  胜率: {data['win_rate']:.1%}")
                    report.append(f"  方向偏好: {data['direction_bias']}")
                    report.append(f"  总盈亏: ${data['total_pnl']:+.2f}")
                    report.append("")
            
            # 信号质量部分
            if 'total_signals' in signal_qual:
                report.append("📈 信号质量分析:")
                report.append("-" * 30)
                report.append(f"总信号数量: {signal_qual['total_signals']}")
                report.append(f"成功信号: {len(signal_qual.get('success_patterns', []))}")
                report.append(f"失败信号: {len(signal_qual.get('failure_patterns', []))}")
                
                if 'strength_summary' in signal_qual:
                    report.append("按强度统计:")
                    for strength, data in signal_qual['strength_summary'].items():
                        report.append(f"  {strength}: {data['count']}次, 胜率: {data['win_rate']:.1%}")
                report.append("")
            
            # 优化建议部分
            if 'model_recommendations' in recommendations:
                report.append("💡 优化建议:")
                report.append("-" * 30)
                for i, rec in enumerate(recommendations['model_recommendations'][:5], 1):
                    report.append(f"{i}. [{rec['priority'].upper()}] {rec['suggestion']}")
                    report.append(f"   原因: {rec['reason']}")
                    report.append(f"   实施: {rec['implementation']}")
                    report.append("")
            
            # 总体评分
            overall_score = recommendations.get('overall_score', 0)
            report.append(f"🏆 系统优化潜力评分: {overall_score}/100")
            if overall_score >= 80:
                report.append("✅ 系统表现优秀，具有很高的优化价值")
            elif overall_score >= 60:
                report.append("⚡ 系统表现良好，有明确的优化方向")
            else:
                report.append("📊 需要更多数据来进行深度优化分析")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
            return f"报告生成失败: {e}"

def main():
    """演示日志分析功能"""
    try:
        analyzer = TradingLogAnalyzer()
        
        print("🔍 开始分析交易日志...")
        report = analyzer.generate_performance_report()
        print(report)
        
        # 保存报告
        report_path = Path("logs") / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 报告已保存到: {report_path}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    main()