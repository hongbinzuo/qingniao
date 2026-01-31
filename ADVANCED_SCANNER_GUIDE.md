# Advanced PA Scanner Guide

## Overview

The Advanced PA Scanner implements all your requirements:

1. ✅ **Multi-timeframe scanning**: 5m, 15m, 1h
2. ✅ **Top 20 coins by market cap** (CoinCap ranking)
3. ✅ **Audit reports every 4 hours** (saved locally)
4. ✅ **Three signal modes**: Aggressive, Neutral, Conservative
5. ✅ **Vector match filtering**: Excludes low probability matches
6. ✅ **Trend following**: 5m allows counter-trend, others follow trend

## Quick Start

### Option 1: All Signal Modes (Recommended for Comparison)
Double-click: `scripts/abu/run_advanced_scan_all.bat`

This runs all three signal modes simultaneously to compare results.

### Option 2: Neutral Mode (Recommended for Most Users)
Double-click: `scripts/abu/run_advanced_scan_neutral.bat`

Balanced approach with good signal quality.

### Option 3: Conservative Mode (High Quality Only)
Double-click: `scripts/abu/run_advanced_scan_conservative.bat`

Fewer signals, but higher confidence.

### Option 4: Aggressive Mode (More Signals)
Double-click: `scripts/abu/run_advanced_scan_aggressive.bat`

More signals, lower threshold for entry.

## Signal Modes Explained

### Aggressive Mode
- **Min Score**: 0.5
- **Min Vector Match**: 0.6 (60%)
- **Context Filter**: Off
- **Best for**: Finding more opportunities, active trading
- **Trade-off**: More signals but lower quality

### Neutral Mode (Recommended)
- **Min Score**: 0.65
- **Min Vector Match**: 0.7 (70%)
- **Context Filter**: Brooks patterns
- **Best for**: Balanced trading, most users
- **Trade-off**: Good balance of quantity and quality

### Conservative Mode
- **Min Score**: 0.75
- **Min Vector Match**: 0.8 (80%)
- **Context Filter**: Brooks + Regime36
- **Best for**: High confidence trades only
- **Trade-off**: Fewer signals but higher quality

## Timeframe Rules

### 5m Timeframe
- **Counter-trend allowed**: Yes
- **Use case**: Quick scalps, can trade against trend
- **Risk**: Higher, requires active monitoring

### 15m Timeframe
- **Counter-trend allowed**: No (trend following only)
- **Use case**: Swing trades, follow the trend
- **Risk**: Moderate

### 1h Timeframe
- **Counter-trend allowed**: No (trend following only)
- **Use case**: Position trades, strong trend following
- **Risk**: Lower, more reliable signals

## Audit Reports

Audit reports are automatically generated every 4 hours and saved locally.

**Report location**: `outputs/audit_reports/performance_report_YYYYMMDD_HHMMSS.txt`

**What's included**:
- Signal performance analysis (TP/SL hits)
- Win/loss statistics
- Per-timeframe breakdown

## Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--top` | Number of top coins by market cap | 20 |
| `--interval` | Minutes between scan cycles | 15 |
| `--duration` | Total duration in minutes | 360 (6 hours) |
| `--mode` | Signal mode (aggressive/neutral/conservative/all) | all |
| `--audit-interval` | Minutes between audit reports | 240 (4 hours) |

## Custom Usage Examples

### Example 1: 12-hour session with all modes
```bash
python scripts\advanced_continuous_scan.py --duration 720 --mode all
```

### Example 2: Conservative mode, 30 coins, 8 hours
```bash
python scripts\advanced_continuous_scan.py --top 30 --mode conservative --duration 480
```

### Example 3: Aggressive mode, scan every 10 minutes
```bash
python scripts\advanced_continuous_scan.py --mode aggressive --interval 10 --duration 360
```

## Monitoring & Logs

### Real-time Console Output
The scanner displays:
- Current scan cycle number
- Signal mode being executed
- Timeframe scan results
- Audit report generation status

### Log File
All activity logged to: `logs/advanced_scan.log`

View recent activity:
```bash
powershell -command "Get-Content advanced_scan.log -Tail 100"
```

## Database & Signal Storage

All signals are stored in PostgreSQL: `trading_signals` table (via `PG_*` env vars)

View signals using:
```bash
python scripts\view_recent_signals.py --hours 24
```

Filter by timeframe:
```bash
python scripts\view_recent_signals.py --hours 12 --timeframe 15m
```

## Files Created

- `scripts/advanced_continuous_scan.py` - Main advanced scanner
- `scripts/abu/run_advanced_scan_all.bat` - Run all modes
- `scripts/abu/run_advanced_scan_neutral.bat` - Neutral mode only
- `scripts/abu/run_advanced_scan_conservative.bat` - Conservative mode only
- `scripts/abu/run_advanced_scan_aggressive.bat` - Aggressive mode only
- `advanced_scan.log` - Activity log
- `audit_report_*.txt` - Audit reports (generated every 4 hours)

---

**Ready to start?** Double-click `scripts/abu/run_advanced_scan_all.bat` to compare all three signal modes!

