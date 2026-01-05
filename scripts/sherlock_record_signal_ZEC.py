#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys, json
from datetime import datetime

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    symbol = 'ZEC/USDT'
    # User provided params
    limit_entry = 473.0
    dca_entry   = 442.0
    stop_loss   = 415.67
    final_tp    = 760.0
    market_frac = 0.33
    limit1_frac = 0.34
    limit2_frac = 0.33

    # Expected weighted avg on full fill (conservative: market ~ limit price)
    expected_avg = (limit_entry * (market_frac + limit1_frac)) + (dca_entry * limit2_frac)
    risk = expected_avg - stop_loss
    reward = final_tp - expected_avg
    rr = (reward / risk) if risk > 0 else None

    db = TraderDBManager('sherlock')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sig_id = db.add_trading_signal(
        signal_time=ts,
        timeframe='4h',
        signal_type='long',
        entry_price=limit_entry,
        stop_loss=stop_loss,
        take_profit_1=None,
        take_profit_2=final_tp,
        entry_model='hybrid_market_limit',
        strength='strong',  # rating 10/10
        risk_reward_ratio=rr,
        volatility_level=None,
        system_name='sherlock'
    )

    plan = {
        'symbol': symbol,
        'mode': 'hybrid',
        'market_frac': market_frac,
        'legs': [
            {'type':'market','frac':market_frac,'price_source':'median(gate,bitget,binance)'},
            {'type':'limit','frac':limit1_frac,'price':limit_entry,'ttl_bars':6,'tf':'5m'},
            {'type':'limit','frac':limit2_frac,'price':dca_entry,'ttl_bars':6,'tf':'5m'}
        ],
        'sl': {'type':'hard','price':stop_loss,'policy':'relative_to_filled_avg'},
        'tp': [{'price':final_tp,'frac':1.0}],
        'costs': {'taker_bps':6,'maker_bps':2,'note':'approx'},
        'notes': '1D Support Retest + 1D QVWAP + 1D 12EMA + TVEM BAND + Monthly VWAP/AVWAP toward entry; rating 10/10',
        'expected_full_avg_entry': expected_avg,
        'approx_rr_fullfill': rr
    }

    vp_content = f"Sherlock 执行计划 | sig#{sig_id} | {symbol} LONG | 4h\n" + json.dumps(plan, ensure_ascii=False)
    db.add_viewpoint(content=vp_content, timestamp=ts, source='sherlock', category='plan', tags=['sherlock','plan'], btc_price=None)
    db.close()
    print(f"✓ Sherlock signal recorded: sig#{sig_id} ({symbol} LONG) RR≈{rr:.2f}")

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()
