from pathlib import Path
import sys
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from db_manager_trader import TraderDBManager

def main():
    db = TraderDBManager('de')
    # De. 做空 90k-90.2k，SL 90588，已止损
    ts = '2026-01-04 10:44:00'
    symbol = 'BTC/USDT'
    direction = 'short'
    entry_price = 90100.0  # 区间中点
    exit_price = 90588.0   # 止损被打
    text = 'De. 挂单区间 90000–90200；止损 90588；该单已止损。截图: IMG_1908.jpg'
    shot = r'C:\\Users\\zuoho\\Pictures\\IMG_1908.jpg'
    tid = db.add_trade_record(timestamp=ts, symbol=symbol, direction=direction,
        leverage=None, entry_price=entry_price, exit_price=exit_price,
        profit_pct=None, profit_usdt=None, strategy='bracket_short',
        screenshot_path=shot, text_content=text, source='manual')
    # 回填评估规则与点距
    con = db._get_connection()
    con.execute("UPDATE trade_records SET stop_distance_points=?, tp_rule=?, stop_rule=?, timeframe=? WHERE id=?",
        [488.0, '1R_take_profit', 'break_even_after_1R', '15m', tid])
    con.commit()
    db.close()
    print('added trade', tid)

if __name__ == '__main__':
    main()
