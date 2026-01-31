#!/bin/bash
cd /c/Users/zuoho/code/qingniao
echo "======================================"
echo "Moonshot Vision Batch Processing"
echo "Images: 601-1000 (400 images)"
echo "Model: kimi-k2.5"
echo "======================================"
echo ""
python scripts/batch_process_601_1000.py
echo ""
echo "======================================"
echo "Batch processing complete!"
echo "======================================"
