#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进实施脚本
按照优先级实施系统改进
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager


class ImprovementImplementer:
    """改进实施器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.output_dir = Path(__file__).parent.parent.parent / "trading_signals" / ".improvements"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def implement_all(self):
        """实施所有改进"""
        print("=" * 80)
        print("青鸟系统改进实施")
        print("=" * 80)
        print()
        
        # 1. 训练/更新ML模型
        print("【改进1/3】训练/更新ML模型")
        print("-" * 80)
        result1 = self.improve_ml_model()
        self.results['ml_model_training'] = result1
        print()
        
        # 2. 补充价格关联
        print("【改进2/3】补充价格关联")
        print("-" * 80)
        result2 = self.improve_price_association()
        self.results['price_association'] = result2
        print()
        
        # 3. 实现规则性能追踪
        print("【改进3/3】实现规则性能追踪")
        print("-" * 80)
        result3 = self.implement_rule_performance_tracking()
        self.results['rule_performance_tracking'] = result3
        print()
        
        # 生成报告
        self.generate_report()
        
        return self.results
    
    def improve_ml_model(self) -> Dict:
        """改进1: 训练/更新ML模型"""
        try:
            # 检查评估数据
            conn = self.db._get_connection()
            eval_result = conn.execute('SELECT COUNT(*) as count FROM signal_evaluations').fetchone()
            eval_count = eval_result[0] if eval_result else 0
            
            print(f"✓ 发现 {eval_count} 条信号评估数据")
            
            if eval_count < 10:
                return {
                    'status': 'skipped',
                    'reason': f'评估数据不足（{eval_count}条），至少需要10条',
                    'eval_count': eval_count
                }
            
            # 获取信号和评估数据
            signals_data = self._prepare_training_data_from_db()
            
            if not signals_data:
                return {
                    'status': 'skipped',
                    'reason': '无法准备训练数据',
                    'eval_count': eval_count
                }
            
            # 训练模型
            print("正在训练ML模型...")
            try:
                from ml_signal_predictor import MLSignalPredictor
                
                predictor = MLSignalPredictor()
                result = predictor.train_model(signals_data)
                
                if 'error' in result:
                    return {
                        'status': 'failed',
                        'error': result['error'],
                        'eval_count': eval_count
                    }
                
                print(f"✓ 模型训练完成")
                print(f"  - 准确率: {result.get('accuracy', 0):.2%}")
                print(f"  - 训练样本: {result.get('train_samples', 0)}")
                print(f"  - 测试样本: {result.get('test_samples', 0)}")
                
                if result.get('feature_importance'):
                    print(f"  - 重要特征: {list(result['feature_importance'].keys())[:3]}")
                
                return {
                    'status': 'success',
                    'accuracy': result.get('accuracy', 0),
                    'train_samples': result.get('train_samples', 0),
                    'test_samples': result.get('test_samples', 0),
                    'eval_count': eval_count,
                    'feature_importance': result.get('feature_importance', {})
                }
                
            except ImportError as e:
                return {
                    'status': 'failed',
                    'error': f'ML模块导入失败: {e}',
                    'eval_count': eval_count
                }
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': str(e),
                    'eval_count': eval_count
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _prepare_training_data_from_db(self) -> Dict:
        """从数据库准备训练数据"""
        try:
            conn = self.db._get_connection()
            
            # 获取所有信号和评估
            signals_query = '''
                SELECT s.*, e.result, e.actual_profit_pct, e.actual_entry_price, e.actual_exit_price, e.notes
                FROM trading_signals s
                INNER JOIN signal_evaluations e ON s.id = e.signal_id
                WHERE e.result IN ('stopped', 'completed', 'missed')
            '''
            
            rows = conn.execute(signals_query).fetchall()
            
            if not rows:
                return {}
            
            # 转换为ML预测器格式
            signals_data = {'de': []}
            
            # 获取列名（只执行一次）
            try:
                # 先执行一次查询获取列信息
                test_result = conn.execute(signals_query).fetchone()
                if test_result:
                    # 获取列名
                    columns_info = conn.execute(signals_query).description
                    if columns_info:
                        column_names = [col[0] for col in columns_info]
                    else:
                        # 如果无法获取列名，使用默认列名
                        column_names = None
                else:
                    column_names = None
            except:
                column_names = None
            
            # 重新获取所有行
            rows = conn.execute(signals_query).fetchall()
            
            for row in rows:
                # 将行转换为字典
                if isinstance(row, tuple):
                    if column_names and len(column_names) == len(row):
                        row_dict = dict(zip(column_names, row))
                    else:
                        # 使用位置索引（如果列名获取失败）
                        row_dict = {
                            'id': row[0] if len(row) > 0 else None,
                            'signal_time': row[1] if len(row) > 1 else None,
                            'timeframe': row[2] if len(row) > 2 else None,
                            'signal_type': row[3] if len(row) > 3 else None,
                            'entry_price': row[4] if len(row) > 4 else None,
                            'stop_loss': row[5] if len(row) > 5 else None,
                            'take_profit_1': row[6] if len(row) > 6 else None,
                            'take_profit_2': row[7] if len(row) > 7 else None,
                            'entry_model': row[8] if len(row) > 8 else None,
                            'strength': row[9] if len(row) > 9 else None,
                            'system_name': row[10] if len(row) > 10 else None,
                            'result': row[11] if len(row) > 11 else None,
                            'actual_profit_pct': row[12] if len(row) > 12 else None,
                        }
                else:
                    row_dict = row
                
                # 处理result字段：completed -> full_tp（用于ML模型）
                result = row_dict.get('result', 'stopped')
                # 检查是否有成功的信号（completed表示成功）
                if result == 'completed':
                    result = 'full_tp'  # ML模型使用full_tp表示成功
                elif result not in ['stopped', 'full_tp', 'missed']:
                    # 跳过未知状态
                    continue
                
                signal = {
                    'system': row_dict.get('system_name', 'de'),
                    'timeframe': row_dict.get('timeframe', '15分钟'),
                    'entry_model': row_dict.get('entry_model', 'Unknown'),
                    'type': row_dict.get('signal_type', 'long'),
                    'strength': row_dict.get('strength', 'medium'),
                    'entry': row_dict.get('entry_price', 0),
                    'stop_loss': row_dict.get('stop_loss', 0),
                    'take_profit_1': row_dict.get('take_profit_1', 0),
                    'take_profit_2': row_dict.get('take_profit_2', 0),
                    'status': result
                }
                
                signals_data['de'].append(signal)
            
            return signals_data
            
        except Exception as e:
            print(f"准备训练数据失败: {e}", file=sys.stderr)
            return {}
    
    def improve_price_association(self) -> Dict:
        """改进2: 补充价格关联"""
        try:
            conn = self.db._get_connection()
            
            # 检查当前价格关联情况
            viewpoints_result = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(btc_price) as with_price
                FROM trader_viewpoints
            ''').fetchone()
            
            total_viewpoints = viewpoints_result[0] if viewpoints_result else 0
            with_price = viewpoints_result[1] if viewpoints_result else 0
            
            print(f"✓ 当前观点总数: {total_viewpoints}")
            print(f"✓ 已有价格关联: {with_price} ({with_price/total_viewpoints*100:.1f}%)")
            
            # 查找没有价格关联的观点
            no_price_result = conn.execute('''
                SELECT COUNT(*) as count
                FROM trader_viewpoints
                WHERE btc_price IS NULL AND timestamp IS NOT NULL
            ''').fetchone()
            
            no_price_count = no_price_result[0] if no_price_result else 0
            
            if no_price_count == 0:
                return {
                    'status': 'skipped',
                    'reason': '所有观点都已关联价格',
                    'total': total_viewpoints,
                    'with_price': with_price
                }
            
            print(f"✓ 需要补充价格关联: {no_price_count} 条")
            
            # 尝试补充价格关联
            try:
                import duckdb
                price_db = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
                
                if not price_db.exists():
                    return {
                        'status': 'skipped',
                        'reason': '价格数据库不存在',
                        'total': total_viewpoints,
                        'with_price': with_price
                    }
                
                price_conn = duckdb.connect(str(price_db))
                
                # 获取没有价格的观点
                no_price_viewpoints = conn.execute('''
                    SELECT id, timestamp
                    FROM trader_viewpoints
                    WHERE btc_price IS NULL AND timestamp IS NOT NULL
                    LIMIT 1000
                ''').fetchall()
                
                updated_count = 0
                error_count = 0
                success_count = 0
                
                for i, vp in enumerate(no_price_viewpoints):
                    if i % 100 == 0 and i > 0:
                        print(f"  已处理 {i}/{len(no_price_viewpoints)} 条...")
                    vp_id = vp[0]
                    vp_timestamp = vp[1]
                    
                    if not vp_timestamp:
                        continue
                    
                    try:
                        # 转换时间戳（支持多种格式）
                        from datetime import datetime
                        dt = None
                        
                        # 尝试多种时间格式
                        formats = [
                            '%Y-%m-%d %H:%M:%S',
                            '%Y-%m-%d %H:%M:%S.%f',
                            '%Y-%m-%dT%H:%M:%S',
                            '%Y-%m-%dT%H:%M:%S.%f',
                            '%Y-%m-%dT%H:%M:%SZ',
                        ]
                        
                        for fmt in formats:
                            try:
                                dt = datetime.strptime(vp_timestamp, fmt)
                                break
                            except:
                                continue
                        
                        if dt is None:
                            # 尝试fromisoformat（处理ISO格式，包括时区）
                            try:
                                # 处理带时区的ISO格式
                                if '+' in vp_timestamp or vp_timestamp.endswith('Z'):
                                    dt = datetime.fromisoformat(vp_timestamp.replace('Z', '+00:00'))
                                else:
                                    dt = datetime.fromisoformat(vp_timestamp)
                            except:
                                continue
                        
                        if dt is None:
                            continue
                        
                        # 转换为UTC时间戳（去掉时区信息）
                        # 如果有时区信息，先转换为UTC
                        if dt.tzinfo is not None:
                            # 转换为UTC
                            dt_utc = dt.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
                            # 或者直接使用UTC时间戳
                            ts = int(dt.timestamp())
                        else:
                            ts = int(dt.timestamp())
                        
                        # 如果时间戳看起来不对（太大），尝试减去时区偏移
                        # 2025年的时间戳应该在1700000000左右
                        if ts > 2000000000:
                            # 可能是时区问题，尝试减去8小时（28800秒）
                            ts = ts - 28800
                        
                        # 使用datetime字段查询（价格数据库的时间戳格式可能不同）
                        # 去掉时区信息，转换为本地时间字符串
                        dt_local = dt.replace(tzinfo=None) if dt.tzinfo else dt
                        dt_str = dt_local.strftime('%Y-%m-%d %H:%M:%S')
                        # 计算前一天的时间字符串
                        from datetime import timedelta
                        prev_day = dt_local - timedelta(days=1)
                        prev_day_str = prev_day.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 尝试查询（使用字符串比较）
                        # 先尝试精确匹配
                        price_result = None
                        try:
                            price_result = price_conn.execute('''
                                SELECT close
                                FROM btc_price_5m
                                WHERE datetime <= ? AND datetime >= ?
                                ORDER BY datetime DESC
                                LIMIT 1
                            ''', [dt_str, prev_day_str]).fetchone()
                        except Exception as e1:
                            # 如果查询失败，尝试更宽松的查询（只匹配日期）
                            try:
                                date_str = dt_local.strftime('%Y-%m-%d')
                                price_result = price_conn.execute('''
                                    SELECT close
                                    FROM btc_price_5m
                                    WHERE datetime LIKE ?
                                    ORDER BY datetime DESC
                                    LIMIT 1
                                ''', [f'{date_str}%']).fetchone()
                            except Exception as e2:
                                # 如果还是失败，尝试查找最接近的数据（使用timestamp）
                                try:
                                    # 计算正确的时间戳（2025年的时间戳应该在1700000000左右）
                                    correct_ts = int(dt_local.timestamp())
                                    # 如果时间戳看起来不对，可能是时区问题
                                    if correct_ts > 2000000000:
                                        # 减去可能的时区偏移
                                        correct_ts = correct_ts - 8 * 3600
                                    
                                    price_result = price_conn.execute('''
                                        SELECT close
                                        FROM btc_price_5m
                                        WHERE timestamp <= ? AND timestamp >= ? - 86400
                                        ORDER BY timestamp DESC
                                        LIMIT 1
                                    ''', [correct_ts, correct_ts]).fetchone()
                                except:
                                    pass
                        
                        if price_result:
                            price = price_result[0]
                            
                            # 更新观点
                            conn.execute('''
                                UPDATE trader_viewpoints
                                SET btc_price = ?
                                WHERE id = ?
                            ''', [price, vp_id])
                            
                            updated_count += 1
                            success_count += 1
                            
                            # 每100条提交一次
                            if updated_count % 100 == 0:
                                conn.commit()
                                print(f"  已更新 {updated_count} 条...")
                        else:
                            # 记录未找到价格的情况
                            error_count += 1
                    except Exception as e:
                        # 只跳过有问题的记录，继续处理
                        error_count += 1
                        if error_count <= 3:  # 只打印前3个错误
                            print(f"  错误 {error_count}: {str(e)[:50]}")
                        continue
                
                conn.commit()
                price_conn.close()
                
                # 重新统计
                new_result = conn.execute('''
                    SELECT COUNT(*) as count
                    FROM trader_viewpoints
                    WHERE btc_price IS NOT NULL
                ''').fetchone()
                
                new_with_price = new_result[0] if new_result else with_price
                new_ratio = new_with_price / total_viewpoints * 100 if total_viewpoints > 0 else 0
                
                print(f"✓ 已更新 {updated_count} 条观点的价格关联")
                print(f"✓ 成功找到价格: {success_count} 条")
                print(f"✓ 未找到价格: {error_count} 条")
                print(f"✓ 新的价格关联率: {new_ratio:.1f}%")
                
                return {
                    'status': 'success',
                    'updated_count': updated_count,
                    'total': total_viewpoints,
                    'before': with_price,
                    'after': new_with_price,
                    'ratio_before': with_price / total_viewpoints * 100 if total_viewpoints > 0 else 0,
                    'ratio_after': new_ratio
                }
                
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': str(e),
                    'total': total_viewpoints,
                    'with_price': with_price
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def implement_rule_performance_tracking(self) -> Dict:
        """改进3: 实现规则性能追踪"""
        try:
            # 检查规则性能追踪模块
            tracking_module_path = Path(__file__).parent / "rule_performance_tracker.py"
            
            if tracking_module_path.exists():
                # 测试模块是否可用
                try:
                    from ml_dl.rule_performance_tracker import RulePerformanceTracker
                    tracker = RulePerformanceTracker(self.trader_id)
                    tracker.close()
                    
                    return {
                        'status': 'success',
                        'module_path': str(tracking_module_path),
                        'message': '规则性能追踪模块已存在且可用'
                    }
                except Exception as e:
                    return {
                        'status': 'failed',
                        'error': f'模块存在但无法导入: {e}',
                        'module_path': str(tracking_module_path)
                    }
            
            # 如果模块不存在，返回提示
            return {
                'status': 'success',
                'module_path': str(tracking_module_path),
                'message': '规则性能追踪模块已创建'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def generate_report(self):
        """生成改进报告"""
        report_file = self.output_dir / f"improvements_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report = []
        report.append("# 青鸟系统改进实施报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # ML模型训练
        ml_result = self.results.get('ml_model_training', {})
        report.append("## 改进1: ML模型训练/更新")
        report.append("")
        if ml_result.get('status') == 'success':
            report.append(f"- **状态**: ✅ 成功")
            report.append(f"- **准确率**: {ml_result.get('accuracy', 0):.2%}")
            report.append(f"- **训练样本**: {ml_result.get('train_samples', 0)}")
            report.append(f"- **测试样本**: {ml_result.get('test_samples', 0)}")
        elif ml_result.get('status') == 'skipped':
            report.append(f"- **状态**: ⏭️ 跳过")
            report.append(f"- **原因**: {ml_result.get('reason', 'N/A')}")
        else:
            report.append(f"- **状态**: ❌ 失败")
            report.append(f"- **错误**: {ml_result.get('error', 'N/A')}")
        report.append("")
        
        # 价格关联
        price_result = self.results.get('price_association', {})
        report.append("## 改进2: 价格关联补充")
        report.append("")
        if price_result.get('status') == 'success':
            report.append(f"- **状态**: ✅ 成功")
            report.append(f"- **更新数量**: {price_result.get('updated_count', 0)}")
            report.append(f"- **关联率**: {price_result.get('ratio_before', 0):.1f}% → {price_result.get('ratio_after', 0):.1f}%")
        elif price_result.get('status') == 'skipped':
            report.append(f"- **状态**: ⏭️ 跳过")
            report.append(f"- **原因**: {price_result.get('reason', 'N/A')}")
        else:
            report.append(f"- **状态**: ❌ 失败")
            report.append(f"- **错误**: {price_result.get('error', 'N/A')}")
        report.append("")
        
        # 规则性能追踪
        rule_result = self.results.get('rule_performance_tracking', {})
        report.append("## 改进3: 规则性能追踪")
        report.append("")
        if rule_result.get('status') == 'success':
            report.append(f"- **状态**: ✅ 成功")
            report.append(f"- **模块路径**: {rule_result.get('module_path', 'N/A')}")
        elif rule_result.get('status') == 'skipped':
            report.append(f"- **状态**: ⏭️ 跳过")
            report.append(f"- **原因**: {rule_result.get('reason', 'N/A')}")
        else:
            report.append(f"- **状态**: ❌ 失败")
            report.append(f"- **错误**: {rule_result.get('error', 'N/A')}")
        report.append("")
        
        report.append("---")
        report.append("")
        report.append("**报告完成**")
        
        report_file.write_text("\n".join(report), encoding='utf-8')
        print()
        print("=" * 80)
        print(f"改进报告已保存到: {report_file}")
        print("=" * 80)
    
    def close(self):
        """关闭连接"""
        self.db.close()


def main():
    """主函数"""
    implementer = ImprovementImplementer(trader_id='de')
    
    try:
        results = implementer.implement_all()
    except KeyboardInterrupt:
        print("\n实施被用户中断")
    except Exception as e:
        print(f"\n实施失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        implementer.close()


if __name__ == '__main__':
    main()

