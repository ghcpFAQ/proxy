"""
配置模块 - 管理环境变量和全局配置
"""
import os

# 通过环境变量控制是否启用认证功能
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# 通过环境变量控制是否启用URL过滤功能
ENABLE_URL_FILTERING = os.getenv("ENABLE_URL_FILTERING", "false").lower() == "true"

# 通过环境变量控制是否保存遥测事件到文件
ENABLE_TELEMETRY_FILE_SAVE = os.getenv("ENABLE_TELEMETRY_FILE_SAVE", "false").lower() == "true"

# Elasticsearch配置
ELASTICSEARCH_URL = "http://xxx:9200/"
ELASTICSEARCH_USERNAME = "xxx"
ELASTICSEARCH_PASSWORD = "xxx"

# URL白名单配置
allowed_patterns = [
     "*.*",
    #  "https://github.com/login.*",
    #  "https://vscode.dev/redirect.*",
    #  "https://github.com/settings/two_factor_checkup.*",
    #  "https://github.com/favicon.ico",
    #  "https://github.com/session",
    #  "https://github.com/sessions.*",
    #  "https://github.githubassets.com/assets.*",
    #  "https://api.github.com/user.*",
    #  "https://education.github.com/api/user",
    #  "https://api.github.com/copilot_internal/v2/token.*",
    #  "https://api.github.com/copilot_internal/notification.*",
    #  "https://default.exp-tas.com/.*",
    #  "https://copilot-proxy.githubusercontent.com.*",
    #  "https://api.github.com/applications/[0-9a-fA-F]+/token",
    #  "https://api.githubcopilot.com/.*",
    #  "https://copilot-telemetry-service.githubusercontent.com/.*",
    #  "https://copilot-telemetry.githubusercontent.com/.*",
    #  "https://api.github.com/teams/.*",
    #  "https://api.github.com/.*"
]

# 认证白名单URL - 仅在启用认证时使用
auth_whitelist_url = [
    "api.github.com.*",
    "api.enterprise.githubcopilot.com.*", 
    "api.busniess.githubcopilot.com.*",
] if ENABLE_AUTH else []
