"""
Elasticsearch 客户端模块 - 管理ES连接和数据存储
"""
import functools
from datetime import datetime
from elasticsearch import Elasticsearch
from config import ELASTICSEARCH_URL, ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD

# 创建ES客户端实例
es = Elasticsearch(
    [ELASTICSEARCH_URL],
    # use_ssl=False,
    verify_certs=False,
    http_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD),
)

async def save_to_telemetry_streaming_index(doc_data, loop):
    """保存数据到 telemetry-streaming 索引"""
    index_func = functools.partial(es.index, index='telemetry-streaming', body=doc_data)
    await loop.run_in_executor(None, index_func)

async def save_to_mitmproxy_stream_index(doc_data, loop):
    """保存数据到 mitmproxy-stream 索引"""
    index_func = functools.partial(es.index, index='mitmproxy-stream', body=doc_data)
    await loop.run_in_executor(None, index_func)

async def save_to_telemetry_raw_index(doc_data, loop):
    """保存数据到 telemetry-raw 索引"""
    index_func = functools.partial(es.index, index='telemetry-raw', body=doc_data)
    await loop.run_in_executor(None, index_func)
