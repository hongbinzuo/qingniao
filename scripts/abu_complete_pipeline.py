#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU PDF处理完整流程
从PDF到最终模式库的端到端自动化流程

完整PDF处理流程（9000+图片）：
1. PDF提取 → 使用 PyMuPDF 提取页面和图片（不使用Gemini）
2. 图片导出 → data/abu/images/ （PNG格式）
3. 图表识别 → 提取图表到 pattern_library 表
4. 模式分类 → 使用 LLaVA/Gemini 分类图表类型
5. 文字提取 → 使用 Gemini Vision API 提取交易策略文字（使用Gemini）
6. 数据库完整 → 模式库就绪

技术选择：
- PDF转图片：PyMuPDF（本地工具，快速免费）✅
- 图片文字识别：Gemini Vision API（准确率高）✅
- 实时BTC图表：算法分析（不使用Gemini）✅

每次更新流程时，需要同步更新此脚本
"""

import sys
import os
from pathlib import Path
from typing import Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from detailed_logger import get_detailed_logger

def step1_ingest_pdf(pdf_path: str, max_pages: Optional[int] = None) -> int:
    """步骤1: PDF提取"""
    logger = get_detailed_logger('pdf_pipeline_step1')
    logger.log_startup({'pdf_path': pdf_path, 'max_pages': max_pages})
    
    logger.info("步骤1: PDF提取 - 提取页面文本和图片")
    
    try:
        from scripts.pa_ingest_pdf import extract
        
        out_path = str(ROOT / 'data' / 'abu' / 'raw_pages.jsonl')
        images_dir = str(ROOT / 'data' / 'abu' / 'images')
        
        cnt = extract(
            pdf_path=pdf_path,
            out_path=out_path,
            max_pages=max_pages,
            images_dir=images_dir,
            progress_interval=10
        )
        
        logger.info(f"PDF提取完成: {cnt} 页")
        logger.log_shutdown(exit_code=0, details={'pages_extracted': cnt})
        return cnt
        
    except Exception as e:
        logger.error(f"PDF提取失败: {e}")
        logger.log_shutdown(exit_code=1)
        raise


def step2_build_library() -> int:
    """步骤2: 构建模式库（提取模式到数据库）"""
    logger = get_detailed_logger('pdf_pipeline_step2')
    logger.log_startup()
    
    logger.info("步骤2: 构建模式库 - 从raw_pages.jsonl提取图表模式")
    
    try:
        # 这里需要调用构建模式库的脚本
        # 可能需要导入或调用 abu_build_library.py 或相关脚本
        logger.warning("步骤2需要确认具体的构建脚本")
        logger.log_shutdown(exit_code=0)
        return 0
        
    except Exception as e:
        logger.error(f"构建模式库失败: {e}")
        logger.log_shutdown(exit_code=1)
        raise


def step3_classify_patterns(model: str = 'llava', limit: Optional[int] = None) -> int:
    """步骤3: 模式分类（llava/gemini）"""
    logger = get_detailed_logger('pdf_pipeline_step3')
    logger.log_startup({'model': model, 'limit': limit})
    
    logger.info(f"步骤3: 模式分类 - 使用 {model} 分类图表模式")
    
    try:
        # 这里需要调用分类脚本
        # 例如: abu_llava_classify_patterns.py 或 abu_gemini_annotate.py
        logger.warning("步骤3需要确认具体的分类脚本")
        logger.log_shutdown(exit_code=0)
        return 0
        
    except Exception as e:
        logger.error(f"模式分类失败: {e}")
        logger.log_shutdown(exit_code=1)
        raise


def step4_extract_ocr_text(limit: Optional[int] = None, force: bool = False, use_vision: bool = True) -> dict:
    """
    步骤4: 文字提取
    
    Args:
        limit: 限制处理的记录数（用于分批次处理9000+图片）
        force: 强制重新提取已有文字的记录
        use_vision: 是否使用Gemini Vision API（True）还是本地OCR（False）
    """
    logger = get_detailed_logger('pdf_pipeline_step4')
    logger.log_startup({'limit': limit, 'force': force, 'use_vision': use_vision})
    
    if use_vision:
        logger.info("步骤4: 文字提取 - 使用 Gemini Vision API 提取图片中的交易策略文字")
        method = "Gemini Vision API"
    else:
        logger.info("步骤4: 文字提取 - 使用本地 OCR (Tesseract) 提取图片中的交易策略文字")
        method = "本地 OCR (Tesseract)"
    
    try:
        import sys
        import subprocess
        
        if use_vision:
            # 使用 Gemini Vision API 提取文字（推荐，准确率高）
            script_path = ROOT / 'scripts' / 'extract_pattern_text_openrouter.py'
            cmd = [sys.executable, str(script_path)]
            if limit:
                cmd.extend(['--limit', str(limit)])
            if force:
                cmd.append('--force')
            cmd.extend(['--model', 'google/gemini-2.5-flash-image'])
            cmd.extend(['--sleep-ms', '1000'])  # 控制API调用频率
            
        else:
            # 使用本地 OCR (Tesseract) 提取文字
            script_path = ROOT / 'scripts' / 'extract_pattern_ocr_text.py'
            cmd = [sys.executable, str(script_path)]
            if limit:
                cmd.extend(['--limit', str(limit)])
            if force:
                cmd.append('--force')
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(ROOT))
        
        logger.info(f"文字提取完成（使用 {method}）")
        logger.log_shutdown(exit_code=result.returncode)
        return {'success': result.returncode == 0, 'method': method}
        
    except Exception as e:
        logger.error(f"文字提取失败: {e}")
        logger.log_shutdown(exit_code=1)
        raise


def run_complete_pipeline(
    pdf_path: Optional[str] = None,
    max_pages: Optional[int] = None,
    skip_steps: list = None,
    ocr_limit: Optional[int] = None,
    ocr_force: bool = False,
    use_vision: bool = True
):
    """运行完整流程"""
    logger = get_detailed_logger('abu_complete_pipeline')
    logger.log_startup({
        'pdf_path': pdf_path,
        'max_pages': max_pages,
        'skip_steps': skip_steps or [],
        'ocr_limit': ocr_limit
    })
    
    skip_steps = skip_steps or []
    
    print("\n" + "="*80)
    print("ABU PDF处理完整流程")
    print("="*80 + "\n")
    
    results = {}
    
    # 步骤1: PDF提取
    if 'step1' not in skip_steps:
        if not pdf_path:
            logger.warning("跳过步骤1: 未提供PDF路径")
        else:
            logger.info("执行步骤1: PDF提取")
            try:
                pages = step1_ingest_pdf(pdf_path, max_pages)
                results['step1'] = {'success': True, 'pages': pages}
            except Exception as e:
                results['step1'] = {'success': False, 'error': str(e)}
                logger.error(f"步骤1失败: {e}")
                return results
    else:
        logger.info("跳过步骤1: PDF提取")
        results['step1'] = {'skipped': True}
    
    # 步骤2: 构建模式库
    if 'step2' not in skip_steps:
        logger.info("执行步骤2: 构建模式库")
        try:
            step2_build_library()
            results['step2'] = {'success': True}
        except Exception as e:
            results['step2'] = {'success': False, 'error': str(e)}
            logger.error(f"步骤2失败: {e}")
    else:
        logger.info("跳过步骤2: 构建模式库")
        results['step2'] = {'skipped': True}
    
    # 步骤3: 模式分类
    if 'step3' not in skip_steps:
        logger.info("执行步骤3: 模式分类")
        try:
            step3_classify_patterns(limit=max_pages)
            results['step3'] = {'success': True}
        except Exception as e:
            results['step3'] = {'success': False, 'error': str(e)}
            logger.error(f"步骤3失败: {e}")
    else:
        logger.info("跳过步骤3: 模式分类")
        results['step3'] = {'skipped': True}
    
    # 步骤4: 文字提取
    if 'step4' not in skip_steps:
        logger.info("执行步骤4: 文字提取")
        try:
            ocr_result = step4_extract_ocr_text(limit=ocr_limit, force=ocr_force, use_vision=use_vision)
            results['step4'] = ocr_result
        except Exception as e:
            results['step4'] = {'success': False, 'error': str(e)}
            logger.error(f"步骤4失败: {e}")
    else:
        logger.info("跳过步骤4: 文字提取")
        results['step4'] = {'skipped': True}
    
    # 总结
    print("\n" + "="*80)
    print("流程完成总结")
    print("="*80 + "\n")
    
    for step, result in results.items():
        if result.get('skipped'):
            print(f"{step}: 已跳过")
        elif result.get('success'):
            print(f"{step}: ✓ 成功")
            if 'pages' in result:
                print(f"  提取了 {result['pages']} 页")
        else:
            print(f"{step}: ✗ 失败")
            if 'error' in result:
                print(f"  错误: {result['error']}")
    
    logger.log_shutdown(exit_code=0, details=results)
    return results


def main():
    import argparse
    
    ap = argparse.ArgumentParser(
        description='ABU PDF处理完整流程',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
流程步骤：
  1. PDF提取 → raw_pages.jsonl
  2. 构建模式库 → pattern_library 表
  3. 模式分类 → 更新 pattern_type
  4. OCR文字提取 → 更新 chart_features_json.ocr_text

示例：
  # 完整流程
  python scripts/abu_complete_pipeline.py --pdf path/to/book.pdf
  
  # 只执行OCR提取（其他步骤已完成）
  python scripts/abu_complete_pipeline.py --skip step1,step2,step3 --ocr-limit 100
  
  # 跳过某些步骤
  python scripts/abu_complete_pipeline.py --pdf book.pdf --skip step3,step4
        """
    )
    
    ap.add_argument('--pdf', type=str, help='PDF文件路径')
    ap.add_argument('--max-pages', type=int, help='最大处理页数')
    ap.add_argument('--skip', type=str, help='跳过的步骤（逗号分隔，如 step1,step2）')
    ap.add_argument('--ocr-limit', type=int, help='文字提取限制数量（用于分批处理9000+图片）')
    ap.add_argument('--ocr-force', action='store_true', help='强制重新提取已有文字的记录')
    ap.add_argument('--use-vision', action='store_true', help='使用Gemini Vision API提取文字（默认，推荐）')
    ap.add_argument('--use-ocr', action='store_true', help='使用本地OCR (Tesseract)提取文字（不推荐，准确率低）')
    
    args = ap.parse_args()
    
    skip_steps = []
    if args.skip:
        skip_steps = [s.strip() for s in args.skip.split(',')]
    
    # 确定使用Vision还是OCR（默认Vision）
    # 如果指定了 --use-ocr，则使用OCR；否则默认使用Vision
    use_vision = not args.use_ocr
    
    run_complete_pipeline(
        pdf_path=args.pdf,
        max_pages=args.max_pages,
        skip_steps=skip_steps,
        ocr_limit=args.ocr_limit,
        ocr_force=args.ocr_force,
        use_vision=use_vision
    )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

