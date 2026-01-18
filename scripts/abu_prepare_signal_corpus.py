#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清洗ABU文本语料，抽取结构化要素，并生成模式权重文件。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import itertools
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
PDF_PAGES = ROOT / 'data' / 'abu' / 'raw_pages_improved.jsonl'
PATTERNS_FILE = ROOT / 'data' / 'abu' / 'patterns.json'
EBOOK_DIR = ROOT / 'data' / 'abu' / 'ebooks' / 'extracted'

NOISE_PATTERNS = [
    r'阿布价格行为全套课程',
    r'人工精校字幕',
    r'加入VIP',
    r'联系微信',
    r'Unmarked Chart',
    r'Your Own Analysis',
    r'copyright',
    r'All rights reserved',
]

PATTERN_SYNONYMS = {
    'Wedge': ['wedge', '楔形'],
    'Triangle': ['triangle', '三角形', '三角整理'],
    'Channel': ['channel', '通道', '通道线'],
    'Flag': ['flag', '旗形', '旗形整理'],
    'Pennant': ['pennant', '三角旗'],
    'DoubleTop': ['double top', '双顶'],
    'DoubleBottom': ['double bottom', '双底', 'w底', 'w bottom'],
    'HeadAndShoulders': ['head and shoulders', '头肩顶', '头肩底'],
    'Breakout': ['breakout', '突破', '向上突破', '向下突破'],
    'Pullback': ['pullback', '回调', '回撤'],
    'TradingRange': ['trading range', '区间', '盘整', '震荡区间'],
    'MeasuredMove': ['measured move', '测量运动', '量度升幅', '量度下跌'],
    'Engulfing': ['engulfing', '吞没'],
    'InsideBar': ['inside bar', '内包线', '内包'],
    'PinBar': ['pin bar', '针形', '锤子线', '上吊线'],
    'Trend': ['trend', '趋势'],
    'Reversal': ['reversal', '反转'],
    'Continuation': ['continuation', '延续'],
}

LONG_KEYWORDS = ['long', 'buy', 'bull', 'bullish', '做多', '看多', '多头']
SHORT_KEYWORDS = ['short', 'sell', 'bear', 'bearish', '做空', '看空', '空头']
ENTRY_KEYWORDS = ['entry', 'enter', '入场', '进场', '开仓']
STOP_KEYWORDS = ['stop', '止损', 'sl']
TP_KEYWORDS = ['take profit', 'tp', 'target', '止盈', '目标']
RR_KEYWORDS = ['risk reward', 'risk_reward', 'reward risk', 'rr', '盈亏比']
TIMEFRAME_KEYWORDS = ['5m', '15m', '1h', '4h', '5分钟', '15分钟', '1小时', '4小时']


def _compile_noise_patterns() -> List[re.Pattern]:
    return [re.compile(pat, re.IGNORECASE) for pat in NOISE_PATTERNS]


def _is_latin_phrase(text: str) -> bool:
    return bool(re.fullmatch(r'[a-z0-9\s\-]+', text))


def _synonym_in_text(text_lower: str, synonym: str) -> bool:
    syn_lower = synonym.lower()
    if _is_latin_phrase(syn_lower):
        return re.search(r'\b' + re.escape(syn_lower) + r'\b', text_lower) is not None
    return syn_lower in text_lower


def clean_text(text: str, noise_patterns: List[re.Pattern], min_line_len: int) -> str:
    if not text:
        return ''
    text = text.replace('\r', '\n').replace('\t', ' ')
    lines = [ln.strip() for ln in text.split('\n')]
    seen = set()
    cleaned_lines = []
    for line in lines:
        if len(line) < min_line_len:
            continue
        if any(pat.search(line) for pat in noise_patterns):
            continue
        if line in seen:
            continue
        seen.add(line)
        cleaned_lines.append(line)
    cleaned = ' '.join(cleaned_lines)
    return re.sub(r'\s+', ' ', cleaned).strip()


def extract_patterns(text_lower: str) -> List[str]:
    found = []
    for name, synonyms in PATTERN_SYNONYMS.items():
        for syn in synonyms:
            if _synonym_in_text(text_lower, syn):
                found.append(name)
                break
    return found


