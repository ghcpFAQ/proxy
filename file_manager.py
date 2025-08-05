"""
文件存储模块 - 处理遥测数据的文件保存功能
"""
import os
import json
from datetime import datetime
from mitmproxy import ctx
from config import ENABLE_TELEMETRY_FILE_SAVE

class TelemetryFileManager:
    """遥测数据文件管理器"""
    
    def __init__(self):
        pass
    
    async def save_json_objects_to_file(self, json_objects, username, connectionid, url):
        """将解析的JSON对象保存到文件中，用于后续分析 - 通过环境变量控制"""
        # 检查是否启用文件保存功能
        if not ENABLE_TELEMETRY_FILE_SAVE:
            ctx.log.info("遥测事件文件保存功能已禁用 (ENABLE_TELEMETRY_FILE_SAVE=false)")
            return
            
        try:
            # 创建按日期组织的保存目录
            today = datetime.utcnow().strftime("%Y%m%d")
            save_dir = f"copilot_telemetry_data/{today}"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 生成文件名：包含时间戳、用户名和连接ID
            timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]  # 格式: HH:MM:SS.mmm
            filename = f"{save_dir}/telemetry_{timestamp}_{username}_{connectionid}.json"
            
            # 准备要保存的数据
            telemetry_data = {
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "username": username,
                    "connectionid": connectionid,
                    "url": url,
                    "total_objects": len(json_objects),
                    "processing_direction": "req",  # 固定为req，因为只处理请求
                },
                "telemetry_objects": json_objects,
                "raw_statistics": {
                    "events_by_type": {},
                    "total_events": len(json_objects)
                }
            }
            
            # 统计事件类型
            for obj in json_objects:
                try:
                    # 添加类型检查，确保obj是字典类型
                    if isinstance(obj, dict):
                        event_type = obj.get("data", {}).get("baseData", {}).get("name", "unknown")
                        if event_type in telemetry_data["raw_statistics"]["events_by_type"]:
                            telemetry_data["raw_statistics"]["events_by_type"][event_type] += 1
                        else:
                            telemetry_data["raw_statistics"]["events_by_type"][event_type] = 1
                    else:
                        # 记录非字典类型的对象
                        obj_type = f"non_dict_{type(obj).__name__}"
                        if obj_type in telemetry_data["raw_statistics"]["events_by_type"]:
                            telemetry_data["raw_statistics"]["events_by_type"][obj_type] += 1
                        else:
                            telemetry_data["raw_statistics"]["events_by_type"][obj_type] = 1
                except Exception as e:
                    ctx.log.info(f"统计事件类型时出错: {str(e)[:50]}...")
                    pass
            
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(telemetry_data, f, ensure_ascii=False, indent=2)
            
            ctx.log.info(f"已保存{len(json_objects)}个JSON对象到文件: {filename}")
            ctx.log.info(f"事件类型统计: {telemetry_data['raw_statistics']['events_by_type']}")
            
            # 同时创建一个汇总日志文件，记录所有保存的文件
            summary_file = f"copilot_telemetry_data/telemetry_summary.log"
            with open(summary_file, 'a', encoding='utf-8') as f:
                summary_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "date": today,
                    "filename": filename,
                    "username": username,
                    "connectionid": connectionid,
                    "object_count": len(json_objects),
                    "url": url,
                    "events_by_type": telemetry_data["raw_statistics"]["events_by_type"]
                }
                f.write(json.dumps(summary_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            ctx.log.info(f"保存JSON对象到文件时出错: {str(e)}")
