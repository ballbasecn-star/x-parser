# X/Twitter Parser

从 Twitter/X 链接提取推文内容和元数据的 Python 工具。

## 特性

- 🚀 **无需 Twitter API** - 使用 Tavily API，无需申请 Twitter 开发者账号
- 📝 **完整内容提取** - 支持普通推文和长文章
- 🖼️ **媒体提取** - 自动提取图片和视频链接
- 📊 **互动数据** - 提取点赞、转发、浏览量等
- 🔗 **双域名支持** - 同时支持 `twitter.com` 和 `x.com`
- 🛠️ **多种接口** - CLI 命令行、Python API、HTTP API

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd x-parser

# 安装依赖
pip install -r requirements.txt

# 或使用 pip 安装
pip install -e .
```

## 配置

1. 获取 Tavily API Key：https://tavily.com/
2. 设置环境变量：

```bash
# 方式一：直接设置
export TAVILY_API_KEY=tvly-your-api-key

# 方式二：使用 .env 文件
cp .env.example .env
# 编辑 .env 文件，填入 API Key
```

## 快速开始

### 命令行

```bash
# 解析推文
python main.py "https://x.com/elonmusk/status/123456789"

# JSON 格式输出
python main.py --json "https://x.com/..."

# 检查 API Key 配置
python main.py --check
```

### Python API

```python
from xparser.parser import parse

# 解析推文
result = parse("https://x.com/username/status/123456789")

if result.success:
    tweet = result.tweet
    print(f"作者: {tweet.display_name} (@{tweet.username})")
    print(f"内容: {tweet.content_clean}")
    print(f"点赞: {tweet.metrics.likes}")
    print(f"图片: {len(tweet.images)} 张")
```

### 批量解析

```python
from xparser.parser import Parser

parser = Parser()

urls = [
    "https://x.com/user1/status/111",
    "https://x.com/user2/status/222",
]

results = parser.parse_batch(urls)
for r in results:
    if r.success:
        print(r.tweet.content_clean)
```

### HTTP API

```bash
# 启动服务
python -m web.app

# 或使用 gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web.app:app
```

**API 端点：**

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/health` | GET | 统一契约健康检查 |
| `/check-key` | GET | 检查 API Key 配置 |
| `/api/v1/parse` | POST | 统一契约解析推文 |
| `/api/v1/capabilities` | GET | 统一契约能力声明 |

**示例请求：**

```bash
# 解析推文
curl -X POST http://localhost:5000/api/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"requestId":"req_demo","input":{"sourceUrl":"https://x.com/elonmusk/status/123456789","platformHint":"x"}}'
```

## 发布脚本

当前仓库已经补齐“本地构建镜像 -> 导出镜像包 -> 上传服务器部署”的三段脚本：

```bash
./scripts/build-release-image.sh
./scripts/export-release-bundle.sh
./scripts/deploy-prebuilt-release.sh
```

部署时需要先准备：

- `deploy/.env.prod`
- 服务器目录，默认 `/root/apps/parsers/x-parser`
- 共享 Docker 网络 `content-shared`

## 契约与失败语义

`x-parser` 当前遵循统一 parser 契约，但需要特别注意一条约束：

- 只要 Tavily 没有提取到可用正文，就不能把结果伪装成成功
- 此时应该返回明确失败，而不是只返回 `tweet_id`、空正文和空 `rawData`

当前本地实现已经补上这条规则：

- 当正文提取为空时，`/api/v1/parse` 返回：
  - HTTP `422`
  - `error.code = UPSTREAM_CHANGED`
  - `error.message = 正文提取为空`

这样主系统可以明确识别“上游内容提取失败”，而不是把它当作一个可阅读内容继续入库和展示。

## 已知真实样本

当前有一个已经验证过的真实样本：

- `https://x.com/naval/status/1765427439452942630`

本地真实返回结论：

- Tavily 当前对该样本返回空结果
- `x-parser` 现已显式返回失败，而不是伪成功

对应统一契约返回示例：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "UPSTREAM_CHANGED",
    "message": "正文提取为空",
    "retryable": true
  },
  "meta": {
    "requestId": "req_local_real_x",
    "parserVersion": "0.1.0"
  }
}
```

这份样本用于后续回归，避免每次都先在线上主系统里反复排查。

补充两个 `X article` 本地回归样本：

- 成功样本：
  - `https://x.com/vista8/status/2035544573876023605`
  - 当前本地可返回 `200`
  - 已能提取出正文主体，适合用来回归 article 正文清洗
- 壳子失败样本：
  - `https://x.com/seekjourney/status/2035923833707012270`
  - 当前本地应返回 `422 / UPSTREAM_CHANGED / 正文提取为空`
  - 用于防止“只抓到 X 登录页壳子也被误判成功”

继续补充两条稳定可用的 `X article` 清洗回归样本：

- `https://x.com/boniusex/status/2035630916668907740`
  - 当前本地返回 `200`
  - 标题已稳定提取为 `Claude + Obsidian = 一个真正的 AI 员工`
  - 适合回归长文型 article 的正文段落清洗
- `https://x.com/aikangarooking/status/2035978244567306276`
  - 当前本地返回 `200`
  - 标题已稳定提取为 `耗时1天，开发了个信息聚合平台IdeaHub，已免费开源～`
  - 适合回归中文长文 article 的正文分段展示

