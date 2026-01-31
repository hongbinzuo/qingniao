#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight chart recognizer for Abu images (no cloud services).

Goals
- Locate likely chart region (ROI) inside the image
- Extract simple features: grid/axes lines, trendlines, candlestick-like bar density
- Optional OCR of annotations if pytesseract is available
- Emit JSON for downstream ranking/learning

This is heuristic; it prefers robustness over perfect accuracy and never crashes the batch.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional


def _convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型，用于JSON序列化"""
    import numpy as np
    if isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


def _try_imports():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as e:  # pragma: no cover
        print('ERROR: opencv-python and numpy required. Install with: pip install opencv-python numpy', file=sys.stderr)
        raise
    try:
        import pytesseract  # type: ignore
    except Exception:
        pytesseract = None  # type: ignore
    return cv2, np, pytesseract


def _load_image(cv2, path: str):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f'cannot read image: {path}')
    return img


def _detect_roi(cv2, np, img, debug: Optional[Path] = None) -> Tuple[Tuple[int, int, int, int], Dict[str, Any]]:
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    # Prefer long horizontal/vertical segments
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=int(min(w, h) * 0.3), maxLineGap=10)
    xs, ys = [], []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0, :]:
            # Keep near horizontal/vertical
            if abs(y1 - y2) < 5 or abs(x1 - x2) < 5:
                xs += [x1, x2]
                ys += [y1, y2]
    # Fallback to contours if lines poor
    if xs and ys:
        x0, x1 = max(0, min(xs)), min(w - 1, max(xs))
        y0, y1 = max(0, min(ys)), min(h - 1, max(ys))
    else:
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 31, 5)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        close = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=2)
        cnts, _ = cv2.findContours(close, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return (0, 0, w, h), {'roi_method': 'full', 'lines': 0}
        # pick largest rectangular-ish contour
        best = max(cnts, key=cv2.contourArea)
        x, y, ww, hh = cv2.boundingRect(best)
        x0, y0, x1, y1 = x, y, x + ww, y + hh
    # Expand a bit inward margins
    pad_x = int((x1 - x0) * 0.02)
    pad_y = int((y1 - y0) * 0.02)
    x0 = max(0, x0 + pad_x)
    x1 = min(w, x1 - pad_x)
    y0 = max(0, y0 + pad_y)
    y1 = min(h, y1 - pad_y)
    if debug is not None:
        dbg = img.copy()
        cv2.rectangle(dbg, (x0, y0), (x1, y1), (0, 255, 0), 2)
        cv2.imwrite(str(debug), dbg)
    return (x0, y0, x1, y1), {'roi_method': 'lines' if lines is not None else 'contour', 'lines': 0 if lines is None else len(lines)}


def _candlestick_like_score(cv2, np, roi) -> Dict[str, Any]:
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    # Use Otsu to separate foreground
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Prefer dark-on-light
    if np.mean(bw) > 127:
        bw = 255 - bw
    # Vertical projection
    proj = (bw > 0).sum(axis=0)
    # Find dominant bar width (distance between local maxima)
    # Rough: count columns with significant ink
    ink_cols = (proj > (0.1 * bw.shape[0])).astype(np.uint8)
    # Estimate groups
    counts = []
    c = 0
    for v in ink_cols:
        if v:
            c += 1
        elif c:
            counts.append(c); c = 0
    if c:
        counts.append(c)
    dom = int(np.median(counts)) if counts else 0
    # Body/overall vertical ratio
    body_ratio = float((bw > 0).sum()) / float(bw.shape[0] * bw.shape[1])
    score = 0.0
    if dom and 1 <= dom <= 30:
        score += 0.5
    if 0.02 <= body_ratio <= 0.35:
        score += 0.5
    return {
        'dominant_bar_width': dom,
        'body_ratio': round(body_ratio, 4),
        'candlestick_like_score': round(score, 2)
    }


def _trendlines(cv2, np, roi) -> Dict[str, Any]:
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(g, 80, 200)
    lines = cv2.HoughLinesP(e, 1, np.pi / 180, threshold=60, minLineLength=max(20, roi.shape[1] // 8), maxLineGap=8)
    cnt = 0
    non_axis = 0
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0, :]:
            cnt += 1
            # count non-horizontal/vertical
            if abs(y1 - y2) > 5 and abs(x1 - x2) > 5:
                non_axis += 1
    return {'line_segments': cnt, 'trendline_like': non_axis}


def _ocr(pytesseract, roi) -> str:
    if pytesseract is None:
        return ''
    try:
        import cv2  # local import
        # 转换为灰度
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 图像增强：提高对比度
        # 使用CLAHE (Contrast Limited Adaptive Histogram Equalization) 提高对比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        g = clahe.apply(g)
        
        # 降噪处理
        g = cv2.bilateralFilter(g, 5, 50, 50)
        
        # 尝试OCR：优先使用英文（交易策略文字主要是英文）
        # 如果英文识别失败，fallback到中英文混合
        try:
            txt = pytesseract.image_to_string(g, lang='eng', config='--psm 6')
            # 如果英文识别结果为空或太短，尝试中英文混合
            if not txt or len(txt.strip()) < 3:
                txt = pytesseract.image_to_string(g, lang='chi_sim+eng', config='--psm 6')
        except Exception:
            # 如果指定语言包不存在，fallback到默认
            txt = pytesseract.image_to_string(g, config='--psm 6')
        
        return txt.strip()
    except Exception:
        return ''


def analyze(image_path: str, debug_out: Optional[str] = None) -> Dict[str, Any]:
    cv2, np, pytesseract = _try_imports()
    img = _load_image(cv2, image_path)
    dbg_path = Path(debug_out) if debug_out else None
    if dbg_path is not None:
        dbg_path.parent.mkdir(parents=True, exist_ok=True)
    roi_xyxy, meta = _detect_roi(cv2, np, img, debug=dbg_path)
    x0, y0, x1, y1 = roi_xyxy
    roi = img[y0:y1, x0:x1]
    feats = {
        'image': image_path,
        'roi': {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'w': x1 - x0, 'h': y1 - y0},
        'roi_meta': meta,
    }
    try:
        feats.update(_candlestick_like_score(cv2, np, roi))
    except Exception:
        feats.update({'dominant_bar_width': 0, 'body_ratio': 0.0, 'candlestick_like_score': 0.0})
    try:
        feats.update(_trendlines(cv2, np, roi))
    except Exception:
        feats.update({'line_segments': 0, 'trendline_like': 0})
    try:
        # OCR提取：对ROI区域和全图都进行OCR，合并结果
        ocr_roi = _ocr(pytesseract, roi)
        ocr_full = _ocr(pytesseract, img)
        
        # 合并OCR结果：优先使用更长的结果，如果两者都非空则合并去重
        ocr_texts = []
        if ocr_roi and len(ocr_roi.strip()) > 3:
            ocr_texts.append(ocr_roi.strip())
        if ocr_full and len(ocr_full.strip()) > 3:
            ocr_texts.append(ocr_full.strip())
        
        # 合并去重：保留更详细的结果
        if ocr_texts:
            # 如果ROI和全图结果相似，只保留一个
            if len(ocr_texts) == 2:
                roi_text = ocr_texts[0].lower()
                full_text = ocr_texts[1].lower()
                # 如果全图结果包含ROI结果，优先使用全图结果
                if roi_text in full_text or full_text in roi_text:
                    ocr_text = max(ocr_texts, key=len)
                else:
                    # 否则合并（用换行符分隔）
                    ocr_text = '\n'.join(ocr_texts)
            else:
                ocr_text = ocr_texts[0]
        else:
            ocr_text = ''
        
        feats['ocr_text'] = ocr_text
    except Exception:
        feats['ocr_text'] = ''
    # 转换所有numpy类型为Python原生类型，确保可以JSON序列化
    return _convert_numpy_types(feats)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Recognize chart features from an image (heuristic)')
    ap.add_argument('--image', required=True)
    ap.add_argument('--debug-out', default=None, help='Optional debug image path with ROI box')
    args = ap.parse_args()
    try:
        out = analyze(args.image, debug_out=args.debug_out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print('Failed:', e)
        sys.exit(1)

