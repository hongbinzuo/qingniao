#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks pattern constraints evaluator for filtering/scoring signals."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = ROOT / 'config' / 'brooks_pattern_constraints.yaml'


@dataclass
class ConstraintResult:
    status: str
    score_adjust: float
    reasons: List[str]
    rule_name: Optional[str] = None


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.lower()
    return value


def _get_feature(features: Dict[str, Any], key: str) -> Any:
    return features.get(key)


def _compare(value: Any, op: str, target: Any) -> Optional[bool]:
    if value is None:
        return None
    value_norm = _normalize(value)
    target_norm = _normalize(target)

    if op == '==':
        return value_norm == target_norm
    if op == '!=':
        return value_norm != target_norm
    if op in ('>', '>=', '<', '<='):
        try:
            val = float(value_norm)
            tgt = float(target_norm)
        except (TypeError, ValueError):
            return False
        if op == '>':
            return val > tgt
        if op == '>=':
            return val >= tgt
        if op == '<':
            return val < tgt
        if op == '<=':
            return val <= tgt
    if op == 'in':
        if isinstance(target_norm, list):
            return value_norm in [_normalize(x) for x in target_norm]
        return False
    if op == 'not_in':
        if isinstance(target_norm, list):
            return value_norm not in [_normalize(x) for x in target_norm]
        return False
    if op == 'contains':
        if isinstance(value_norm, list):
            return _normalize(target_norm) in [_normalize(x) for x in value_norm]
        if isinstance(value_norm, str):
            return str(target_norm) in value_norm
        return False
    return False


def _rule_matches(rule: Dict[str, Any], pattern_name: str, direction: Optional[str]) -> bool:
    name = (rule.get('name') or '').lower()
    aliases = [str(a).lower() for a in (rule.get('aliases') or [])]
    pname = (pattern_name or '').lower()
    if name and name in pname:
        pass_match = True
    else:
        pass_match = any(alias in pname for alias in aliases)
    if not pass_match:
        return False
    rule_dir = (rule.get('direction') or '').lower()
    if direction and rule_dir and rule_dir != direction.lower():
        return False
    return True


class BrooksPatternConstraints:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG
        self.rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        if not self.config_path.exists():
            return
        try:
            import yaml
        except Exception:
            return
        try:
            obj = yaml.safe_load(self.config_path.read_text(encoding='utf-8')) or {}
            self.rules = obj.get('rules') or []
        except Exception:
            self.rules = []

    def evaluate(self, features: Dict[str, Any], pattern_name: str, direction: Optional[str] = None) -> ConstraintResult:
        if not self.rules:
            return ConstraintResult(status='warn', score_adjust=0.0, reasons=['constraints_not_loaded'])

        rule = None
        for candidate in self.rules:
            if _rule_matches(candidate, pattern_name, direction):
                rule = candidate
                break

        if not rule:
            return ConstraintResult(status='warn', score_adjust=0.0, reasons=['no_matching_rule'])

        reasons: List[str] = []
        status = 'pass'

        for cond in rule.get('avoid', []) or []:
            feat = _get_feature(features, cond.get('feature'))
            result = _compare(feat, cond.get('op', '=='), cond.get('value'))
            if result is True:
                status = 'fail'
                reasons.append(f"avoid:{cond.get('feature')}")
                break

        if status != 'fail':
            for cond in rule.get('required', []) or []:
                feat = _get_feature(features, cond.get('feature'))
                result = _compare(feat, cond.get('op', '=='), cond.get('value'))
                if result is None:
                    if status != 'fail':
                        status = 'warn'
                    reasons.append(f"missing:{cond.get('feature')}")
                elif result is False:
                    status = 'fail'
                    reasons.append(f"required:{cond.get('feature')}")
                    break

        score_boost = float(rule.get('score_boost') or 0.0)
        score_penalty = float(rule.get('score_penalty') or -0.3)
        score_adjust = 0.0
        if status == 'pass':
            score_adjust = score_boost
        elif status == 'fail':
            score_adjust = score_penalty

        return ConstraintResult(status=status, score_adjust=score_adjust, reasons=reasons, rule_name=rule.get('name'))
