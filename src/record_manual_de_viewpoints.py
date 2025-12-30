#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录手工提供的De.观点
支持录入观点内容和时间戳
"""

import json
import sys
from datetime import datetime
from pathlib import Path

VIEWPOINTS_FILE = Path(__file__).parent / "de_manual_viewpoints.json"

def load_viewpoints():
    """加载已记录的观点"""
    if VIEWPOINTS_FILE.exists():
        try:
            with open(VIEWPOINTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    return {
        "viewpoints": [],
        "last_updated": None,
        "total_count": 0
    }

def save_viewpoints(data):
    """保存观点数据"""
    VIEWPOINTS_FILE.parent.mkdir(exist_ok=True)
    data["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(VIEWPOINTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_viewpoint(content, timestamp=None, source="manual", category=None):
    """添加一个观点"""
    data = load_viewpoints()
    
    # 如果没有提供时间戳，使用当前时间
    if not timestamp:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    viewpoint = {
        "id": f"viewpoint_{len(data['viewpoints']) + 1}",
        "content": content,
        "timestamp": timestamp,
        "recorded_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "source": source,  # manual, dialog, etc.
        "category": category  # trading, analysis, instruction, etc.
    }
    
    data["viewpoints"].append(viewpoint)
    data["total_count"] = len(data["viewpoints"])
    
    save_viewpoints(data)
    return viewpoint["id"]

def list_viewpoints(limit=None):
    """列出所有观点"""
    data = load_viewpoints()
    viewpoints = data.get("viewpoints", [])
    
    if limit:
        viewpoints = viewpoints[-limit:]
    
    return viewpoints

def show_viewpoints(limit=20):
    """显示观点列表"""
    viewpoints = list_viewpoints(limit)
    
    print("=" * 80)
    print("De.手工观点记录")
    print("=" * 80)
    print()
    
    if not viewpoints:
        print("暂无记录的观点")
        return
    
    print(f"共 {len(viewpoints)} 条观点（显示最近{min(limit, len(viewpoints))}条）")
    print()
    
    for i, vp in enumerate(reversed(viewpoints), 1):
        print(f"{i}. [{vp.get('timestamp', 'N/A')}]")
        print(f"   内容: {vp.get('content', '')[:150]}")
        print(f"   来源: {vp.get('source', 'unknown')} | 类别: {vp.get('category', 'N/A')}")
        print(f"   录入时间: {vp.get('recorded_time', 'N/A')}")
        print()

def interactive_add():
    """交互式添加观点"""
    print("=" * 80)
    print("录入De.观点")
    print("=" * 80)
    print()
    
    print("请输入De.的观点内容（输入空行结束）:")
    lines = []
    while True:
        try:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        except EOFError:
            break
    
    if not lines:
        print("未输入内容，已取消")
        return
    
    content = '\n'.join(lines)
    
    print()
    print("请输入时间戳（格式: 2025-12-30 10:30:00，直接回车使用当前时间）:")
    timestamp = input().strip()
    if not timestamp:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print()
    print("请输入类别（可选: trading/analysis/instruction/other，直接回车跳过）:")
    category = input().strip() or None
    
    vp_id = add_viewpoint(content, timestamp, source="manual", category=category)
    print()
    print(f"✅ 已添加观点 (ID: {vp_id})")
    print(f"   时间: {timestamp}")
    print(f"   内容: {content[:100]}...")

def batch_add_from_file(file_path):
    """从文件批量导入观点（每行一个观点，格式: 时间戳|内容）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        count = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 支持格式: 时间戳|内容 或 内容（使用当前时间）
            if '|' in line:
                parts = line.split('|', 1)
                timestamp = parts[0].strip()
                content = parts[1].strip()
            else:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                content = line
            
            if content:
                add_viewpoint(content, timestamp, source="manual")
                count += 1
        
        print(f"✅ 已批量导入 {count} 条观点")
    except Exception as e:
        print(f"❌ 导入失败: {e}", file=sys.stderr)

def export_to_markdown(output_file=None):
    """导出为Markdown格式"""
    viewpoints = list_viewpoints()
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"De_手工观点记录_{timestamp}.md"
    
    md = []
    md.append("# De.手工观点记录")
    md.append("")
    md.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    md.append(f"**总记录数**: {len(viewpoints)}  ")
    md.append("")
    md.append("---")
    md.append("")
    
    # 按时间排序
    sorted_viewpoints = sorted(viewpoints, key=lambda x: x.get('timestamp', ''))
    
    for i, vp in enumerate(sorted_viewpoints, 1):
        md.append(f"## {i}. {vp.get('timestamp', 'N/A')}")
        md.append("")
        md.append(f"**来源**: {vp.get('source', 'unknown')}  ")
        if vp.get('category'):
            md.append(f"**类别**: {vp.get('category')}  ")
        md.append(f"**录入时间**: {vp.get('recorded_time', 'N/A')}  ")
        md.append("")
        md.append("**内容**:")
        md.append("")
        # 保持原始格式
        content = vp.get('content', '')
        for line in content.split('\n'):
            md.append(f"  {line}")
        md.append("")
        md.append("---")
        md.append("")
    
    output_path = Path(output_file)
    output_path.write_text('\n'.join(md), encoding='utf-8')
    print(f"✅ 已导出到: {output_path}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python record_manual_de_viewpoints.py add          # 交互式添加")
        print("  python record_manual_de_viewpoints.py show [N]    # 显示最近N条（默认20）")
        print("  python record_manual_de_viewpoints.py export      # 导出为Markdown")
        print("  python record_manual_de_viewpoints.py import <file> # 从文件批量导入")
        return
    
    command = sys.argv[1]
    
    if command == 'add':
        interactive_add()
    elif command == 'show':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_viewpoints(limit)
    elif command == 'export':
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        export_to_markdown(output_file)
    elif command == 'import':
        if len(sys.argv) < 3:
            print("请提供文件路径")
            return
        batch_add_from_file(sys.argv[2])
    else:
        print(f"未知命令: {command}")

if __name__ == '__main__':
    main()

