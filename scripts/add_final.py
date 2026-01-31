import json

with open('temp_import_931_940.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

final_records = [
  {
    "image_id": "page_0939_img_01_clip.jpg",
    "page": 939,
    "slide_type": "chart",
    "slide_title": "Bear Channel: Bear BO",
    "layout_type": "single_chart",
    "instructional_focus": "trap",
    "timeframe_hint": "5m",
    "market": "unknown",
    "chart": {
      "market_cycle": "trend",
      "trend_maturity": "middle",
      "direction_bias": "short",
      "ema_20": {
        "exists": True,
        "relation": "above",
        "slope": "down",
        "confidence": 0.95
      }
    },
    "patterns": [
      {
        "pattern_family": "trap",
        "pattern_type": "trap",
        "pattern_name": "Bull Trap",
        "direction_bias": "short",
        "status": "confirmed",
        "confidence": 0.9,
        "evidence": [
          "Bull trap at EMA",
          "Lower High Double Top bear flag at EMA"
        ],
        "raw": None
      },
      {
        "pattern_family": "gap",
        "pattern_type": "gap",
        "pattern_name": "Bear Measuring Gap",
        "direction_bias": "short",
        "status": "confirmed",
        "confidence": 0.85,
        "evidence": [
          "Became Measuring Gap",
          "Consecutive big bear bars closing near their lows"
        ],
        "raw": None
      }
    ],
    "text_logic": {
      "bull_logic": [
        "S Climax (Sell Climax)",
        "Bull bar closing near its H",
        "Expect 2 legs sideways or up"
      ],
      "bear_logic": [
        "Bull trap at EMA",
        "2nd leg up from Sell Climax was sideways, not up",
        "Bear Surprise",
        "Expect at least a 2nd leg down",
        "Instead of reversal up from LL MTR, now accelerating down"
      ]
    },
    "summary": "Highlights a Bull Trap at the EMA which converts a potential reversal into a continuation of the bear trend. The subsequent Bear Breakout becomes a Measuring Gap, signaling acceleration down.",
    "quality": {
      "ocr_quality": "good",
      "chart_visibility": "full",
      "notes": None
    }
  },
  {
    "image_id": "page_0940_img_01_clip.jpg",
    "page": 940,
    "slide_type": "chart",
    "slide_title": "Bear Leg in TR: Bear BO",
    "layout_type": "single_chart",
    "instructional_focus": "market_cycle_theory",
    "timeframe_hint": "5m",
    "market": "unknown",
    "chart": {
      "market_cycle": "trading_range",
      "trend_maturity": "late",
      "direction_bias": "neutral",
      "ema_20": {
        "exists": True,
        "relation": "above",
        "slope": "down",
        "confidence": 0.9
      }
    },
    "patterns": [
      {
        "pattern_family": "trend",
        "pattern_type": "trend",
        "pattern_name": "Small Pullback Bear Trend",
        "direction_bias": "short",
        "status": "confirmed",
        "confidence": 0.9,
        "evidence": [
          "Endless PB from strong rally on open",
          "Became Small PB Bear Trend"
        ],
        "raw": None
      },
      {
        "pattern_family": "breakout",
        "pattern_type": "breakout",
        "pattern_name": "Exhaustion Gap",
        "direction_bias": "long",
        "status": "suspected",
        "confidence": 0.8,
        "evidence": [
          "Biggest BO late in bear trend",
          "Often is exhaustive end of bear trend"
        ],
        "raw": None
      }
    ],
    "text_logic": {
      "bull_logic": [
        "Lots of TR price action and strong rally on open so odds favor at least small rally before end of day",
        "Expect at least 10 bars and 2 legs up to relieve exhaustion"
      ],
      "bear_logic": [
        "Always In Short",
        "Consecutive bear bars closing near their lows",
        "Bears want at least small 2nd leg down likely after Surprise Bear BO"
      ]
    },
    "summary": "Discusses a Bear Leg within a Trading Range context. A late, large Bear Breakout is identified as likely Exhaustion, suggesting a reversal or relief rally rather than a new trend leg.",
    "quality": {
      "ocr_quality": "good",
      "chart_visibility": "full",
      "notes": None
    }
  }
]

data.extend(final_records)
print(f"Total records: {len(data)}")

with open('temp_import_931_940.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    
print("Complete! Pages 931-940 ready for import.")
