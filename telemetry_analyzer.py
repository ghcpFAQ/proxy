#!/usr/bin/env python3
"""
Copilot 遥测数据分析工具

用于分析保存的遥测JSON文件，提取用户使用Copilot的用量数据

使用方法:
    python telemetry_analyzer.py --date 20250804 --user username
    python telemetry_analyzer.py --all
"""

import json
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import glob

class TelemetryAnalyzer:
    def __init__(self, data_dir="copilot_telemetry_data"):
        self.data_dir = data_dir
        
    def get_files_by_date(self, date_str=None):
        """获取指定日期的所有遥测文件"""
        if date_str:
            pattern = f"{self.data_dir}/{date_str}/telemetry_*.json"
        else:
            pattern = f"{self.data_dir}/*/telemetry_*.json"
        
        return glob.glob(pattern)
    
    def load_telemetry_file(self, file_path):
        """加载单个遥测文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"无法加载文件 {file_path}: {e}")
            return None
    
    def analyze_usage_summary(self, date_str=None, username=None):
        """分析用量汇总"""
        files = self.get_files_by_date(date_str)
        
        total_stats = {
            "total_files": 0,
            "total_events": 0,
            "users": defaultdict(int),
            "event_types": defaultdict(int),
            "dates": defaultdict(int),
            "connections": set(),
            "accepted_stats": {
                "total_lines": 0,
                "total_chars": 0,
                "count": 0
            },
            "shown_stats": {
                "total_lines": 0,
                "total_chars": 0,
                "count": 0
            },
            "languages": defaultdict(int),
            "editors": defaultdict(int)
        }
        
        for file_path in files:
            data = self.load_telemetry_file(file_path)
            if not data:
                continue
                
            # 过滤用户
            if username and data["metadata"]["username"] != username:
                continue
                
            total_stats["total_files"] += 1
            total_stats["total_events"] += data["metadata"]["total_objects"]
            total_stats["users"][data["metadata"]["username"]] += data["metadata"]["total_objects"]
            
            # 提取日期
            file_date = data["metadata"]["timestamp"][:10]  # YYYY-MM-DD
            total_stats["dates"][file_date] += data["metadata"]["total_objects"]
            
            # 连接ID
            total_stats["connections"].add(data["metadata"]["connectionid"])
            
            # 事件类型统计
            for event_type, count in data["raw_statistics"]["events_by_type"].items():
                total_stats["event_types"][event_type] += count
            
            # 分析具体的遥测对象
            for obj in data["telemetry_objects"]:
                if isinstance(obj, dict):
                    try:
                        base_data = obj.get("data", {}).get("baseData", {})
                        event_name = base_data.get("name", "")
                        
                        # 统计接受和显示的数据
                        if "accepted" in event_name.lower():
                            measurements = base_data.get("measurements", {})
                            lines = measurements.get("numLines", 0)
                            chars = measurements.get("compCharLen", 0)
                            if lines > 0:
                                total_stats["accepted_stats"]["total_lines"] += lines
                                total_stats["accepted_stats"]["total_chars"] += chars
                                total_stats["accepted_stats"]["count"] += 1
                        
                        elif "shown" in event_name.lower():
                            measurements = base_data.get("measurements", {})
                            lines = measurements.get("numLines", 0)
                            chars = measurements.get("compCharLen", 0)
                            if lines > 0:
                                total_stats["shown_stats"]["total_lines"] += lines
                                total_stats["shown_stats"]["total_chars"] += chars
                                total_stats["shown_stats"]["count"] += 1
                        
                        # 语言和编辑器统计
                        properties = base_data.get("properties", {})
                        if properties:
                            lang = properties.get("languageId", "unknown")
                            editor_version = properties.get("editor_version", "unknown")
                            
                            total_stats["languages"][lang] += 1
                            total_stats["editors"][editor_version] += 1
                            
                    except Exception as e:
                        continue
        
        return total_stats
    
    def print_summary(self, stats):
        """打印汇总统计"""
        print("=" * 60)
        print("Copilot 遥测数据分析报告")
        print("=" * 60)
        
        print(f"\n📁 文件统计:")
        print(f"  总文件数: {stats['total_files']}")
        print(f"  总事件数: {stats['total_events']}")
        print(f"  连接数: {len(stats['connections'])}")
        
        print(f"\n👤 用户统计:")
        for user, count in sorted(stats['users'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {user}: {count} 事件")
        
        print(f"\n📅 日期统计:")
        for date, count in sorted(stats['dates'].items()):
            print(f"  {date}: {count} 事件")
        
        print(f"\n🔄 事件类型统计:")
        for event_type, count in sorted(stats['event_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {event_type}: {count} 次")
        
        print(f"\n✅ 接受统计:")
        accepted = stats['accepted_stats']
        if accepted['count'] > 0:
            print(f"  接受次数: {accepted['count']}")
            print(f"  总行数: {accepted['total_lines']}")
            print(f"  总字符数: {accepted['total_chars']}")
            print(f"  平均行数/次: {accepted['total_lines'] / accepted['count']:.2f}")
            print(f"  平均字符数/次: {accepted['total_chars'] / accepted['count']:.2f}")
        else:
            print("  无接受数据")
        
        print(f"\n👁 显示统计:")
        shown = stats['shown_stats']
        if shown['count'] > 0:
            print(f"  显示次数: {shown['count']}")
            print(f"  总行数: {shown['total_lines']}")
            print(f"  总字符数: {shown['total_chars']}")
            print(f"  平均行数/次: {shown['total_lines'] / shown['count']:.2f}")
            print(f"  平均字符数/次: {shown['total_chars'] / shown['count']:.2f}")
        else:
            print("  无显示数据")
        
        # 计算接受率
        if shown['count'] > 0 and accepted['count'] > 0:
            acceptance_rate = (accepted['count'] / shown['count']) * 100
            print(f"\n📊 接受率: {acceptance_rate:.2f}%")
        
        print(f"\n💻 语言统计:")
        for lang, count in sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {lang}: {count} 次")
        
        print(f"\n🖥 编辑器统计:")
        for editor, count in sorted(stats['editors'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {editor}: {count} 次")
    
    def generate_daily_report(self, date_str):
        """生成指定日期的详细报告"""
        stats = self.analyze_usage_summary(date_str)
        
        # 保存报告到文件
        report_file = f"copilot_analysis_report_{date_str}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            # 将set转换为list以便JSON序列化
            stats_for_json = dict(stats)
            stats_for_json['connections'] = list(stats['connections'])
            json.dump(stats_for_json, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        return stats

def main():
    parser = argparse.ArgumentParser(description='Copilot 遥测数据分析工具')
    parser.add_argument('--date', help='分析指定日期的数据 (格式: YYYYMMDD)')
    parser.add_argument('--user', help='分析指定用户的数据')
    parser.add_argument('--all', action='store_true', help='分析所有数据')
    parser.add_argument('--report', action='store_true', help='生成详细报告文件')
    
    args = parser.parse_args()
    
    analyzer = TelemetryAnalyzer()
    
    if args.all:
        stats = analyzer.analyze_usage_summary()
    else:
        stats = analyzer.analyze_usage_summary(args.date, args.user)
    
    analyzer.print_summary(stats)
    
    if args.report:
        date_str = args.date or datetime.now().strftime("%Y%m%d")
        analyzer.generate_daily_report(date_str)

if __name__ == "__main__":
    main()
