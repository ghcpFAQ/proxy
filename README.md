# GitHub Copilot Proxy - 遥测数据采集

一个基于mitmproxy的GitHub Copilot遥测数据采集和分析程序，支持实时数据流处理、Elasticsearch存储和多种配置选项。
GitHub Copilot 官方提供 metric API , 仅以此程序用于辅助 GitHub Copilot 的用量数据的采集，及某些场景下需要对代码进出开发环境时的必要监控。

## 📁 项目结构

```
ctrip/
├── proxy-es-streaming.py      # 主代理服务器入口
├── config.py                  # 配置管理模块
├── auth.py                    # 认证管理模块
├── stream_saver.py            # 数据流处理模块
├── json_parser.py             # JSON数据解析模块
├── telemetry_handlers.py      # 遥测事件处理器
├── file_manager.py            # 文件管理模块
├── elasticsearch_client.py    # Elasticsearch客户端
├── creds.txt                  # 认证凭据文件
├── certs_v1/                  # SSL证书目录
│   ├── mitmproxy_ca.crt
│   ├── mitmproxy_ca.key
│   └── ...
└── copilot_telemetry_data/    # 遥测数据存储目录（自动创建）
    └── YYYYMMDD/
        ├── telemetry_events_*.json
        └── ...
```

## 🚀 快速开始

### 方式一：Docker部署（推荐）


#### 使用Docker单独部署

```bash
# 构建镜像
docker build -t copilot-proxy .

# 运行容器（基础模式）
docker run -d \
  --name copilot-proxy \
  -p 8080:8080 \
  copilot-proxy

# 运行容器（启用所有功能）
docker run -d \
  --name copilot-proxy \
  -p 8080:8080 \
  -e ENABLE_AUTH=true \
  -e ENABLE_URL_FILTERING=true \
  -e ENABLE_TELEMETRY_FILE_SAVE=true \
  -v $(pwd)/copilot_telemetry_data:/app/copilot_telemetry_data \
  -v $(pwd)/creds.txt:/app/creds.txt:ro \
  copilot-proxy
```

### 方式二：本地安装

#### 1. 环境准备

确保已安装以下依赖：

```bash
# 安装mitmproxy
pip install pip mitmproxy==11.0.2 

# 安装Elasticsearch 库， 版本根据实际使用的 es 定，当前代码使用的是7.13.1 
pip install elasticsearch


# 安装其他依赖
pip install asyncio logging gzip datetime
```

#### 2. 环境变量配置

创建认证文件（可选）：

```bash
# 创建creds.txt文件，包含Elasticsearch认证信息
echo "your_es_username:your_es_password" > creds.txt
```

设置环境变量：

```bash

export ENABLE_AUTH=true                    # 启用代理用户认证
export ENABLE_URL_FILTERING=true          # 启用URL过滤
export ENABLE_TELEMETRY_FILE_SAVE=true    # 启用本地文件保存
```

#### 3. 启动代理服务器

```bash
# 完整功能启动
mitmdump -s proxy-es-streaming.py --listen-port 8080 --set confdir=./certs
```

### 环境变量说明

系统支持通过环境变量进行灵活配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `ENABLE_AUTH` | `false` | 启用/禁用用户认证功能 |
| `ENABLE_URL_FILTERING` | `false` | 启用/禁用URL过滤功能 |
| `ENABLE_TELEMETRY_FILE_SAVE` | `false` | 启用/禁用遥测数据文件保存 |

### 认证配置(可选)

如果启用认证功能，需要创建 `creds.txt` 文件：

```bash
# creds.txt 格式（每行一个用户）
username1:password1
username2:password2
admin:secret123
```

**注意**: 使用冒号(:)分隔用户名和密码。

### 客户端配置


在 IDE 的代理部分配置 HTTP 代理, 如下为 bash 中的配置样例 : 

```bash
# 设置HTTP代理
export http_proxy=http://@localhost:8080
export https_proxy=http://@localhost:8080

# 或在应用程序中设置代理
curl --proxy http://localhost:8080 https://api.github.com
```

