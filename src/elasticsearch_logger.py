# -*- coding: utf-8 -*-
"""
Elasticsearch日志记录器
保存所有原始对话记录和关键系统操作到Elasticsearch
至少保留3个月
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import uuid

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import ConnectionError, RequestError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    print("⚠️ 警告: elasticsearch库未安装，请运行: pip install elasticsearch")


class ElasticsearchLogger:
    """Elasticsearch日志记录器"""
    
    def __init__(self, 
                 hosts: List[str] = None,
                 index_prefix: str = "qingniao_conversations",
                 retention_days: int = 90):
        """
        初始化Elasticsearch日志记录器
        
        Args:
            hosts: Elasticsearch服务器地址列表，默认['localhost:9200']
            index_prefix: 索引前缀，默认'qingniao_conversations'
            retention_days: 保留天数，默认90天（3个月）
        """
        if not ELASTICSEARCH_AVAILABLE:
            self.available = False
            return
        
        # 确保hosts格式正确（完整的URL）
        if hosts:
            self.hosts = [f"http://{h}" if not h.startswith('http') else h for h in hosts]
        else:
            self.hosts = ['http://localhost:9200']
        self.index_prefix = index_prefix
        self.retention_days = retention_days
        
        try:
            self.es = Elasticsearch(
                hosts=self.hosts,
                request_timeout=30,
                max_retries=3
            )
            # 测试连接
            if self.es.ping():
                self.available = True
                print(f"✅ Elasticsearch连接成功: {self.hosts}")
                self._ensure_index_template()
            else:
                self.available = False
                print(f"⚠️ Elasticsearch连接失败: {self.hosts}")
        except Exception as e:
            self.available = False
            print(f"⚠️ Elasticsearch初始化失败: {e}")
            print("   提示: 对话记录将仅保存到数据库，不会保存到Elasticsearch")
    
    def _ensure_index_template(self):
        """确保索引模板存在"""
        template_name = f"{self.index_prefix}_template"
        template_body = {
            "index_patterns": [f"{self.index_prefix}-*"],
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index.lifecycle.name": f"{self.index_prefix}_policy",
                "index.lifecycle.rollover_alias": f"{self.index_prefix}_write"
            },
            "mappings": {
                "properties": {
                    "log_id": {"type": "keyword"},
                    "log_type": {"type": "keyword"},  # conversation, operation, error, warning
                    "log_level": {"type": "keyword"},  # info, warning, error, critical
                    "operation_type": {"type": "keyword"},  # signal_generation, trade_record, price_sync, etc.
                    "session_id": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "user_message": {"type": "text", "analyzer": "ik_max_word"},
                    "assistant_message": {"type": "text", "analyzer": "ik_max_word"},
                    "trader_message": {"type": "text", "analyzer": "ik_max_word"},
                    "source": {"type": "keyword"},
                    "btc_price": {"type": "float"},
                    "has_trading_info": {"type": "boolean"},
                    "has_evaluation": {"type": "boolean"},
                    "evaluation_content": {"type": "text"},
                    "operation_details": {"type": "object", "enabled": True},
                    "raw_data": {"type": "object", "enabled": True},
                    "created_at": {"type": "date"}
                }
            }
        }
        
        try:
            self.es.indices.put_index_template(
                name=template_name,
                body=template_body
            )
        except Exception as e:
            # 如果模板已存在或创建失败，忽略错误
            pass
    
    def _get_index_name(self, date: datetime = None) -> str:
        """获取索引名称（按月分片）"""
        if date is None:
            date = datetime.now()
        return f"{self.index_prefix}-{date.strftime('%Y.%m')}"
    
    def log_operation(self,
                     operation_type: str,
                     operation_details: Dict,
                     log_level: str = 'info',
                     timestamp: str = None,
                     btc_price: float = None,
                     raw_data: Dict = None) -> Optional[str]:
        """
        记录系统操作日志
        
        Args:
            operation_type: 操作类型（signal_generation, trade_record, price_sync, strategy_extraction等）
            operation_details: 操作详情
            log_level: 日志级别（info, warning, error, critical）
            timestamp: 时间戳
            btc_price: BTC价格
            raw_data: 原始数据
        
        Returns:
            文档ID
        """
        if not self.available:
            return None
        
        try:
            if timestamp:
                try:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            doc = {
                "log_id": str(uuid.uuid4()),
                "log_type": "operation",
                "log_level": log_level,
                "operation_type": operation_type,
                "timestamp": dt.isoformat(),
                "btc_price": btc_price,
                "operation_details": operation_details or {},
                "raw_data": raw_data or {},
                "created_at": datetime.now().isoformat()
            }
            
            index_name = self._get_index_name(dt)
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name)
            
            response = self.es.index(
                index=index_name,
                document=doc,
                refresh=True
            )
            
            return response['_id']
            
        except Exception as e:
            print(f"⚠️ Elasticsearch操作日志记录失败: {e}", file=sys.stderr)
            return None
    
    def log_conversation(self,
                        user_message: str,
                        assistant_message: str = None,
                        trader_message: str = None,
                        timestamp: str = None,
                        session_id: str = None,
                        source: str = 'conversation',
                        btc_price: float = None,
                        has_trading_info: bool = False,
                        has_evaluation: bool = False,
                        evaluation_content: str = None,
                        raw_data: Dict = None) -> Optional[str]:
        """
        记录对话到Elasticsearch
        
        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            trader_message: 交易员消息（De.的消息）
            timestamp: 时间戳（格式：YYYY-MM-DD HH:MM:SS）
            session_id: 会话ID
            source: 来源（conversation/discord/manual等）
            btc_price: BTC价格
            has_trading_info: 是否包含交易信息
            has_evaluation: 是否包含用户评价
            evaluation_content: 评价内容
            raw_data: 原始数据（完整保存）
        
        Returns:
            文档ID，如果失败返回None
        """
        if not self.available:
            return None
        
        try:
            # 解析时间戳
            if timestamp:
                try:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            # 构建文档
            doc = {
                "log_id": str(uuid.uuid4()),
                "log_type": "conversation",
                "log_level": "info",
                "session_id": session_id or str(uuid.uuid4()),
                "timestamp": dt.isoformat(),
                "user_message": user_message or "",
                "assistant_message": assistant_message or "",
                "trader_message": trader_message or "",
                "source": source,
                "btc_price": btc_price,
                "has_trading_info": has_trading_info,
                "has_evaluation": has_evaluation,
                "evaluation_content": evaluation_content or "",
                "raw_data": raw_data or {},
                "created_at": datetime.now().isoformat()
            }
            
            # 获取索引名称
            index_name = self._get_index_name(dt)
            
            # 确保索引存在
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name)
            
            # 索引文档
            response = self.es.index(
                index=index_name,
                document=doc,
                refresh=True
            )
            
            return response['_id']
            
        except Exception as e:
            print(f"⚠️ Elasticsearch记录失败: {e}", file=sys.stderr)
            return None
    
    def log_de_conversation(self,
                           timestamp: str,
                           trader_message: str,
                           user_message: str = None,
                           source: str = 'discord',
                           btc_price: float = None,
                           conversation_id: int = None,
                           has_trading_info: bool = False,
                           has_evaluation: bool = False,
                           evaluation_content: str = None,
                           extracted_content: str = None) -> Optional[str]:
        """
        记录De.交易员的对话（便捷方法）
        
        Args:
            timestamp: 时间戳
            trader_message: 交易员消息
            user_message: 用户消息
            source: 来源
            btc_price: BTC价格
            conversation_id: 数据库中的对话ID
            has_trading_info: 是否包含交易信息
            has_evaluation: 是否包含用户评价
            evaluation_content: 评价内容
            extracted_content: 提取的内容
        
        Returns:
            文档ID
        """
        raw_data = {
            "conversation_id": conversation_id,
            "extracted_content": extracted_content,
            "original_trader_message": trader_message,
            "original_user_message": user_message
        }
        
        return self.log_conversation(
            user_message=user_message or "",
            trader_message=trader_message,
            timestamp=timestamp,
            source=source,
            btc_price=btc_price,
            has_trading_info=has_trading_info,
            has_evaluation=has_evaluation,
            evaluation_content=evaluation_content,
            raw_data=raw_data
        )
    
    def search(self,
              query: str = None,
              start_date: str = None,
              end_date: str = None,
              source: str = None,
              has_trading_info: bool = None,
              limit: int = 100) -> List[Dict]:
        """
        搜索对话记录
        
        Args:
            query: 搜索关键词
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            source: 来源过滤
            has_trading_info: 是否包含交易信息
            limit: 返回数量限制
        
        Returns:
            文档列表
        """
        if not self.available:
            return []
        
        try:
            # 构建查询
            must_clauses = []
            
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["user_message", "assistant_message", "trader_message", "evaluation_content"]
                    }
                })
            
            if start_date or end_date:
                range_clause = {}
                if start_date:
                    range_clause["gte"] = start_date
                if end_date:
                    range_clause["lte"] = end_date
                must_clauses.append({"range": {"timestamp": range_clause}})
            
            if source:
                must_clauses.append({"term": {"source": source}})
            
            if has_trading_info is not None:
                must_clauses.append({"term": {"has_trading_info": has_trading_info}})
            
            query_body = {
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            if must_clauses:
                query_body["query"] = {"bool": {"must": must_clauses}}
            else:
                query_body["query"] = {"match_all": {}}
            
            # 确定搜索的索引范围（最近3个月）
            indices = []
            for i in range(3):
                date = datetime.now() - timedelta(days=30 * i)
                index_name = self._get_index_name(date)
                if self.es.indices.exists(index=index_name):
                    indices.append(index_name)
            
            if not indices:
                return []
            
            # 执行搜索
            response = self.es.search(
                index=','.join(indices),
                body=query_body
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append(hit['_source'])
            
            return results
            
        except Exception as e:
            print(f"⚠️ Elasticsearch搜索失败: {e}", file=sys.stderr)
            return []
    
    def cleanup_old_indices(self, days: int = None):
        """
        清理旧索引（超过保留期的数据）
        
        Args:
            days: 保留天数，默认使用初始化时的retention_days
        """
        if not self.available:
            return
        
        retention_days = days or self.retention_days
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        try:
            # 获取所有索引
            indices = self.es.indices.get_alias(index=f"{self.index_prefix}-*")
            
            deleted_count = 0
            for index_name in indices:
                # 从索引名称提取日期
                try:
                    date_str = index_name.split('-')[-1]  # 格式：2025.01
                    index_date = datetime.strptime(date_str, '%Y.%m')
                    
                    if index_date < cutoff_date:
                        self.es.indices.delete(index=index_name)
                        deleted_count += 1
                        print(f"✓ 已删除旧索引: {index_name}")
                except:
                    continue
            
            if deleted_count > 0:
                print(f"✓ 清理完成，共删除 {deleted_count} 个旧索引")
            else:
                print("✓ 没有需要清理的旧索引")
                
        except Exception as e:
            print(f"⚠️ 清理旧索引失败: {e}", file=sys.stderr)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.available:
            return {"available": False}
        
        try:
            # 获取最近3个月的索引
            indices = []
            for i in range(3):
                date = datetime.now() - timedelta(days=30 * i)
                index_name = self._get_index_name(date)
                if self.es.indices.exists(index=index_name):
                    indices.append(index_name)
            
            if not indices:
                return {
                    "available": True,
                    "total_docs": 0,
                    "indices": []
                }
            
            # 统计文档数
            response = self.es.count(index=','.join(indices))
            
            return {
                "available": True,
                "total_docs": response['count'],
                "indices": indices,
                "retention_days": self.retention_days
            }
        except Exception as e:
            return {
                "available": True,
                "error": str(e)
            }


# 全局实例
_es_logger = None

def get_es_logger() -> ElasticsearchLogger:
    """获取全局Elasticsearch日志记录器实例"""
    global _es_logger
    if _es_logger is None:
        # 从配置文件读取设置
        config_file = Path(__file__).parent.parent / "config" / "elasticsearch_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                _es_logger = ElasticsearchLogger(
                    hosts=config.get('hosts', ['localhost:9200']),
                    index_prefix=config.get('index_prefix', 'qingniao_conversations'),
                    retention_days=config.get('retention_days', 90)
                )
            except Exception as e:
                print(f"⚠️ 读取Elasticsearch配置失败: {e}，使用默认配置")
                _es_logger = ElasticsearchLogger()
        else:
            _es_logger = ElasticsearchLogger()
    return _es_logger


if __name__ == '__main__':
    # 测试
    logger = get_es_logger()
    
    if logger.available:
        print("测试记录对话...")
        doc_id = logger.log_conversation(
            user_message="测试消息",
            assistant_message="测试回复",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        print(f"✓ 记录成功，文档ID: {doc_id}")
        
        print("\n测试搜索...")
        results = logger.search(query="测试", limit=5)
        print(f"✓ 找到 {len(results)} 条记录")
        
        print("\n统计信息:")
        stats = logger.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print("❌ Elasticsearch不可用，请检查配置和连接")

