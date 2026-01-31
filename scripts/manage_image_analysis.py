#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manager script for Al Brooks Deep Vision Analysis.
Tracks progress and provides the next batch of images for the Agent to process.
"""
import os
import json
from pathlib import Path

# Config
IMAGE_DIR = Path('data/abu/images')
OUTPUT_DIR = Path('outputs/abu_deep_analysis/json')
BATCH_SIZE = 10

def get_status():
    """Check which images are done and which are pending."""
    if not IMAGE_DIR.exists():
        print(f"Error: Image directory {IMAGE_DIR} not found.")
        return [], []

    # All source images
    all_images = sorted([f.name for f in IMAGE_DIR.glob('*.png')])
    
    # Processed JSONs
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    processed_files = set([f.name.replace('.json', '.png') for f in OUTPUT_DIR.glob('*.json')])
    
    # Calculate pending
    pending_images = [img for img in all_images if img not in processed_files]
    
    return pending_images, processed_files

def main():
    pending, processed = get_status()
    
    print(f"=== Status Report ===")
    print(f"Total Images: {len(pending) + len(processed)}")
    print(f"Processed:    {len(processed)}")
    print(f"Pending:      {len(pending)}")
    print(f"Progress:     {len(processed) / (len(pending) + len(processed)) * 100:.1f}%")
    print(f"=====================")
    
    if not pending:
        print("All images processed! 🎉")
        return

    # Output next batch for the Agent
    next_batch = pending[:BATCH_SIZE]
    print(f"\nNext Batch to Process ({len(next_batch)} images):")
    print(json.dumps(next_batch, indent=2))
    
    print("\n[Instruction for Agent]")
    print(f"Please process these {len(next_batch)} images using 'read' tool.")
    print("For each image, generate a structured JSON analysis and save it to:")
    print(f"{OUTPUT_DIR}/<image_name>.json")

if __name__ == "__main__":
    main()
