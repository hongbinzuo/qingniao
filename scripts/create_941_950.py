import json

# Read the input JSON from stdin and save to file
input_json = """[
  {
    "image_id": "page_0941_img_01_clip.jpg",
    "page": 941,
    "slide_type": "chart",
    "slide_title": "Tight Bear Channel: Bear Breakout often Leads to MM Down",
    "layout_type": "single_chart",
    "instructional_focus": "market_cycle_theory",
    "timeframe_hint": null,
    "market": null,
    "chart": {
      "market_cycle": "tight_channel",
      "trend_maturity": "middle",
      "direction_bias": "short",
      "ema_20": {
        "exists": true,
        "relation": "above",
        "slope": "down",
        "confidence": 0.95
      }
    },
    "patterns": [
      {
        "pattern_family": "channel",
        "pattern_type": "channel",
        "pattern_name": "Tight Bear Channel",
        "direction_bias": "short",
        "status": "confirmed",
        "confidence": 0.95,
        "evidence": [
          "Tight price action within channel lines",
          "Persistent downward movement"
        ],
        "raw": null
      },
      {
        "pattern_family": "breakout",
        "pattern_type": "breakout",
        "pattern_name": "Bear Breakout",
        "direction_bias": "short",
        "status": "confirmed",
        "confidence": 0.9,
        "evidence": [
          "Bear BO below bear channel annotation"
        ],
        "raw": null
      }
    ],
    "bar_by_bar": {
      "body_gap": null,
      "overlap_level": "medium",
      "follow_through": "strong",
      "setup_signal_entry": "setup",
      "confidence": 0.8
    },
    "counting": {
      "leg_count": null,
      "hl_count": null,
      "bar_number": null,
      "confidence": 0.0
    },
    "kline_features": [],
    "key_levels": {
      "support": [],
      "resistance": [],
      "confidence": 0.0
    },
    "targets_probabilities": [
      {
        "target": "Trend down continue",
        "probability": 0.0
      }
    ],
    "text_logic": {
      "bull_logic": [],
      "bear_logic": [
        "Bear BO below bear channel",
        "Expect all wedge bottoms to fail and for trend down to continue"
      ]
    },
    "confirmations": [
      "Small Pullback Bear Trends form many wedge bottoms"
    ],
    "invalidations": [],
    "annotations_text": [
      "Bear BO below bear channel",
      "Small Pullback Bear Trends form many wedge bottoms",
      "Expect all to fail and for trend down to continue"
    ],
    "summary": "Chart illustrating a tight bear channel where bear breakouts often lead to a measured move down, and small pullback bear trends cause wedge bottoms to fail.",
    "quality": {
      "ocr_quality": "good",
      "chart_visibility": "full",
      "notes": null
    },
    "raw": null
  }
]"""

data = json.loads(input_json)
print(f"Loaded {len(data)} records")

with open('temp_import_941_950.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Saved to temp_import_941_950.json")
