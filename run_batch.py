#!/usr/bin/env python3
import sys
import os
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath('src'))

try:
    from abu.gemini_vision_analyzer import GeminiVisionAnalyzer
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    print("Starting smart batch analysis...")
    
    analyzer = GeminiVisionAnalyzer(
        images_dir=Path('data/abu/images'),
        output_file=Path('outputs/abu_gemini_annotations_enhanced.jsonl'),
        state_file=Path('outputs/abu_gemini_analysis_state.json'),
        sleep_ms=2000
    )
    
    # 1. First, ensure full state is initialized with ALL images
    # We do this by calling analyze_all with limit=1 just to trigger initialization
    # if state doesn't exist.
    if not analyzer.state_file.exists():
        print("Initializing full state...")
        # Hack: calling with limit=None first to initialize full list, 
        # but we want to return immediately.
        # Since analyze_all doesn't have a dry_run flag, we'll implement a custom logic here.
        # But wait, analyzer.analyze_all() collects images first.
        
        # Let's just let it run fully but catch specific count.
        pass

    # Actually, the logic in analyze_all(limit=N) restricts the image_paths list BEFORE initialization.
    # We need to manually initialize state if it's missing.
    
    if not analyzer.state_file.exists():
        # Initialize full state manually
        print("Creating new full state file...")
        image_paths = sorted(list(analyzer.images_dir.glob('*.png')) + list(analyzer.images_dir.glob('*.jpg')))
        image_paths = [p for p in image_paths if p.is_file()]
        state = analyzer._initialize_analysis_state(image_paths)
        analyzer._save_analysis_state(state)
        print(f"State initialized with {len(image_paths)} images.")

    # 2. Now run with resume=True, it will load the FULL state
    # and we can implement a custom batch loop here to control limit
    
    print("Loading state...")
    state = analyzer._load_analysis_state()
    pending = analyzer.AnalysisState(
        **{k:v for k,v in asdict(state).items() if k != 'get_pending_images'}
    ).get_pending_images if hasattr(state, 'get_pending_images') else state.get_pending_images()
    
    # Wait, state object from _load_analysis_state is a dataclass instance
    pending_images = [img['image_path'] for img in state.images 
                     if img['status'] in ['pending', 'failed'] and img['retry_count'] < analyzer.max_retries]
    
    print(f"Pending images: {len(pending_images)}")
    
    if not pending_images:
        print("All done!")
        return

    # 3. Take next 50
    batch_size = 50
    target_images = pending_images[:batch_size]
    print(f"Processing batch of {len(target_images)} images...")
    
    count = 0
    total_cost = 0
    
    for img_path_str in target_images:
        img_path = Path(img_path_str)
        result = analyzer.analyze_single_image(img_path)
        
        # Update state
        cost = result.get('estimated_cost_usd', 0)
        total_cost += cost
        count += 1
        
        # Update specific image state
        for img in state.images:
            if img['image_path'] == img_path_str:
                if 'error' in result.get('result', {}):
                    img['status'] = 'failed'
                    img['error_message'] = str(result['result'].get('error'))
                    img['retry_count'] += 1
                else:
                    img['status'] = 'completed' if not result.get('cached') else 'skipped'
                    img['processed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                break
        
        # Save output if not cached/skipped
        if not result.get('cached') and result.get('status') != 'skipped':
            try:
                with analyzer.output_file.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"Error saving output: {e}")

        # Save state every 5 images
        if count % 5 == 0:
            analyzer._save_analysis_state(state)
            
        time.sleep(analyzer.sleep_ms / 1000)

    # Final save
    analyzer._save_analysis_state(state)
    print(f"\nBatch finished. Processed: {count}, Cost: ${total_cost:.4f}")

if __name__ == "__main__":
    from dataclasses import asdict
    main()