### 服务验证

启动服务后，验证各组件是否正常运行：

```bash
# 检查代理服务是否启动
curl -I --proxy http://localhost:8080 https://www.google.com



# 查看实时日志
mitmdump -s proxy-es-streaming.py --listen-port 8080 --set confdir=./certs --set termlog_verbosity=debug
```

## 🔧 功能特性

### 1. 用户认证系统
- **基于HTTP基础认证**的用户验证

### 2. URL过滤系统
- **模式匹配**：支持多种URL过滤模式
- **白名单机制**：仅允许匹配的URL通过
- **动态配置**：可在`config.py`中调整过滤规则

### 3. 遥测数据处理
- **多格式支持**：自动处理JSON、列表、字典等数据格式
- **智能转换**：非标准格式数据自动转换为标准baseData结构
- **事件分类**：根据事件类型分流处理

### 4. 数据存储系统

#### Elasticsearch存储
- **多索引支持**：
  - `mitmproxy-stream`: 一般代理流量数据
  - `telemetry-streaming`: 会话相关遥测事件

#### 文件存储（可选）
- **按日期组织**：`copilot_telemetry_data/YYYYMMDD/`
- **JSON格式**：结构化存储，便于分析
- **自动轮转**：按日期自动创建新目录

### 5. 事件处理器

系统支持多种遥测事件类型：

| 事件类型 | 处理器 | 说明 |
|---------|--------|------|
| `reportEditArc` | `handle_edit_arc_event` | 编辑弧事件 |
| `editSources.details` | `handle_edit_sources_details_event` | 编辑源详情事件 |
| `trackEditSurvival` | `handle_track_edit_survival_event` | 编辑存活跟踪事件 |
| `conversation.*` | `handle_conversation_events` | 会话相关事件 |
| `inlineConversation.*` | `handle_conversation_events` | 内联会话事件 |
| 其他事件 | `handle_general_telemetry_event` | 通用遥测事件 |

## 📊 数据分析

### 查看实时日志
```bash
# 查看详细调试信息
mitmdump -s proxy-es-streaming.py --set termlog_verbosity=debug

```

### 文件数据分析（如设定 ENABLE_TELEMETRY_FILE_SAVE 为 true）

```bash
# 查看今天的遥测数据
ls copilot_telemetry_data/$(date +%Y%m%d)/

# 分析JSON数据
cat copilot_telemetry_data/$(date +%Y%m%d)/telemetry_events_*.json | jq '.'
```

## 🛠️ 开发指南

### 添加新的事件处理器

1. 在 `telemetry_handlers.py` 中添加新的处理方法：

```python
async def handle_new_event_type(self, obj, username, ip, connectionid, url):
    """处理新事件类型"""
    # 处理逻辑
    pass
```

2. 在 `stream_saver.py` 中添加事件匹配逻辑：

```python
elif baseDataName == "new.event.type":
    await self.telemetry_handlers.handle_new_event_type(obj, username, ip, connectionid, url)
    continue
```


## 📋 功能组合说明

| ENABLE_AUTH | ENABLE_URL_FILTERING | ENABLE_TELEMETRY_FILE_SAVE | 行为描述 |
|-------------|---------------------|---------------------------|---------|
| false | false | false | 允许所有连接访问所有URL，仅ES存储（默认） |
| true | false | false | 需要认证但允许访问所有URL，仅ES存储 |
| false | true | false | 不需要认证但只能访问允许的URL，仅ES存储 |
| true | true | false | 需要认证且只能访问允许的URL，仅ES存储 |
| false | false | true | 允许所有连接访问所有URL，ES+文件存储 |
| true | true | true | 完整功能：认证+过滤+双重存储 |

## 📄 配置文件说明

### Elasticsearch配置

在 `elasticsearch_client.py` 中配置连接：

```python
ELASTICSEARCH_URL = "http://localhost:9200/"
ELASTICSEARCH_USERNAME = "elastic"
ELASTICSEARCH_PASSWORD = "your_password"
```

