#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉匹配结果写入PostgreSQL
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from db_manager_trader import PostgresDBManager
except Exception:
    try:
        from src.db_manager_trader import PostgresDBManager  # type: ignore
    except Exception:
        PostgresDBManager = None


class VisionMatchRecorder:
    """视觉匹配结果入库器"""

    _table_ready = False

    def __init__(self, trader_id: str = "abu", enabled: bool = True):
        self.enabled = enabled and PostgresDBManager is not None
        self.db = None
        if self.enabled:
            try:
                self.db = PostgresDBManager(trader_id)
            except Exception as exc:
                print(f"[WARN] 视觉匹配入库初始化失败: {exc}", file=sys.stderr)
                self.enabled = False

    def _ensure_table(self) -> None:
        if not self.enabled or VisionMatchRecorder._table_ready:
            return
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vision_match_records (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    batch_id TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    pattern_id TEXT,
                    pattern_name TEXT,
                    pattern_type TEXT,
                    algorithm_score DOUBLE PRECISION,
                    vision_score DOUBLE PRECISION,
                    final_score DOUBLE PRECISION,
                    accepted BOOLEAN,
                    model TEXT,
                    pattern_image TEXT,
                    chart_image TEXT,
                    vision_result JSONB,
                    extra JSONB
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_symbol ON vision_match_records(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_timeframe ON vision_match_records(timeframe)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_created_at ON vision_match_records(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_batch ON vision_match_records(batch_id)")
            conn.commit()
            VisionMatchRecorder._table_ready = True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[WARN] 视觉匹配表初始化失败: {e}", file=sys.stderr)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.return_connection(conn)

    def record_match(self, record: Dict[str, Any]) -> bool:
        """写入一条视觉匹配记录"""
        if not self.enabled:
            return False
        self._ensure_table()
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            payload = {
                "created_at": record.get("created_at") or datetime.now(),
                "source": record.get("source"),
                "batch_id": record.get("batch_id"),
                "symbol": record.get("symbol"),
                "timeframe": record.get("timeframe"),
                "pattern_id": record.get("pattern_id"),
                "pattern_name": record.get("pattern_name"),
                "pattern_type": record.get("pattern_type"),
                "algorithm_score": record.get("algorithm_score"),
                "vision_score": record.get("vision_score"),
                "final_score": record.get("final_score"),
                "accepted": record.get("accepted"),
                "model": record.get("model"),
                "pattern_image": record.get("pattern_image"),
                "chart_image": record.get("chart_image"),
                "vision_result": json.dumps(record.get("vision_result") or {}, ensure_ascii=False),
                "extra": json.dumps(record.get("extra") or {}, ensure_ascii=False),
            }
            cursor.execute(
                """
                INSERT INTO vision_match_records (
                    created_at, source, batch_id, symbol, timeframe,
                    pattern_id, pattern_name, pattern_type,
                    algorithm_score, vision_score, final_score, accepted,
                    model, pattern_image, chart_image, vision_result, extra
                ) VALUES (
                    %(created_at)s, %(source)s, %(batch_id)s, %(symbol)s, %(timeframe)s,
                    %(pattern_id)s, %(pattern_name)s, %(pattern_type)s,
                    %(algorithm_score)s, %(vision_score)s, %(final_score)s, %(accepted)s,
                    %(model)s, %(pattern_image)s, %(chart_image)s, %(vision_result)s, %(extra)s
                )
                """,
                payload,
            )
            conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[WARN] 视觉匹配记录写入失败: {e}", file=sys.stderr)
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.return_connection(conn)

    def fetch_cached(self, cache_key: str, pattern_id: str) -> Optional[Dict[str, Any]]:
        """按cache_key + pattern_id读取最近一次视觉匹配结果"""
        if not self.enabled or not cache_key or not pattern_id:
            return None
        self._ensure_table()
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT vision_score, vision_result, final_score, model, created_at
                FROM vision_match_records
                WHERE pattern_id = %s
                  AND extra->>'cache_key' = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(pattern_id), cache_key),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if isinstance(row, dict):
                vision_result = row.get("vision_result")
                if isinstance(vision_result, str):
                    try:
                        vision_result = json.loads(vision_result)
                    except Exception:
                        vision_result = {}
                return {
                    "vision_score": row.get("vision_score"),
                    "vision_result": vision_result or {},
                    "final_score": row.get("final_score"),
                    "model": row.get("model"),
                    "created_at": row.get("created_at"),
                }
            # Tuple fallback
            vision_score, vision_result, final_score, model, created_at = row
            if isinstance(vision_result, str):
                try:
                    vision_result = json.loads(vision_result)
                except Exception:
                    vision_result = {}
            return {
                "vision_score": vision_score,
                "vision_result": vision_result or {},
                "final_score": final_score,
                "model": model,
                "created_at": created_at,
            }
        except Exception as e:
            print(f"[WARN] 读取视觉缓存失败: {e}", file=sys.stderr)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.return_connection(conn)
