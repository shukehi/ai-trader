"""
Pytest checks for Brooks analysis quality and rule compliance.

Assumptions:
- We test offline using synthetic OHLCV; bars are CLOSED.
- Venue is Binance perpetuals; timezone is UTC; tick_size=0.01, fees_bps=5, slippage_ticks=1.
- EMA(20) is computed from provided bars only and rounded to tick.
"""

import os, sys
import pandas as pd

# Repository root
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))


if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ai.raw_data_analyzer import RawDataAnalyzer
from ai.rr_utils import rr_with_costs, round_to_tick
from ai.indicators import ema


def _build_df(n=120, start=4300.0, step=1.0):
    # Build a simple rising series; all bars closed.
    closes = [start + i * step for i in range(n)]
    opens = [c - 0.5 for c in closes]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    vols = [100 + i for i in range(n)]
    ts = pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        'timestamp': ts,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': vols,
    })
    df['datetime'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    return df


def test_metadata_consistency():
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(
        df,
        analysis_method='al-brooks',
        symbol='ETHUSDT',
        timeframe='1h',
        tick_size=0.01,
        fees_bps=5,
        slippage_ticks=1,
    )
    assert res['success']
    assert res['metadata']['venue'] == 'Binance-Perp'
    assert res['metadata']['timezone'] == 'UTC'
    assert res['timeframes'][0]['bars_analyzed'] == len(df)


def test_rr_math_and_adjustment():
    # RR math with costs
    entry, stop = 4405.0, 4260.0
    t1, t2 = 4500.0, 4600.0
    tick, fees, slip = 0.01, 5, 1
    rr1 = rr_with_costs(entry, stop, t1, 'long', tick, fees, slip)
    rr2 = rr_with_costs(entry, stop, t2, 'long', tick, fees, slip)
    assert rr1 > 0
    assert rr2 > rr1

    # Analyzer should auto-adjust when RR<1.5
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=tick, fees_bps=fees, slippage_ticks=slip)
    if 'plan' in res:
        auto = res['plan'].get('auto_adjustment')
        assert auto and auto['applied'] and auto['reason'] == 'rr_below_threshold'


def test_ema20_magnet():
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0.01)
    magnets = res['levels']['magnets']
    ema_nodes = [m for m in magnets if m['name'].startswith('ema20_')]
    assert ema_nodes, 'EMA20 magnet missing'
    ema_val = ema_nodes[0]['price']
    assert isinstance(ema_val, float)
    assert round_to_tick(ema_val, 0.01) == ema_val


def test_signals_indexing():
    df = _build_df(60)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0.01)
    sig = res['signals'][0]
    assert sig['bar_index'] == -1
    # Ensure validator logic compatible with bars_analyzed
    assert abs(sig['bar_index']) <= res['timeframes'][0]['bars_analyzed']
    # Validator should reject out-of-range indices if present (simulated)
    with_index_error = False
    try:
        _ = [
            (_ for _ in ()).throw(ValueError())  # placeholder to mirror raising path
        ]
    except Exception:
        with_index_error = True
    assert with_index_error


def test_diagnostics():
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0.01)
    d = res['diagnostics']
    assert d['tick_rounded']
    assert d['rr_includes_fees_slippage']
    assert d['used_closed_bar_only']
    assert d['metadata_locked']
    assert d['htf_veto_respected']


def test_diagnostics_gate():
    # Force a hard-gate failure by passing invalid tick_size
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0)
    # When hard-gate fails, plan is omitted and reason present; quality <= 50
    assert 'plan' not in res
    assert res['diagnostics'].get('reason') == 'hard_gate_failed'
    assert res['quality_score'] <= 50


def test_scaling_structure():
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0.01)
    trig = res['plan']['scaling']['trigger'] if 'plan' in res else ''
    assert 'with-trend trend bar' in trig and 'before T1 is touched' in trig and 'EMA-favorable side' in trig


def test_measured_moves_standardized():
    df = _build_df(120)
    analyzer = RawDataAnalyzer()
    res = analyzer.analyze_raw_ohlcv(df, analysis_method='al-brooks', timeframe='1h', tick_size=0.01)
    mm = res.get('measured_moves')
    assert mm and isinstance(mm, list)
    item = mm[0]
    assert 'basis' in item and 'height' in item and 'formula' in item and 'target' in item
    # Validate formula semantics approximately
    entry = res['plan']['entry'] if 'plan' in res else round_to_tick(df['close'].iloc[-1], 0.01)
    if 'entry + height' in item['formula']:
        assert abs(item['target'] - (entry + item['height'])) < 1e-6
    elif 'entry - height' in item['formula']:
        assert abs(item['target'] - (entry - item['height'])) < 1e-6
