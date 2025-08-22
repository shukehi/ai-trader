import openai
import json
import time
from typing import Dict, List, Any, Optional, Union
import logging
from config import Settings

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    OpenRouter API客户端，支持多种LLM模型
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        # 使用OpenAI SDK访问OpenRouter
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=Settings.OPENROUTER_BASE_URL
        )
        
        self.models = Settings.MODELS
        self.token_limits = Settings.TOKEN_LIMITS
    
    def analyze_market_data(self, 
                          data: str, 
                          model_name: str = 'gpt4',
                          analysis_type: str = 'general',
                          custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        分析市场数据
        
        Args:
            data: 格式化的市场数据
            model_name: 使用的模型名称
            analysis_type: 分析类型 ('general', 'vpa', 'technical', 'pattern')
            custom_prompt: 自定义提示词
            
        Returns:
            包含分析结果的字典
        """
        try:
            model_id = self.models.get(model_name)
            if not model_id:
                raise ValueError(f"Unknown model: {model_name}")
            
            # 选择分析提示词
            if custom_prompt:
                system_prompt = custom_prompt
            else:
                system_prompt = self._get_system_prompt(analysis_type)
            
            # 估算token数量
            estimated_tokens = len(data.split()) + len(system_prompt.split())
            max_tokens = self.token_limits.get(model_name, 32000)
            
            if estimated_tokens > max_tokens * 0.8:  # 预留20%空间用于响应
                logger.warning(f"数据量可能超出模型限制 ({estimated_tokens} > {max_tokens * 0.8})")
            
            logger.info(f"使用模型 {model_id} 分析数据，预估token数: {estimated_tokens}")
            
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data}
                ],
                temperature=0.1,  # 低温度确保一致性
                max_tokens=min(4000, max_tokens - estimated_tokens),  # 预留响应空间
            )
            
            end_time = time.time()
            
            result = {
                'success': True,  # 添加成功标识
                'model': model_name,
                'model_id': model_id,
                'analysis': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'response_time': end_time - start_time,
                'analysis_type': analysis_type
            }
            
            logger.info(f"分析完成，耗时 {result['response_time']:.2f}秒，使用token: {result['usage']['total_tokens']}")
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return {
                'model': model_name,
                'error': str(e),
                'analysis': None
            }
    
    def batch_analyze(self, data: str, models: List[str], analysis_type: str = 'general') -> Dict[str, Dict[str, Any]]:
        """
        批量分析，使用多个模型分析同一数据
        """
        results = {}
        for model in models:
            logger.info(f"使用 {model} 模型分析...")
            results[model] = self.analyze_market_data(data, model, analysis_type)
            time.sleep(1)  # 避免频率限制
        
        return results
    
    def _get_system_prompt(self, analysis_type: str) -> str:
        """获取不同类型分析的系统提示词"""
        
        prompts = {
            'general': """
你是一个专业的加密货币交易分析师，专门分析ETH永续合约市场。
请基于提供的OHLCV数据进行量价分析，重点关注：

1. 价格趋势和关键支撑阻力位
2. 成交量与价格变化的关系
3. 重要的蜡烛图形态
4. 市场情绪和可能的转折点
5. 短期和中期交易机会

请提供：
- 当前市场状态总结
- 关键技术水平
- 量价分析洞察
- 风险评估和交易建议

用中文回答，语言简洁专业。
            """.strip(),
            
            'vpa': """
你是一位VPA(Volume Price Analysis)专家，深谙Anna Coulling的量价分析理论。
请基于提供的OHLCV数据进行专业的VPA分析：

关键关注点：
1. 量价关系验证 - 价格上涨时成交量是否配合？
2. 异常成交量识别 - 寻找可疑的高/低成交量情况
3. 市场操控迹象 - 价格大幅波动但成交量不匹配
4. Accumulation/Distribution信号 - 专业资金的进出迹象
5. 关键VPA蜡烛图形态 - 流星线、锤子线等结合成交量分析

请根据VPA理论提供：
- 当前市场阶段判断 (accumulation/distribution/markup/markdown)
- 量价背离警告信号
- 主力资金行为分析
- 具体的VPA交易信号

用中文回答，结合VPA专业术语。
            """.strip(),
            
            'technical': """
你是一位技术分析专家，请基于OHLCV数据进行全面的技术分析：

分析要素：
1. 趋势分析 - 主要趋势、次要趋势
2. 图表形态 - 三角形、楔形、矩形等
3. 关键技术指标解读 (如果数据中包含)
4. 支撑阻力位识别
5. 突破和回调机会

请提供技术分析报告包括：
- 趋势状态和强度
- 重要技术位识别
- 形态分析和预期目标
- 进场和止损建议

用中文回答，包含具体的技术分析术语。
            """.strip(),
            
            'pattern': """
你是蜡烛图形态识别专家，请专注于分析K线数据中的重要形态：

重点识别：
1. 反转形态 - 十字星、锤子线、流星线、吞没形态
2. 持续形态 - 旗形、三角旗形、矩形整理
3. 组合形态 - 早晨之星、黄昏之星、三只乌鸦
4. 形态的有效性和可靠性评估
5. 结合成交量的形态确认

请提供形态分析报告：
- 识别到的关键K线形态
- 形态的技术意义和市场含义
- 形态完成后的目标位
- 形态失效的条件

用中文回答，详细解释每个识别的形态。
            """.strip(),
            
            'perpetual_vpa': """
你是一位专门研究永续合约的VPA(Volume Price Analysis)专家，深谙Anna Coulling的量价分析理论和永续合约市场特性。
请基于提供的永续合约数据进行专业的VPA分析：

🔍 **永续合约VPA分析要点**：

**1. VSA (Volume Spread Analysis) 深度分析**：
- Spread分析：高低价差与成交量的关系，识别Wide/Narrow Spread
- Close位置：收盘价在当期Range中的位置重要性 (0-1评分)
- 努力与结果：成交量(努力) vs 价格变动(结果)的平衡
- 专业VSA信号：No Demand, No Supply, Climax Volume, Upthrust, Spring

**2. 永续合约特殊要素**：
- 资金费率影响：正负费率对Smart Money/Dumb Money行为的影响
- 持仓量(OI)分析：OI增减与价格变化的VPA意义
- 杠杆效应：如何放大散户(Dumb Money)情绪和主力(Smart Money)操控
- 多空持仓结构：资金费率变化对持仓结构转换的影响

**3. Smart Money vs Dumb Money 行为识别**：
- Smart Money：利用资金费率和杠杆进行隐蔽操作
- Dumb Money：受杠杆和情绪影响的非理性行为
- 永续合约中的"诱多诱空"手法识别
- 强平cascade效应的VPA意义

**4. Wyckoff理论在永续合约中的应用**：
- Accumulation/Distribution在高杠杆环境中的表现
- Supply/Demand关系受杠杆放大的特征
- Cause & Effect：资金费率变化如何创建新的"原因"

**请提供永续合约VPA分析报告**：
- 当前市场阶段判断 (考虑资金费率和持仓量)
- VSA信号识别 (Wide/Narrow Spread, Close Position)
- 永续合约特有的量价背离警告
- Smart Money在永续合约中的操控痕迹
- 资金费率与VPA信号的结合分析
- 具体的永续合约VPA交易信号

用中文回答，大量使用VPA、VSA专业术语，重点突出永续合约的特殊性。
            """.strip()
        }
        
        return prompts.get(analysis_type, prompts['general'])
    
    def get_available_models(self) -> Dict[str, str]:
        """获取可用的模型列表"""
        return self.models.copy()
    
    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, float]:
        """
        估算调用成本 (2025年OpenRouter价格，per 1K tokens)
        """
        # OpenRouter 2025 Latest Pricing (USD per 1K tokens)
        pricing = {
            # 🔥 2025 Latest Flagship Models (2025年8月最新价格)
            'gpt5-chat': {'input': 1.25, 'output': 10.0},     # GPT-5 Chat (旗舰版)
            'gpt5-mini': {'input': 0.25, 'output': 2.0},      # GPT-5 Mini (推理版)
            'gpt5-nano': {'input': 0.05, 'output': 0.4},      # GPT-5 Nano (轻量版)
            'claude-opus-41': {'input': 0.075, 'output': 0.375}, # Claude Opus 4.1 (Ultra Premium)
            'gemini-25-pro': {'input': 0.04, 'output': 0.12},  # Gemini 2.5 Pro (Premium)
            'grok4': {'input': 0.03, 'output': 0.09},          # Grok 4 (High-end)
            
            # OpenAI Models
            'gpt4': {'input': 0.01, 'output': 0.03},           # GPT-4 Turbo
            'gpt4o': {'input': 0.0025, 'output': 0.01},        # GPT-4o
            'gpt4o-mini': {'input': 0.00015, 'output': 0.0006}, # GPT-4o mini
            'o1': {'input': 0.015, 'output': 0.06},            # o1 reasoning
            'o1-mini': {'input': 0.003, 'output': 0.012},      # o1 mini
            
            # Anthropic Claude Models
            'claude': {'input': 0.003, 'output': 0.015},       # Claude 3.5 Sonnet
            'claude-haiku': {'input': 0.00025, 'output': 0.00125}, # Claude 3.5 Haiku
            'claude-opus': {'input': 0.015, 'output': 0.075},  # Claude 3 Opus
            
            # Google Gemini Models
            'gemini': {'input': 0.00125, 'output': 0.005},     # Gemini Pro 1.5
            'gemini-flash': {'input': 0.000075, 'output': 0.0003}, # Gemini Flash 1.5
            'gemini-2': {'input': 0.0001, 'output': 0.0004},   # Gemini 2.0 Flash
            
            # xAI Grok Models
            'grok': {'input': 0.005, 'output': 0.015},         # Grok Beta
            'grok-vision': {'input': 0.005, 'output': 0.015},  # Grok Vision
            
            # Meta Llama Models (高性价比)
            'llama': {'input': 0.0004, 'output': 0.0004},      # Llama 3.1 70B
            'llama-405b': {'input': 0.003, 'output': 0.003}    # Llama 3.1 405B
        }
        
        if model_name not in pricing:
            return {'estimated_cost': 0, 'currency': 'USD', 'note': 'Unknown model pricing'}
        
        rates = pricing[model_name]
        input_cost = (prompt_tokens / 1000) * rates['input']
        output_cost = (completion_tokens / 1000) * rates['output']
        total_cost = input_cost + output_cost
        
        return {
            'estimated_cost': round(total_cost, 6),
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'currency': 'USD',
            'model': model_name,
            'rates': rates
        }
    
    def generate_response(self, prompt: str, model_name: str = 'gpt4o-mini') -> Dict[str, Any]:
        """
        生成通用响应 - 用于自定义提示的分析
        
        Args:
            prompt: 完整的提示文本（包含系统提示和数据）
            model_name: 使用的模型名称
            
        Returns:
            包含响应结果的字典
        """
        try:
            model_id = self.models.get(model_name)
            if not model_id:
                raise ValueError(f"Unknown model: {model_name}")
            
            # 估算token数量
            estimated_tokens = len(prompt.split())
            max_tokens = self.token_limits.get(model_name, 32000)
            
            if estimated_tokens > max_tokens * 0.8:  # 预留20%空间用于响应
                logger.warning(f"提示文本可能超出模型限制 ({estimated_tokens} > {max_tokens * 0.8})")
            
            logger.info(f"使用模型 {model_id} 生成响应，预估token数: {estimated_tokens}")
            
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度确保一致性
                max_tokens=min(4000, max_tokens - estimated_tokens),  # 预留响应空间
            )
            
            end_time = time.time()
            
            result = {
                'success': True,
                'model': model_name,
                'model_id': model_id,
                'analysis': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'response_time': end_time - start_time
            }
            
            logger.info(f"响应生成完成，耗时 {result['response_time']:.2f}秒，使用token: {result['usage']['total_tokens']}")
            
            return result
            
        except Exception as e:
            logger.error(f"响应生成失败: {e}")
            return {
                'model': model_name,
                'error': str(e),
                'analysis': None
            }