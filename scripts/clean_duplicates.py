#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理pattern_library表中的重复记录
只保留每个source_page的最新记录（按updated_at排序）
"""

import psycopg2

def clean_duplicates():
    """清理重复记录"""

    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )
    cursor = conn.cursor()

    try:
        # 1. 查找所有有重复记录的页面
        cursor.execute("""
            SELECT source_page, COUNT(*) as count
            FROM pattern_library
            GROUP BY source_page
            HAVING COUNT(*) > 1
            ORDER BY source_page
        """)
        duplicates = cursor.fetchall()

        print(f"\n{'='*60}")
        print(f"Found {len(duplicates)} pages with duplicate records")
        print(f"{'='*60}\n")

        if not duplicates:
            print("No duplicates found!")
            return

        total_deleted = 0

        # 2. 对每个有重复的页面，删除旧记录
        for page_num, count in duplicates:
            print(f"Page {page_num}: {count} records")

            # 查找该页面的所有记录，按updated_at降序
            cursor.execute("""
                SELECT id, pattern_name, pattern_type,
                       updated_at, created_at
                FROM pattern_library
                WHERE source_page = %s
                ORDER BY updated_at DESC NULLS LAST, created_at DESC
            """, (page_num,))
            records = cursor.fetchall()

            # 保留第一条（最新的），删除其他
            keep_id = records[0][0]
            delete_ids = [r[0] for r in records[1:]]

            print(f"  Keep: ID={keep_id}, updated={records[0][3]}")
            print(f"  Delete: {len(delete_ids)} old records")

            # 删除pattern_vectors中的旧记录
            if delete_ids:
                cursor.execute("""
                    DELETE FROM pattern_vectors
                    WHERE pattern_library_id = ANY(%s)
                """, (delete_ids,))

                # 删除pattern_library中的旧记录
                cursor.execute("""
                    DELETE FROM pattern_library
                    WHERE id = ANY(%s)
                """, (delete_ids,))

                total_deleted += len(delete_ids)

        conn.commit()

        print(f"\n{'='*60}")
        print(f"Cleanup Complete!")
        print(f"Total deleted: {total_deleted} old records")
        print(f"{'='*60}\n")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clean_duplicates()
