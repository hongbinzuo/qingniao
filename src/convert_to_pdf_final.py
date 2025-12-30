#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Markdown报告完整转换为PDF格式
"""

import re
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

def markdown_to_pdf(md_file: str, pdf_file: str):
    """将Markdown文件转换为PDF"""
    print(f"正在读取Markdown文件: {md_file}")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print("正在生成PDF文件...")
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # 创建样式
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
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#555'),
        spaceAfter=6,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )
    
    # 解析内容
    story = []
    lines = md_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            story.append(Spacer(1, 6))
            i += 1
            continue
        
        # 标题
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            
            # 处理粗体
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
        
        # 列表项
        elif line.startswith('-') or line.startswith('*'):
            text = line.lstrip('-*').strip()
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
            story.append(Paragraph(f"• {text}", normal_style))
        
        # 数字列表
        elif re.match(r'^\d+\.', line):
            text = re.sub(r'^\d+\.\s*', '', line)
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
            story.append(Paragraph(text, normal_style))
        
        # 普通文本
        else:
            if line and not line.startswith('|'):
                # 处理格式
                text = line
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
                text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
                
                if text.strip():
                    story.append(Paragraph(text, normal_style))
        
        i += 1
    
    # 构建PDF
    print("正在构建PDF文档...")
    doc.build(story)
    
    file_size = os.path.getsize(pdf_file) / 1024
    print(f"[OK] PDF文件已成功生成: {pdf_file}")
    print(f"文件大小: {file_size:.2f} KB")
    return True

def main():
    md_file = "De_trading_system_ml_analysis.md"
    pdf_file = "De_trading_system_ml_analysis.pdf"
    
    if not os.path.exists(md_file):
        print(f"错误: 找不到文件 {md_file}")
        return
    
    print("=" * 80)
    print("Markdown转PDF工具")
    print("=" * 80)
    print()
    
    try:
        success = markdown_to_pdf(md_file, pdf_file)
        
        if success:
            print()
            print("=" * 80)
            print("转换完成！")
            print("=" * 80)
            print(f"PDF文件已保存到: {pdf_file}")
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()




