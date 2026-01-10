#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GM - Global Manager（全局管理器）
保存和查询系统工作状态、任务列表、工作计划

功能：
- 保存当前系统状态
- 记录TODO任务
- 记录工作计划
- 下次启动时快速查询

使用：
  # 保存当前状态
  python scripts/gm_status.py --save
  
  # 查询当前状态
  python scripts/gm_status.py --show
  
  # 更新TODO
  python scripts/gm_status.py --update-todo
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = ROOT / 'docs' / 'SYSTEM_STATUS.md'
JSON_FILE = ROOT / 'docs' / 'system_status.json'

if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from detailed_logger import get_detailed_logger

def get_system_status() -> Dict:
    """获取系统当前状态"""
    logger = get_detailed_logger('gm_status')
    
    status = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'system': {}
    }
    
    # 数据库状态
    try:
        from db_manager_trader import TraderDBManager
        
        for trader in ['abu', 'de', 'dream']:
            try:
                db = TraderDBManager(trader)
                conn = db._get_connection()
                
                # 交易信号统计
                signals_count = conn.execute('SELECT COUNT(*) FROM trading_signals').fetchone()[0]
                latest_signal = conn.execute('SELECT MAX(signal_time) FROM trading_signals').fetchone()[0]
                
                # 模式库统计（仅abu）
                pattern_count = 0
                if trader == 'abu':
                    try:
                        pattern_count = conn.execute('SELECT COUNT(*) FROM pattern_library').fetchone()[0]
                        pattern_classified = conn.execute('''
                            SELECT COUNT(*) FROM pattern_library 
                            WHERE pattern_type IS NOT NULL 
                              AND pattern_type != 'other'
                              AND pattern_type != ''
                        ''').fetchone()[0]
                        pattern_ocr = conn.execute('''
                            SELECT COUNT(*) FROM pattern_library 
                            WHERE chart_features_json IS NOT NULL 
                              AND chart_features_json != '' 
                              AND chart_features_json LIKE '%ocr_text%'
                        ''').fetchone()[0]
                    except:
                        pass
                
                status['system'][trader] = {
                    'signals_count': signals_count,
                    'latest_signal': latest_signal,
                    'pattern_count': pattern_count if trader == 'abu' else None,
                    'pattern_classified': pattern_classified if trader == 'abu' else None,
                    'pattern_ocr_extracted': pattern_ocr if trader == 'abu' else None
                }
                
                db.close()
            except Exception as e:
                status['system'][trader] = {'error': str(e)}
    except Exception as e:
        status['system']['database'] = {'error': str(e)}
    
    # 文件状态
    status['files'] = {
        'raw_pages_jsonl': {
            'exists': (ROOT / 'data' / 'abu' / 'raw_pages.jsonl').exists(),
            'size': (ROOT / 'data' / 'abu' / 'raw_pages.jsonl').stat().st_size if (ROOT / 'data' / 'abu' / 'raw_pages.jsonl').exists() else 0
        },
        'patterns_json': {
            'exists': (ROOT / 'data' / 'abu' / 'patterns.json').exists(),
            'size': (ROOT / 'data' / 'abu' / 'patterns.json').stat().st_size if (ROOT / 'data' / 'abu' / 'patterns.json').exists() else 0
        }
    }
    
    return status

def get_todos() -> List[Dict]:
    """获取当前TODO列表"""
    # 从TODO系统获取
    todos = []
    
    # 手动管理的TODO（重要任务）
    todos.extend([
        {
            'id': 'extract_ocr_text_from_pattern_images',
            'content': '批量OCR提取模式库图片中的文字说明（如Gap bar交易策略文字），更新到数据库chart_features_json字段',
            'status': 'in_progress',
            'progress': '5/1004 (0.5%)',
            'estimated_time': '约1小时',
            'script': 'scripts/extract_pattern_ocr_text.py'
        },
        {
            'id': 'implement_pattern_library_realtime_matching',
            'content': '实施模式库实时匹配方案：将PDF识别的模式库与实时价格图表（BTC/ETH等）进行匹配，生成交易信号',
            'status': 'pending',
            'script': 'scripts/pattern_library_matcher.py'
        },
        {
            'id': 'organize_pdf_processing_pipeline',
            'content': '整合PDF处理完整流程：从PDF提取→图片导出→模式识别→OCR文字提取→数据库存储，形成端到端自动化流程，每次有更新都要整合进去',
            'status': 'pending',
            'script': 'scripts/abu_complete_pipeline.py'
        }
    ])
    
    return todos

