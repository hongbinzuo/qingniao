#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Markdown报告转换为PDF格式（使用reportlab）
"""

import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

def markdown_to_pdf(md_file: str, pdf_file: str):
    """将Markdown文件转换为PDF"""
    print(f"正在读取Markdown文件: {md_file}")
    
    # 读取Markdown文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 创建PDF文档
    print("正在生成PDF文件...")
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # 创建样式
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#555'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    # 解析Markdown内容
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
            
            if level == 1:
                if '=' in text or '交易员' in text:
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
            # 处理粗体
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(f"• {text}", normal_style))
        
        # 数字列表
        elif re.match(r'^\d+\.', line):
            text = re.sub(r'^\d+\.\s*', '', line)
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(text, normal_style))
        
        # 表格（简化处理）
        elif '|' in line and line.count('|') > 2:
            # 跳过表格分隔行
            if '---' in line or '===' in line:
                i += 1
                continue
            
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                # 创建表格
                table_data = [cells]
                # 读取下一行（如果有）
                if i + 1 < len(lines) and '|' in lines[i + 1]:
                    i += 1
                    next_line = lines[i].strip()
                    if '---' not in next_line and '===' not in next_line:
                        next_cells = [cell.strip() for cell in next_line.split('|') if cell.strip()]
                        if next_cells:
                            table_data.append(next_cells)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
        
        # 普通文本
        else:
            # 处理Markdown格式
            text = line
            
            # 粗体
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # 代码
            text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
            # 链接（简化处理）
            text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
            
            if text.strip():
                story.append(Paragraph(text, normal_style))
        
        i += 1
    
    # 构建PDF
    print("正在构建PDF文档...")
    doc.build(story)
    print(f"[OK] PDF文件已成功生成: {pdf_file}")
    return True

def main():
    md_file = "De_trading_system_ml_analysis.md"
    pdf_file = "De_trading_system_ml_analysis.pdf"
    
    import os
    if not os.path.exists(md_file):
        print(f"错误: 找不到文件 {md_file}")
        return
    
    print("=" * 80)
    print("Markdown转PDF工具 (使用ReportLab)")
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
            print(f"文件大小: {os.path.getsize(pdf_file) / 1024:.2f} KB")
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

