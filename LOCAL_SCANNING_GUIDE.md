# Local Continuous PA Scanner Guide

## Quick Start

### Option 1: Run with Default Settings (Recommended)
Simply double-click: `scripts/abu/run_continuous_scan.bat`

**Default settings:**
- Timeframe: 15m
- Top coins: 20
- Duration: 3 hours (180 minutes)
- Scan interval: Every 15 minutes
- Exchange: Gate.io

### Option 2: Custom Settings
Open command prompt and run:

```bash
# Example: 5m timeframe, 30 coins, 6 hours, scan every 10 minutes
python scripts/continuous_scan.py --timeframe 5m --top 30 --interval 10 --duration 360

# Example: 1h timeframe, 10 coins, 12 hours, scan every 60 minutes
python scripts/continuous_scan.py --timeframe 1h --top 10 --interval 60 --duration 720
```

## View Generated Signals

### Quick View
Double-click: `scripts/abu/view_signals.bat`

This shows signals from the last 24 hours.

### Custom Signal Queries
```bash
# View last 6 hours
python scripts/view_recent_signals.py --hours 6

# View only 15m timeframe signals
python scripts/view_recent_signals.py --timeframe 15m

# View signals for specific symbol
python scripts/view_recent_signals.py --symbol BTCUSDT

# Combine filters
python scripts/view_recent_signals.py --hours 12 --timeframe 15m --limit 50
```

## Command Options

### Continuous Scanner Options

| Option | Description | Default |
|--------|-------------|---------|
| `--timeframe` | Timeframe to scan (5m, 15m, 1h) | 15m |
| `--top` | Number of top coins to scan | 20 |
| `--interval` | Minutes between scans | 15 |
| `--duration` | Total duration in minutes | 180 (3 hours) |
| `--exchange` | Exchange (gate, bybit, bitget, split) | gate |

### Signal Viewer Options

| Option | Description | Default |
|--------|-------------|---------|
| `--hours` | Show signals from last N hours | 24 |
| `--limit` | Maximum number of signals to show | 20 |
| `--timeframe` | Filter by timeframe (5m, 15m, 1h) | None (all) |
| `--symbol` | Filter by symbol (e.g., BTCUSDT) | None (all) |

## Recommended Scanning Strategies

### Strategy 1: Short-term Scalping (5m)
```bash
python scripts/continuous_scan.py --timeframe 5m --top 30 --interval 5 --duration 120
```
- Best for: Active trading, quick entries
- Scan every 5 minutes for 2 hours
- More signals, higher frequency

### Strategy 2: Balanced Swing Trading (15m) - RECOMMENDED
```bash
python scripts/continuous_scan.py --timeframe 15m --top 20 --interval 15 --duration 360
```
- Best for: Balanced approach, moderate frequency
- Scan every 15 minutes for 6 hours
- Good signal quality, manageable frequency

### Strategy 3: Position Trading (1h)
```bash
python scripts/continuous_scan.py --timeframe 1h --top 15 --interval 60 --duration 720
```
- Best for: Longer-term positions, lower frequency
- Scan every hour for 12 hours
- Higher quality signals, fewer entries

## Monitoring & Logs

### Real-time Monitoring
The scanner outputs progress to the console in real-time. You'll see:
- Scan start/completion messages
- Number of signals found
- Any errors or warnings

### Log Files
All scan activity is logged to: `continuous_scan.log`

View the log:
```bash
# View entire log
type continuous_scan.log

# View last 50 lines
powershell -command "Get-Content continuous_scan.log -Tail 50"
```

## Database Location

Signals are stored in: `src/data/qingniao.db` (SQLite database)

You can query the database directly using any SQLite tool or the provided `view_recent_signals.py` script.

## Tips & Best Practices

1. **Start with default settings** - Run `scripts/abu/run_continuous_scan.bat` first to test
2. **Monitor the first scan** - Watch the console output to ensure everything works
3. **Check signals regularly** - Use `scripts/abu/view_signals.bat` to see what's being generated
4. **Adjust based on results** - If too many/few signals, adjust `--top` or `--timeframe`
5. **Stop anytime** - Press `Ctrl+C` to stop the scanner gracefully

## Troubleshooting

### Scanner won't start
- Check that Python is installed: `python --version`
- Verify dependencies: `pip install -r requirements.txt`
- Check `.env` file exists with API keys

### No signals generated
- This is normal - not every scan finds signals
- Try increasing `--top` to scan more coins
- Check different timeframes (5m, 15m, 1h)

### Scanner times out
- Reduce `--top` to scan fewer coins
- Check internet connection
- Try different exchange with `--exchange`

## Files Created

- `scripts/continuous_scan.py` - Main continuous scanner
- `scripts/view_recent_signals.py` - Signal viewer
- `scripts/abu/run_continuous_scan.bat` - Quick start batch file
- `scripts/abu/view_signals.bat` - Quick signal viewer
- `continuous_scan.log` - Scan activity log

---

**Ready to start?** Double-click `scripts/abu/run_continuous_scan.bat` and let it run!