def extract_features(text: str) -> Dict:
    text_lower = text.lower()
    patterns = extract_patterns(text_lower)
    directions = []
    if any(key in text_lower for key in LONG_KEYWORDS):
        directions.append('long')
    if any(key in text_lower for key in SHORT_KEYWORDS):
        directions.append('short')

    features = {
        'patterns': patterns,
        'directions': directions,
        'has_entry': any(key in text_lower for key in ENTRY_KEYWORDS),
        'has_stop': any(key in text_lower for key in STOP_KEYWORDS),
        'has_tp': any(key in text_lower for key in TP_KEYWORDS),
        'has_rr': any(key in text_lower for key in RR_KEYWORDS),
        'has_timeframe': any(key in text_lower for key in TIMEFRAME_KEYWORDS),
    }
    return features


def iter_pdf_pages() -> Iterable[Tuple[str, Dict]]:
    if not PDF_PAGES.exists():
        return
    with PDF_PAGES.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            texts = []
            if obj.get('text'):
                texts.append(obj['text'])
            blocks = obj.get('blocks') or []
            for block in blocks:
                if isinstance(block, list) and len(block) >= 5 and isinstance(block[4], str):
                    texts.append(block[4])
            if texts:
                yield 'pdf', {
                    'id': obj.get('page'),
                    'text': '\n'.join(texts)
                }


