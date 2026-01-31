import json

# Read existing data
with open('temp_import_931_940.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Remaining 3 records
remaining = [
  {
    "image_id": "page_0938_img_01_clip.jpg",
    "page": 938,
    "slide_type": "chart",
    "slide_title": "Exhaustive Sell Climax: Expect Reversal Up",
    "layout_type": "single_chart",
    "instructional_focus": "reversal",
    "timeframe_hint": "5m",
    "market": "unknown",
    "chart": {
      "market_cycle": "climactic",
      "trend_maturity": "climactic",
      "direction_bias": "long",
      "ema_20": {
        "exists": True,
        "relation": "crossing",
        "slope": "down",
        "confidence": 0.9
      }
    },
    "patterns": [
      {
        "pattern_family": "wedge",
        "pattern_type": "wedge",
        "pattern_name": "Parabolic Wedge Sell Climax",
        "direction_bias": "long",
        "status": "confirmed",
        "confidence": 0.9,
        "evidence": [
          "3 legs down in Tight Bear Channel",
          "Each leg getting bigger",
          "Final leg was huge"
        ],
        "raw": None
      },
      {
        "pattern_family": "reversal",
        "pattern_type": "reversal",
        "pattern_name": "Climactic Reversal",
        "direction_bias": "long",
        "status": "confirmed",
        "confidence": 0.85,
        "evidence": [
          "Exhaustive Sell Climax",
          "Should attract profit taking"
        ],
        "raw": None
      }
    ],
    "targets_probabilities": [
      {
        "target": "One more brief leg down",
        "probability": 0.6
      },
      {
        "target": "Reversal up",
        "probability": 0.6
      }
    ],
    "text_logic": {
      "bull_logic": [
        "Exhaustive Sell Climax so 60% chance of reversal up either here or after one more brief leg down",
        "Should attract profit taking and lead to a couple legs sideways to up"
      ],
      "bear_logic": [
        "Bear Surprise so 60% chance of one more brief leg down",
        "Biggest bear breakout late in bear trend"
      ]
    },
    "summary": "Analyzes an Exhaustive Sell Climax characterized by a Parabolic Wedge. While the strong breakout implies a 60% chance of one more leg down, the climax nature implies a 60% chance of a reversal up shortly.",
    "quality": {
      "ocr_quality": "good",
      "chart_visibility": "full",
      "notes": None
    }
  }
]

data.extend(remaining)
print(f"Total records: {len(data)}")

with open('temp_import_931_940.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
