
"""
Mitmproxy 代理服务器 - 支持条件性认证和URL过滤

环境变量配置：
- ENABLE_AUTH: 设置为 "true" 启用认证功能，设置为 "false" 或不设置则禁用认证
- ENABLE_URL_FILTERING: 设置为 "true" 启用URL过滤功能，设置为 "false" 或不设置则禁用URL过滤
- ENABLE_TELEMETRY_FILE_SAVE: 设置为 "true" 启用遥测事件文件保存，设置为 "false" 或不设置则禁用文件保存
  
使用示例：
- 启用所有功能: export ENABLE_AUTH=true ENABLE_URL_FILTERING=true ENABLE_TELEMETRY_FILE_SAVE=true && mitmdump -s proxy-es-streaming.py
- 仅启用认证: export ENABLE_AUTH=true && mitmdump -s proxy-es-streaming.py
- 仅启用文件保存: export ENABLE_TELEMETRY_FILE_SAVE=true && mitmdump -s proxy-es-streaming.py
- 全部禁用: mitmdump -s proxy-es-streaming.py (默认全部禁用)
"""

from mitmproxy import ctx, http
from config import (
    ENABLE_AUTH, 
    ENABLE_URL_FILTERING, 
    ENABLE_TELEMETRY_FILE_SAVE,
    allowed_patterns
)
from auth import AuthManager, is_url_allowed
from stream_saver import StreamSaver


def load(loader):
    """加载插件时的初始化函数"""
    ctx.log.debug("loading streaming server addon")
    ctx.log.info(f"认证功能: {'启用' if ENABLE_AUTH else '禁用'}")
    ctx.log.info(f"URL过滤功能: {'启用' if ENABLE_URL_FILTERING else '禁用'}")
    ctx.log.info(f"遥测文件保存: {'启用' if ENABLE_TELEMETRY_FILE_SAVE else '禁用'}")
    
    if ENABLE_AUTH:
        ctx.log.info("认证模式: 需要有效凭据")
    else:
        ctx.log.info("认证模式: 允许匿名访问")
    
    if ENABLE_URL_FILTERING:
        ctx.log.info(f"URL过滤: 仅允许匹配模式的URL ({len(allowed_patterns)} 个模式)")
    else:
        ctx.log.info("URL过滤: 允许所有URL访问")
    
    if ENABLE_TELEMETRY_FILE_SAVE:
        ctx.log.info("遥测数据将保存到文件和ES")
    else:
        ctx.log.info("遥测数据仅保存到ES，不保存文件")
    
    # 简化版本：直接存储模式，无需缓存管理器
    ctx.log.info("遥测数据处理模式: 直接存储到ES")

class MITM_ADDON:
    """主要的mitmproxy插件类"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
    
    def http_connect(self, flow: http.HTTPFlow):
        """处理HTTP连接"""
        self.auth_manager.handle_http_connect(flow)

    def request(self, flow: http.HTTPFlow):
        """处理请求"""
        # 仅在启用URL过滤时执行URL检测
        if ENABLE_URL_FILTERING and not is_url_allowed(flow.request.pretty_url, allowed_patterns):
            ctx.log.info("Forbidden URL:\t"+flow.request.pretty_url)
            error_str = "Forbidden URL:\t"+flow.request.pretty_url
            flow.response = http.Response.make(403, error_str, {"Content-Type": "text/html"})
            flow.kill()
            return
        
        # 仅在启用认证时执行登录验证
        if self.auth_manager.handle_github_session_request(flow):
            return

    def requestheaders(self, flow: http.HTTPFlow) -> None:
        """处理请求头"""
        username = self.auth_manager.get_username(flow.client_conn.id)
        flow.request.stream = StreamSaver(flow, flow.request.url, flow.request.method, flow.request.headers, "req", flow.client_conn.address[0], flow.client_conn.id, username)

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """处理响应头"""
        if isinstance(flow.request.stream, StreamSaver):
            flow.request.stream.done()
        username = self.auth_manager.get_username(flow.client_conn.id)
        flow.response.stream = StreamSaver(flow, flow.request.url, flow.request.method, flow.response.headers, "rsp", flow.client_conn.address[0], flow.client_conn.id, username)

    def response(self, flow: http.HTTPFlow) -> None:
        """处理响应"""
        if isinstance(flow.response.stream, StreamSaver):
            flow.response.stream.done()

    def error(self, flow: http.HTTPFlow) -> None:
        """处理错误"""
        ctx.log.info("error")
        if flow.request and isinstance(flow.request.stream, StreamSaver):
            flow.request.stream.done()
        if flow.response and isinstance(flow.response.stream, StreamSaver):
            flow.response.stream.done()


addons = [
    MITM_ADDON()
]