当前另有一个短帖样本：

- `https://x.com/dontbesilent/status/2035077391266324525`
  - 这条更接近短帖，不纳入本轮 `X article` 正文清洗目标
  - 后续如果要做短帖展示策略，再单独回归

## 项目结构

```
x-parser/
├── main.py              # CLI 入口
├── requirements.txt     # 依赖
├── pyproject.toml       # 项目配置
├── .env.example         # 环境变量示例
├── xparser/             # 主模块
│   ├── __init__.py
│   ├── models.py        # 数据模型
│   ├── url_detector.py  # URL 检测
│   ├── crawler.py       # Tavily API 调用
│   ├── parser.py        # 主解析入口
│   └── utils.py         # 工具函数
├── tests/               # 测试
│   ├── __init__.py
│   ├── test_url_detector.py
│   └── test_utils.py
└── web/                 # Web 服务
    ├── __init__.py
    └── app.py
```

## 数据结构

### TweetInfo

```python
@dataclass
class TweetInfo:
    tweet_id: str           # 推文 ID
    username: str           # 用户名
    display_name: str       # 显示名称
    content: str            # 原始内容
    content_clean: str      # 清洗后内容
    title: Optional[str]    # 长文章标题
    created_at: str         # 发布时间
    images: List[str]       # 图片列表
    videos: List[str]       # 视频列表
    metrics: TweetMetrics   # 互动数据
    hashtags: List[str]     # 标签
    mentions: List[str]     # 提及
```

### TweetMetrics

```python
@dataclass
class TweetMetrics:
    likes: int          # 点赞数
    retweets: int       # 转发数
    replies: int        # 回复数
    quotes: int         # 引用数
    views: int          # 浏览量
    bookmarks: int      # 书签数
```

## 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 带覆盖率
pytest --cov=xparser
```

当前补充的最小回归建议：

```bash
pytest tests/test_parser_contract_api.py tests/test_parser_content_quality.py
```

## 注意事项

1. **Tavily API 限制**：免费版有请求次数限制，请查看 https://tavily.com/ 的定价
2. **内容可用性**：私密账号或已删除的推文无法获取
3. **代理设置**：如需代理，设置 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量

## License

MIT

## 镜像构建与线上更新

当前仓库的生产发布固定采用“本地构建镜像 -> 本地导出 bundle -> 上传服务器并重启”的方式。

### 前置条件

本地需要具备：

- Docker / Docker Buildx
- 可用的 `TAVILY_API_KEY`
- 已安装 `ssh`、`scp`
- 如果使用密码登录，还需要 `sshpass`

服务器默认目录：

```text
/root/apps/parsers/x-parser/
  deploy/
  images/
```

### 1. 准备生产环境文件

先复制模板：

```bash
cd /Users/apple/Workspace/linker-platform/parsers/x-parser/deploy
cp .env.prod.example .env.prod
```

至少确认这些配置：

- `TAVILY_API_KEY`
- `X_PARSER_HOST_PORT`

### 2. 本地构建镜像

```bash
cd /Users/apple/Workspace/linker-platform/parsers/x-parser
IMAGE_TAG=20260323-<git短提交> ./scripts/build-release-image.sh
```

可选覆盖参数：

- `TARGET_PLATFORM`，默认 `linux/amd64`
- `X_PARSER_IMAGE`，默认 `ballbase/x-parser`

### 3. 导出镜像 bundle

```bash
cd /Users/apple/Workspace/linker-platform/parsers/x-parser
IMAGE_TAG=20260323-<git短提交> ./scripts/export-release-bundle.sh
```

导出结果默认在：

```text
.tmp/release/<IMAGE_TAG>/
```

其中包含：

- `images/x-parser.tar`
- `deploy/compose.prod.yaml`
- `deploy/.env.prod.example`
- `deploy/release.env`

### 4. 上传服务器并更新

```bash
cd /Users/apple/Workspace/linker-platform/parsers/x-parser
DEPLOY_HOST=117.72.207.52 \
DEPLOY_USER=root \
DEPLOY_PASSWORD='服务器密码' \
DEPLOY_ENV_FILE=deploy/.env.prod \
IMAGE_TAG=20260323-<git短提交> \
./scripts/deploy-prebuilt-release.sh
```

脚本默认会把服务部署到：

```text
/root/apps/parsers/x-parser
```

如需覆盖，可设置：

- `DEPLOY_BASE_DIR`
- `DEPLOY_PORT`

### 5. 发布后验证

服务器本机验证：

```bash
curl -sS http://127.0.0.1:5000/api/v1/health
curl -sS http://127.0.0.1:5000/api/v1/capabilities
```

主系统联调验证：

```bash
curl -sS https://linker.ballbase.cloud/api/v1/system/parsers
```

### 6. 回滚

重新指定旧版本 `IMAGE_TAG` 再执行一遍部署脚本：

```bash
DEPLOY_HOST=117.72.207.52 \
DEPLOY_USER=root \
DEPLOY_PASSWORD='服务器密码' \
DEPLOY_ENV_FILE=deploy/.env.prod \
IMAGE_TAG=<旧版本号> \
./scripts/deploy-prebuilt-release.sh
```
