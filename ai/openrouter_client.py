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
    
    def _estimate_tokens(self, text: str) -> int:
        """
        更精确的token估算方法
        使用启发式规则：平均1个token约等于0.75个单词或4个字符
        """
        if not text:
            return 0
        
        # 方法1：基于单词数的估算
        word_count = len(text.split())
        word_based_tokens = int(word_count / 0.75)
        
        # 方法2：基于字符数的估算  
        char_count = len(text)
        char_based_tokens = int(char_count / 4)
        
        # 取更大值作为保守估计
        estimated_tokens = max(word_based_tokens, char_based_tokens)
        
        # 添加10%的安全边距
        return int(estimated_tokens * 1.1)
    
    def _get_fallback_models(self, current_model: str) -> List[str]:
        """
        根据当前模型获取降级备选方案
        按token容量从大到小排序
        """
        model_capacities = [
            ('gemini-25-pro', 2097152),
            ('claude-opus-41', 200000), 
            ('grok4', 131072),
            ('gpt5-chat', 128000)
        ]
        
        # 找到当前模型的容量
        current_capacity = self.token_limits.get(current_model, 0)
        
        # 返回比当前模型容量更大的模型列表
        fallback_models = [
            model for model, capacity in model_capacities 
            if capacity > current_capacity and model in self.models
        ]
        
        return fallback_models
    
    def _try_fallback_model(self, data: str, original_model: str, analysis_type: str, 
                           system_prompt: str, original_error: Exception) -> Optional[Dict[str, Any]]:
        """
        当原模型token超限时，尝试使用更大容量的模型
        """
        fallback_models = self._get_fallback_models(original_model)
        
        if not fallback_models:
            logger.warning(f"没有可用的降级模型，原模型: {original_model}")
            return None
        
        logger.info(f"Token超限，尝试降级到更大容量模型: {fallback_models}")
        
        for fallback_model in fallback_models:
            try:
                logger.info(f"尝试使用降级模型: {fallback_model}")
                
                # 递归调用，但标记为降级尝试
                result = self.analyze_market_data(
                    data=data, 
                    model_name=fallback_model, 
                    analysis_type=analysis_type,
                    custom_prompt=system_prompt,
                    _is_fallback=True
                )
                
                if result.get('success', False):
                    result['fallback_from'] = original_model
                    result['fallback_reason'] = str(original_error)
                    logger.info(f"成功使用降级模型 {fallback_model} 完成分析")
                    return result
                
            except Exception as e:
                logger.warning(f"降级模型 {fallback_model} 也失败: {e}")
                continue
        
        logger.error("所有降级模型都失败")
        return None
    
    def analyze_market_data(self, 
                          data: str, 
                          model_name: str = 'gpt4',
                          analysis_type: str = 'general',
                          custom_prompt: Optional[str] = None,
                          _is_fallback: bool = False) -> Dict[str, Any]:
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
            
            # 改进的token估算 - 使用更精确的方法
            estimated_input_tokens = self._estimate_tokens(data) + self._estimate_tokens(system_prompt)
            max_model_tokens = self.token_limits.get(model_name, 32000)
            
            # 添加保守的安全边距 (20%)
            safe_model_limit = int(max_model_tokens * 0.8)
            
            # 检查输入是否超限
            if estimated_input_tokens > safe_model_limit:
                raise ValueError(f"输入token数量 ({estimated_input_tokens}) 超过模型安全限制 ({safe_model_limit})")
            
            # 根据分析类型动态分配响应空间比例，但更保守
            response_ratios = {
                'general': 0.25,
                'vpa': 0.35,
                'technical': 0.30,
                'pattern': 0.30,
                'perpetual_vpa': 0.40,  # VPA分析需要更多空间
                'raw_vpa': 0.35,
                'complete': 0.30  # 添加complete类型
            }
            response_ratio = response_ratios.get(analysis_type, 0.25)
            
            # 计算可用的响应token数，确保总和不超过安全限制
            available_response_tokens = safe_model_limit - estimated_input_tokens
            max_response_tokens = max(1000, min(
                int(available_response_tokens * response_ratio),
                available_response_tokens - 1000  # 额外安全边距
            ))
            
            total_tokens = estimated_input_tokens + max_response_tokens
            if total_tokens > safe_model_limit:
                logger.warning(f"预计总token ({total_tokens}) 接近限制 ({safe_model_limit})")
            
            logger.info(f"使用模型 {model_id} 分析数据，输入token: {estimated_input_tokens}, 最大响应token: {max_response_tokens}, 总计: {total_tokens}/{max_model_tokens}")
            
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data}
                ],
                temperature=0.1,  # 低温度确保一致性
                max_tokens=max_response_tokens,  # 动态分配响应空间
            )
            
            end_time = time.time()
            
            result = {
                'success': True,  # 添加成功标识
                'model': model_name,
                'model_id': model_id,
                'analysis': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                },
                'response_time': end_time - start_time,
                'analysis_type': analysis_type
            }
            
            logger.info(f"分析完成，耗时 {result['response_time']:.2f}秒，使用token: {result['usage']['total_tokens']}")
            
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"分析失败: {error_message}")
            
            # 检查是否是token限制错误，如果是则尝试降级（但不是已经在降级过程中）
            if not _is_fallback and ("maximum context length" in error_message or "tokens" in error_message):
                fallback_result = self._try_fallback_model(data, model_name, analysis_type, system_prompt, e)
                if fallback_result:
                    return fallback_result
            
            return {
                'success': False,
                'model': model_name,
                'error': error_message,
                'analysis': None
            }
    
    
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
            max_model_tokens = self.token_limits.get(model_name, 32000)
            
            # 为通用响应分配50%的剩余空间
            available_response_tokens = int((max_model_tokens - estimated_tokens) * 0.5)
            max_response_tokens = max(1000, min(available_response_tokens, max_model_tokens - estimated_tokens - 500))
            
            if estimated_tokens > max_model_tokens * 0.7:
                logger.warning(f"输入token较多 ({estimated_tokens} > {max_model_tokens * 0.7})，响应空间: {max_response_tokens}")
            
            logger.info(f"使用模型 {model_id} 生成响应，输入token: {estimated_tokens}, 最大响应token: {max_response_tokens}")
            
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度确保一致性
                max_tokens=max_response_tokens,  # 动态分配响应空间
            )
            
            end_time = time.time()
            
            result = {
                'success': True,
                'model': model_name,
                'model_id': model_id,
                'analysis': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
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