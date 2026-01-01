#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Falcon 定时任务

功能:
- 每 1 小时生成一组 BTC 信号（5m/15m/1h，风格筛选：RR≥1.5、排除突破、入场偏差≤0.3%）
- 对“从今天开始生成的所有信号”分组做结果评估（按 signal_time 分组）
- 信号与评估结果写入数据库（DuckDB，trader=de），同时输出 Markdown 文件
- 维护状态文件，便于外部检查运行状态

用法:
  python3 scripts/falcon.py --once        # 仅运行一次（生成+评估）
  python3 scripts/falcon.py --daemon      # 常驻进程，每小时运行（默认）

文件输出:
- 信号: trading_signals/BTC_de_signals_简要_<ts>_style_filtered.md 与 ..._full.md
- 评估: trading_signals/signal_evaluation_<ts>.md（按组）
- 状态: trading_signals/.falcon_state.json（最近一次运行信息）
"""

import sys
import os
import json
import time
import subprocess
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

# 允许从 src/ 导入现有能力
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import argparse
import requests

# 现有模块复用
from generate_btc_de_signals import (
    get_btc_kline_gateio,
    get_btc_kline_bitget,
    analyze_timeframe,
    validate_signal,
)
from volatility_analyzer import calculate_risk_reward_ratio
from db_manager_trader import TraderDBManager

# 评估模块
from evaluate_signal_results import (
    evaluate_signals_from_report,
    format_evaluation_report,
)


OUTDIR = Path("trading_signals")
STATE_FILE = OUTDIR / ".falcon_state.json"


def ensure_db_ready():
    """确保 DuckDB 数据库存在（若不存在则初始化）。"""
    # 若 de 库不存在，调用 V2 初始化
    db_file = SRC_DIR / "data" / "qingniao_de.duckdb"
    if not db_file.exists():
        from database_design_v2 import DatabaseDesignV2
        DatabaseDesignV2().init_all_databases()


def get_tickers() -> Tuple[Dict, Dict]:
    gate = {"exchange": "Gate.io", "price": None, "error": None}
    bitget = {"exchange": "Bitget", "price": None, "error": None}
    try:
        r = requests.get(
            "https://api.gateio.ws/api/v4/spot/tickers",
            params={"currency_pair": "BTC_USDT"}, timeout=12
        )
        d = r.json()
        if isinstance(d, list) and d:
            gate["price"] = float(d[0]["last"]) 
            gate["raw"] = d[0]
    except Exception as e:
        gate["error"] = str(e)
    try:
        r = requests.get(
            "https://api.bitget.com/api/spot/v1/market/ticker",
            params={"symbol": "BTCUSDT"}, timeout=12
        )
        d = r.json()
        if d.get("code") == "00000" and d.get("data"):
            bitget["price"] = float(d["data"]["last"]) 
            bitget["raw"] = d["data"]
    except Exception as e:
        bitget["error"] = str(e)
    return gate, bitget


def analyze_signals(current_price: float, k5: List[Dict], k15: List[Dict], k1h: List[Dict],
                    min_rr: float = 1.5, tolerance: float = 0.003,
                    exclude_keywords: List[str] = None) -> List[Tuple[str, Dict, bool]]:
    """基于青鸟分析产出各时间框架的最优信号。返回列表[(tf, signal, passed)]。"""
    exclude_keywords = exclude_keywords or ["突破", "breakout", "区间突破"]
    tf_map_cn = {"5m": "5分钟", "15m": "15分钟", "1h": "1小时"}
    analyses = {
        "5m": analyze_timeframe(k5, tf_map_cn["5m"], current_price) if k5 else None,
        "15m": analyze_timeframe(k15, tf_map_cn["15m"], current_price) if k15 else None,
        "1h": analyze_timeframe(k1h, tf_map_cn["1h"], current_price) if k1h else None,
    }
    results = []
    for tf in ("5m", "15m", "1h"):
        a = analyses.get(tf)
        if not a or not a.get("signals"):
            continue
        filtered = []
        for s in a["signals"]:
            text = (s.get("entry_model", "") or "") + " " + (s.get("reason", "") or "")
            if any(kw in text for kw in exclude_keywords):
                continue
            ok, _ = validate_signal(s, current_price, tolerance_pct=tolerance)
            if not ok:
                continue
            rr = calculate_risk_reward_ratio(
                s["entry"], s["stop_loss"], s["take_profit_1"], s["take_profit_2"], s["type"]
            )
            s["_rr"] = rr
            if rr["avg_rr_ratio"] >= min_rr:
                filtered.append(s)
        if filtered:
            def score_good(x):
                strength = 3 if x["strength"] == "strong" else 2 if x["strength"] == "medium" else 1
                return (x["_rr"]["avg_rr_ratio"], strength)
            best = sorted(filtered, key=score_good, reverse=True)[0]
            results.append((tf, best, True))
        else:
            # 参考：取RR最高的一个
            candidates = []
            for s in a["signals"]:
                text = (s.get("entry_model", "") or "") + " " + (s.get("reason", "") or "")
                if any(kw in text for kw in exclude_keywords):
                    continue
                ok, _ = validate_signal(s, current_price, tolerance_pct=tolerance)
                if not ok:
                    continue
                rr = calculate_risk_reward_ratio(
                    s["entry"], s["stop_loss"], s["take_profit_1"], s["take_profit_2"], s["type"]
                )
                s["_rr"] = rr
                candidates.append(s)
            if candidates:
                def score_ref(x):
                    strength = 3 if x["strength"] == "strong" else 2 if x["strength"] == "medium" else 1
                    return (x["_rr"]["avg_rr_ratio"], strength)
                best = sorted(candidates, key=score_ref, reverse=True)[0]
                results.append((tf, best, False))
    return results


def generate_and_store_signals(db: TraderDBManager, system_name: str = "de",
                               outdir: Path = OUTDIR) -> Tuple[str, List[Tuple[str, Dict, bool]]]:
    """生成一组信号，写文件，入库。返回(signal_time_str, results)。"""
    gate, bitget = get_tickers()
    prices = [p for p in (gate.get("price"), bitget.get("price")) if p]
    if not prices:
        # 回退
        current_price = None
    else:
        current_price = prices[0]

    # 获取K线（Gate优先，Bitget兜底）
    k5 = get_btc_kline_gateio("5m", 200) or get_btc_kline_bitget("5m", 200)
    k15 = get_btc_kline_gateio("15m", 200) or get_btc_kline_bitget("15m", 200)
    k1h = get_btc_kline_gateio("1h", 200) or get_btc_kline_bitget("1h", 200)

    if current_price is None:
        # 双ticker失败，回退最近收盘价
        for ks in (k1h, k15, k5):
            if ks:
                current_price = ks[-1]["close"]
                break

    if not current_price or not k5 or not k15:
        raise RuntimeError("无法获取足够的数据以生成信号")

    # 分析并筛选最优信号
    results = analyze_signals(current_price, k5, k15, k1h)

    # 写简要/详细文件（复用已有脚本以保持格式）；同时生成官方De.版报告
    exe = sys.executable or 'python'
    # 先记录调用前的文件列表用于后验校验
    before = set(str(p) for p in outdir.glob('BTC_de_signals_*_style_filtered*.md'))
    gen_ok = True
    try:
        r = subprocess.run([exe, str(Path('scripts')/ 'generate_style_filtered_signals.py'), '--outdir', str(outdir)], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            gen_ok = False
            print('[Falcon] style_filtered 生成失败:', r.stderr[:400], file=sys.stderr)
    except Exception as e:
        gen_ok = False
        print('[Falcon] style_filtered 调用异常:', e, file=sys.stderr)
    try:
        r2 = subprocess.run([exe, str(Path('src')/ 'generate_btc_de_signals.py')], capture_output=True, text=True, timeout=600)
        if r2.returncode != 0:
            print('[Falcon] 官方De生成器返回码非0:', r2.returncode, file=sys.stderr)
    except Exception as e:
        print('[Falcon] 官方De生成器调用异常:', e, file=sys.stderr)
    # 后验校验：是否真的写出了新文件
    after = set(str(p) for p in outdir.glob('BTC_de_signals_*_style_filtered*.md'))
    if not (after - before):
        gen_ok = False
        print('[Falcon] 警告: 未检测到新的风格筛选文件写入', file=sys.stderr)

    # 将信号入库
    signal_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for tf, s, passed in results:
        rr = s.get("_rr", {})
        db.add_trading_signal(
            signal_time=signal_time_str,
            timeframe=tf,
            signal_type=s.get("type"),
            entry_price=s.get("entry"),
            stop_loss=s.get("stop_loss"),
            take_profit_1=s.get("take_profit_1"),
            take_profit_2=s.get("take_profit_2"),
            entry_model=s.get("entry_model"),
            strength=s.get("strength"),
            risk_reward_ratio=rr.get("avg_rr_ratio"),
            volatility_level=None,
            system_name=system_name,
        )
    if not gen_ok and not results:
        raise RuntimeError('signal_generation_failed')
    return signal_time_str, results


def eval_pending_older_than_24h_and_store(db: TraderDBManager, outdir: Path = OUTDIR):
    """评估“未评估且已超过24小时”的所有历史信号，入库并写报告。"""
    threshold_dt = datetime.now() - timedelta(hours=24)
    threshold = threshold_dt.strftime('%Y-%m-%d %H:%M:%S')
    # 获取阈值之前的所有信号
    signals = db.get_trading_signals(end_date=threshold)
    if not signals:
        return
    # 仅保留尚未有评估记录的信号
    pending: List[Dict] = []
    for s in signals:
        try:
            if db.get_signal_evaluation(s['id']) is None:
                pending.append(s)
        except Exception:
            # 容错：出现异常则暂时跳过
            continue

    if not pending:
        return

    # 按 signal_time 分组评估
    groups: Dict[str, List[Dict]] = {}
    for s in pending:
        groups.setdefault(s['signal_time'], []).append(s)

    for stime, group in sorted(groups.items()):
        # 所有信号使用相同的 signal_time（分组）
        try:
            signal_time = datetime.strptime(stime, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                signal_time = datetime.fromisoformat(stime)
            except Exception:
                continue

        sigs_for_eval = []
        for s in group:
            sigs_for_eval.append({
                'timeframe': s['timeframe'],
                'type': s['signal_type'],
                'entry': s['entry_price'],
                'stop_loss': s['stop_loss'],
                'take_profit_1': s['take_profit_1'],
                'take_profit_2': s['take_profit_2'],
                'model': s.get('entry_model') if isinstance(s, dict) else None,
                'strength': s.get('strength') if isinstance(s, dict) else None,
            })

        if not sigs_for_eval:
            continue

        results = evaluate_signals_from_report(sigs_for_eval, signal_time)
        # 入库评估结果
        for res in results:
            matched_id = None
            for s in group:
                if (
                    s['timeframe'] == res['timeframe'] and
                    abs(float(s['entry_price']) - float(res['entry'])) < 1e-6 and
                    abs(float(s['stop_loss']) - float(res['stop_loss'])) < 1e-6
                ):
                    matched_id = s['id']
                    break
            if matched_id is None:
                continue
            try:
                db.add_signal_evaluation(
                    signal_id=matched_id,
                    evaluation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    result=res.get('status'),
                    actual_entry_price=res.get('entry'),
                    actual_exit_price=None,
                    actual_profit_pct=res.get('current_pnl_pct'),
                    actual_profit_usdt=None,
                    stop_loss_hit=1 if res.get('hit_stop_loss') else 0,
                    take_profit_1_hit=1 if res.get('reached_tp1') else 0,
                    take_profit_2_hit=1 if res.get('reached_tp2') else 0,
                    missed=1 if res.get('status') == 'invalid' else 0,
                    notes=None,
                )
            except Exception as e:
                print(f"[Falcon] 写入评估失败: {e}", file=sys.stderr)
                continue

        # 输出评估报告
        report_md = format_evaluation_report(results)
        out_file = outdir / f"signal_evaluation_{signal_time.strftime('%Y%m%d_%H%M%S')}.md"
        out_file.write_text(report_md, encoding='utf-8')

    # 评估完成后：生成学习建议并更新系统参数（De.系统）
    try:
        from learn_from_signal_report import SignalLearningSystem
        system = SignalLearningSystem(trader_id='de')
        analysis = system.analyze_and_learn()
        if analysis:
            params = system.update_system_parameters(analysis)
            report = system.generate_learning_report(analysis, params)
            learn_file = outdir / f"学习建议_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            learn_file.write_text(report, encoding='utf-8')
            # 同时写入观点表，便于检索
            try:
                content = f"学习建议摘要:\n- 总信号: {analysis.get('total_signals')}\n- 止损问题: {len(analysis.get('stop_loss_issues', []))}\n- 入场价问题: {len(analysis.get('entry_price_issues', []))}"
                db.add_viewpoint(content=content, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                 source='falcon', category='learning', tags=['learning','improvement'])
            except Exception:
                pass
            system.close()
    except Exception as e:
        print(f"[Falcon] 生成学习建议失败: {e}", file=sys.stderr)


def update_state(running: bool, last_ok: bool, last_run_at: datetime, pid: int, last_errors: list | None = None, last_files: list | None = None):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    state = {
        'running': running,
        'last_ok': last_ok,
        'last_run': last_run_at.strftime('%Y-%m-%d %H:%M:%S'),
        'pid': pid,
    }
    if last_errors:
        state['last_errors'] = last_errors[-10:]
    if last_files:
        state['last_files'] = last_files[:10]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Falcon 定时任务')
    parser.add_argument('--once', action='store_true', help='仅运行一次')
    parser.add_argument('--daemon', action='store_true', help='常驻进程（默认）')
    parser.add_argument('--interval', type=int, default=3600, help='执行间隔（秒），默认3600')
    args = parser.parse_args()

    def run_cycle():
        ts_start = datetime.now()
        ok = True
        errs: list[str] = []
        files_created: list[str] = []
        # 在每轮内部创建/关闭DB，避免长期持锁
        db = TraderDBManager('de')
        try:
            signal_time_str, results = generate_and_store_signals(db)
            # 粗略检查：若没有任何信号返回，记为警告
            if not results:
                ok = False
                errs.append('no_signals_generated')
        except Exception as e:
            ok = False
            msg = f"generate_failed: {e}"
            errs.append(msg)
            print(f"[Falcon] 生成信号失败: {e}", file=sys.stderr)
            traceback.print_exc()
        try:
            eval_pending_older_than_24h_and_store(db)
        except Exception as e:
            ok = False
            msg = f"eval_failed: {e}"
            errs.append(msg)
            print(f"[Falcon] 评估失败: {e}", file=sys.stderr)
            traceback.print_exc()
        try:
            db.close()
        except Exception:
            pass
        # 记录最近生成的文件（近15分钟内）
        try:
            now = time.time()
            for p in sorted(OUTDIR.glob('BTC_de_signals_*_style_filtered*.md'), key=lambda x: x.stat().st_mtime, reverse=True):
                if now - p.stat().st_mtime < 900:
                    files_created.append(str(p))
        except Exception:
            pass
        update_state(running=True, last_ok=ok, last_run_at=ts_start, pid=os.getpid(), last_errors=errs, last_files=files_created)

    ensure_db_ready()
    if args.once and not args.daemon:
        run_cycle()
        print("[Falcon] 一次性任务完成")
        return

    # 默认守护模式
    print("[Falcon] 守护任务启动，间隔 {} 秒".format(args.interval))
    update_state(running=True, last_ok=True, last_run_at=datetime.now(), pid=os.getpid())
    while True:
        run_cycle()
        time.sleep(max(10, args.interval))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        update_state(running=False, last_ok=True, last_run_at=datetime.now(), pid=os.getpid())
        print("[Falcon] 已停止")
