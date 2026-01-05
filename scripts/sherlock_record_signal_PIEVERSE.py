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
    symbol = 'PIEVERSE/USDT'
    # Base params from user
    limit_entry = 0.5947
    dca_entry   = 0.5522
    stop_loss   = 0.5187
    final_tp    = 1.0
    market_frac = 0.33
    limit1_frac = 0.34
    limit2_frac = 0.33

    # Expected full-fill weighted avg assuming market at limit price for conservative estimate
    expected_avg = (limit_entry * (market_frac + limit1_frac)) + (dca_entry * limit2_frac)
    risk = expected_avg - stop_loss
    reward = final_tp - expected_avg
    rr = (reward / risk) if risk > 0 else None

    # Insert into Sherlock DB (signal + viewpoint execution plan)
    db = TraderDBManager('sherlock')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sig_id = db.add_trading_signal(
        signal_time=ts,
        timeframe='4h',
        signal_type='long',
        entry_price=limit_entry,  # anchor price for the setup
        stop_loss=stop_loss,
        take_profit_1=None,
        take_profit_2=final_tp,
        entry_model='hybrid_market_limit',
        strength='medium',  # rating 6/10
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
        'notes': '1D Support Retest + Monthly VWAP；共振不多需谨慎（rating 6/10）。',
        'expected_full_avg_entry': expected_avg,
        'approx_rr_fullfill': rr
    }

    vp_content = (
        f"Sherlock 执行计划 | sig#{sig_id} | {symbol} LONG | 4h\n" +
        json.dumps(plan, ensure_ascii=False)
    )
    db.add_viewpoint(
        content=vp_content,
        timestamp=ts,
        source='sherlock',
        category='plan',
        tags=['sherlock','plan'],
        btc_price=None,
        related_trade_id=None,
        related_conversation_id=None
    )
    db.close()
    print(f"✓ Sherlock signal recorded: sig#{sig_id} ({symbol} LONG)")

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
