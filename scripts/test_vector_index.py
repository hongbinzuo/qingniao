#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试向量索引"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import annoy
    print("Annoy: OK")
except ImportError:
    print("Annoy: NOT INSTALLED (pip install annoy)")

try:
    import numpy
    print("NumPy: OK")
except ImportError:
    print("NumPy: NOT INSTALLED (pip install numpy)")
