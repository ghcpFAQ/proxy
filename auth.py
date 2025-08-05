"""
认证模块 - 处理用户认证和权限验证
"""
import os
import re
import base64
import urllib.parse
from mitmproxy import ctx, http
from config import ENABLE_AUTH, auth_whitelist_url

def is_url_allowed(url: str, allowed_patterns) -> bool:
    """检查URL是否在允许的模式列表中"""
    for pattern in allowed_patterns:
        if re.match(pattern, url):
            return True
    return False

class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        if ENABLE_AUTH:
            self.proxy_authorizations = {} 
            self.credentials = self.load_credentials("creds.txt")
        else:
            self.proxy_authorizations = {}
            self.credentials = {}
    
    def load_credentials(self, file_path):
        """从文件加载认证凭据"""
        if not ENABLE_AUTH:
            return {}
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Credentials file '{file_path}' not found")
        creds = {}
        with open(file_path, "r") as f:
            for line in f:
                username, password = line.strip().split(",")
                creds[username] = password
        return creds
    
    def handle_http_connect(self, flow: http.HTTPFlow):
        """处理HTTP连接认证"""
        if not ENABLE_AUTH:
            # 如果认证被禁用，直接允许连接
            self.proxy_authorizations[flow.client_conn.id] = "anonymous"
            return
            
        proxy_auth = flow.request.headers.get("Proxy-Authorization", "")
        url = flow.request.pretty_url
        # 如果没有代理授权头，返回401
        if not proxy_auth and not is_url_allowed(url, auth_whitelist_url):
            ctx.log.info("Proxy-Authorization: 401 failed " + url)
            flow.response = http.Response.make(401)

        ctx.log.info("Proxy-Authorization: " + proxy_auth.strip())
        if proxy_auth.strip() == "" :
            self.proxy_authorizations[(flow.client_conn.id)] = ""
            return
        auth_type, auth_string = proxy_auth.split(" ", 1)
        auth_string = base64.b64decode(auth_string).decode("utf-8")
        username, password = auth_string.split(":")
        if username == "admin":
            flow.response = http.Response.make(401)
        ctx.log.info("User: " + username + " Password: " + password)

        if username in self.credentials:
            # If the username exists, check if the password is correct
            if self.credentials[username] != password:
                ctx.log.info("User: " + username + " attempted to log in with an incorrect password.")
                flow.response = http.Response.make(401)
                return
        else:
            # If the username does not exist, log the event and return a 401 response
            ctx.log.info("Username: " + username + " does not exist.")
            flow.response = http.Response.make(401)
            return
    
        # ctx.log.info("Authenticated: " + flow.client_conn.id + ". url "  + flow.request.url)
        self.proxy_authorizations[(flow.client_conn.id)] = username
    
    def handle_github_session_request(self, flow: http.HTTPFlow):
        """处理GitHub会话请求的特殊验证"""
        if ENABLE_AUTH and flow.request.url == "https://github.com/session":
            request_body = flow.request.content
            # 输出请求体
            ctx.log.info("Request body: " + str(request_body))
            parsed_body = urllib.parse.parse_qs(request_body.decode())
            login_value = parsed_body.get('login', [''])[0]
            ctx.log.info("login value1: " + login_value)
            #if login_value contains _hdkj
            if not login_value.endswith('_cdemoemu'):
                flow.response = http.Response.make(403, b"Forbidden", {"Content-Type": "text/html"})
                return True
        return False
    
    def get_username(self, client_conn_id):
        """获取连接对应的用户名"""
        return self.proxy_authorizations.get(client_conn_id, "anonymous")
