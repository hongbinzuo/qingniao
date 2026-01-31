# Advanced PA Scanner - Design Decisions

## English Version

### Overview
This document outlines the key design decisions made for the Advanced PA Scanner system, which enables continuous local scanning for trading signals across multiple timeframes and signal quality modes.

---

## 1. Deployment Strategy

**Decision**: Local execution instead of cloud deployment (Railway + Neon)

**Rationale**:
- Greater control over execution environment
- No deployment complexity or costs
- Easier debugging and monitoring
- Immediate access to logs and signals
- No dependency on external services

**Implementation**:
- Python scripts run locally on Windows
- Batch files for easy execution
- Local PostgreSQL database for signal storage
- Local file system for audit reports

---

## 2. Multi-Timeframe Scanning

**Decision**: Scan 5m, 15m, and 1h timeframes simultaneously

**Rationale**:
- Captures opportunities across different trading styles
- 5m: Quick scalps and counter-trend opportunities
- 15m: Balanced swing trades
- 1h: Longer-term position trades
- Provides comprehensive market coverage

**Implementation**:
- Sequential scanning of all three timeframes in each cycle
- Each timeframe uses appropriate context filters
- Results stored with timeframe metadata

---

## 3. Coin Selection

**Decision**: Top 20 coins by market capitalization

**Rationale**:
- Market cap indicates liquidity and stability
- Reduces risk of low-volume manipulation
- Focuses on established cryptocurrencies
- Manageable number for continuous monitoring

**Implementation**:
- Uses `--rank-by marketcap` parameter
- Queries CoinCap API for rankings
- Configurable via `--top` parameter

---

## 4. Signal Quality Modes

**Decision**: Three distinct signal modes (Aggressive, Neutral, Conservative)

**Rationale**:
- Different traders have different risk tolerances
- Allows comparison of signal quality vs. quantity
- Enables optimization based on results
- Provides flexibility for different market conditions

**Mode Specifications**:

### Aggressive Mode
- Min Score: 0.5
- Min Vector Match: 0.6 (60%)
- Context Filter: Off
- Use Case: More signals, active trading

### Neutral Mode (Recommended)
- Min Score: 0.65
- Min Vector Match: 0.7 (70%)
- Context Filter: Brooks patterns
- Use Case: Balanced approach

### Conservative Mode
- Min Score: 0.75
- Min Vector Match: 0.8 (80%)
- Context Filter: Brooks + Regime36
- Use Case: High-quality signals only

---

## 5. Vector Match Filtering

**Decision**: Exclude low-probability vector matches

**Rationale**:
- Vector matching provides pattern similarity scores
- Low scores indicate weak pattern alignment
- Filtering improves signal quality
- Reduces false positives

**Implementation**:
- Minimum thresholds vary by mode (60%, 70%, 80%)
- Applied during pattern matching phase
- Documented in signal metadata

---

## 6. Trend Following Rules

**Decision**: 5m allows counter-trend, 15m and 1h follow trend only

**Rationale**:
- 5m timeframe: Fast moves can profit from counter-trend
- 15m/1h timeframes: Trend following is more reliable
- Reduces risk on longer timeframes
- Aligns with Brooks PA principles

**Implementation**:
- `allow_counter_trend` flag set per timeframe
- Context filters enforce trend alignment
- Logged in scan output

---

## 7. Audit Reports

**Decision**: Generate audit reports every 4 hours

**Rationale**:
- Regular performance tracking
- Identifies pattern effectiveness
- Enables continuous improvement
- Provides accountability

**Implementation**:
- Automated generation via `--audit-interval`
- Saved as timestamped text files under `outputs/audit_reports/`
- Includes win/loss statistics and per-timeframe breakdown

---

## 8. Scan Interval

**Decision**: Default 15-minute scan interval

**Rationale**:
- Balances freshness with API rate limits
- Allows time for pattern development
- Reduces computational load
- Configurable for different needs

**Implementation**:
- Configurable via `--interval` parameter
- Sleep between scan cycles
- Logged with timestamps

---

## 9. Database Storage

**Decision**: Local PostgreSQL database

**Rationale**:
- Strong relational integrity
- High precision numeric types (DECIMAL)
- Better concurrency for continuous scans
- Compatible with future cloud migration

**Implementation**:
- Database: PostgreSQL (configured via `PG_*` env vars)
- Table: `trading_signals`
- Includes all signal metadata

---

## 10. User Interface

**Decision**: Batch files + command-line interface

**Rationale**:
- Simple for Windows users
- No GUI complexity
- Easy to customize
- Scriptable and automatable

**Implementation**:
- `.bat` files for common scenarios
- Python CLI with argparse
- Comprehensive logging to console and file

---

## Summary of Key Benefits

1. **Flexibility**: Multiple modes and timeframes
2. **Control**: Local execution and storage
3. **Quality**: Vector filtering and trend rules
4. **Accountability**: Regular audit reports
5. **Simplicity**: Easy-to-use batch files
6. **Scalability**: Configurable parameters

---

