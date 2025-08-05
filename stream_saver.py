"""
StreamSaver模块 - 处理数据流的保存和处理
"""
import asyncio
import logging
import gzip
from datetime import datetime
from mitmproxy import ctx
from config import ENABLE_TELEMETRY_FILE_SAVE
from json_parser import JSONParser
from telemetry_handlers import TelemetryEventHandlers
from file_manager import TelemetryFileManager
from elasticsearch_client import save_to_mitmproxy_stream_index, save_to_telemetry_raw_index

class StreamSaver:
    """数据流保存器 - 处理流式数据的收集、解析和存储"""
    
    TAG = "save_streamed_data: "
    
    def __init__(self, flow, url, method, headers, direction, ip, connectionid, username):
        self.loop = asyncio.get_event_loop()
        self.flow = flow
        self.url = url
        self.method = method
        self.headers = headers
        self.direction = direction
        self.content = ""
        self.ip = ip
        self.fh = False
        self.path = None
        self.connectionid = connectionid
        self.username = username
        
        # 初始化处理器
        self.json_parser = JSONParser()
        self.telemetry_handlers = TelemetryEventHandlers(self.loop)
        self.file_manager = TelemetryFileManager()

    async def save_to_elasticsearch(self, ip, url, method, headers, content, direction, connectionid, username):
        """保存数据到Elasticsearch"""
        if len(content.strip()) == 0:
            return
            
        if "complet" in url or "telemetry" in url:
            if direction == "rsp" and "complet" in url:
                content = await self.json_parser.parse_res_content(content)
                if len(content.strip()) == 0:
                    return
                    
            doc = {
                'user': username,
                'user_ip': ip,
                'connectionid': connectionid,
                "timestamp": datetime.utcnow().isoformat(),
                'payload': {
                    'url': url,
                    'method': method,
                    'headers': dict(headers),
                    'content': content,
                    'direction': direction,
                },
            }
            
            if "complet" in url:
                await save_to_mitmproxy_stream_index(doc, self.loop)
            else:
                # 处理遥测数据
                if direction == "rsp":
                    return
                    
                await self._process_telemetry_data(content, username, ip, connectionid, url)

    async def _process_telemetry_data(self, request_content, username, ip, connectionid, url):
        """处理遥测数据"""
        json_objects = await self.json_parser.split_jsons(request_content, url)
        
        # 如果找到了JSON对象，按原逻辑处理
        if json_objects:
            # 保存JSON对象到文件，用于后续分析
            await self.file_manager.save_json_objects_to_file(json_objects, username, connectionid, url)
            
            for obj in json_objects:
                # 打印调试信息，看看 obj 的具体内容和类型
                ctx.log.debug(f"调试: obj类型 = {type(obj).__name__}")
                ctx.log.debug(f"调试: obj内容 = {obj}")
                if hasattr(obj, '__len__'):
                    ctx.log.debug(f"调试: obj长度 = {len(obj)}")
                
                # 使用嵌套函数递归处理对象
                async def process_single_obj(single_obj, is_from_list=False):
                    """处理单个对象的嵌套函数"""
                    if is_from_list:
                        ctx.log.debug(f"调试: 处理从列表拆分的对象，类型 = {type(single_obj).__name__}")
                        ctx.log.debug(f"调试: 拆分对象内容 = {single_obj}")
                    
                    # 如果是非字典类型，转换为标准格式
                    if not isinstance(single_obj, dict):
                        single_obj = self._convert_non_dict_to_basedata(single_obj)
                    
                    # 检查并处理缺少 baseDataName 的情况
                    baseDataName = single_obj.get("data", {}).get("baseData", {}).get("name")

                    # 处理特定事件类型
                    if baseDataName == "GitHub.copilot-chat/vscode.editTelemetry.reportEditArc":
                        await self.telemetry_handlers.handle_edit_arc_event(single_obj, username, ip, connectionid, url)
                        return
                    
                    # 处理 editSources.details 事件
                    elif baseDataName == "GitHub.copilot-chat/vscode.editTelemetry.editSources.details":
                        await self.telemetry_handlers.handle_edit_sources_details_event(single_obj, username, ip, connectionid, url)
                        return
                    
                    # 处理 trackEditSurvival 事件
                    elif baseDataName == "agent/conversation.codeMapper.trackEditSurvival":
                        await self.telemetry_handlers.handle_track_edit_survival_event(single_obj, username, ip, connectionid, url)
                        return
                    
                    # 处理会话相关事件
                    elif any(suffix in baseDataName for suffix in [
                        "conversation.appliedCodeblock",
                        "conversation.acceptedInsert", 
                        "conversation.acceptedCopy",
                        "inlineConversation.acceptedInsert"
                    ]):
                        await self.telemetry_handlers.handle_conversation_events(single_obj, username, ip, connectionid, url)
                        return

                    # 处理一般的遥测事件
                    # await self.telemetry_handlers.handle_general_telemetry_event(single_obj, username, ip, connectionid, url)
                
                # 主处理逻辑：检查是否为列表，如果是则拆分处理
                if isinstance(obj, list):
                    ctx.log.debug(f"调试: 发现列表对象，内容 = {obj}")
                    ctx.log.debug(f"调试: 列表元素类型 = {[type(item).__name__ for item in obj]}")
                    ctx.log.debug(f"调试: 将列表拆分为 {len(obj)} 个独立对象进行处理")
                    
                    # 将列表中的每个元素作为独立对象处理
                    for i, list_item in enumerate(obj):
                        ctx.log.debug(f"调试: 处理列表中第 {i+1} 个对象")
                        await process_single_obj(list_item, is_from_list=True)
                else:
                    # 非列表对象，直接处理
                    await process_single_obj(obj)
        else:
            # 如果无法解析为JSON，但是是遥测数据，仍然保存原始内容
            ctx.log.debug("遥测数据无法解析为JSON，保存原始内容")
            doc = {
                'user': username,
                'user_ip': ip,
                'connectionid': connectionid,
                "timestamp": datetime.utcnow().isoformat(),
                'request': {
                    'url': url,
                    'raw_content': request_content[:1000],  # 限制长度避免存储过大
                    'content_length': len(request_content),
                    'content_type': 'unknown/binary',
                    'parsing_status': 'failed_json_parse'
                },
            }
            await save_to_telemetry_raw_index(doc, self.loop)

    def done(self):
        """流结束时的处理"""
        # 初始化为空内容，优先使用解压缩内容
        final_content = ""
        
        if "telemetry" in self.url and self.flow:
            ctx.log.info(f"处理遥测数据: URL={self.url}, direction={self.direction}")
            try:
                # 第一优先级：使用mitmproxy的完整解压缩内容
                if self.direction == "req" and self.flow.request and hasattr(self.flow.request, 'content'):
                    if self.flow.request.content:
                        try:
                            # 直接使用mitmproxy解压缩的完整内容
                            decoded_content = self.flow.request.content.decode('utf-8', errors='ignore')
                            ctx.log.debug(f"从mitmproxy request获取完整内容: 长度={len(decoded_content)}")
                            # 显示前200字符用于调试
                            debug_preview = decoded_content[:200]
                            ctx.log.debug(f"内容预览: {debug_preview}")
                            final_content = decoded_content
                        except Exception as e:
                            ctx.log.debug(f"从request.content解码失败: {str(e)}")
                            
                elif self.direction == "rsp" and self.flow.response and hasattr(self.flow.response, 'content'):
                    if self.flow.response.content:
                        try:
                            # 直接使用mitmproxy解压缩的完整内容
                            decoded_content = self.flow.response.content.decode('utf-8', errors='ignore')
                            ctx.log.debug(f"从mitmproxy response获取完整内容: 长度={len(decoded_content)}")
                            # 显示前200字符用于调试
                            debug_preview = decoded_content[:200]
                            ctx.log.debug(f"内容预览: {debug_preview}")
                            final_content = decoded_content
                        except Exception as e:
                            ctx.log.debug(f"从response.content解码失败: {str(e)}")
                
                # 第二优先级：如果mitmproxy没有提供合适的内容，尝试手动解压缩原始字节数据
                if not final_content and hasattr(self, 'raw_bytes') and self.raw_bytes:
                    ctx.log.debug(f"尝试手动解压缩原始字节数据: 长度={len(self.raw_bytes)}")
                    try:
                        # 尝试gzip解压缩
                        if self.raw_bytes[:2] == b'\x1f\x8b':  # gzip magic number
                            decompressed = gzip.decompress(self.raw_bytes)
                            final_content = decompressed.decode('utf-8', errors='ignore')
                            ctx.log.debug(f"手动gzip解压缩成功: 长度={len(final_content)}")
                        # 尝试zlib解压缩
                        elif len(self.raw_bytes) > 2:
                            import zlib
                            try:
                                decompressed = zlib.decompress(self.raw_bytes)
                                final_content = decompressed.decode('utf-8', errors='ignore')
                                ctx.log.debug(f"手动zlib解压缩成功: 长度={len(final_content)}")
                            except:
                                # 如果不是压缩数据，直接解码
                                final_content = self.raw_bytes.decode('utf-8', errors='ignore')
                                ctx.log.debug(f"直接解码原始字节数据: 长度={len(final_content)}")
                    except Exception as e:
                        ctx.log.debug(f"手动解压缩失败: {str(e)}")
                        # 最后的退路：使用流式收集的内容
                        final_content = self.content
                
                # 第三优先级：如果上述都失败，使用流式收集的内容
                if not final_content:
                    final_content = self.content
                    ctx.log.debug(f"使用流式收集的内容: 长度={len(final_content)}")
                        
            except Exception as e:
                ctx.log.debug(f"处理遥测数据时出错: {str(e)}")
                final_content = self.content
        else:
            # 非遥测数据，直接使用收集的内容
            final_content = self.content

        asyncio.ensure_future(self.save_to_elasticsearch(self.ip, self.url, self.method, self.headers, final_content, self.direction, self.connectionid, self.username))
        
        if self.fh:
            self.fh = False

        self.flow = None
        self.content = ""
        if hasattr(self, 'raw_bytes'):
            del self.raw_bytes

    def __call__(self, data):
        """处理流式数据"""
        # End of stream?
        if len(data) == 0:
            self.done()
            return data

        # This is a safeguard but should not be needed
        if not self.flow or not self.flow.request:
            return data

        if not self.fh:
            self.fh = True

        if self.fh:
            try:
                # 对于遥测数据，我们需要收集原始字节数据，不要在这里解码
                if "telemetry" in self.url:
                    # 保存原始字节数据，不进行任何转换，等到done()时统一处理
                    if isinstance(data, bytes):
                        if not hasattr(self, 'raw_bytes'):
                            self.raw_bytes = b''
                        self.raw_bytes += data
                    self.content = self.content + data.decode('utf-8', 'ignore')
                else:
                    # 普通数据的处理方式
                    self.content = self.content + data.decode('utf-8', 'ignore')
            except OSError:
                logging.error(f"{self.TAG}Failed to write to: {self.path}")

        return data