def iter_patterns_context() -> Iterable[Tuple[str, Dict]]:
    if not PATTERNS_FILE.exists():
        return
    try:
        data = json.loads(PATTERNS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return
    for item in data:
        texts = []
        if item.get('context_text'):
            texts.append(item['context_text'])
        if item.get('key_features'):
            if isinstance(item['key_features'], list):
                texts.extend(item['key_features'])
            elif isinstance(item['key_features'], str):
                texts.append(item['key_features'])
        raw = item.get('gemini_annotation_json') or ''
        if raw:
            try:
                ann = json.loads(raw)
                parsed = ann.get('parsed', ann) if isinstance(ann, dict) else ann
                text_notes = parsed.get('text_notes') if isinstance(parsed, dict) else None
                if isinstance(text_notes, list):
                    texts.extend([t for t in text_notes if isinstance(t, str)])
                narrative = parsed.get('complete_narrative') if isinstance(parsed, dict) else None
                if isinstance(narrative, str):
                    texts.append(narrative)
            except Exception:
                pass
        if texts:
            yield 'pattern_context', {
                'id': item.get('id'),
                'text': '\n'.join(texts)
            }


def iter_ebook_texts() -> Iterable[Tuple[str, Dict]]:
    if not EBOOK_DIR.exists():
        return
    for ebook_file in sorted(EBOOK_DIR.glob('*_extracted.json')):
        try:
            data = json.loads(ebook_file.read_text(encoding='utf-8'))
        except Exception:
            continue
        chapters = data.get('chapters') or []
        for chapter in chapters:
            chapter_title = chapter.get('chapter_title')
            paragraphs = chapter.get('paragraphs') or []
            for para in paragraphs:
                if isinstance(para, str) and para.strip():
                    yield 'ebook', {
                        'id': f"{ebook_file.stem}:{chapter_title}",
                        'text': para
                    }


def compute_weights(total: Counter, long: Counter, short: Counter,
                    min_weight: float, max_weight: float, top_n: int) -> Dict[str, Dict[str, float]]:
    weights: Dict[str, Dict[str, float]] = {}
    if not total:
        return weights

    max_total = max(total.values()) or 1
    for pattern, count in total.most_common(top_n):
        base = min_weight + (max_weight - min_weight) * (math.log1p(count) / math.log1p(max_total))
        lcount = long.get(pattern, 0)
        scount = short.get(pattern, 0)
        if lcount + scount == 0:
            l_weight = base
            s_weight = base
        else:
            l_ratio = lcount / (lcount + scount)
            s_ratio = scount / (lcount + scount)
            l_weight = base * (0.6 + 0.4 * l_ratio)
            s_weight = base * (0.6 + 0.4 * s_ratio)

        weights[pattern] = {
            'long': round(max(0.05, min(1.0, l_weight)), 3),
            'short': round(max(0.05, min(1.0, s_weight)), 3)
        }
    return weights


def write_weights_yaml(path: Path, weights: Dict[str, Dict[str, float]], sources: List[str]) -> None:
    lines = [
        "# Auto-generated pattern weights (do not edit manually)",
        f"version: v0.2",
        f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "sources:"
    ]
    for src in sources:
        lines.append(f"  - {src}")
    lines.append("weights:")
    for pattern, values in weights.items():
        lines.append(f"  {pattern}:")
        lines.append(f"    long: {values['long']}")
        lines.append(f"    short: {values['short']}")
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='ABU文本清洗与权重生成')
    parser.add_argument('--output-dir', default='outputs/abu_nlp', help='输出目录')
    parser.add_argument('--min-line-len', type=int, default=6, help='最短文本行长度')
    parser.add_argument('--min-text-len', type=int, default=40, help='最短文本长度')
    parser.add_argument('--top-patterns', type=int, default=60, help='权重输出的模式数量')
    parser.add_argument('--write-weights', action='store_true', help='写入权重配置文件')
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    noise_patterns = _compile_noise_patterns()
    cleaned_path = output_dir / 'cleaned_corpus.jsonl'
    structured_path = output_dir / 'structured_features.jsonl'
    counts_path = output_dir / 'pattern_counts.json'

    total_counts = Counter()
    long_counts = Counter()
    short_counts = Counter()

    cleaned_written = 0
    structured_written = 0

    with cleaned_path.open('w', encoding='utf-8') as cleaned_fp, \
            structured_path.open('w', encoding='utf-8') as structured_fp:
        for source, entry in itertools.chain(iter_pdf_pages(), iter_patterns_context(), iter_ebook_texts()):
            raw_text = entry.get('text') or ''
            cleaned = clean_text(raw_text, noise_patterns, args.min_line_len)
            if len(cleaned) < args.min_text_len:
                continue
            cleaned_fp.write(json.dumps({
                'source': source,
                'id': entry.get('id'),
                'text': cleaned
            }, ensure_ascii=False) + '\n')
            cleaned_written += 1

            features = extract_features(cleaned)
            if features['patterns'] or features['has_entry'] or features['has_stop'] or features['has_tp']:
                structured_fp.write(json.dumps({
                    'source': source,
                    'id': entry.get('id'),
                    **features
                }, ensure_ascii=False) + '\n')
                structured_written += 1

            for pattern in features['patterns']:
                total_counts[pattern] += 1
                if 'long' in features['directions']:
                    long_counts[pattern] += 1
                if 'short' in features['directions']:
                    short_counts[pattern] += 1

    counts_path.write_text(json.dumps({
        'total': total_counts,
        'long': long_counts,
        'short': short_counts
    }, indent=2, ensure_ascii=False), encoding='utf-8')

    sources = [
        str(PDF_PAGES.relative_to(ROOT)) if PDF_PAGES.exists() else 'data/abu/raw_pages_improved.jsonl (missing)',
        str(PATTERNS_FILE.relative_to(ROOT)) if PATTERNS_FILE.exists() else 'data/abu/patterns.json (missing)',
        str(EBOOK_DIR.relative_to(ROOT)) if EBOOK_DIR.exists() else 'data/abu/ebooks/extracted (missing)'
    ]

    weights = compute_weights(
        total=total_counts,
        long=long_counts,
        short=short_counts,
        min_weight=0.1,
        max_weight=0.9,
        top_n=args.top_patterns
    )

    if args.write_weights:
        write_weights_yaml(ROOT / 'config' / 'abu_pattern_weights.yaml', weights, sources)
        write_weights_yaml(ROOT / 'config' / 'pattern_weights.yaml', weights, sources)

    print("✅ 文本清洗完成")
    print(f"  cleaned_corpus: {cleaned_written} 条 -> {cleaned_path}")
    print(f"  structured_features: {structured_written} 条 -> {structured_path}")
    print(f"  pattern_counts: {counts_path}")
    print(f"✅ 权重条目: {len(weights)}")
    if args.write_weights:
        print("✅ 权重文件已写入 config/abu_pattern_weights.yaml 与 config/pattern_weights.yaml")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
