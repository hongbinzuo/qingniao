#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移: 将交易信号价格字段精度提升到 NUMERIC(20,9)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore


def main() -> int:
    db = TraderDBManager("abu")
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            ALTER TABLE trading_signals
                ALTER COLUMN entry_price TYPE NUMERIC(20,9) USING entry_price::NUMERIC(20,9),
                ALTER COLUMN stop_loss TYPE NUMERIC(20,9) USING stop_loss::NUMERIC(20,9),
                ALTER COLUMN take_profit_1 TYPE NUMERIC(20,9) USING take_profit_1::NUMERIC(20,9),
                ALTER COLUMN take_profit_2 TYPE NUMERIC(20,9) USING take_profit_2::NUMERIC(20,9),
                ALTER COLUMN exit_price TYPE NUMERIC(20,9) USING exit_price::NUMERIC(20,9),
                ALTER COLUMN entry_price_actual TYPE NUMERIC(20,9) USING entry_price_actual::NUMERIC(20,9)
            """
        )
        cursor.execute(
            """
            ALTER TABLE signal_evaluations
                ALTER COLUMN actual_entry_price TYPE NUMERIC(20,9) USING actual_entry_price::NUMERIC(20,9),
                ALTER COLUMN actual_exit_price TYPE NUMERIC(20,9) USING actual_exit_price::NUMERIC(20,9)
            """
        )
        conn.commit()
        print("OK: precision updated to NUMERIC(20,9)")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        cursor.close()
        db.return_connection(conn)


if __name__ == "__main__":
    raise SystemExit(main())
