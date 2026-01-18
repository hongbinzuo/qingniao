#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 OpenRouter + Gemini Vision API 批量提取模式库图片中的文字说明
相比本地 OCR，Gemini Vision 准确率更高，能更好识别交易策略文字
"""

import sys
import json
import base64
import time
from pathlib import Path
from typing import Dict, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加 src 到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from detailed_logger import get_detailed_logger
from openrouter_config import get_openrouter_api_key, get_openrouter_api_url, is_openrouter_configured


# Gemini Vision 专用提示词，专注于提取交易策略文字说明
VISION_PROMPT = """You are analyzing a trading chart image. Extract any text descriptions related to trading strategies.

Focus on extracting:
- Pattern names (e.g., "Gap bar", "Bullish Engulfing", "Head and Shoulders")
- Trading direction (e.g., "buy", "sell", "long", "short")
- Market conditions (e.g., "bull trend", "bear trend", "small PB")
- Probability/success rate (e.g., "75% chance", "80% success")
- Targets (e.g., "test of high of day", "test of low of day")
- Entry conditions (e.g., "on small PB", "after pullback")

Return ONLY the extracted text descriptions, without any additional commentary or formatting. If no trading strategy text is found, return an empty string."""


def encode_image_to_base64(image_path: Path) -> Optional[str]:
    """将图片编码为 base64 字符串"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_str = base64.b64encode(image_data).decode('utf-8')
            # 检测图片格式
            if image_path.suffix.lower() == '.png':
                mime_type = 'image/png'
            elif image_path.suffix.lower() in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            else:
                mime_type = 'image/png'  # 默认 PNG
            return f"data:{mime_type};base64,{base64_str}"
    except Exception as e:
        print(f"⚠️ 图片编码失败: {e}", file=sys.stderr)
        return None


