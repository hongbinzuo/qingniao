#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath('src'))

try:
    from abu.gemini_vision_analyzer import GeminiVisionAnalyzer
    print("Successfully imported GeminiVisionAnalyzer")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    try:
        # Initialize analyzer
        # It will automatically look for .env and OPENROUTER_API_KEY
        analyzer = GeminiVisionAnalyzer(
            images_dir=Path('data/abu/images'),
            output_file=Path('outputs/abu_gemini_annotations_enhanced.jsonl'),
            state_file=Path('outputs/abu_gemini_analysis_state.json')
        )
        
        print("Analyzer initialized successfully")
        
        # Test with just 1 image to verify API connection
        print("Starting test analysis of 1 image...")
        analyzer.analyze_all(limit=1, resume=False) # force start new for test
        
        print("Test complete!")
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your .env file has OPENROUTER_API_KEY")
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == "__main__":
    main()
