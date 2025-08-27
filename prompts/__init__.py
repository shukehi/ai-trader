"""
提示词管理模块

支持多种交易分析方法的提示词管理，包括：
- VPA (Volume Price Analysis) 
- ICT (Inner Circle Trader) 概念
- 价格行为分析
- 综合分析方法
"""

from .prompt_manager import PromptManager

__all__ = ['PromptManager']