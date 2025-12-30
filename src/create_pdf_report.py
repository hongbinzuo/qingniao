#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建完整的PDF报告
"""

import re
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

def create_pdf_report(md_file: str, pdf_file: str):
    """创建PDF报告"""
    print(f"正在读取文件: {md_file}")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("正在创建PDF文档...")
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # 定义样式
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'H1',
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        leading=18
    )
    
    h2_style = ParagraphStyle(
        'H2',
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        leading=16
    )
    
    h3_style = ParagraphStyle(
        'H3',
        fontSize=11,
        textColor=colors.HexColor('#555'),
        spaceAfter=6,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        leading=14
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        fontSize=10,
        leading=14,
        alignment=TA_LEFT
    )
    
    # 解析内容
    story = []
    lines = content.split('\n')
    in_list = False
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # 空行
        if not line:
            if in_list:
                in_list = False
            story.append(Spacer(1, 6))
            continue
        
        # 标题
        if line.startswith('#'):
            in_list = False
            level = 0
            while level < len(line) and line[level] == '#':
                level += 1
            
            text = line[level:].strip()
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            
            if level == 1:
                if '交易员' in text or '分析报告' in text:
                    story.append(Paragraph(text, title_style))
                else:
                    story.append(Paragraph(text, h1_style))
            elif level == 2:
                story.append(Paragraph(text, h2_style))
            elif level == 3:
                story.append(Paragraph(text, h3_style))
            else:
                story.append(Paragraph(text, h3_style))
        
        # 分隔线
        elif line.startswith('=') and len(line) > 10:
            story.append(Spacer(1, 12))
        
        # 列表
        elif line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line):
            in_list = True
            if line.startswith('-') or line.startswith('*'):
                text = line.lstrip('-*').strip()
            else:
                text = re.sub(r'^\d+\.\s*', '', line)
            
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
            
            if line.startswith('-') or line.startswith('*'):
                story.append(Paragraph(f"• {text}", normal_style))
            else:
                story.append(Paragraph(text, normal_style))
        
        # 普通文本
        else:
            if not line.startswith('|'):  # 跳过表格
                text = line
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
                text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
                
                if text.strip():
                    story.append(Paragraph(text, normal_style))
    
    # 构建PDF
    print("正在构建PDF...")
    try:
        doc.build(story)
        file_size = os.path.getsize(pdf_file) / 1024
        print(f"[OK] PDF已生成: {pdf_file}")
        print(f"文件大小: {file_size:.2f} KB")
        return True
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    md_file = "De_trading_system_final_complete.md"
    pdf_file = "De_trading_system_final_complete.pdf"
    
    if not os.path.exists(md_file):
        print(f"错误: 找不到文件 {md_file}")
        return
    
    print("=" * 80)
    print("PDF报告生成工具")
    print("=" * 80)
    print()
    
    success = create_pdf_report(md_file, pdf_file)
    
    if success:
        print()
        print("=" * 80)
        print("完成！")
        print("=" * 80)
        print(f"PDF文件: {pdf_file}")

if __name__ == "__main__":
    main()

