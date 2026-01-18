#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Markdown转换为PDF（使用pandoc）
"""

import sys
import subprocess
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent

def main():
    md_file = ROOT / 'docs' / 'stage_reports' / 'ABU_ML_DL_完整执行报告汇总.md'
    pdf_file = ROOT / 'docs' / 'stage_reports' / 'ABU_ML_DL_完整执行报告汇总.pdf'
    
    if not md_file.exists():
        print(f"❌ 源文件不存在: {md_file}")
        return 1
    
    print(f"正在转换: {md_file.name} -> {pdf_file.name}")
    print()
    
    # 使用pandoc转换
    # 使用--from markdown明确指定输入格式
    # 使用--to pdf明确指定输出格式
    try:
        # 尝试不同的PDF引擎
        engines = ['xelatex', 'pdflatex', 'wkhtmltopdf', 'weasyprint']
        
        for engine in engines:
            try:
                cmd = [
                    'pandoc',
                    str(md_file),
                    '-f', 'markdown',
                    '-t', 'pdf',
                    '-o', str(pdf_file),
                    f'--pdf-engine={engine}',
                    '--toc',
                    '--toc-depth=3',
                    '--variable=geometry:margin=1in'
                ]
                
                # 如果是xelatex，添加中文字体设置
                if engine == 'xelatex':
                    cmd.insert(-2, '-V')
                    cmd.insert(-2, 'CJKmainfont=Microsoft YaHei')
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
                
                if result.returncode == 0 and pdf_file.exists() and pdf_file.stat().st_size > 0:
                    print(f"✅ PDF已生成（使用{engine}引擎）: {pdf_file}")
                    print(f"   文件大小: {pdf_file.stat().st_size / 1024:.1f} KB")
                    return 0
            except subprocess.TimeoutExpired:
                print(f"⚠️  {engine}引擎超时，尝试下一个...")
                continue
            except Exception:
                continue
        
        # 如果所有PDF引擎都失败，使用HTML
        print("\n所有PDF引擎都不可用，已生成HTML版本")
        return convert_via_html(md_file, pdf_file)
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"✅ PDF已生成: {pdf_file}")
            print(f"   文件大小: {pdf_file.stat().st_size / 1024:.1f} KB")
            return 0
        else:
            print(f"❌ 转换失败:")
            print(result.stderr)
            
            # 如果xelatex失败，尝试使用wkhtmltopdf或直接HTML
            print("\n尝试备用方案：HTML转PDF...")
            return convert_via_html(md_file, pdf_file)
            
    except FileNotFoundError:
        print("❌ pandoc未找到，请确保已安装pandoc")
        print("   安装命令: winget install --id JohnMacFarlane.Pandoc")
        return 1
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return 1

def convert_via_html(md_file, pdf_file):
    """通过HTML中间格式转换"""
    html_file = pdf_file.with_suffix('.html')
    
    try:
        # 先转为HTML
        cmd1 = [
            'pandoc',
            str(md_file),
            '-f', 'markdown',
            '-t', 'html',
            '-o', str(html_file),
            '--standalone',
            '--toc',
            '--toc-depth=3'
        ]
        
        result1 = subprocess.run(cmd1, capture_output=True, text=True, encoding='utf-8')
        if result1.returncode != 0:
            print(f"HTML转换失败: {result1.stderr}")
            return 1
        
        print(f"✅ 已生成HTML: {html_file}")
        print(f"   可以使用浏览器打开HTML文件，然后打印为PDF")
        return 0
        
    except Exception as e:
        print(f"❌ HTML转换失败: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

