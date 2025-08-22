#!/usr/bin/env python3
"""
ETH永续合约AI分析助手 - 成本控制系统
功能：
1. 实时成本追踪
2. 预算限制
3. 智能降级
4. 成本优化建议
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class CostController:
    """成本控制器"""
    
    def __init__(self, config_file='config/cost_limits.json'):
        self.config_file = config_file
        self.load_config()
        self.setup_logging()
        self.usage_log = Path('logs/cost_usage.jsonl')
        
        # 模型成本表 (基于2025年价格)
        self.model_costs = {
            # GPT-5系列
            'gpt5-chat': {'input': 1.25, 'output': 10.0},
            'gpt5-mini': {'input': 0.25, 'output': 2.0},
            'gpt5-nano': {'input': 0.05, 'output': 0.4},
            
            # Claude系列
            'claude-opus-41': {'input': 0.3, 'output': 0.6},
            'claude': {'input': 0.15, 'output': 0.75},
            'claude-haiku': {'input': 0.0025, 'output': 0.0125},
            
            # Gemini系列
            'gemini-25-pro': {'input': 0.002, 'output': 0.008},
            'gemini-flash': {'input': 0.0001, 'output': 0.0004},
            'gemini': {'input': 0.001, 'output': 0.005},
            
            # GPT-4系列
            'gpt4o': {'input': 0.005, 'output': 0.015},
            'gpt4o-mini': {'input': 0.00015, 'output': 0.0006},
            
            # 其他模型
            'grok4': {'input': 0.01, 'output': 0.02},
            'llama': {'input': 0.001, 'output': 0.001}
        }
    
    def load_config(self):
        """加载成本配置"""
        default_config = {
            'daily_budget': 50.0,
            'hourly_budget': 5.0,
            'single_request_limit': 2.0,
            'warning_threshold': 0.8,  # 80%预算时警告
            'auto_downgrade': True,
            'emergency_stop_threshold': 0.95,  # 95%预算时紧急停止
            'model_tiers': {
                'premium': ['gpt5-chat', 'claude-opus-41'],
                'standard': ['gpt5-mini', 'gpt4o', 'claude'],
                'economy': ['gpt4o-mini', 'claude-haiku', 'gemini-flash'],
                'ultra_economy': ['gpt5-nano']
            }
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.config = {**default_config, **config}
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"成本配置加载失败，使用默认配置: {e}")
            self.config = default_config
    
    def save_config(self):
        """保存配置"""
        try:
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"成本配置保存失败: {e}")
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> Dict:
        """估算成本"""
        if model not in self.model_costs:
            self.logger.warning(f"未知模型: {model}, 使用默认成本")
            cost_data = {'input': 0.001, 'output': 0.001}
        else:
            cost_data = self.model_costs[model]
        
        # 成本计算 (美元/1K tokens)
        input_cost = (input_tokens / 1000) * cost_data['input']
        output_cost = (output_tokens / 1000) * cost_data['output']
        total_cost = input_cost + output_cost
        
        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'estimated': output_tokens == 0  # 如果没有实际输出token，这是估算
        }
    
    def get_usage_stats(self, period: str = 'day') -> Dict:
        """获取使用统计"""
        if not self.usage_log.exists():
            return {'total_cost': 0.0, 'request_count': 0, 'period': period}
        
        now = datetime.now()
        if period == 'day':
            cutoff = now - timedelta(days=1)
        elif period == 'hour':
            cutoff = now - timedelta(hours=1)
        else:
            cutoff = now - timedelta(days=30)  # 默认一个月
        
        total_cost = 0.0
        request_count = 0
        
        try:
            with open(self.usage_log, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        record_time = datetime.fromisoformat(record['timestamp'])
                        
                        if record_time >= cutoff:
                            total_cost += record.get('total_cost', 0.0)
                            request_count += 1
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"读取使用日志失败: {e}")
        
        return {
            'total_cost': round(total_cost, 4),
            'request_count': request_count,
            'period': period,
            'cutoff_time': cutoff.isoformat()
        }
    
    def log_usage(self, cost_info: Dict):
        """记录使用"""
        usage_record = {
            'timestamp': datetime.now().isoformat(),
            **cost_info
        }
        
        try:
            self.usage_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.usage_log, 'a') as f:
                f.write(json.dumps(usage_record, ensure_ascii=False) + '\\n')
        except Exception as e:
            self.logger.error(f"使用记录写入失败: {e}")
    
    def check_budget_limits(self, estimated_cost: float) -> Dict:
        """检查预算限制"""
        daily_usage = self.get_usage_stats('day')
        hourly_usage = self.get_usage_stats('hour')
        
        daily_after_request = daily_usage['total_cost'] + estimated_cost
        hourly_after_request = hourly_usage['total_cost'] + estimated_cost
        
        # 检查各种限制
        violations = []
        
        # 单次请求限制
        if estimated_cost > self.config['single_request_limit']:
            violations.append(f"单次请求成本超限: ${estimated_cost:.4f} > ${self.config['single_request_limit']:.4f}")
        
        # 小时预算
        if hourly_after_request > self.config['hourly_budget']:
            violations.append(f"小时预算超限: ${hourly_after_request:.4f} > ${self.config['hourly_budget']:.4f}")
        
        # 日预算
        if daily_after_request > self.config['daily_budget']:
            violations.append(f"日预算超限: ${daily_after_request:.4f} > ${self.config['daily_budget']:.4f}")
        
        # 预算使用率
        daily_usage_rate = daily_after_request / self.config['daily_budget']
        hourly_usage_rate = hourly_after_request / self.config['hourly_budget']
        
        # 警告阈值
        warning = False
        if daily_usage_rate > self.config['warning_threshold']:
            warning = True
        
        # 紧急停止
        emergency_stop = (daily_usage_rate > self.config['emergency_stop_threshold'] or
                         hourly_usage_rate > self.config['emergency_stop_threshold'])
        
        return {
            'allowed': len(violations) == 0 and not emergency_stop,
            'violations': violations,
            'warning': warning,
            'emergency_stop': emergency_stop,
            'usage_rates': {
                'daily': round(daily_usage_rate, 3),
                'hourly': round(hourly_usage_rate, 3)
            },
            'current_usage': {
                'daily': daily_usage,
                'hourly': hourly_usage
            }
        }
    
    def suggest_model_downgrade(self, current_model: str, target_cost_reduction: float = 0.5) -> Optional[str]:
        """建议模型降级"""
        if current_model not in self.model_costs:
            return None
        
        current_cost = self.model_costs[current_model]
        current_avg_cost = (current_cost['input'] + current_cost['output']) / 2
        target_cost = current_avg_cost * target_cost_reduction
        
        # 寻找成本更低的模型
        cheaper_models = []
        for model, cost_data in self.model_costs.items():
            avg_cost = (cost_data['input'] + cost_data['output']) / 2
            if avg_cost < target_cost:
                cheaper_models.append((model, avg_cost))
        
        # 按成本排序，选择最接近目标的模型
        if cheaper_models:
            cheaper_models.sort(key=lambda x: x[1], reverse=True)
            return cheaper_models[0][0]
        
        return None
    
    def get_cost_optimization_advice(self) -> List[str]:
        """获取成本优化建议"""
        daily_usage = self.get_usage_stats('day')
        advice = []
        
        if daily_usage['total_cost'] > self.config['daily_budget'] * 0.8:
            advice.append("🔴 日预算使用率过高，建议:")
            advice.append("   - 使用经济型模型 (gemini-flash, gpt5-nano)")
            advice.append("   - 启用快速验证模式 (--fast-validation)")
            advice.append("   - 减少数据量 (--limit 30)")
        
        if daily_usage['request_count'] > 50:
            advice.append("🟡 请求频率较高，建议:")
            advice.append("   - 批量处理多个分析")
            advice.append("   - 使用缓存避免重复分析")
        
        # 推荐经济型配置
        advice.append("💰 经济型配置推荐:")
        advice.append("   主分析: python main.py --model gemini-flash")
        advice.append("   验证模式: python main.py --model gpt5-nano --fast-validation")
        advice.append("   批量分析: python main.py --model claude-haiku --limit 100")
        
        return advice
    
    def pre_request_check(self, model: str, estimated_tokens: int) -> Dict:
        """请求前检查"""
        # 估算成本
        cost_estimate = self.estimate_cost(model, estimated_tokens)
        
        # 检查预算
        budget_check = self.check_budget_limits(cost_estimate['total_cost'])
        
        # 生成建议
        suggestions = []
        if not budget_check['allowed']:
            if budget_check['emergency_stop']:
                suggestions.append("🛑 紧急停止: 预算即将用尽")
            
            # 建议降级模型
            downgrade_model = self.suggest_model_downgrade(model)
            if downgrade_model:
                downgrade_cost = self.estimate_cost(downgrade_model, estimated_tokens)
                suggestions.append(f"💡 建议降级到: {downgrade_model} (节省 ${cost_estimate['total_cost'] - downgrade_cost['total_cost']:.4f})")
        
        elif budget_check['warning']:
            suggestions.append("⚠️ 预算警告: 接近每日限额")
            suggestions.extend(self.get_cost_optimization_advice()[:2])
        
        return {
            'cost_estimate': cost_estimate,
            'budget_check': budget_check,
            'suggestions': suggestions,
            'recommended_action': 'proceed' if budget_check['allowed'] else 'block'
        }
    
    def post_request_log(self, model: str, actual_input_tokens: int, actual_output_tokens: int):
        """请求后记录"""
        actual_cost = self.estimate_cost(model, actual_input_tokens, actual_output_tokens)
        self.log_usage(actual_cost)
        
        # 检查是否需要发出警告
        daily_usage = self.get_usage_stats('day')
        usage_rate = daily_usage['total_cost'] / self.config['daily_budget']
        
        if usage_rate > self.config['warning_threshold']:
            self.logger.warning(f"预算警告: 已使用 {usage_rate:.1%} 的日预算")
        
        return actual_cost

def main():
    """测试成本控制器"""
    print("💰 ETH永续合约AI分析助手 - 成本控制器测试")
    print("=" * 50)
    
    controller = CostController()
    
    # 测试成本估算
    print("🧮 测试成本估算:")
    test_cases = [
        ('gpt5-mini', 100, 50),
        ('gemini-flash', 200, 100),
        ('claude-haiku', 150, 75)
    ]
    
    for model, input_tokens, output_tokens in test_cases:
        cost = controller.estimate_cost(model, input_tokens, output_tokens)
        print(f"   {model}: ${cost['total_cost']:.4f} ({input_tokens}→{output_tokens} tokens)")
    
    # 测试预算检查
    print("\\n📊 测试预算检查:")
    check_result = controller.pre_request_check('gpt5-mini', 100)
    print(f"   成本估算: ${check_result['cost_estimate']['total_cost']:.4f}")
    print(f"   预算状态: {'✅ 允许' if check_result['budget_check']['allowed'] else '❌ 阻止'}")
    
    if check_result['suggestions']:
        print("   建议:")
        for suggestion in check_result['suggestions']:
            print(f"     {suggestion}")
    
    # 获取使用统计
    print("\\n📈 当前使用统计:")
    daily_stats = controller.get_usage_stats('day')
    print(f"   今日使用: ${daily_stats['total_cost']:.4f} ({daily_stats['request_count']} 次请求)")
    
    # 成本优化建议
    print("\\n💡 成本优化建议:")
    advice = controller.get_cost_optimization_advice()
    for tip in advice[:3]:
        print(f"   {tip}")

if __name__ == '__main__':
    main()