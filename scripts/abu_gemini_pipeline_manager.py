#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini处理流程管理器

功能：
- 管理Gemini分析的完整流程：解析 -> 数据库更新 -> 轮询补充
- 定时轮询（默认4小时）获取最新Gemini输出并补充处理
- 完整的进度跟踪（包含所有步骤）
- 日志和监控功能，异常处理和关键信息记录

步骤：
1. 解析Gemini输出（parse）
2. 更新pattern_library表（update_db）
3. 定时轮询获取最新Gemini输出并补充

进度跟踪：
- 步骤1：Gemini分析（来自gemini_analysis_state.json）
- 步骤2：解析Gemini输出
- 步骤3：更新pattern_library表
- 步骤4：轮询补充（增量处理）

使用：
    # 运行一次（处理已有输出）
    python scripts/abu_gemini_pipeline_manager.py

    # 启用轮询模式（每4小时）
    python scripts/abu_gemini_pipeline_manager.py --poll --interval 4

    # 只运行解析步骤
    python scripts/abu_gemini_pipeline_manager.py --step parse

    # 只运行数据库更新步骤
    python scripts/abu_gemini_pipeline_manager.py --step update_db
"""

from __future__ import annotations
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
SCRIPTS = ROOT / 'scripts'
OUTPUTS = ROOT / 'outputs'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 日志系统
try:
    from system_logger import SystemLogger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

# 文件路径
GEMINI_ANNOTATIONS_FILE = OUTPUTS / 'abu_gemini_annotations_enhanced.jsonl'
GEMINI_PARSED_FILE = OUTPUTS / 'abu_gemini_parsed.jsonl'
GEMINI_STATE_FILE = OUTPUTS / 'abu_gemini_analysis_state.json'
PIPELINE_STATE_FILE = OUTPUTS / 'abu_gemini_pipeline_state.json'
PIPELINE_LOG_FILE = OUTPUTS / 'abu_gemini' / 'pipeline_manager.log'

# 确保日志目录存在
PIPELINE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


class PipelineState:
    """处理流程状态管理"""
    
    def __init__(self, state_file: Path = PIPELINE_STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            try:
                with self.state_file.open('r', encoding='utf-8') as f:
                    state = json.load(f)
                    # 确保包含ml_training步骤（向后兼容）
                    if 'steps' in state and 'ml_training' not in state['steps']:
                        state['steps']['ml_training'] = {
                            'status': 'pending',
                            'last_trained_samples': 0,
                            'accuracy': 0.0,
                            'last_update': None
                        }
                    return state
            except Exception as e:
                print(f"⚠️  加载状态文件失败: {e}", file=sys.stderr)
        
        # 默认状态
        return {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_poll_time': None,
            'steps': {
                'gemini_analysis': {
                    'status': 'running',
                    'total': 9000,  # 完整版约9000+张图片
                    'completed': 0,
                    'failed': 0,
                    'skipped': 0,
                    'last_update': None
                },
                'parse': {
                    'status': 'pending',
                    'total': 0,
                    'processed': 0,
                    'failed': 0,
                    'last_update': None,
                    'last_processed_line': 0
                },
                'update_db': {
                    'status': 'pending',
                    'total': 0,
                    'updated': 0,
                    'matched': 0,
                    'skipped': 0,
                    'failed': 0,
                    'last_update': None,
                    'last_processed_line': 0
                },
                'ml_training': {
                    'status': 'pending',
                    'last_trained_samples': 0,
                    'accuracy': 0.0,
                    'last_update': None
                }
            },
            'errors': []
        }
    
    def save(self):
        """保存状态"""
        self.state['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self.state_file.open('w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存状态文件失败: {e}", file=sys.stderr)
    
    def update_gemini_analysis_state(self):
        """更新Gemini分析状态（从gemini_analysis_state.json读取）"""
        if GEMINI_STATE_FILE.exists():
            try:
                with GEMINI_STATE_FILE.open('r', encoding='utf-8') as f:
                    gemini_state = json.load(f)
                
                step_state = self.state['steps']['gemini_analysis']
                # 从状态文件读取实际总数，如果没有则动态计算或使用9000作为上限
                step_state['total'] = gemini_state.get('total_images', 9000)
                step_state['completed'] = gemini_state.get('completed_count', 0)
                step_state['failed'] = gemini_state.get('failed_count', 0)
                step_state['skipped'] = gemini_state.get('skipped_count', 0)
                step_state['last_update'] = gemini_state.get('last_update')
                
                # 判断状态
                total = step_state['total']
                completed = step_state['completed']
                if completed >= total:
                    step_state['status'] = 'completed'
                elif completed > 0:
                    step_state['status'] = 'running'
                else:
                    step_state['status'] = 'pending'
                
                return True
            except Exception as e:
                print(f"⚠️  读取Gemini分析状态失败: {e}", file=sys.stderr)
                return False
        return False
    
    def get_progress_summary(self) -> Dict:
        """获取进度摘要"""
        summary = {
            'overall_progress': 0.0,
            'steps': {}
        }
        
        # 步骤1: Gemini分析
        gemini_step = self.state['steps']['gemini_analysis']
        gemini_total = gemini_step['total']
        gemini_completed = gemini_step['completed'] + gemini_step['skipped']
        gemini_progress = (gemini_completed / gemini_total * 100) if gemini_total > 0 else 0.0
        summary['steps']['gemini_analysis'] = {
            'status': gemini_step['status'],
            'progress': gemini_progress,
            'completed': gemini_completed,
            'total': gemini_total
        }
        
        # 步骤2: 解析
        parse_step = self.state['steps']['parse']
        parse_progress = (parse_step['processed'] / parse_step['total'] * 100) if parse_step['total'] > 0 else 0.0
        summary['steps']['parse'] = {
            'status': parse_step['status'],
            'progress': parse_progress,
            'processed': parse_step['processed'],
            'total': parse_step['total']
        }
        
        # 步骤3: 数据库更新
        update_step = self.state['steps']['update_db']
        update_progress = (update_step['updated'] / update_step['total'] * 100) if update_step['total'] > 0 else 0.0
        summary['steps']['update_db'] = {
            'status': update_step['status'],
            'progress': update_progress,
            'updated': update_step['updated'],
            'total': update_step['total']
        }
        
        # 总体进度（三个步骤各占33.3%）
        overall = (gemini_progress * 0.333 + parse_progress * 0.333 + update_progress * 0.333)
        summary['overall_progress'] = overall
        
        return summary
    
    def add_error(self, step: str, error: str):
        """添加错误记录"""
        error_record = {
            'step': step,
            'error': error,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.state['errors'].append(error_record)
        # 只保留最近100条错误
        if len(self.state['errors']) > 100:
            self.state['errors'] = self.state['errors'][-100:]


class PipelineLogger:
    """处理流程日志记录器"""
    
    def __init__(self, log_file: Path = PIPELINE_LOG_FILE):
        self.log_file = log_file
        self.system_logger = SystemLogger() if LOGGER_AVAILABLE else None
    
    def log(self, level: str, message: str, details: Dict = None):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'details': details or {}
        }
        
        # 写入文件
        try:
            with self.log_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  写入日志失败: {e}", file=sys.stderr)
        
        # 控制台输出
        if level in ['error', 'critical']:
            print(f"[{timestamp}] {level.upper()}: {message}", file=sys.stderr)
        elif level == 'warning':
            print(f"[{timestamp}] WARNING: {message}", file=sys.stdout)
        else:
            print(f"[{timestamp}] {message}", file=sys.stdout)
        
        # 系统日志
        if self.system_logger:
            try:
                if level == 'error':
                    self.system_logger.log_error(details=details)
                elif level == 'warning':
                    self.system_logger.log_warning(details=details)
            except Exception:
                pass
    
    def log_step_start(self, step: str, details: Dict = None):
        """记录步骤开始"""
        self.log('info', f"步骤开始: {step}", details)
    
    def log_step_complete(self, step: str, details: Dict = None):
        """记录步骤完成"""
        self.log('info', f"步骤完成: {step}", details)
    
    def log_step_error(self, step: str, error: str, details: Dict = None):
        """记录步骤错误"""
        error_details = {'error': error, **(details or {})}
        self.log('error', f"步骤错误: {step} - {error}", error_details)
    
    def log_progress(self, step: str, current: int, total: int, message: str = None):
        """记录进度"""
        progress_pct = (current / total * 100) if total > 0 else 0.0
        details = {
            'step': step,
            'current': current,
            'total': total,
            'progress_pct': progress_pct
        }
        if message:
            details['message'] = message
        self.log('info', f"进度更新: {step} - {current}/{total} ({progress_pct:.1f}%)", details)


class GeminiPipelineManager:
    """Gemini处理流程管理器"""
    
    def __init__(self, poll_interval_hours: int = 4):
        self.poll_interval_hours = poll_interval_hours
        self.poll_interval_seconds = poll_interval_hours * 3600
        self.state = PipelineState()
        self.logger = PipelineLogger()
    
    def update_gemini_state(self):
        """更新Gemini分析状态"""
        self.state.update_gemini_analysis_state()
        self.state.save()
    
    def run_parse_step(self) -> bool:
        """运行解析步骤"""
        self.logger.log_step_start('parse')
        self.state.state['steps']['parse']['status'] = 'running'
        self.state.save()
        
        try:
            # 检查输入文件
            if not GEMINI_ANNOTATIONS_FILE.exists():
                self.logger.log('warning', f"输入文件不存在: {GEMINI_ANNOTATIONS_FILE}")
                self.state.state['steps']['parse']['status'] = 'pending'
                self.state.save()
                return False
            
            # 统计输入文件行数
            input_lines = sum(1 for _ in GEMINI_ANNOTATIONS_FILE.open('r', encoding='utf-8'))
            last_processed = self.state.state['steps']['parse']['last_processed_line']
            
            # 如果已有输出文件，统计已处理的行数
            if GEMINI_PARSED_FILE.exists():
                parsed_lines = sum(1 for _ in GEMINI_PARSED_FILE.open('r', encoding='utf-8'))
                last_processed = parsed_lines
            
            # 如果没有新数据需要处理，跳过
            if last_processed >= input_lines:
                self.logger.log('info', f"解析步骤: 无新数据需要处理 ({last_processed}/{input_lines})")
                self.state.state['steps']['parse']['status'] = 'completed'
                self.state.state['steps']['parse']['total'] = input_lines
                self.state.state['steps']['parse']['processed'] = input_lines
                self.state.save()
                return True
            
            # 运行解析脚本
            cmd = [
                sys.executable,
                str(SCRIPTS / 'abu_parse_gemini_output.py'),
                '--input', str(GEMINI_ANNOTATIONS_FILE),
                '--output', str(GEMINI_PARSED_FILE)
            ]
            
            self.logger.log('info', f"运行解析脚本: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                self.logger.log_step_error('parse', f"解析脚本失败: {error_msg}")
                self.state.add_error('parse', error_msg)
                self.state.state['steps']['parse']['status'] = 'failed'
                self.state.save()
                return False
            
            # 统计输出文件行数
            if GEMINI_PARSED_FILE.exists():
                parsed_lines = sum(1 for _ in GEMINI_PARSED_FILE.open('r', encoding='utf-8'))
                self.state.state['steps']['parse']['total'] = input_lines
                self.state.state['steps']['parse']['processed'] = parsed_lines
                self.state.state['steps']['parse']['last_processed_line'] = parsed_lines
                self.state.state['steps']['parse']['status'] = 'completed' if parsed_lines >= input_lines else 'running'
                self.state.state['steps']['parse']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                self.logger.log_progress('parse', parsed_lines, input_lines)
                self.logger.log_step_complete('parse', {'processed': parsed_lines, 'total': input_lines})
            else:
                self.state.state['steps']['parse']['status'] = 'failed'
                self.logger.log_step_error('parse', "输出文件未生成")
            
            self.state.save()
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.logger.log_step_error('parse', error_msg)
            self.state.add_error('parse', error_msg)
            self.state.state['steps']['parse']['status'] = 'failed'
            self.state.save()
            return False
    
    def run_update_db_step(self) -> bool:
        """运行数据库更新步骤"""
        self.logger.log_step_start('update_db')
        self.state.state['steps']['update_db']['status'] = 'running'
        self.state.save()
        
        try:
            # 检查输入文件
            if not GEMINI_PARSED_FILE.exists():
                self.logger.log('warning', f"输入文件不存在: {GEMINI_PARSED_FILE}")
                self.state.state['steps']['update_db']['status'] = 'pending'
                self.state.save()
                return False
            
            # 统计输入文件行数
            input_lines = sum(1 for _ in GEMINI_PARSED_FILE.open('r', encoding='utf-8'))
            last_processed = self.state.state['steps']['update_db']['last_processed_line']
            
            # 运行数据库更新脚本（增量处理通过skip-existing实现）
            cmd = [
                sys.executable,
                str(SCRIPTS / 'abu_update_pattern_library_from_gemini.py'),
                '--input', str(GEMINI_PARSED_FILE),
                '--skip-existing'
            ]
            
            self.logger.log('info', f"运行数据库更新脚本: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                self.logger.log_step_error('update_db', f"数据库更新脚本失败: {error_msg}")
                self.state.add_error('update_db', error_msg)
                self.state.state['steps']['update_db']['status'] = 'failed'
                self.state.save()
                return False
            
            # 解析输出，提取统计信息
            output = result.stdout
            matched = 0
            updated = 0
            skipped = 0
            errors = 0
            
            # 从输出中提取统计信息
            for line in output.split('\n'):
                if '总记录数:' in line:
                    try:
                        total_match = line.split('总记录数:')[1].strip().split()[0]
                        input_lines = int(total_match)
                    except:
                        pass
                elif '匹配记录:' in line:
                    try:
                        matched = int(line.split('匹配记录:')[1].strip().split()[0])
                    except:
                        pass
                elif '更新记录:' in line:
                    try:
                        updated = int(line.split('更新记录:')[1].strip().split()[0])
                    except:
                        pass
                elif '跳过记录:' in line:
                    try:
                        skipped = int(line.split('跳过记录:')[1].strip().split()[0])
                    except:
                        pass
                elif '错误记录:' in line:
                    try:
                        errors = int(line.split('错误记录:')[1].strip().split()[0])
                    except:
                        pass
            
            self.state.state['steps']['update_db']['total'] = input_lines
            self.state.state['steps']['update_db']['matched'] = matched
            self.state.state['steps']['update_db']['updated'] = updated
            self.state.state['steps']['update_db']['skipped'] = skipped
            self.state.state['steps']['update_db']['failed'] = errors
            self.state.state['steps']['update_db']['last_processed_line'] = input_lines
            self.state.state['steps']['update_db']['status'] = 'completed'
            self.state.state['steps']['update_db']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.log_step_complete('update_db', {'total': input_lines})
            self.state.save()
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.logger.log_step_error('update_db', error_msg)
            self.state.add_error('update_db', error_msg)
            self.state.state['steps']['update_db']['status'] = 'failed'
            self.state.save()
            return False
    
    def run_ml_training_step(self) -> bool:
        """运行ML模型训练步骤（增量训练）"""
        self.logger.log_step_start('ml_training')
        
        try:
            # 检查是否需要训练
            from ml_dl.abu_price_action_learner import PriceActionLearner
            from db_manager_trader import TraderDBManager
            
            learner = PriceActionLearner()
            
            # 检查数据量
            db = TraderDBManager('abu')
            conn = db._get_connection()
            current_count = conn.execute('''
                SELECT COUNT(*) FROM pattern_library
                WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
            ''').fetchone()[0]
            db.close()
            
            # 检查是否需要训练
            needs_retrain = learner.check_needs_retrain(current_count)
            
            if not needs_retrain:
                self.logger.log('info', f"ML训练步骤: 数据量未增加10%以上，跳过训练 (当前: {current_count}, 上次: {learner.model_state.get('last_trained_samples', 0)})")
                self.state.state['steps']['ml_training']['status'] = 'skipped'
                self.state.save()
                return True
            
            # 检查是否有已训练的模型
            model_file = ROOT / 'models' / 'abu' / 'price_action_model.pkl'
            is_retrain = model_file.exists()
            
            if is_retrain:
                self.logger.log('info', f"开始增量训练（当前数据量: {current_count}）")
                result = learner.train(retrain=True)
            else:
                self.logger.log('info', f"开始首次训练（当前数据量: {current_count}）")
                result = learner.train(retrain=False)
            
            if result.get('success'):
                self.state.state['steps']['ml_training']['status'] = 'completed'
                self.state.state['steps']['ml_training']['last_trained_samples'] = result.get('total_samples', 0)
                self.state.state['steps']['ml_training']['accuracy'] = result.get('test_accuracy', 0.0)
                self.state.state['steps']['ml_training']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.state.save()
                
                self.logger.log_step_complete('ml_training', {
                    'samples': result.get('total_samples', 0),
                    'accuracy': result.get('test_accuracy', 0.0),
                    'is_retrain': is_retrain
                })
                return True
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.log_step_error('ml_training', error_msg)
                self.state.add_error('ml_training', error_msg)
                self.state.state['steps']['ml_training']['status'] = 'failed'
                self.state.save()
                return False
                
        except ImportError as e:
            error_msg = f"ML模块导入失败: {e}"
            self.logger.log_step_error('ml_training', error_msg)
            self.state.add_error('ml_training', error_msg)
            self.state.state['steps']['ml_training']['status'] = 'pending'
            self.state.save()
            return False
        except Exception as e:
            error_msg = str(e)
            self.logger.log_step_error('ml_training', error_msg)
            self.state.add_error('ml_training', error_msg)
            self.state.state['steps']['ml_training']['status'] = 'failed'
            self.state.save()
            return False
    
    def run_all_steps(self):
        """运行所有步骤"""
        self.logger.log('info', "=" * 80)
        self.logger.log('info', "开始运行Gemini处理流程")
        self.logger.log('info', "=" * 80)
        
        # 更新Gemini分析状态
        self.update_gemini_state()
        
        # 显示当前进度
        self.print_progress()
        
        # 步骤1: 解析（如果还没完成）
        if self.state.state['steps']['parse']['status'] != 'completed':
            if not self.run_parse_step():
                self.logger.log('error', "解析步骤失败，停止处理")
                return False
        
        # 步骤2: 数据库更新（如果还没完成）
        if self.state.state['steps']['update_db']['status'] != 'completed':
            if not self.run_update_db_step():
                self.logger.log('error', "数据库更新步骤失败，停止处理")
                return False
        
        # 步骤3: ML模型训练（增量训练）
        # 检查是否需要训练（数据量增加10%以上）
        if self.state.state['steps']['update_db']['status'] == 'completed':
            self.run_ml_training_step()
        
        # 显示最终进度
        self.print_progress()
        self.logger.log('info', "=" * 80)
        self.logger.log('info', "Gemini处理流程完成")
        self.logger.log('info', "=" * 80)
        
        return True
    
    def poll_and_process(self):
        """轮询并处理新数据"""
        self.logger.log('info', f"开始轮询模式，间隔: {self.poll_interval_hours}小时")
        
        try:
            while True:
                # 运行所有步骤
                self.run_all_steps()
                
                # 更新轮询时间
                self.state.state['last_poll_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.state.save()
                
                # 计算下次运行时间
                next_run = datetime.now() + timedelta(seconds=self.poll_interval_seconds)
                self.logger.log('info', f"下次轮询时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.log('info', f"等待 {self.poll_interval_hours} 小时...")
                
                # 等待
                time.sleep(self.poll_interval_seconds)
        
        except KeyboardInterrupt:
            self.logger.log('info', "轮询已停止")
    
    def print_progress(self):
        """打印进度摘要"""
        self.update_gemini_state()
        summary = self.state.get_progress_summary()
        
        print("\n" + "=" * 80)
        print("Gemini处理流程进度")
        print("=" * 80)
        print(f"\n总体进度: {summary['overall_progress']:.1f}%")
        print()
        
        # 步骤1: Gemini分析
        gemini = summary['steps']['gemini_analysis']
        print(f"步骤1 - Gemini分析:")
        print(f"  状态: {gemini['status']}")
        print(f"  进度: {gemini['progress']:.1f}% ({gemini['completed']}/{gemini['total']})")
        
        # 步骤2: 解析
        parse = summary['steps']['parse']
        print(f"\n步骤2 - 解析Gemini输出:")
        print(f"  状态: {parse['status']}")
        print(f"  进度: {parse['progress']:.1f}% ({parse['processed']}/{parse['total']})")
        
        # 步骤3: 数据库更新
        update = summary['steps']['update_db']
        update_step_state = self.state.state['steps']['update_db']
        print(f"\n步骤3 - 更新pattern_library表:")
        print(f"  状态: {update['status']}")
        print(f"  进度: {update['progress']:.1f}% (匹配: {update_step_state.get('matched', 0)}, 更新: {update_step_state.get('updated', 0)}, 跳过: {update_step_state.get('skipped', 0)})")
        
        # 步骤4: ML模型训练
        ml_training_step = self.state.state['steps']['ml_training']
        print(f"\n步骤4 - ML模型训练:")
        print(f"  状态: {ml_training_step.get('status', 'pending')}")
        if ml_training_step.get('last_trained_samples', 0) > 0:
            print(f"  上次训练样本数: {ml_training_step.get('last_trained_samples', 0)}")
            print(f"  准确率: {ml_training_step.get('accuracy', 0.0):.4f}")
        
        print("\n" + "=" * 80 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU Gemini处理流程管理器')
    parser.add_argument('--poll', action='store_true', help='启用轮询模式')
    parser.add_argument('--interval', type=int, default=4, help='轮询间隔（小时），默认4小时')
    parser.add_argument('--step', type=str, choices=['parse', 'update_db'], help='只运行指定步骤')
    
    args = parser.parse_args()
    
    manager = GeminiPipelineManager(poll_interval_hours=args.interval)
    
    if args.step:
        # 只运行指定步骤
        if args.step == 'parse':
            manager.run_parse_step()
        elif args.step == 'update_db':
            manager.run_update_db_step()
    elif args.poll:
        # 轮询模式
        manager.poll_and_process()
    else:
        # 运行一次
        manager.run_all_steps()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