def get_work_plan() -> Dict:
    """获取工作计划"""
    plan = {
        'current_focus': 'OCR文字提取',
        'next_steps': [
            '完成OCR批量提取（约1小时）',
            '查看OCR提取结果，确认文字说明是否正确',
            '实施模式库实时匹配方案',
            '整合PDF处理完整流程'
        ],
        'recent_completions': [
            'llava图片模式识别已完成（850条已分类）',
            '详细日志系统已实现',
            '模式库实时匹配方案已设计'
        ]
    }
    return plan

def save_status():
    """保存系统状态到文件"""
    logger = get_detailed_logger('gm_status')
    logger.log_startup({'action': 'save_status'})
    
    status = get_system_status()
    todos = get_todos()
    plan = get_work_plan()
    
    # 保存JSON
    full_data = {
        'status': status,
        'todos': todos,
        'work_plan': plan,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    JSON_FILE.write_text(
        json.dumps(full_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # 生成Markdown文档
    md_content = generate_markdown(full_data)
    STATUS_FILE.write_text(md_content, encoding='utf-8')
    
    print(f"\n✓ 状态已保存到:")
    print(f"  - {STATUS_FILE}")
    print(f"  - {JSON_FILE}")
    
    logger.info("状态保存完成", {'files': [str(STATUS_FILE), str(JSON_FILE)]})
    logger.log_shutdown(exit_code=0)
    
    return full_data

def generate_markdown(data: Dict) -> str:
    """生成Markdown格式的状态文档"""
    status = data['status']
    todos = data['todos']
    plan = data['work_plan']
    
    md = f"""# 青鸟系统工作状态

> **最后更新**: {data['last_updated']}  
> **版本**: {status.get('version', '1.0')}

---

## 📊 系统状态

### 数据库统计

"""
    
    # 数据库状态
    for trader, stats in status.get('system', {}).items():
        if 'error' in stats:
            md += f"\n**{trader.upper()}**: ❌ 错误 - {stats['error']}\n"
        else:
            md += f"\n#### {trader.upper()}\n\n"
            md += f"- 交易信号数: {stats.get('signals_count', 0):,}\n"
            md += f"- 最新信号: {stats.get('latest_signal', 'N/A')}\n"
            
            if trader == 'abu' and stats.get('pattern_count'):
                md += f"\n**模式库统计:**\n"
                md += f"- 总模式数: {stats.get('pattern_count', 0):,}\n"
                md += f"- 已分类: {stats.get('pattern_classified', 0):,}\n"
                md += f"- OCR文字提取: {stats.get('pattern_ocr_extracted', 0):,}\n"
    
    md += f"""
### 文件状态

"""
    
    for file_name, file_info in status.get('files', {}).items():
        if file_info['exists']:
            size_mb = file_info['size'] / (1024 * 1024)
            md += f"- `{file_name}`: ✅ 存在 ({size_mb:.2f} MB)\n"
        else:
            md += f"- `{file_name}`: ❌ 不存在\n"
    
    md += f"""
---

## ✅ TODO 任务

"""
    
    # 按状态分组
    by_status = {}
    for todo in todos:
        status_key = todo.get('status', 'pending')
        if status_key not in by_status:
            by_status[status_key] = []
        by_status[status_key].append(todo)
    
    for status_key in ['in_progress', 'pending', 'completed']:
        if status_key in by_status:
            status_emoji = {'in_progress': '🔄', 'pending': '⏳', 'completed': '✅'}.get(status_key, '•')
            status_name = {'in_progress': '进行中', 'pending': '待处理', 'completed': '已完成'}.get(status_key, status_key)
            
            md += f"\n### {status_emoji} {status_name}\n\n"
            
            for todo in by_status[status_key]:
                md += f"- **[{todo.get('id', 'N/A')}]** {todo.get('content', '')}\n"
                if todo.get('progress'):
                    md += f"  - 进度: {todo['progress']}\n"
                if todo.get('estimated_time'):
                    md += f"  - 预计时间: {todo['estimated_time']}\n"
                if todo.get('script'):
                    md += f"  - 脚本: `{todo['script']}`\n"
                md += "\n"
    
    md += f"""
---

## 📋 工作计划

### 当前重点

{plan.get('current_focus', 'N/A')}

### 下一步行动

"""
    
    for i, step in enumerate(plan.get('next_steps', []), 1):
        md += f"{i}. {step}\n"
    
    md += f"""
### 最近完成

"""
    
    for completion in plan.get('recent_completions', []):
        md += f"- ✅ {completion}\n"
    
    md += f"""
---

## 🔧 快速命令

### OCR提取
```bash
# 测试运行
python scripts/extract_pattern_ocr_text.py --limit 10 --dry-run

# 批量处理
python scripts/extract_pattern_ocr_text.py --limit 100

# 后台运行（Windows）
start /b python scripts/extract_pattern_ocr_text.py > ocr_log.txt 2>&1
```

### 查看结果
```bash
# 查看模式库
python scripts/pattern_library_matcher.py --list-library

# 查看OCR文字
python scripts/view_pattern_text_descriptions.py --limit 20

# 查看完整结果
python scripts/view_llava_complete_results.py
```

### PDF处理流程
```bash
# 完整流程
python scripts/abu_complete_pipeline.py --pdf path/to/book.pdf

# 只执行OCR
python scripts/abu_complete_pipeline.py --skip step1,step2,step3
```

---

## 📝 备注

- 此文档由 `scripts/gm_status.py` 自动生成
- 运行 `python scripts/gm_status.py --save` 更新状态
- 运行 `python scripts/gm_status.py --show` 查看状态

---

**生成时间**: {data['last_updated']}
"""
    
    return md

def show_status():
    """显示当前状态"""
    if not JSON_FILE.exists():
        print("❌ 状态文件不存在，请先运行 --save")
        return 1
    
    data = json.loads(JSON_FILE.read_text(encoding='utf-8'))
    
    print("\n" + "="*80)
    print("青鸟系统工作状态")
    print("="*80 + "\n")
    
    print(f"最后更新: {data['last_updated']}\n")
    
    # 显示TODO
    print("TODO任务:")
    print("-" * 80)
    for todo in data['todos']:
        status_icon = {'in_progress': '🔄', 'pending': '⏳', 'completed': '✅'}.get(todo.get('status'), '•')
        print(f"{status_icon} [{todo.get('status', 'unknown').upper()}] {todo.get('content', '')}")
        if todo.get('progress'):
            print(f"   进度: {todo['progress']}")
        if todo.get('estimated_time'):
            print(f"   预计时间: {todo['estimated_time']}")
        print()
    
    # 显示工作计划
    plan = data['work_plan']
    print("\n当前重点:")
    print(f"  {plan.get('current_focus', 'N/A')}")
    
    print("\n下一步行动:")
    for i, step in enumerate(plan.get('next_steps', []), 1):
        print(f"  {i}. {step}")
    
    # 显示系统状态摘要
    print("\n系统状态摘要:")
    print("-" * 80)
    for trader, stats in data['status'].get('system', {}).items():
        if 'error' not in stats:
            print(f"{trader.upper()}: 信号={stats.get('signals_count', 0)}, 最新={stats.get('latest_signal', 'N/A')}")
            if trader == 'abu' and stats.get('pattern_count'):
                print(f"  模式库: {stats.get('pattern_count', 0)}条, 已分类={stats.get('pattern_classified', 0)}, OCR={stats.get('pattern_ocr_extracted', 0)}")
    
    print(f"\n详细状态文档: {STATUS_FILE}")
    
    return 0

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description='GM - 全局管理器（保存/查询系统状态）')
    ap.add_argument('--save', action='store_true', help='保存当前状态')
    ap.add_argument('--show', action='store_true', help='显示当前状态')
    ap.add_argument('--update-todo', action='store_true', help='更新TODO列表')
    
    args = ap.parse_args()
    
    if args.save:
        save_status()
        return 0
    elif args.show:
        return show_status()
    elif args.update_todo:
        save_status()  # 重新保存会更新TODO
        return 0
    else:
        # 默认显示
        return show_status()

if __name__ == '__main__':
    sys.exit(main())

