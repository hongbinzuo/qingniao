#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Bitget supported base assets to improve Dream symbol matching.
Outputs: config/dream_bitget_bases.json (sorted upper-case base codes)
"""
from __future__ import annotations
import sys, json
from pathlib import Path

import requests

OUT = Path('config') / 'dream_bitget_bases.json'


def get(url: str, params: dict | None = None):
    r = requests.get(url, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_spot_products() -> set[str]:
    bases: set[str] = set()
    try:
        data = get('https://api.bitget.com/api/spot/v1/public/products')
        items = data.get('data') or []
        for it in items:
            base = (it.get('baseCoin') or '').upper()
            quote = (it.get('quoteCoin') or '').upper()
            if not base:
                continue
            if quote in ('USDT', 'USDC', 'USD'):
                bases.add(base)
    except Exception:
        pass
    return bases


def fetch_mix_contracts() -> set[str]:
    bases: set[str] = set()
    for pt in ('umcbl', 'dmcbl'):
        try:
            data = get('https://api.bitget.com/api/mix/v1/market/contracts', {'productType': pt})
            items = data.get('data') or []
            for it in items:
                base = (it.get('baseCoin') or '').upper()
                quote = (it.get('quoteCoin') or '').upper()
                if not base:
                    continue
                if quote in ('USDT', 'USDC', 'USD'):
                    bases.add(base)
        except Exception:
            continue
    return bases


def fetch_currencies() -> set[str]:
    bases: set[str] = set()
    try:
        data = get('https://api.bitget.com/api/spot/v1/public/currencies')
        items = data.get('data') or []
        for it in items:
            coin = (it.get('coin') or '').upper()
            if coin:
                bases.add(coin)
    except Exception:
        pass
    return bases


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    bases = set()
    s1 = fetch_spot_products(); bases |= s1
    s2 = fetch_mix_contracts(); bases |= s2
    s3 = fetch_currencies();    bases |= s3
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lst = sorted(bases)
    OUT.write_text(json.dumps(lst, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✓ Saved {len(lst)} bases to {OUT}")
    print(f"  spot={len(s1)}, mix={len(s2)}, currencies={len(s3)}")


if __name__ == '__main__':
    main()

