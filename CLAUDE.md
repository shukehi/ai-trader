# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Trader is an advanced AI-powered trading analysis system that directly analyzes raw OHLCV candlestick data without traditional technical indicator preprocessing. The core innovation is using LLMs to understand price action patterns through natural language analysis rather than mathematical calculations.

**Core Breakthrough**: AI directly interprets raw market data → Professional Al Brooks price action analysis (70-80/100 quality scores)

**Current Status**: Production-ready system specialized exclusively for Al Brooks price action methodology. The system has been optimized and simplified to focus on this single, highly effective analysis approach using 4 premium models: GPT-5-Chat, Claude-Opus-41, Gemini-25-Pro, and Grok4.

## Essential Commands

### Development Setup
```bash
# Environment setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env to add OPENROUTER_API_KEY

# Validate system components
python -c "from config import Settings; Settings.validate()"
python -c "from ai import RawDataAnalyzer; print('✅ RawDataAnalyzer ready')"
python -c "from data import BinanceFetcher; print('✅ Data fetching ready')"
```

### Primary Analysis Commands
```bash
# Basic Al Brooks analysis (120 bars default for swing structure analysis)
python main.py analyze --symbol ETHUSDT --model gpt5-chat

# Al Brooks price action analysis (currently the only supported method)
python main.py analyze --method al-brooks --symbol BTCUSDT --model claude-opus-41

# Multi-timeframe Al Brooks analysis
python main.py multi-analyze --symbol ETHUSDT --timeframes "15m,1h,4h"

# Real-time analysis
python main.py realtime --symbol ETHUSDT

# List available methods and configuration
python main.py methods
python main.py config

# Interactive demo
python main.py demo

# Verbose output for debugging
python main.py analyze --verbose
```

### Testing and Quality Validation
```bash
# Run Brooks quality compliance tests
pytest -q

# Test individual components
python -c "from ai import RawDataAnalyzer; analyzer = RawDataAnalyzer(); print('✅ Ready')"

# Test data retrieval without AI analysis
python -c "from data import BinanceFetcher; fetcher = BinanceFetcher(); df = fetcher.get_ohlcv('ETH/USDT', '1h', 5); print(f'✅ Retrieved {len(df)} records')"

# Quality score testing (expect 70-80+ for Al Brooks method)
python main.py analyze --method al-brooks --symbol ETHUSDT --limit 120 --verbose
```

## Core Architecture

### High-Level Data Flow
```
Raw OHLCV Data → AI Direct Analysis → Professional Al Brooks Report
     ↓                    ↓                     ↓
  Binance API       RawDataAnalyzer        Structured JSON +
 (120+ bars)      (with quality scoring)     Text Analysis
```

### Key Components

**AI Analysis Layer** (`ai/`):
- `RawDataAnalyzer`: Primary analysis engine with Al Brooks quality scoring system and intelligent token management
- `OpenRouterClient`: LLM API client with automatic fallback mechanism when token limits are exceeded
- `MultiTimeframeAnalyzer`: Parallel analysis across multiple timeframes
- `AnalysisEngine`: Legacy interface, still used by some flows
- Quality scoring system specifically optimized for Al Brooks terminology and concepts

**Data Layer** (`data/`):
- `BinanceFetcher`: CCXT-based market data retrieval with automatic format handling (ETHUSDT ↔ ETH/USDT)
- `BinanceWebSocket`: Real-time data streaming for live Al Brooks analysis
- Robust error handling and reconnection logic

**Prompt System** (`prompts/`):
- `PromptManager`: External prompt file management system (simplified for Al Brooks only)
- Al Brooks methodology prompts in `price_action/al_brooks_analysis.txt` (only remaining prompt file)
- Term mapping system to resolve Al Brooks evaluation inconsistencies
- System specialized exclusively for Al Brooks analysis - all other methods removed

**Configuration** (`config/`):
- `Settings`: API key management and model definitions with token limit validation
- Premium model support: GPT-5-Chat (128K), Claude-Opus-41 (200K), Gemini-25-Pro (2M), Grok4 (128K)
- Intelligent model fallback configuration based on token capacity

**CLI Interface** (`main.py`):
- Typer + Rich modern CLI with progress bars, formatted tables, and color-coded output
- Comprehensive command structure for Al Brooks analysis, real-time monitoring, and system management

## Critical Architecture Features

### Token Management and Error Handling
The system includes sophisticated token management to prevent API failures:

1. **Conservative Token Limits**: Uses 80% of model capacity as safety margin
2. **Intelligent Estimation**: Precise token counting using word/character-based heuristics
3. **Automatic Fallback**: When token limits are exceeded, automatically upgrades to higher-capacity models
4. **Model Hierarchy**: gemini-25-pro (2M) → claude-opus-41 (200K) → grok4/gpt5-chat (128K)

### Al Brooks Quality Validation
The system enforces strict quality standards for Al Brooks price action analysis:

