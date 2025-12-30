#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Markdown报告转换为PDF格式
"""

import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import os

def markdown_to_pdf(md_file: str, pdf_file: str):
    """将Markdown文件转换为PDF"""
    print(f"正在读取Markdown文件: {md_file}")
    
    # 读取Markdown文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 将Markdown转换为HTML
    print("正在转换Markdown为HTML...")
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables', 'toc']
    )
    
    # 创建完整的HTML文档
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
                font-size: 12pt;
                line-height: 1.6;
                color: #333;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            h2 {{
                color: #34495e;
                border-bottom: 2px solid #95a5a6;
                padding-bottom: 8px;
                margin-top: 25px;
            }}
            h3 {{
                color: #555;
                margin-top: 20px;
            }}
            h4 {{
                color: #666;
                margin-top: 15px;
            }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border-left: 4px solid #3498db;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            li {{
                margin: 5px 0;
            }}
            blockquote {{
                border-left: 4px solid #3498db;
                margin: 15px 0;
                padding: 10px 20px;
                background-color: #f9f9f9;
                font-style: italic;
            }}
            strong {{
                color: #2c3e50;
                font-weight: bold;
            }}
            hr {{
                border: none;
                border-top: 2px solid #ecf0f1;
                margin: 30px 0;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 3px solid #3498db;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # 转换为PDF
    print(f"正在生成PDF文件: {pdf_file}")
    try:
        HTML(string=html_doc).write_pdf(pdf_file)
        print(f"✓ PDF文件已成功生成: {pdf_file}")
        return True
    except Exception as e:
        print(f"✗ 生成PDF时出错: {e}")
        return False

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
    
    success = markdown_to_pdf(md_file, pdf_file)
    
    if success:
        print()
        print("=" * 80)
        print("转换完成！")
        print("=" * 80)
        print(f"PDF文件已保存到: {pdf_file}")
    else:
        print()
        print("转换失败，请检查错误信息")

if __name__ == "__main__":
    main()




