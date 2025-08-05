#!/usr/bin/env python3
"""
Copilot 遥测数据分析工具

用于分析保存的遥测JSON文件，提取用户使用统计数据

使用方法:
1. 分析特定日期的数据: python analyze_telemetry.py --date 20250803
2. 分析特定用户的数据: python analyze_telemetry.py --user username
3. 生成完整报告: python analyze_telemetry.py --report
4. 分析最近N天的数据: python analyze_telemetry.py --days 7
"""

import json
import os
import argparse
import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import pandas as pd

class TelemetryAnalyzer:
    def __init__(self, data_dir="copilot_telemetry_data"):
        self.data_dir = data_dir
        self.summary_data = []
        
    def load_summary_log(self):
        """加载汇总日志文件"""
        summary_file = os.path.join(self.data_dir, "w.log")
        if not os.path.exists(summary_file):
            print(f"汇总日志文件不存在: {summary_file}")
            return []
        
        summary_data = []
        with open(summary_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    summary_data.append(entry)
                except json.JSONDecodeError:
                    continue
        
        self.summary_data = summary_data
        return summary_data
    
    def get_files_by_date(self, target_date):
        """获取指定日期的所有文件"""
        date_dir = os.path.join(self.data_dir, target_date)
        if not os.path.exists(date_dir):
            return []
        
        files = glob.glob(os.path.join(date_dir, "telemetry_*.json"))
        return files
    
    def get_files_by_user(self, username):
        """获取指定用户的所有文件"""
        files = []
        for entry in self.summary_data:
            if entry.get("username") == username:
                files.append(entry.get("filename"))
        return [f for f in files if f and os.path.exists(f)]
    
    def get_files_by_days(self, days):
        """获取最近N天的所有文件"""
        files = []
        target_dates = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            target_dates.append(date)
        
        for date in target_dates:
            files.extend(self.get_files_by_date(date))
        
        return files
    
    def analyze_file(self, filename):
        """分析单个JSON文件"""
        if not os.path.exists(filename):
            print(f"文件不存在: {filename}")
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get("metadata", {})
            telemetry_objects = data.get("telemetry_objects", [])
            
            analysis = {
                "filename": filename,
                "metadata": metadata,
                "total_events": len(telemetry_objects),
                "event_types": defaultdict(int),
                "copilot_events": {
                    "completions_shown": 0,
                    "completions_accepted": 0,
                    "characters_shown": 0,
                    "characters_accepted": 0,
                    "lines_shown": 0,
                    "lines_accepted": 0
                },
                "languages": defaultdict(int),
                "editors": defaultdict(int)
            }
            
            # 分析每个遥测对象
            for obj in telemetry_objects:
                try:
                    base_data = obj.get("data", {}).get("baseData", {})
                    event_name = base_data.get("name", "unknown")
                    analysis["event_types"][event_name] += 1
                    
                    # 提取Copilot相关指标
                    if "shown" in event_name.lower():
                        analysis["copilot_events"]["completions_shown"] += 1
                        measurements = base_data.get("measurements", {})
                        analysis["copilot_events"]["characters_shown"] += measurements.get("compCharLen", 0)
                        analysis["copilot_events"]["lines_shown"] += measurements.get("numLines", 0)
                    
                    elif "accepted" in event_name.lower():
                        analysis["copilot_events"]["completions_accepted"] += 1
                        measurements = base_data.get("measurements", {})
                        analysis["copilot_events"]["characters_accepted"] += measurements.get("compCharLen", 0)
                        analysis["copilot_events"]["lines_accepted"] += measurements.get("numLines", 0)
                    
                    # 提取语言和编辑器信息
                    properties = base_data.get("properties", {})
                    language = properties.get("languageId", "unknown")
                    editor_version = properties.get("editor_version", "unknown")
                    
                    if language != "unknown":
                        analysis["languages"][language] += 1
                    
                    if "/" in editor_version:
                        editor = editor_version.split("/")[0]
                        analysis["editors"][editor] += 1
                        
                except Exception as e:
                    print(f"分析对象时出错: {str(e)}")
                    continue
            
            return analysis
            
        except Exception as e:
            print(f"分析文件 {filename} 时出错: {str(e)}")
            return None
    
    def analyze_multiple_files(self, files):
        """分析多个文件并汇总"""
        all_analyses = []
        summary = {
            "total_files": len(files),
            "total_events": 0,
            "event_types": defaultdict(int),
            "copilot_summary": {
                "completions_shown": 0,
                "completions_accepted": 0,
                "characters_shown": 0,
                "characters_accepted": 0,
                "lines_shown": 0,
                "lines_accepted": 0,
                "acceptance_rate": 0.0
            },
            "languages": defaultdict(int),
            "editors": defaultdict(int),
            "users": set(),
            "date_range": {"start": None, "end": None}
        }
        
        for filename in files:
            analysis = self.analyze_file(filename)
            if analysis:
                all_analyses.append(analysis)
                
                # 汇总数据
                summary["total_events"] += analysis["total_events"]
                
                for event_type, count in analysis["event_types"].items():
                    summary["event_types"][event_type] += count
                
                for key, value in analysis["copilot_events"].items():
                    summary["copilot_summary"][key] += value
                
                for lang, count in analysis["languages"].items():
                    summary["languages"][lang] += count
                
                for editor, count in analysis["editors"].items():
                    summary["editors"][editor] += count
                
                # 添加用户
                username = analysis["metadata"].get("username")
                if username:
                    summary["users"].add(username)
                
                # 更新日期范围
                timestamp = analysis["metadata"].get("timestamp")
                if timestamp:
                    if not summary["date_range"]["start"] or timestamp < summary["date_range"]["start"]:
                        summary["date_range"]["start"] = timestamp
                    if not summary["date_range"]["end"] or timestamp > summary["date_range"]["end"]:
                        summary["date_range"]["end"] = timestamp
        
        # 计算接受率
        if summary["copilot_summary"]["completions_shown"] > 0:
            summary["copilot_summary"]["acceptance_rate"] = (
                summary["copilot_summary"]["completions_accepted"] / 
                summary["copilot_summary"]["completions_shown"] * 100
            )
        
        summary["users"] = list(summary["users"])
        return summary, all_analyses
    
    def generate_report(self, summary, output_file=None):
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("Copilot 遥测数据分析报告")
        report.append("=" * 60)
        report.append("")
        
        # 基本统计
        report.append("📊 基本统计:")
        report.append(f"  总文件数: {summary['total_files']}")
        report.append(f"  总事件数: {summary['total_events']}")
        report.append(f"  用户数量: {len(summary['users'])}")
        report.append(f"  日期范围: {summary['date_range']['start']} 到 {summary['date_range']['end']}")
        report.append("")
        
        # Copilot 使用统计
        report.append("🤖 Copilot 使用统计:")
        copilot = summary["copilot_summary"]
        report.append(f"  代码建议显示次数: {copilot['completions_shown']}")
        report.append(f"  代码建议接受次数: {copilot['completions_accepted']}")
        report.append(f"  接受率: {copilot['acceptance_rate']:.2f}%")
        report.append(f"  显示字符数: {copilot['characters_shown']}")
        report.append(f"  接受字符数: {copilot['characters_accepted']}")
        report.append(f"  显示行数: {copilot['lines_shown']}")
        report.append(f"  接受行数: {copilot['lines_accepted']}")
        report.append("")
        
        # 编程语言统计
        report.append("💻 编程语言使用统计:")
        for lang, count in sorted(summary["languages"].items(), key=lambda x: x[1], reverse=True)[:10]:
            report.append(f"  {lang}: {count} 次")
        report.append("")
        
        # 编辑器统计
        report.append("🔧 编辑器使用统计:")
        for editor, count in sorted(summary["editors"].items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {editor}: {count} 次")
        report.append("")
        
        # 事件类型统计
        report.append("📝 事件类型统计 (Top 10):")
        for event_type, count in sorted(summary["event_types"].items(), key=lambda x: x[1], reverse=True)[:10]:
            report.append(f"  {event_type}: {count} 次")
        report.append("")
        
        # 用户列表
        report.append("👥 用户列表:")
        for user in sorted(summary["users"]):
            report.append(f"  {user}")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存到: {output_file}")
        else:
            print(report_text)
        
        return report_text


def main():
    parser = argparse.ArgumentParser(description="Copilot 遥测数据分析工具")
    parser.add_argument("--date", help="分析指定日期的数据 (格式: YYYYMMDD)")
    parser.add_argument("--user", help="分析指定用户的数据")
    parser.add_argument("--days", type=int, help="分析最近N天的数据")
    parser.add_argument("--report", action="store_true", help="生成完整报告")
    parser.add_argument("--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    analyzer = TelemetryAnalyzer()
    analyzer.load_summary_log()
    
    files = []
    
    if args.date:
        files = analyzer.get_files_by_date(args.date)
        print(f"找到 {len(files)} 个文件 (日期: {args.date})")
    elif args.user:
        files = analyzer.get_files_by_user(args.user)
        print(f"找到 {len(files)} 个文件 (用户: {args.user})")
    elif args.days:
        files = analyzer.get_files_by_days(args.days)
        print(f"找到 {len(files)} 个文件 (最近 {args.days} 天)")
    elif args.report:
        # 分析所有可用文件
        all_files = glob.glob("copilot_telemetry_data/*/telemetry_*.json")
        files = all_files
        print(f"找到 {len(files)} 个文件 (所有数据)")
    else:
        print("请指定分析参数。使用 --help 查看帮助信息。")
        return
    
    if not files:
        print("没有找到符合条件的文件。")
        return
    
    print("正在分析数据...")
    summary, analyses = analyzer.analyze_multiple_files(files)
    
    output_file = args.output if args.output else None
    analyzer.generate_report(summary, output_file)


if __name__ == "__main__":
    main()