- **120 Bar Minimum**: Al Brooks analysis requires 120+ bars for effective swing structure analysis
- **Quality Scoring**: 60% analysis quality + 40% terminology accuracy, targeting 70-80/100 scores
- **Term Mapping**: Resolves evaluation inconsistencies ("reversal bar with long tail" → "pin bar")
- **Diagnostic Fields**: All analyses include validation flags for compliance

### Specialized Al Brooks System
- **Single Method Focus**: System exclusively supports Al Brooks price action analysis
- **Optimized Prompts**: Single, highly optimized prompt file for Al Brooks methodology
- **Specialized Quality Evaluation**: Quality scoring tailored specifically for Al Brooks concepts and terminology
- **Simplified Architecture**: Removed complexity by focusing on one proven methodology

## Development Workflow

### Making Changes to Analysis Quality
1. Modify evaluation criteria in `prompts/prompt_manager.py` 
2. Update term mappings in `BROOKS_TERM_MAPPING` if needed
3. Test with GPT-5-Chat and Claude-Opus-41 models
4. Run `pytest -q` to validate Brooks quality compliance
5. Expect quality scores of 70-80+ for properly optimized prompts

### Al Brooks Prompt Development
1. Edit the single prompt file: `prompts/price_action/al_brooks_analysis.txt`
2. Update method mapping in `PromptManager.get_method_info()` if needed
3. Adjust quality evaluator in `PromptManager._evaluate_pa_quality()`
4. Add tests in `tests/` directory following Brooks quality pattern

### Token Limit Troubleshooting
If encountering token limit errors:
1. Check `ai/openrouter_client.py` for token calculation logic
2. Verify model limits in `config/settings.py` TOKEN_LIMITS
3. Test fallback mechanism with verbose logging
4. Consider reducing data limit (--limit parameter) for testing

### Model Integration and Testing
- Models are configured in `config/settings.py` with conservative token limits
- Test new models by adding to MODELS dict and TOKEN_LIMITS
- Fallback hierarchy is defined in `OpenRouterClient._get_fallback_models()`
- Quality thresholds are model-specific and defined in validation config

## Important Files

- **`main.py`**: Typer CLI with Rich formatting, primary entry point
- **`ai/raw_data_analyzer.py`**: Core analysis engine with Al Brooks quality scoring
- **`ai/openrouter_client.py`**: LLM API client with intelligent token management and fallback
- **`prompts/prompt_manager.py`**: Al Brooks quality evaluation and term mapping system
- **`prompts/price_action/al_brooks_analysis.txt`**: Al Brooks methodology prompt (only prompt file)
- **`config/settings.py`**: API configuration, model definitions, and token limits
- **`tests/test_brooks_quality.py`**: Brooks analysis quality compliance tests
- **`.env.example`**: Complete configuration template

## Al Brooks Quality Validation Rules

The system enforces specific rules for Al Brooks analysis compliance:

- Use only closed bars; `timeframes[].bars_analyzed` must match actual data
- Metadata locked: `venue=Binance-Perp`, `timezone=UTC`, `tick_size`, `fees_bps`, `slippage_ticks`
- Price rounding to tick_size; local EMA(20) calculation for magnetic levels
- Risk/reward includes fees and slippage; auto-adjust if RR < 1.5
- Bar indexing uses negative indices relative to last closed bar (-1 = latest)
- Diagnostic validation: `tick_rounded`, `rr_includes_fees_slippage`, `used_closed_bar_only`, `metadata_locked`, `htf_veto_respected` all true

## Al Brooks Specific Concepts

The system understands and evaluates these Al Brooks concepts:

**Core Terminology**:
- Always In concepts (Always In Long, Always In Short, market state transitions)
- Bar patterns (pin bars, inside bars, outside bars, trend bars, follow-through)
- Swing structure (H1, H2, L1, L2, swing points, pullbacks)
- Trading ranges (breakout mode, tight trading range, measured moves)

**Quality Evaluation**:
- Structure analysis depth (30 points): Always In states, swing identification
- Trading plan completeness (20 points): Entry, exit, stop, risk management
- Brooks concepts application (10 points): Specific methodology terms
- Brooks terminology accuracy (25 points): Correct use of technical terms
- Price data integration (15 points): Specific price references and analysis

## Performance and Monitoring

- **Target Response Time**: 5-15 seconds average for standard analysis
- **Quality Target**: 70-80/100 Al Brooks analysis scores (improved from earlier 50-60 range)
- **Token Efficiency**: ~60% reduction through CSV formatting and intelligent allocation
- **Error Recovery**: Automatic model fallback with graceful degradation
- **Real-time Capability**: WebSocket support for live market monitoring
- **Analysis Success Rate**: >98% with intelligent token management

## System Evolution Notes

**Recent Optimizations (v1.3.0)**:
- Specialized system exclusively for Al Brooks analysis
- Removed VPA, ICT, and other analysis methods for simplicity and focus
- Optimized quality scoring specifically for Al Brooks terminology
- Improved token management with automatic model fallbacks
- Enhanced error handling and system reliability

Run quality validation tests regularly to ensure system performance maintains professional Al Brooks analysis standards.