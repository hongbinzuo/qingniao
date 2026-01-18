#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成阶段性报告PDF（汇总所有重要文档）
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("=" * 80)
    print("生成阶段性报告PDF")
    print("=" * 80)
    print()
    
    # 重要文档列表
    important_docs = [
        # 方案文档
        ROOT / 'docs' / 'design' / 'features' / 'ABU_ML_DL完整执行方案.md',
        
        # 阶段报告
        ROOT / 'docs' / 'stage_reports' / 'stage0_gemini_analysis_status.md',
        ROOT / 'docs' / 'stage_reports' / 'stage0_optimization_complete.md',
        
        # 技术偏好
        ROOT / 'docs' / 'design' / 'requirements' / '技术偏好与优化要求.md',
        
        # 使用指南
        ROOT / 'docs' / 'design' / 'features' / 'Gemini_Vision_模块使用说明.md',
    ]
    
    # 检查文件存在
    existing_docs = []
    missing_docs = []
    
    for doc in important_docs:
        if doc.exists():
            existing_docs.append(doc)
        else:
            missing_docs.append(doc)
    
    print(f"找到文档: {len(existing_docs)}/{len(important_docs)}")
    if missing_docs:
        print("\n缺失文档:")
        for doc in missing_docs:
            print(f"  - {doc.relative_to(ROOT)}")
    print()
    
    # 生成汇总Markdown
    output_md = ROOT / 'docs' / 'stage_reports' / 'ABU_ML_DL_完整执行报告汇总.md'
    
    with output_md.open('w', encoding='utf-8') as f:
        f.write("# ABU ML/DL 完整执行报告汇总\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for i, doc_path in enumerate(existing_docs, 1):
            f.write(f"\n## 文档 {i}: {doc_path.stem}\n\n")
            f.write(f"**路径**: `{doc_path.relative_to(ROOT)}`\n\n")
            f.write("---\n\n")
            
            try:
                content = doc_path.read_text(encoding='utf-8')
                f.write(content)
                f.write("\n\n")
            except Exception as e:
                f.write(f"**读取错误**: {e}\n\n")
    
    print(f"✅ 汇总Markdown已生成: {output_md.relative_to(ROOT)}")
    print()
    
    # 尝试转换为PDF（需要pandoc或markdown-pdf）
    try:
        import subprocess
        
        # 方法1: 使用pandoc
        pdf_output = ROOT / 'docs' / 'stage_reports' / 'ABU_ML_DL_完整执行报告汇总.pdf'
        
        try:
            subprocess.run([
                'pandoc',
                str(output_md),
                '-o', str(pdf_output),
                '--pdf-engine=xelatex',
                '-V', 'CJKmainfont=SimSun',
                '--toc',
                '--toc-depth=3'
            ], check=True, capture_output=True)
            
            print(f"✅ PDF已生成: {pdf_output.relative_to(ROOT)}")
            return 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  pandoc未安装或转换失败")
            print("   请安装pandoc: https://pandoc.org/installing.html")
            print("   或使用在线工具转换Markdown为PDF")
            print()
            print("替代方案:")
            print("  1. 使用VS Code的Markdown PDF插件")
            print("  2. 使用在线工具: https://www.markdowntopdf.com/")
            print("  3. 使用Chrome打印功能（打开Markdown预览后打印为PDF）")
            return 1
    except Exception as e:
        print(f"⚠️  PDF转换失败: {e}")
        print(f"   汇总Markdown文件已生成: {output_md.relative_to(ROOT)}")
        print("   可以手动转换为PDF")
        return 1

if __name__ == '__main__':
    sys.exit(main())