def analyze_image_with_openrouter(image_path: Path, model: str = "google/gemini-1.5-flash") -> Optional[str]:
    """使用 OpenRouter API 调用 Gemini Vision 分析图片"""
    import requests
    
    if not is_openrouter_configured():
        print("❌ OpenRouter API Key 未配置，请检查 .env 文件", file=sys.stderr)
        return None
    
    api_key = get_openrouter_api_key()
    api_url = f"{get_openrouter_api_url()}/chat/completions"
    
    # 编码图片
    image_data_url = encode_image_to_base64(image_path)
    if not image_data_url:
        return None
    
    # 构建请求
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/qingniao",  # 可选，用于统计
        "X-Title": "QingNiao Trading Pattern Extractor"  # 可选，用于统计
    }
    
    # OpenRouter 使用 OpenAI 兼容格式，但对于 Gemini Vision 需要使用特定格式
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": VISION_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,  # 降低温度以获得更稳定的结果
        "max_tokens": 500
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return content.strip()
            else:
                print(f"⚠️ API 响应格式异常: {result}", file=sys.stderr)
                return None
        else:
            error_text = response.text
            print(f"⚠️ API 请求失败 (状态码 {response.status_code}): {error_text}", file=sys.stderr)
            return None
            
    except requests.exceptions.Timeout:
        print(f"⚠️ API 请求超时", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️ API 请求异常: {e}", file=sys.stderr)
        return None


def main():
    import argparse
    
    ap = argparse.ArgumentParser(description='使用 OpenRouter + Gemini Vision 批量提取模式库图片文字说明')
    ap.add_argument('--limit', type=int, default=5, help='限制处理的记录数（测试用，默认5条）')
    ap.add_argument('--pattern-type', type=str, help='只处理特定模式类型')
    ap.add_argument('--dry-run', action='store_true', help='仅显示，不更新数据库')
    ap.add_argument('--force', action='store_true', help='强制重新提取已有文字的记录')
    ap.add_argument('--model', type=str, default='google/gemini-2.5-flash-image', 
                    help='使用的模型 (默认: google/gemini-2.5-flash-image，可选: google/gemini-2.5-flash, google/gemini-2.5-pro)')
    ap.add_argument('--sleep-ms', type=int, default=1000, 
                    help='每次请求之间的延迟（毫秒，默认1000ms，用于控制成本和速率）')
    args = ap.parse_args()
    
    # 检查配置
    if not is_openrouter_configured():
        print("❌ 错误: OpenRouter API Key 未配置")
        print("   请确保 .env 文件中包含 OPENROUTER_API_KEY")
        return 1
    
    logger = get_detailed_logger('extract_pattern_text_openrouter')
    logger.log_startup({
        'limit': args.limit, 
        'pattern_type': args.pattern_type, 
        'dry_run': args.dry_run,
        'model': args.model,
        'sleep_ms': args.sleep_ms
    })
    
    print("\n" + "="*80)
    print("使用 OpenRouter + Gemini Vision 批量提取模式库图片文字说明")
    print("="*80)
    print(f"模型: {args.model}")
    print(f"限制: {args.limit} 条记录")
    print(f"延迟: {args.sleep_ms}ms 每次请求")
    if args.dry_run:
        print("模式: DRY RUN (不会更新数据库)")
    print("="*80 + "\n")
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查询需要处理的记录
    query = '''
        SELECT id, pattern_name, pattern_type, image_path, chart_features_json
        FROM pattern_library 
        WHERE image_path IS NOT NULL AND image_path != ''
    '''
    params = []
    
    if args.pattern_type:
        query += ' AND pattern_type = ?'
        params.append(args.pattern_type)
    
    if not args.force:
        # 只处理还没有 Vision 文字的记录
        query += " AND (chart_features_json IS NULL OR chart_features_json = '' OR chart_features_json NOT LIKE '%vision_text%')"
    
    query += ' LIMIT ?'
    params.append(args.limit)
    
    records = conn.execute(query, params).fetchall()
    
    total = len(records)
    print(f"找到 {total} 条需要处理的记录\n")
    
    if total == 0:
        print("没有需要处理的记录")
        db.close()
        return 0
    
    logger.info(f"开始处理 {total} 条记录")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    text_extracted_count = 0
    total_cost_estimate = 0.0  # 粗略估算成本（基于请求次数）
    
    for i, (pid, name, ptype, img_path, existing_json) in enumerate(records, 1):
        logger.progress('openrouter_vision_extraction', i, total, f"处理 {i}/{total}: ID={pid}")
        
        # 检查图片文件是否存在
        img_file = Path(img_path)
        if not img_file.is_absolute():
            img_file = ROOT / img_path
        img_file = img_file.resolve()
        
        # 如果文件不存在，尝试查找匹配的文件
        if not img_file.exists():
            img_dir = img_file.parent
            img_name = img_file.name
            
            if '_img_' in img_name:
                parts = img_name.split('_img_')
                if len(parts) >= 1:
                    page_part = parts[0]
                    if page_part.startswith('page_'):
                        possible_files = list(img_dir.glob(f'{page_part}_*_clip.png'))
                        if possible_files:
                            img_file = possible_files[0]
                            logger.info(f"找到匹配的图片文件: {img_path} -> {img_file}", {
                                'id': pid, 
                                'original': img_path, 
                                'found': str(img_file)
                            })
            
            if not img_file.exists():
                logger.warning(f"图片文件不存在: {img_path}", {'id': pid, 'path': img_path})
                skipped_count += 1
                continue
        
        try:
            # 使用 OpenRouter + Gemini Vision 分析图片
            vision_text = analyze_image_with_openrouter(img_file, model=args.model)
            
            if vision_text is None:
                logger.warning(f"Vision API 返回空结果", {'id': pid, 'image': img_path})
                failed_count += 1
                continue
            
            vision_text = vision_text.strip()
            
            # 检查是否有新的文字
            existing_chart = None
            if existing_json:
                try:
                    existing_chart = json.loads(existing_json) if isinstance(existing_json, str) else existing_json
                    existing_vision = existing_chart.get('vision_text', '').strip()
                    if existing_vision == vision_text and not args.force:
                        skipped_count += 1
                        continue
                except:
                    pass
            
            # 更新图表特征JSON
            if existing_chart and isinstance(existing_chart, dict):
                chart_features = existing_chart.copy()
            else:
                chart_features = {}
            
            # 更新 Vision 文字
            chart_features['vision_text'] = vision_text
            chart_features['vision_model'] = args.model
            chart_features['vision_extracted_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果有 Vision 文字，记录
            if vision_text:
                text_extracted_count += 1
                logger.info(f"提取到文字说明 (ID={pid}): {vision_text[:100]}...", {
                    'id': pid,
                    'pattern_type': ptype,
                    'text_length': len(vision_text)
                })
                print(f"  [ID={pid}] 提取文字: {vision_text[:150]}...")
            
            # 更新数据库
            if not args.dry_run:
                chart_json = json.dumps(chart_features, ensure_ascii=False)
                conn.execute('''
                    UPDATE pattern_library 
                    SET chart_features_json = ?
                    WHERE id = ?
                ''', (chart_json, pid))
                conn.commit()
                success_count += 1
                total_cost_estimate += 0.001  # 粗略估算：每次请求约 $0.001
            else:
                print(f"  [DRY RUN] 将更新 ID={pid}:")
                if vision_text:
                    print(f"    Vision文字: {vision_text[:200]}...")
                success_count += 1
                total_cost_estimate += 0.001
            
            # 延迟，避免请求过快
            if i < total and args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)
                
        except Exception as e:
            logger.error(f"处理失败 (ID={pid}): {e}", {'id': pid, 'error': str(e)})
            failed_count += 1
            continue
    
    # 统计结果
    print(f"\n{'='*80}")
    print("处理完成")
    print(f"{'='*80}\n")
    print(f"总计: {total} 条")
    print(f"成功: {success_count} 条")
    print(f"失败: {failed_count} 条")
    print(f"跳过: {skipped_count} 条")
    print(f"提取到文字: {text_extracted_count} 条")
    print(f"估算成本: ${total_cost_estimate:.4f} USD")
    
    if args.dry_run:
        print("\n[DRY RUN模式] 未实际更新数据库")
    else:
        print("\n✓ 数据库已更新")
    
    logger.info("OpenRouter Vision 提取完成", {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'text_extracted': text_extracted_count,
        'cost_estimate_usd': total_cost_estimate
    })
    
    db.close()
    logger.log_shutdown(exit_code=0)
    return 0


if __name__ == '__main__':
    sys.exit(main())

