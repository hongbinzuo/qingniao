# Gemini Setup (Vision)

Purpose
- Use Google's Gemini (multimodal) to analyze chart images extracted from PDFs and return structured JSON for downstream ranking/learning.

Prereqs
- Get an API key at https://aistudio.google.com/app/apikey
- Keep the key out of Git. Use environment variables or a local .env

Install (Windows PowerShell)
```
py -3 -m pip install -U pip
py -3 -m pip install google-generativeai pillow python-dotenv
```

Install (Linux/macOS)
```
python3 -m pip install -U pip
python3 -m pip install google-generativeai pillow python-dotenv
```

Configure
- Environment
  - PowerShell:
    ```
    $env:GEMINI_API_KEY = "<your-key>"
    $env:GEMINI_MODEL = "gemini-1.5-pro"   # or gemini-1.5-flash
    ```
  - CMD:
    ```
    set GEMINI_API_KEY=<your-key>
    set GEMINI_MODEL=gemini-1.5-pro
    ```
  - Bash:
    ```
    export GEMINI_API_KEY=<your-key>
    export GEMINI_MODEL=gemini-1.5-pro
    ```

Quick Test
```
py -3 - << 'PY'
import os
import google.generativeai as genai
from PIL import Image

key = os.environ.get('GEMINI_API_KEY')
assert key, 'GEMINI_API_KEY not set'
model = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')

genai.configure(api_key=key)
m = genai.GenerativeModel(model)
print('OK: model ready:', model)
PY
```

How We Use It
- Image extraction is in `scripts/pa_ingest_pdf.py` (writes to `data/abu/images/` and `data/abu/raw_pages.jsonl`).
- Call `scripts/abu_gemini_annotate.py` to annotate those images with Gemini and write JSONL to `outputs/abu_gemini_annotations.jsonl`.

Run Annotation (example)
```
py -3 scripts\abu_gemini_annotate.py --limit 50 --model gemini-1.5-pro
# or include context from surrounding pages (default window=2)
py -3 scripts\abu_gemini_annotate.py --limit 50 --context-window 2 --model gemini-1.5-pro
```

Model Choice
- `gemini-1.5-pro`: stronger reasoning; recommended for accuracy
- `gemini-1.5-flash`: faster/cheaper; optional for bulk annotation

Notes
- Rate limits and billing apply; add `--sleep-ms` to pace requests if needed
- Cache is used under `outputs/.cache/abu_gemini/` to avoid re-annotating the same image
- Never commit API keys; `.env` is ignored by Git
