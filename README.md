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

## 注意事项

1. **Tavily API 限制**：免费版有请求次数限制，请查看 https://tavily.com/ 的定价
2. **内容可用性**：私密账号或已删除的推文无法获取
3. **代理设置**：如需代理，设置 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量

## License

MIT