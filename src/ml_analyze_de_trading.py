#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用机器学习分析交易员 De. 的交易系统
使用NLP技术提取关键信息并总结交易系统
"""

import json
import re
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
from math import log

# 尝试导入jieba，如果没有则使用基础分析
try:
    import jieba
    import jieba.analyse
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    print("提示: 未安装jieba，将使用基础文本分析方法")

def parse_json_file(file_path: str) -> List[Dict]:
    """解析JSON文件，提取消息数据"""
    print("[1/6] 正在读取文件...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        messages = data.get('messages', [])
    print(f"    共读取 {len(messages)} 条消息")
    return messages

def extract_de_messages(messages: List[Dict]) -> List[Dict]:
    """提取De.的所有消息"""
    print("[2/6] 正在提取De.的消息...")
    de_messages = []
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            de_messages.append(msg)
    print(f"    找到 {len(de_messages)} 条De.的消息")
    return de_messages

def extract_trading_keywords(text: str) -> List[str]:
    """提取交易相关关键词"""
    # 定义交易相关关键词
    trading_keywords = [
        '多单', '空单', '做多', '做空', '开仓', '平仓', '加仓', '减仓',
        '止损', '止盈', '挂单', '区间', '突破', '回踩',
        '剥头皮', '震荡', '单边', '趋势', '杠杆', '盈亏比',
        '逐仓', '爆单', '流动性', '假突破', '扫单'
    ]
    
    found_keywords = []
    for keyword in trading_keywords:
        if keyword in text:
            found_keywords.append(keyword)
    return found_keywords

def extract_prices(text: str) -> List[float]:
    """提取价格数字"""
    prices = re.findall(r'\b(\d{4,5})\b', text)
    filtered_prices = []
    for price in prices:
        try:
            p = float(price)
            if 1000 <= p <= 200000:  # BTC价格范围
                filtered_prices.append(p)
        except:
            continue
    return filtered_prices

def simple_tfidf(texts: List[str], top_k: int = 50) -> List[Tuple[str, float]]:
    """简单的TF-IDF实现"""
    # 定义交易相关词汇
    trading_words = [
        '多单', '空单', '做多', '做空', '开仓', '平仓', '加仓', '减仓',
        '止损', '止盈', '挂单', '区间', '突破', '回踩', '剥头皮',
        '震荡', '单边', '趋势', '杠杆', '盈亏比', '逐仓', '爆单',
        '流动性', '假突破', '扫单', 'BTC', '大饼', '价格', '点位'
    ]
    
    # 计算TF
    tf_scores = defaultdict(float)
    for text in texts:
        for word in trading_words:
            count = text.count(word)
            if count > 0:
                tf_scores[word] += count / len(text)
    
    # 计算IDF
    idf_scores = {}
    total_docs = len(texts)
    for word in trading_words:
        doc_count = sum(1 for text in texts if word in text)
        if doc_count > 0:
            idf_scores[word] = log(total_docs / doc_count)
        else:
            idf_scores[word] = 0
    
    # 计算TF-IDF
    tfidf_scores = []
    for word in trading_words:
        if word in tf_scores:
            tfidf = tf_scores[word] * idf_scores[word]
            tfidf_scores.append((word, tfidf))
    
    # 排序并返回top_k
    tfidf_scores.sort(key=lambda x: x[1], reverse=True)
    return tfidf_scores[:top_k]

def simple_textrank(texts: List[str], top_k: int = 30) -> List[Tuple[str, float]]:
    """简单的TextRank实现（基于共现）"""
    # 定义交易相关词汇
    trading_words = [
        '多单', '空单', '止损', '止盈', '挂单', '区间', '突破',
        '震荡', '趋势', '杠杆', '盈亏比', '剥头皮', '流动性'
    ]
    
    # 计算词汇共现
    cooccurrence = defaultdict(int)
    word_freq = defaultdict(int)
    
    for text in texts:
        words_in_text = [w for w in trading_words if w in text]
        for word in words_in_text:
            word_freq[word] += 1
            for other_word in words_in_text:
                if word != other_word:
                    cooccurrence[(word, other_word)] += 1
    
    # 简单的TextRank分数（基于共现频率）
    scores = {}
    for word in trading_words:
        score = word_freq[word]
        for (w1, w2), count in cooccurrence.items():
            if w1 == word:
                score += count * 0.5
            elif w2 == word:
                score += count * 0.5
        scores[word] = score
    
    # 排序并返回
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]

def analyze_with_ml(de_messages: List[Dict]) -> Dict:
    """使用机器学习方法分析交易系统"""
    print("[3/6] 正在使用ML方法分析交易系统...")
    
    # 收集所有交易相关消息
    trading_messages = []
    all_texts = []
    
    for msg in de_messages:
        content = msg.get('content', '')
        if not content or len(content) < 5:
            continue
        
        # 提取交易关键词
        keywords = extract_trading_keywords(content)
        prices = extract_prices(content)
        
        if keywords or prices or any(kw in content for kw in ['BTC', 'btc', '大饼']):
            trading_messages.append({
                'timestamp': msg.get('timestamp', ''),
                'content': content,
                'keywords': keywords,
                'prices': prices
            })
            all_texts.append(content)
    
    print(f"    找到 {len(trading_messages)} 条交易相关消息")
    
    # 使用TF-IDF提取关键词
    print("[4/6] 正在使用TF-IDF提取关键词...")
    if HAS_JIEBA and all_texts:
        combined_text = ' '.join(all_texts)
        
        # 提取关键词
        keywords_tfidf = jieba.analyse.extract_tags(
            combined_text, 
            topK=50, 
            withWeight=True,
            allowPOS=('n', 'v', 'nr', 'ns', 'nt', 'vn')
        )
        
        # 提取关键短语
        keywords_textrank = jieba.analyse.textrank(
            combined_text,
            topK=30,
            withWeight=True
        )
    else:
        # 使用简单的TF-IDF实现
        keywords_tfidf = simple_tfidf(all_texts)
        keywords_textrank = simple_textrank(all_texts)
    
    # 统计关键词频率
    keyword_counter = Counter()
    for msg in trading_messages:
        for kw in msg['keywords']:
            keyword_counter[kw] += 1
    
    # 分类消息
    categories = {
        '止损策略': [],
        '止盈策略': [],
        '入场信号': [],
        '仓位管理': [],
        '风险控制': [],
        '交易规则': [],
        '价格分析': [],
        '交易记录': []
    }
    
    for msg in trading_messages:
        content = msg['content']
        
        if '止损' in content:
            categories['止损策略'].append(msg)
        if '止盈' in content:
            categories['止盈策略'].append(msg)
        if any(kw in content for kw in ['多单', '空单', '开', '挂单']):
            categories['入场信号'].append(msg)
        if any(kw in content for kw in ['仓位', '杠杆', '逐仓', '盈亏比']):
            categories['仓位管理'].append(msg)
        if any(kw in content for kw in ['风险', '爆单', '止损']):
            categories['风险控制'].append(msg)
        if any(kw in content for kw in ['区间', '突破', '震荡', '趋势']):
            categories['交易规则'].append(msg)
        if len(msg['prices']) > 0:
            categories['价格分析'].append(msg)
        if any(kw in content for kw in ['平', '加仓', '减仓']):
            categories['交易记录'].append(msg)
    
    return {
        'trading_messages': trading_messages,
        'keyword_frequency': dict(keyword_counter.most_common(20)),
        'tfidf_keywords': keywords_tfidf[:20],
        'textrank_keywords': keywords_textrank[:20],
        'categories': categories,
        'total_messages': len(trading_messages)
    }

def summarize_category(category_name: str, messages: List[Dict]) -> str:
    """总结某个类别的消息"""
    if not messages:
        return ""
    
    # 提取关键信息
    key_points = []
    price_mentions = []
    
    for msg in messages[:10]:  # 只看前10条
        content = msg['content']
        prices = msg['prices']
        
        if prices:
            price_mentions.extend([f"${p:,.0f}" for p in prices])
        
        # 提取关键句子（包含关键词的句子）
        sentences = re.split(r'[。，！？\n]', content)
        for sentence in sentences:
            if len(sentence) > 10 and any(kw in sentence for kw in ['止损', '止盈', '区间', '挂单', '杠杆', '盈亏比']):
                key_points.append(sentence.strip())
    
    summary = f"### {category_name}\n\n"
    summary += f"**消息数量**: {len(messages)}\n\n"
    
    if price_mentions:
        unique_prices = list(set(price_mentions))[:10]
        summary += f"**涉及价格**: {', '.join(unique_prices)}\n\n"
    
    if key_points:
        summary += "**关键要点**:\n\n"
        unique_points = list(set(key_points))[:5]
        for i, point in enumerate(unique_points, 1):
            summary += f"{i}. {point}\n"
        summary += "\n"
    
    return summary

def generate_ml_report(analysis_result: Dict) -> str:
    """生成ML分析报告"""
    print("[5/6] 正在生成ML分析报告...")
    
    report = []
    report.append("=" * 80)
    report.append("交易员 De. 的交易系统分析报告（机器学习版）")
    report.append("=" * 80)
    report.append("")
    
    # 总体统计
    report.append("## 一、总体统计")
    report.append("")
    report.append(f"- **交易相关消息总数**: {analysis_result['total_messages']} 条")
    report.append(f"- **分析类别数**: {len(analysis_result['categories'])} 个")
    report.append("")
    
    # 关键词分析
    report.append("## 二、关键词频率分析")
    report.append("")
    report.append("### 高频交易关键词（Top 20）")
    report.append("")
    for i, (keyword, count) in enumerate(analysis_result['keyword_frequency'].items(), 1):
        report.append(f"{i}. **{keyword}**: {count} 次")
    report.append("")
    
    if analysis_result['tfidf_keywords']:
        report.append("### TF-IDF关键词（Top 20）")
        report.append("")
        for i, (keyword, weight) in enumerate(analysis_result['tfidf_keywords'], 1):
            report.append(f"{i}. **{keyword}**: {weight:.4f}")
        report.append("")
    
    # 交易系统总结
    report.append("## 三、交易系统核心要素总结")
    report.append("")
    
    categories = analysis_result['categories']
    
    # 止损策略
    if categories['止损策略']:
        report.append(summarize_category("止损策略", categories['止损策略']))
    
    # 止盈策略
    if categories['止盈策略']:
        report.append(summarize_category("止盈策略", categories['止盈策略']))
    
    # 入场信号
    if categories['入场信号']:
        report.append(summarize_category("入场信号", categories['入场信号']))
    
    # 仓位管理
    if categories['仓位管理']:
        report.append(summarize_category("仓位管理", categories['仓位管理']))
    
    # 风险控制
    if categories['风险控制']:
        report.append(summarize_category("风险控制", categories['风险控制']))
    
    # 交易规则
    if categories['交易规则']:
        report.append(summarize_category("交易规则", categories['交易规则']))
    
    # 详细交易记录
    report.append("## 四、详细交易记录示例")
    report.append("")
    
    trading_records = []
    for msg in analysis_result['trading_messages']:
        if any(kw in msg['content'] for kw in ['多单', '空单', '平', '开']):
            trading_records.append(msg)
    
    for i, record in enumerate(trading_records[:20], 1):
        report.append(f"### 交易记录 {i}")
        report.append(f"**时间**: {record['timestamp']}")
        report.append(f"**内容**: {record['content']}")
        if record['prices']:
            report.append(f"**价格**: {', '.join([f'${p:,.0f}' for p in record['prices']])}")
        if record['keywords']:
            report.append(f"**关键词**: {', '.join(record['keywords'])}")
        report.append("")
    
    # 交易系统总结
    report.append("## 五、交易系统总结")
    report.append("")
    
    # 基于关键词频率总结
    top_keywords = list(analysis_result['keyword_frequency'].keys())[:10]
    
    report.append("### 核心特征")
    report.append("")
    report.append("基于关键词频率分析，该交易系统的核心特征包括：")
    report.append("")
    for keyword in top_keywords:
        report.append(f"- **{keyword}**: 出现 {analysis_result['keyword_frequency'][keyword]} 次")
    report.append("")
    
    # 交易风格总结
    report.append("### 交易风格")
    report.append("")
    if '剥头皮' in analysis_result['keyword_frequency']:
        report.append("- **交易类型**: 剥头皮交易（Scalping）")
    if '区间' in analysis_result['keyword_frequency']:
        report.append("- **交易方式**: 区间震荡交易")
    if '挂单' in analysis_result['keyword_frequency']:
        report.append("- **执行方式**: 挂单交易，不追涨杀跌")
    if '止损' in analysis_result['keyword_frequency']:
        report.append("- **风险控制**: 严格止损，窄止损策略")
    report.append("")
    
    return "\n".join(report)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("使用机器学习分析交易员 De. 的交易系统")
    print("=" * 80)
    print()
    
    # 解析文件
    messages = parse_json_file(file_path)
    
    # 提取De.的消息
    de_messages = extract_de_messages(messages)
    
    # ML分析
    analysis_result = analyze_with_ml(de_messages)
    
    # 生成报告
    report = generate_ml_report(analysis_result)
    
    # 保存报告
    output_file = "De_trading_system_ml_analysis.md"
    print(f"[6/6] 正在保存报告到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print()
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)
    print(f"报告已保存到: {output_file}")
    print()
    
    # 打印简要统计
    print("简要统计:")
    print(f"  - 交易相关消息: {analysis_result['total_messages']} 条")
    print(f"  - 高频关键词: {len(analysis_result['keyword_frequency'])} 个")
    for category, msgs in analysis_result['categories'].items():
        if msgs:
            print(f"  - {category}: {len(msgs)} 条")

if __name__ == "__main__":
    main()

