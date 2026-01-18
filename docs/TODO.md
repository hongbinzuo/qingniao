# Project TODO (Persistent)

Purpose
- Long-lived backlog that survives sessions, branches, and machines.
- Ephemeral per-wake tasks live in `trading_signals/.todos/` via `scripts/prepare_sleep.py` and are executed with `scripts/wake_resume.py`.

Conventions
- Use markdown checkboxes and add a brief context.
- Prefix with a date for traceability: `YYYY-MM-DD`.
- Keep it concise; link to files or issues when needed.

Template
- [ ] YYYY-MM-DD scope: short description (owner?)

Inbox (today/next)
- [ ] 2026-01-08 Abu: First PDF sampling run (set `PDF_IN`, `PDF_PAGES=1000`; run `scripts\abu_upgrade_and_run.bat`); expect `data/abu/raw_pages.jsonl` and `config/abu_patterns.yaml`
- [ ] 2026-01-08 Abu: Tune detectors/ranker using `config/abu_patterns.yaml`; adjust scoring weights
- [ ] 2026-01-08 API/UI: Add `/api/abu/history` + multi-chart (ECharts), dynamic top symbols + stablecoin-filter config

In Progress
- [ ] 

Backlog
- [ ] 

Done (recent)
- [x] 2026-01-08 BE: Rename `sherlock_api` -> `qingniao_be_api` (`scripts/qingniao_be_api.py`); add `scripts/start_qingniao_be_api.bat`
- [x] 2026-01-08 DB: `trading_signals` add `symbol/score/notes` (`src/database_design_v2.py`); migration `scripts/migrate_abu_add_score.py`
- [x] 2026-01-08 Abu 15m: `scripts/pa_scan_15m_top10.py` writes `score/notes/symbol`; markdown `trading_signals/ABU_top*_15m_*.md`
- [x] 2026-01-08 UI: `web/abu/index.html` (dark chart + score bars + long/short pills); `/api/abu/status` includes `score` and `reason`, sorted by score
- [x] 2026-01-08 PDF chain: `scripts/pa_ingest_pdf.py` -> `data/abu/raw_pages.jsonl`; `scripts/abu_build_library.py` -> `config/abu_patterns.yaml`
- [x] 2026-01-08 One-click: `scripts/abu_upgrade_and_run.bat` (init/migrate -> optional PDF -> build library -> 15m scan -> start API :8090)

References
- Wake TODO flow (non-persistent): `scripts/prepare_sleep.py`, `scripts/wake_resume.py`
- Output dir (non-persistent): `trading_signals/.todos/`
