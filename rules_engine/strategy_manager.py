#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略管理器
管理所有交易策略文档和配置
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class StrategyInfo:
    """策略信息"""
    name: str
    display_name: str
    description: str
    source: Optional[str] = None
    document_path: Optional[str] = None
    enabled: bool = True
    priority: int = 50
    strategy_type: str = ""
    target_assets: str = ""
    core_logic: str = ""
    created_date: str = ""
    updated_date: str = ""


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, config_file: str = "strategy_registry.yaml"):
        """初始化策略管理器"""
        self.config_file = Path(__file__).parent / config_file
        self.config = self.load_config()
        self.strategies = self._load_strategies()
    
    def load_config(self) -> Dict:
        """加载策略配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError:
            print(f"警告: 策略配置文件 {self.config_file} 不存在")
            return {}
    
    def _load_strategies(self) -> Dict[str, StrategyInfo]:
        """加载所有策略信息"""
        strategies = {}
        
        if 'strategies' in self.config:
            for strategy_id, strategy_data in self.config['strategies'].items():
                strategies[strategy_id] = StrategyInfo(
                    name=strategy_data.get('name', ''),
                    display_name=strategy_data.get('display_name', ''),
                    description=strategy_data.get('description', ''),
                    source=strategy_data.get('source'),
                    document_path=strategy_data.get('document_path'),
                    enabled=strategy_data.get('enabled', True),
                    priority=strategy_data.get('priority', 50),
                    strategy_type=strategy_data.get('strategy_type', ''),
                    target_assets=strategy_data.get('target_assets', ''),
                    core_logic=strategy_data.get('core_logic', ''),
                    created_date=strategy_data.get('created_date', ''),
                    updated_date=strategy_data.get('updated_date', '')
                )
        
        return strategies
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyInfo]:
        """获取指定策略信息"""
        return self.strategies.get(strategy_id)
    
    def list_strategies(self, enabled_only: bool = True) -> List[StrategyInfo]:
        """列出所有策略"""
        strategies = list(self.strategies.values())
        
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]
        
        # 按优先级排序
        strategies.sort(key=lambda s: s.priority, reverse=True)
        
        return strategies
    
    def get_strategy_document_path(self, strategy_id: str) -> Optional[Path]:
        """获取策略文档路径"""
        strategy = self.get_strategy(strategy_id)
        if not strategy or not strategy.document_path:
            return None
        
        # 如果是相对路径，转换为绝对路径
        doc_path = Path(strategy.document_path)
        if not doc_path.is_absolute():
            # 先尝试在rules_engine目录的父目录查找
            parent_dir = Path(__file__).parent.parent
            doc_path = parent_dir / doc_path
            # 如果不在父目录，则在rules_engine目录查找
            if not doc_path.exists():
                doc_path = Path(__file__).parent / strategy.document_path
        
        return doc_path if doc_path.exists() else None
    
    def read_strategy_document(self, strategy_id: str) -> Optional[str]:
        """读取策略文档内容"""
        doc_path = self.get_strategy_document_path(strategy_id)
        if not doc_path:
            return None
        
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"错误: 读取策略文档失败: {e}")
            return None
    
    def get_strategy_summary(self, strategy_id: str) -> Dict:
        """获取策略摘要信息"""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return {}
        
        config_data = self.config.get('strategies', {}).get(strategy_id, {})
        
        return {
            'id': strategy_id,
            'name': strategy.display_name,
            'description': strategy.description,
            'source': strategy.source,
            'enabled': strategy.enabled,
            'priority': strategy.priority,
            'strategy_type': strategy.strategy_type,
            'target_assets': strategy.target_assets,
            'core_logic': strategy.core_logic,
            'parameters': config_data.get('parameters', {}),
            'market_conditions': config_data.get('market_conditions', {}),
            'technical_tools': config_data.get('technical_tools', []),
            'success_rate': config_data.get('success_rate', {}),
            'risk_warnings': config_data.get('risk_warnings', []),
            'document_path': str(self.get_strategy_document_path(strategy_id))
        }
    
    def enable_strategy(self, strategy_id: str, enabled: bool = True):
        """启用/禁用策略"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].enabled = enabled
            
            # 更新配置文件
            if 'strategies' in self.config:
                if strategy_id in self.config['strategies']:
                    self.config['strategies'][strategy_id]['enabled'] = enabled
                    self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"错误: 保存配置文件失败: {e}")


def main():
    """测试策略管理器"""
    manager = StrategyManager()
    
    print("=" * 80)
    print("策略管理器测试")
    print("=" * 80)
    print()
    
    # 列出所有策略
    print("所有策略:")
    strategies = manager.list_strategies(enabled_only=False)
    for strategy in strategies:
        print(f"  - {strategy.display_name} ({'启用' if strategy.enabled else '禁用'})")
        print(f"    描述: {strategy.description}")
        print(f"    优先级: {strategy.priority}")
        print(f"    类型: {strategy.strategy_type}")
        print()
    
    # 获取梦多空策略详情
    print("=" * 80)
    print("梦多空策略详情:")
    print("=" * 80)
    summary = manager.get_strategy_summary('meng_duo_kong')
    for key, value in summary.items():
        if isinstance(value, (dict, list)):
            print(f"{key}:")
            import json
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            print(f"{key}: {value}")
        print()


if __name__ == "__main__":
    main()

