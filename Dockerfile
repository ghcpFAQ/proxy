# 使用官方的mitmproxy镜像作为基础镜像
FROM mitmproxy/mitmproxy:10.0.0

# 安装任何额外的依赖项（如果需要）
RUN pip install mitmproxy==11.0.2 elasticsearch==7.13.1 asyncio logging gzip datetime

# 将所有Python模块文件添加到容器中
COPY *.py /app/

# 将您的proxy 用户名密码本加到容器中（可选）
# COPY creds.txt /app/creds.txt

# 将您的 mitmproxy 的证书加到容器中
COPY ./certs /opt/mitmproxy

# 设置工作目录
WORKDIR /app

# 创建遥测数据存储目录
RUN mkdir -p /app/copilot_telemetry_data

# 设置mitmproxy的启动命令，使用您的脚本作为参数
CMD ["mitmdump", "--set", "confdir=/opt/mitmproxy", "-s", "proxy-es-streaming.py", "-p", "8080", "--listen-host", "0.0.0.0", "--set", "block_global=false", "--allow-hosts", "^(copilot-telemetry-service\\.githubusercontent\\.com|copilot-telemetry\\.githubusercontent\\.com|copilot-proxy\\.githubusercontent\\.com|api\\.github\\.com|api\\.githubcopilot\\.com|telemetry\\.enterprise\\.githubcopilot\\.com|telemetry\\.business\\.githubcopilot\\.com|.*\\.githubcopilot\\.com)$", "--set", "stream_large_bodies=1k"]