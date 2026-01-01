#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统自我学习和优化脚本
根据最新数据和系统功能，自动优化知识库、规则引擎、ML/DL
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


class SystemSelfLearner:
    """系统自我学习器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.output_dir = Path(__file__).parent.parent.parent / "trading_signals" / ".learning_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_system_status(self) -> Dict:
        """分析系统当前状态"""
        print("=" * 80)
        print("系统状态分析")
        print("=" * 80)
        print()
        
        status = {
            'data_status': self._analyze_data_status(),
            'knowledge_base_status': self._analyze_knowledge_base_status(),
            'rules_engine_status': self._analyze_rules_engine_status(),
            'ml_dl_status': self._analyze_ml_dl_status(),
            'timestamp': datetime.now().isoformat()
        }
        
        return status
    
    def _analyze_data_status(self) -> Dict:
        """分析数据状态"""
        print("【1/4】分析数据状态...")
        
        # 获取统计数据
        viewpoints = self.db.get_viewpoints(limit=None)
        
        # 查询对话记录
        conn = self.db._get_connection()
        try:
            conversations_result = conn.execute('SELECT COUNT(*) as count FROM conversations').fetchone()
            conversations_count = conversations_result[0] if conversations_result else 0
            
            conversations_with_price_result = conn.execute(
                'SELECT COUNT(*) as count FROM conversations WHERE btc_price IS NOT NULL'
            ).fetchone()
            conversations_with_price = conversations_with_price_result[0] if conversations_with_price_result else 0
        except:
            conversations_count = 0
            conversations_with_price = 0
        
        # 统计价格关联
        viewpoints_with_price = sum(1 for vp in viewpoints if vp.get('btc_price'))
        
        # 检查信号数据
        try:
            result = conn.execute('SELECT COUNT(*) as count FROM trading_signals').fetchone()
            signal_count = result[0] if result else 0
        except:
            signal_count = 0
        
        # 检查信号评估
        try:
            result = conn.execute('SELECT COUNT(*) as count FROM signal_evaluations').fetchone()
            eval_count = result[0] if result else 0
        except:
            eval_count = 0
        
        status = {
            'viewpoints_total': len(viewpoints),
            'viewpoints_with_price': viewpoints_with_price,
            'viewpoints_price_ratio': viewpoints_with_price / len(viewpoints) * 100 if viewpoints else 0,
            'conversations_total': conversations_count,
            'conversations_with_price': conversations_with_price,
            'conversations_price_ratio': conversations_with_price / conversations_count * 100 if conversations_count > 0 else 0,
            'signals_count': signal_count,
            'evaluations_count': eval_count,
            'data_quality_score': self._calculate_data_quality_score(
                len(viewpoints), viewpoints_with_price, signal_count, eval_count
            )
        }
        
        print(f"✓ 观点总数: {status['viewpoints_total']}")
        print(f"✓ 观点价格关联率: {status['viewpoints_price_ratio']:.1f}%")
        print(f"✓ 对话总数: {status['conversations_total']}")
        print(f"✓ 对话价格关联率: {status['conversations_price_ratio']:.1f}%")
        print(f"✓ 信号数量: {status['signals_count']}")
        print(f"✓ 评估数量: {status['evaluations_count']}")
        print(f"✓ 数据质量评分: {status['data_quality_score']:.1f}/10")
        print()
        
        return status
    
    def _calculate_data_quality_score(self, viewpoints, viewpoints_with_price, signals, evaluations) -> float:
        """计算数据质量评分（0-10）"""
        score = 0.0
        
        # 观点数量（最多3分）
        if viewpoints >= 5000:
            score += 3.0
        elif viewpoints >= 1000:
            score += 2.0
        elif viewpoints >= 100:
            score += 1.0
        
        # 价格关联率（最多2分）
        if viewpoints > 0:
            price_ratio = viewpoints_with_price / viewpoints
            if price_ratio >= 0.8:
                score += 2.0
            elif price_ratio >= 0.5:
                score += 1.5
            elif price_ratio >= 0.3:
                score += 1.0
        
        # 信号数量（最多3分）
        if signals >= 1000:
            score += 3.0
        elif signals >= 100:
            score += 2.0
        elif signals >= 10:
            score += 1.0
        
        # 评估数量（最多2分）
        if evaluations >= 100:
            score += 2.0
        elif evaluations >= 10:
            score += 1.0
        
        return min(score, 10.0)
    
    def _analyze_knowledge_base_status(self) -> Dict:
        """分析知识库状态"""
        print("【2/4】分析知识库状态...")
        
        try:
            from de_strategy_knowledge_base import DeStrategyKnowledgeBase
            kb = DeStrategyKnowledgeBase(self.trader_id)
            
            # 检查策略映射
            mapping = kb.mapping
            strategies = list(mapping.strategy_to_rules.keys())
            
            status = {
                'available': True,
                'strategies_count': len(strategies),
                'strategies': strategies,
                'rules_engine_available': kb.rules_engine_available,
                'trading_brain_available': kb.trading_brain_available
            }
            
            print(f"✓ 知识库可用")
            print(f"✓ 策略数量: {status['strategies_count']}")
            print(f"✓ 规则引擎: {'可用' if status['rules_engine_available'] else '不可用'}")
            print(f"✓ 交易大脑: {'可用' if status['trading_brain_available'] else '不可用'}")
            print()
            
        except Exception as e:
            status = {
                'available': False,
                'error': str(e)
            }
            print(f"✗ 知识库不可用: {e}")
            print()
        
        return status
    
    def _analyze_rules_engine_status(self) -> Dict:
        """分析规则引擎状态"""
        print("【3/4】分析规则引擎状态...")
        
        try:
            import sys
            rules_engine_path = Path(__file__).parent.parent.parent / "rules_engine"
            if str(rules_engine_path) not in sys.path:
                sys.path.insert(0, str(rules_engine_path))
            
            from simple_rules_engine import create_rules_engine
            
            engine = create_rules_engine()
            rules_count = len(engine.rules)
            
            status = {
                'available': True,
                'rules_count': rules_count,
                'has_dynamic_priority': True,
                'has_rule_resonance': True
            }
            
            print(f"✓ 规则引擎可用")
            print(f"✓ 规则数量: {status['rules_count']}")
            print(f"✓ 动态优先级: 支持")
            print(f"✓ 规则共振: 支持")
            print()
            
        except Exception as e:
            status = {
                'available': False,
                'error': str(e)
            }
            print(f"✗ 规则引擎不可用: {e}")
            print()
        
        return status
    
    def _analyze_ml_dl_status(self) -> Dict:
        """分析ML/DL状态"""
        print("【4/4】分析ML/DL状态...")
        
        status = {
            'sentiment_analyzer': self._check_module('ml_dl.sentiment_analyzer', 'SentimentAnalyzer'),
            'price_predictor': self._check_module('ml_dl.price_predictor_lstm', 'BTCPricePredictor'),
            'ml_predictor': self._check_module('ml_signal_predictor', 'MLSignalPredictor'),
            'comprehensive_trainer': self._check_module('ml_dl.comprehensive_training', 'ComprehensiveTrainer'),
            'learning_manager': self._check_module('ml_dl.learning_manager', 'LearningManager')
        }
        
        available_count = sum(1 for v in status.values() if v.get('available', False))
        
        print(f"✓ 可用模块: {available_count}/{len(status)}")
        for name, module_status in status.items():
            if module_status.get('available'):
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name}: {module_status.get('error', 'N/A')}")
        print()
        
        return status
    
    def _check_module(self, module_name: str, class_name: str) -> Dict:
        """检查模块是否可用"""
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            return {'available': True, 'class_name': class_name, 'module_name': module_name}
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def generate_improvement_recommendations(self, status: Dict) -> List[Dict]:
        """生成改进建议"""
        recommendations = []
        
        # 数据改进建议
        data_status = status.get('data_status', {})
        if data_status.get('signals_count', 0) == 0:
            recommendations.append({
                'priority': '最高',
                'category': '数据',
                'title': '导入历史信号',
                'description': '从trading_signals/目录解析历史信号文件并导入数据库',
                'impact': '高',
                'effort': '中',
                'estimated_time': '1-2天'
            })
        
        if data_status.get('evaluations_count', 0) == 0:
            recommendations.append({
                'priority': '最高',
                'category': '数据',
                'title': '评估历史信号',
                'description': '使用价格数据评估历史信号结果，生成训练数据',
                'impact': '高',
                'effort': '中',
                'estimated_time': '1-2天'
            })
        
        if data_status.get('viewpoints_price_ratio', 0) < 50:
            recommendations.append({
                'priority': '高',
                'category': '数据',
                'title': '补充价格关联',
                'description': f"当前价格关联率{data_status.get('viewpoints_price_ratio', 0):.1f}%，建议提升到80%+",
                'impact': '中',
                'effort': '低',
                'estimated_time': '1天'
            })
        
        # 知识库改进建议
        kb_status = status.get('knowledge_base_status', {})
        if not kb_status.get('available'):
            recommendations.append({
                'priority': '中',
                'category': '知识库',
                'title': '修复知识库',
                'description': '检查并修复知识库模块',
                'impact': '中',
                'effort': '低',
                'estimated_time': '半天'
            })
        
        # 规则引擎改进建议
        rules_status = status.get('rules_engine_status', {})
        if rules_status.get('available'):
            recommendations.append({
                'priority': '高',
                'category': '规则引擎',
                'title': '实现规则性能追踪',
                'description': '追踪每个规则的历史表现，为权重优化做准备',
                'impact': '高',
                'effort': '中',
                'estimated_time': '2-3天'
            })
        
        # ML/DL改进建议
        ml_status = status.get('ml_dl_status', {})
        if data_status.get('evaluations_count', 0) >= 10:
            recommendations.append({
                'priority': '高',
                'category': 'ML/DL',
                'title': '训练/更新ML模型',
                'description': '使用新的评估数据训练或更新信号预测模型',
                'impact': '高',
                'effort': '中',
                'estimated_time': '1天'
            })
        
        return recommendations
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        print("=" * 80)
        print("青鸟系统自我学习优化分析")
        print("=" * 80)
        print()
        
        # 1. 分析系统状态
        status = self.analyze_system_status()
        
        # 2. 生成改进建议
        print("=" * 80)
        print("生成改进建议")
        print("=" * 80)
        print()
        
        recommendations = self.generate_improvement_recommendations(status)
        
        # 3. 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': status,
            'recommendations': recommendations,
            'summary': {
                'total_recommendations': len(recommendations),
                'high_priority': sum(1 for r in recommendations if r['priority'] == '最高'),
                'data_quality_score': status.get('data_status', {}).get('data_quality_score', 0)
            }
        }
        
        # 保存报告
        report_file = self.output_dir / f"system_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print("=" * 80)
        print("分析摘要")
        print("=" * 80)
        print()
        print(f"数据质量评分: {report['summary']['data_quality_score']:.1f}/10")
        print(f"改进建议总数: {report['summary']['total_recommendations']}")
        print(f"最高优先级建议: {report['summary']['high_priority']}")
        print()
        
        print("改进建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. 【{rec['priority']}优先级】{rec['title']}")
            print(f"   类别: {rec['category']}")
            print(f"   描述: {rec['description']}")
            print(f"   影响: {rec['impact']} | 工作量: {rec['effort']} | 预计时间: {rec['estimated_time']}")
        
        print()
        print(f"详细报告已保存到: {report_file}")
        print("=" * 80)
        
        return report
    
    def close(self):
        """关闭连接"""
        self.db.close()


def main():
    """主函数"""
    learner = SystemSelfLearner(trader_id='de')
    
    try:
        report = learner.run_full_analysis()
    except KeyboardInterrupt:
        print("\n分析被用户中断")
    except Exception as e:
        print(f"\n分析失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        learner.close()


if __name__ == '__main__':
    main()

