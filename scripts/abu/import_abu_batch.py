#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用ABU批量导入脚本 - 自动检测页码范围并导入"""

import sys
import json
import re
from batch_import_manual import save_to_database
import psycopg2


def fix_page_numbers(data):
    """从image_id中提取正确的页码"""
    for record in data:
        image_id = record.get("image_id", "")
        match = re.search(r'page_(\d+)', image_id)
        if match:
            correct_page = int(match.group(1))
            record["page"] = correct_page
            print(f"  Fixed: {image_id} -> page {correct_page}")
    return data


def detect_page_range(data):
    """检测页码范围"""
    pages = [record.get("page", 0) for record in data]
    if not pages:
        return 0, 0
    return min(pages), max(pages)


def main(json_file_path):
    """主导入流程"""
    # 读取JSON数据
    print(f"\nReading JSON data from: {json_file_path}")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records")

    # 修正页码
    print(f"\n{'='*60}")
    print(f"Fixing page numbers...")
    print(f"{'='*60}\n")
    data = fix_page_numbers(data)

    # 检测范围
    start_page, end_page = detect_page_range(data)

    # 连接数据库
    print(f"\nConnecting to database...")
    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )

    print(f"\n{'='*60}")
    print(f"Batch Import: {len(data)} records (Pages {start_page}-{end_page})")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0

    for record in data:
        page_num = record.get("page", "unknown")
        print(f"Processing page {page_num}...")

        if save_to_database(record, conn):
            success_count += 1
        else:
            fail_count += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"Import Complete!")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Page Range: {start_page}-{end_page}")
    print(f"{'='*60}\n")

    return start_page, end_page, success_count, fail_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_abu_batch.py <json_file_path>")
        print("Example: python import_abu_batch.py temp_import_data.json")
        sys.exit(1)

    json_file_path = sys.argv[1]
    try:
        start_page, end_page, success, failed = main(json_file_path)
        sys.exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
