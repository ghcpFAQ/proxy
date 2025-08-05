"""
遥测事件处理模块 - 处理各种类型的遥测事件
"""
from datetime import datetime
from mitmproxy import ctx
from elasticsearch_client import save_to_telemetry_streaming_index

class TelemetryEventHandlers:
    """遥测事件处理器集合"""
    
    def __init__(self, loop):
        self.loop = loop
    
    async def handle_edit_sources_details_event(self, obj, username, ip, connectionid, url):
        """处理 GitHub.copilot-chat/vscode.editTelemetry.editSources.details 事件"""
        try:
            properties = obj.get("data", {}).get("baseData", {}).get("properties", {})
            source_key = properties.get("sourceKey", "")
            
            # 如果是 undoEdits 事件，跳过不记录
            if "source:Chat.undoEdits" in source_key:
                ctx.log.info(f"跳过 undoEdits 事件: sourceKey={source_key}")
                return
            
            # 其他 editSources.details 事件直接存入ES
            doc_data = {
                'user': username,
                'user_ip': ip,
                'connectionid': connectionid,
                "timestamp": datetime.utcnow().isoformat(),
                'request': {
                    'url': url,
                    'baseData': "GitHub.copilot-chat/vscode.editTelemetry.editSources.details",
                    'sourceKey': source_key,
                    'sourceKeyCleaned': properties.get("sourceKeyCleaned", ""),
                    'languageId': properties.get("languageId", ""),
                    'measurements': obj.get("data", {}).get("baseData", {}).get("measurements", {}),
                    'properties': properties
                },
            }
            
            # 直接保存到ES
            await save_to_telemetry_streaming_index(doc_data, self.loop)
            ctx.log.info(f"保存 editSources.details 事件到ES: sourceKey={source_key}")
            
        except Exception as e:
            ctx.log.info(f"处理 editSources.details 事件时出错: {str(e)}")
    
    async def handle_track_edit_survival_event(self, obj, username, ip, connectionid, url):
        """处理 agent/conversation.codeMapper.trackEditSurvival 事件"""
        try:
            measurements = obj.get("data", {}).get("baseData", {}).get("measurements", {})
            time_delay_ms = measurements.get("timeDelayMs", 0)
            
            # 只记录 timeDelayMs 为 300000 的数据
            if time_delay_ms == 300000:
                properties = obj.get("data", {}).get("baseData", {}).get("properties", {})
                
                doc_data = {
                    'user': username,
                    'user_ip': ip,
                    'connectionid': connectionid,
                    "timestamp": datetime.utcnow().isoformat(),
                    'request': {
                        'url': url,
                        'baseData': "agent/conversation.codeMapper.trackEditSurvival",
                        'messageId': properties.get("messageId", ""),
                        'conversationId': properties.get("conversationId", ""),
                        'unique_id': properties.get("unique_id", ""),
                        'measurements': measurements,
                        'properties': properties
                    },
                }
                
                # 直接保存到ES
                await save_to_telemetry_streaming_index(doc_data, self.loop)
                ctx.log.info(f"保存 trackEditSurvival 事件到ES: timeDelayMs={time_delay_ms}, unique_id={properties.get('unique_id', '')}")
            else:
                ctx.log.info(f"跳过 trackEditSurvival 事件: timeDelayMs={time_delay_ms} (需要300000)")
                
        except Exception as e:
            ctx.log.info(f"处理 trackEditSurvival 事件时出错: {str(e)}")
    
    async def handle_conversation_events(self, obj, username, ip, connectionid, url):
        """处理会话相关事件 (appliedCodeblock, acceptedInsert, acceptedCopy)"""
        try:
            properties = obj.get("data", {}).get("baseData", {}).get("properties", {})
            base_data_name = obj.get("data", {}).get("baseData", {}).get("name", "")
            
            doc_data = {
                'user': username,
                'user_ip': ip,
                'connectionid': connectionid,
                "timestamp": datetime.utcnow().isoformat(),
                'request': {
                    'url': url,
                    'baseData': base_data_name,
                    'messageId': properties.get("messageId", ""),
                    'conversationId': properties.get("conversationId", ""),
                    'codeBlockIndex': properties.get("codeBlockIndex", ""),
                    'source': properties.get("source", ""),
                    'uiKind': properties.get("uiKind", ""),
                    'compType': properties.get("compType", ""),
                    'mode': properties.get("mode", ""),
                    'modelId': properties.get("modelId", ""),
                    'languageId': properties.get("languageId", ""),
                    'fileType': properties.get("fileType", ""),
                    'unique_id': properties.get("unique_id", ""),
                    'measurements': obj.get("data", {}).get("baseData", {}).get("measurements", {}),
                    'properties': properties
                },
            }
            
            # 直接保存到ES
            await save_to_telemetry_streaming_index(doc_data, self.loop)
            ctx.log.info(f"保存会话事件到ES: {base_data_name}, messageId={properties.get('messageId', '')}")
            
        except Exception as e:
            ctx.log.info(f"处理会话事件时出错: {str(e)}")
    
    async def handle_edit_arc_event(self, obj, username, ip, connectionid, url):
        """处理 editTelemetry.reportEditArc 事件 - 直接存入ES"""
        try:
            measurements = obj.get("data", {}).get("baseData", {}).get("measurements", {})
            time_delay_ms = measurements.get("timeDelayMs", 0)
            if time_delay_ms == 0:
                properties = obj.get("data", {}).get("baseData", {}).get("properties", {})
                request_id = properties.get("requestId", "")
                # 准备ES文档数据
                doc_data = {
                    'user': username,
                    'user_ip': ip,
                    'connectionid': connectionid,
                    "timestamp": datetime.utcnow().isoformat(),
                    'request': {
                        'url': url,
                        'baseData': "GitHub.copilot-chat/vscode.editTelemetry.reportEditArc",
                        'requestId': request_id,
                        'editSessionId': properties.get("editSessionId", ""),
                        'sourceKeyCleaned': properties.get("sourceKeyCleaned", ""),
                        'modelId': properties.get("modelId", ""),
                        'measurements': obj.get("data", {}).get("baseData", {}).get("measurements", {}),
                        'properties': properties
                    },
                }
                
                # 直接保存到ES
                await save_to_telemetry_streaming_index(doc_data, self.loop)
                ctx.log.info(f"保存 editTelemetry.reportEditArc 事件到ES: requestId={request_id}")
            
        except Exception as e:
            ctx.log.info(f"处理 editTelemetry.reportEditArc 事件时出错: {str(e)}")
    
    async def handle_general_telemetry_event(self, obj, username, ip, connectionid, url):
        """处理一般的遥测事件 (shown/accepted 等)"""
        try:
            base_data_name = obj.get("data", {}).get("baseData", {}).get("name", "")
            
            accepted_numLines = 0
            accepted_charLens = 0
            shown_numLines = 0
            shown_charLens = 0
            
            if "hown" in base_data_name or "accepted" in base_data_name:
                measurements = obj.get("data", {}).get("baseData", {}).get("measurements", {})
                properties = obj.get("data", {}).get("baseData", {}).get("properties", {})
                
                if "hown" in base_data_name:
                    shown_numLines = measurements.get("numLines", 0)
                    shown_charLens = measurements.get("compCharLen", 0)
                else: 
                    accepted_numLines = measurements.get("numLines", 0)
                    accepted_charLens = measurements.get("compCharLen", 0)
                    
                doc_data = {
                    'user': username,
                    'user_ip': ip,
                    'connectionid': connectionid,
                    "timestamp": datetime.utcnow().isoformat(),
                    'request': {
                        'url': url,
                        'baseData': base_data_name,
                        'accepted_numLines': accepted_numLines,
                        'shown_numLines': shown_numLines,
                        'accepted_charLens': accepted_charLens,
                        'shown_charLens': shown_charLens,
                        'language': properties.get("languageId", ""),
                        'editor': properties.get("editor_version", "/").split("/")[0],
                        'editor_version': properties.get("editor_version", "/").split("/")[1],
                        'copilot-ext-version': properties.get("common_extversion", ""),
                    },
                }
                await save_to_telemetry_streaming_index(doc_data, self.loop)
                ctx.log.info(f"保存一般遥测事件到ES: {base_data_name}")
                
        except Exception as e:
            ctx.log.info(f"处理一般遥测事件时出错: {str(e)}")
