# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Trader is an advanced AI-powered trading analysis system that directly analyzes raw OHLCV candlestick data without traditional technical indicator preprocessing. The core innovation is using LLMs to understand price action patterns through natural language analysis rather than mathematical calculations.

**Core Breakthrough**: AI directly interprets raw market data → Professional trading analysis (80-100/100 quality scores)

**Current Status**: Production-ready system with Al Brooks price action methodology achieving 70-80/100 quality scores after v1.2.0 optimization.

## Essential Commands

### Primary Analysis Commands
```bash
# Basic analysis (120 bars default for Al Brooks method)
python main.py analyze --symbol ETHUSDT --model gemini-flash

# Al Brooks price action analysis (currently the only supported method)
python main.py analyze --method al-brooks --symbol BTCUSDT --model gpt4o-mini

# Multi-timeframe analysis
python main.py multi-analyze --symbol ETHUSDT --timeframes "15m,1h,4h"

# Real-time analysis
python main.py realtime --symbol ETHUSDT

# Verbose output for debugging
python main.py analyze --verbose

# List available methods and configuration
python main.py methods
python main.py config
```

### Development Setup
```bash
# Environment setup
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env to add OPENROUTER_API_KEY

# Validate system components
python -c "from config import Settings; Settings.validate()"
python -c "from ai import RawDataAnalyzer; print('✅ RawDataAnalyzer ready')"
python -c "from data import BinanceFetcher; print('✅ Data fetching ready')"
```

### Testing and Validation
```bash
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
Raw OHLCV Data → AI Direct Analysis → Professional Trading Report
     ↓                    ↓                     ↓
  Binance API       RawDataAnalyzer        Structured JSON +
 (120+ bars)      (with quality scoring)     Text Analysis
```

### Key Components

**AI Analysis Layer** (`ai/`):
- `RawDataAnalyzer`: Primary analysis engine with quality scoring system
- `AnalysisEngine`: Legacy interface, still used by some flows  
- `MultiTimeframeAnalyzer`: Parallel analysis across multiple timeframes
- `OpenRouterClient`: LLM API client supporting 15+ models
- Quality scoring system optimized for Al Brooks methodology (v1.2.0)

**Data Layer** (`data/`):
- `BinanceFetcher`: CCXT-based market data retrieval
- `BinanceWebSocket`: Real-time data streaming
- Automatic symbol format handling (ETHUSDT ↔ ETH/USDT)

**Prompt System** (`prompts/`):
- `PromptManager`: External prompt file management
- Al Brooks methodology prompts in `price_action/al_brooks_analysis.txt`
- Term mapping system to resolve evaluation inconsistencies
- Currently in "Al Brooks validation period" - other methods temporarily disabled

**Configuration** (`config/`):
- `Settings`: API key management and model definitions
- Supports economy, balanced, and premium model tiers

### Critical Architecture Notes

1. **120 Bar Minimum**: Al Brooks analysis requires 120+ bars for effective swing structure analysis. The system validates this and warns if insufficient data.

2. **Quality Scoring System**: Heavily optimized in v1.2.0 to properly evaluate Al Brooks terminology:
   - 60% analysis quality + 40% terminology accuracy 
   - Term mapping resolves "reversal bar with long tail" → "pin bar" mismatches
   - Current targets: 70-80/100 quality scores

3. **Al Brooks Validation Period**: System currently focuses exclusively on Al Brooks price action methodology. Other methods (VPA, ICT) are temporarily disabled pending quality validation.

4. **No Traditional Indicators**: The system deliberately avoids RSI, MACD, etc. AI interprets raw price patterns directly.

## Token Management

The system uses intelligent token allocation based on analysis type and model capacity:
- **Input optimization**: CSV format reduces tokens by ~60%
- **Response allocation**: 30-60% of available tokens based on analysis complexity
- **Model-aware**: Utilizes full capacity (Gemini 1M tokens, Claude 200K tokens)
- **Safety margins**: 70% warning threshold, minimum 1000 token guarantee

## Development Workflow

### Making Changes to Analysis Quality
1. Modify evaluation criteria in `prompts/prompt_manager.py` 
2. Update term mappings in `BROOKS_TERM_MAPPING` if needed
3. Test with both Gemini-Flash and GPT-4o-Mini models
4. Expect quality scores of 70-80+ for properly optimized prompts

### Adding New Analysis Methods
1. Currently disabled during Al Brooks validation period
2. When enabled: add prompts to appropriate `/prompts/` subdirectory  
3. Update method mapping in `PromptManager.get_method_info()`
4. Create quality evaluator in `PromptManager._evaluate_*_quality()`

### Model Integration
Models are configured in `.env` with three tiers:
- **Economy**: `gemini-flash`, `gpt4o-mini`, `claude-haiku` 
- **Balanced**: `gpt4o`, `claude`, `gemini`
- **Premium**: `gpt5-chat`, `claude-opus-41`, `gemini-25-pro`

## Important Files

- **`main.py`**: Typer CLI with Rich formatting, primary entry point
- **`ai/raw_data_analyzer.py`**: Core analysis engine with quality scoring
- **`prompts/prompt_manager.py`**: Quality evaluation and term mapping system
- **`prompts/price_action/al_brooks_analysis.txt`**: Al Brooks methodology prompt
- **`config/settings.py`**: API configuration and model definitions
- **`.env.example`**: Complete configuration template

## Recent Changes (v1.2.0)

The system underwent major quality scoring optimization:
- **Gemini-Flash**: 56→70 points (+25%)
- **GPT-4o-Mini**: 58→80 points (+38%)
- Fixed evaluation/prompt terminology mismatches
- Increased default data from 50 to 120 bars
- Rebalanced scoring: 60% analysis quality + 40% terminology

This represents the current production-ready state focused on Al Brooks price action analysis.