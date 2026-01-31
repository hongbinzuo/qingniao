#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取Al Brooks电子书文本内容
"""
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ 请安装PyMuPDF: pip install pymupdf")
    sys.exit(1)

OUTPUT_DIR = ROOT / 'data' / 'abu' / 'ebooks' / 'extracted'

def extract_text_from_pdf(pdf_path: Path) -> Dict:
    """从PDF提取文本和结构"""
    print(f"  读取PDF: {pdf_path.name}...")
    doc = fitz.open(str(pdf_path))
    
    book_data = {
        "book_title": pdf_path.stem,
        "total_pages": len(doc),
        "chapters": [],
        "all_pages": []
    }
    
    current_chapter = None
    current_section = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        # 识别章节标题
        chapter_match = re.search(r'^Chapter\s+(\d+)[:.\s]+(.+?)$', text, re.MULTILINE | re.IGNORECASE)
        if chapter_match:
            if current_chapter:
                if current_section:
                    current_chapter["sections"].append(current_section)
                book_data["chapters"].append(current_chapter)
            
            current_chapter = {
                "chapter_number": int(chapter_match.group(1)),
                "chapter_title": chapter_match.group(2).strip(),
                "sections": [],
                "page_range": [page_num + 1]
            }
            current_section = None
        
        # 识别节标题（如 1.1, 1.2等）
        section_match = re.search(r'^(\d+\.\d+)\s+(.+?)$', text, re.MULTILINE)
        if section_match:
            if current_chapter:
                if current_section:
                    current_chapter["sections"].append(current_section)
                
                current_section = {
                    "section_number": section_match.group(1),
                    "section_title": section_match.group(2).strip(),
                    "paragraphs": [],
                    "page_number": page_num + 1
                }
        
        # 提取段落
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 20]
        
        if current_section:
            current_section["paragraphs"].extend(paragraphs)
        elif current_chapter:
            if "paragraphs" not in current_chapter:
                current_chapter["paragraphs"] = []
            current_chapter["paragraphs"].extend(paragraphs)
        
        # 保存页面文本
        book_data["all_pages"].append({
            "page": page_num + 1,
            "text": text[:5000]  # 限制长度
        })
    
    # 保存最后一章
    if current_chapter:
        if current_section:
            current_chapter["sections"].append(current_section)
        book_data["chapters"].append(current_chapter)
    
    doc.close()
    return book_data

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 查找PDF文件（优先从指定目录，否则从项目目录）
    external_ebook_dir = Path('C:/baidunetdiskdownload')
    project_ebook_dir = ROOT / 'data' / 'abu' / 'ebooks'
    project_ebook_dir.mkdir(parents=True, exist_ok=True)
    
    # 先检查外部目录
    pdf_files = []
    if external_ebook_dir.exists():
        pdf_files = list(external_ebook_dir.glob('*.pdf'))
        print(f"从外部目录找到 {len(pdf_files)} 个PDF文件: {external_ebook_dir}")
    
    # 如果外部目录没有或为空，检查项目目录
    if not pdf_files:
        pdf_files = list(project_ebook_dir.glob('*.pdf'))
        if pdf_files:
            print(f"从项目目录找到 {len(pdf_files)} 个PDF文件: {project_ebook_dir}")
    
    if not pdf_files:
        print(f"❌ 未找到PDF文件")
        print(f"   请将Al Brooks电子书放在以下任一目录：")
        print(f"   - {external_ebook_dir}")
        print(f"   - {project_ebook_dir}")
        return
    
    # 过滤Al Brooks相关的PDF（可选）
    brooks_keywords = ['brooks', 'price', 'action', 'trading', 'course']
    filtered_files = []
    for pdf in pdf_files:
        name_lower = pdf.name.lower()
        if any(keyword in name_lower for keyword in brooks_keywords) or len(pdf_files) <= 5:
            # 如果文件少，或者包含关键词，则包含
            filtered_files.append(pdf)
    
    # 如果没有过滤出任何文件，使用所有文件
    if filtered_files:
        pdf_files = filtered_files
        print(f"筛选后剩余 {len(pdf_files)} 个PDF文件（包含关键词或总数较少）")
    
    print("=" * 80)
    print("Al Brooks 电子书文本提取")
    print("=" * 80)
    print(f"找到 {len(pdf_files)} 个PDF文件\n")
    
    for pdf_path in pdf_files:
        print(f"处理: {pdf_path.name}")
        
        try:
            # 提取文本
            book_data = extract_text_from_pdf(pdf_path)
            
            # 保存结果
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_extracted.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(book_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已保存: {output_file}")
            print(f"   章节数: {len(book_data['chapters'])}")
            print(f"   总页数: {book_data['total_pages']}")
            print()
            
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 80)
    print("✅ 文本提取完成")
    print("=" * 80)

if __name__ == '__main__':
    main()

