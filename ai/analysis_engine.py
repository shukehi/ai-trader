import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from .openrouter_client import OpenRouterClient
from formatters import DataFormatter

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """
    AI直接分析引擎 - 专注原始数据分析
    
    核心功能：
    1. AI直接理解原始OHLCV数据
    2. 无需技术指标预处理
    3. 支持多种分析类型
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_validation: bool = False):
        """
        初始化分析引擎
        
        Args:
            api_key: OpenRouter API密钥
            enable_validation: 是否启用多模型验证（已简化，暂不支持）
        """
        self.client = OpenRouterClient(api_key)
        self.formatter = DataFormatter()
        logger.info("✅ AI直接分析引擎初始化完成")
    
    def raw_data_analysis(self, 
                         df: pd.DataFrame,
                         analysis_type: str = 'complete',
                         model: str = 'gemini-flash') -> Dict[str, Any]:
        """
        AI直接分析原始OHLCV数据
        
        Args:
            df: 原始OHLCV数据DataFrame
            analysis_type: 分析类型 ('simple', 'complete', 'enhanced')
            model: 使用的AI模型
            
        Returns:
            分析结果字典
        """
        try:
            # 格式化数据
            csv_data = self.formatter.to_csv_format(df, include_volume=True)
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(analysis_type, csv_data)
            
            # 调用AI模型
            response = self.client.complete_sync(
                prompt=prompt,
                model=model,
                max_tokens=2000 if analysis_type == 'enhanced' else 1500
            )
            
            return {
                'analysis': response.get('content', ''),
                'model': model,
                'analysis_type': analysis_type,
                'data_points': len(df),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"AI分析失败: {str(e)}")
            return {
                'analysis': f'分析失败: {str(e)}',
                'model': model,
                'analysis_type': analysis_type,
                'success': False
            }
    
    def _build_analysis_prompt(self, analysis_type: str, csv_data: str) -> str:
        """构建分析提示词"""
        base_prompt = f"""请分析以下ETH永续合约的原始OHLCV数据：

{csv_data}

请从Volume Price Analysis (VPA)专业角度进行分析，包括：
"""
        
        if analysis_type == 'simple':
            return base_prompt + """
1. 价格趋势判断
2. 成交量特征
3. 关键支撑阻力位
4. 简短交易建议

请保持分析简洁明了。"""
        
        elif analysis_type == 'enhanced':
            return base_prompt + """
1. 详细趋势分析（多时间维度）
2. 成交量模式识别
3. 价格行为特征分析
4. 支撑阻力位确认
5. 市场结构评估
6. 风险评估和仓位建议
7. 具体入场出场点位

请提供专业详细的分析报告。"""
        
        else:  # complete
            return base_prompt + """
1. 价格趋势分析
2. 成交量分析
3. 支撑阻力位识别
4. 市场结构判断
5. 交易机会识别
6. 风险提示

请提供完整的专业分析。"""