"""
Flask Web 服务 - HTTP API 接口 + 可视化页面

启动服务:
    python -m web.app
    或
    flask --app web.app run --port 5000

API 端点:
    GET  /                - 可视化页面
    GET  /parse           - 解析推文（可视化展示）
    POST /api/parse       - 解析推文（JSON API）
    GET  /health          - 健康检查
    GET  /check-key       - 检查 API Key 配置
"""
import logging
import os
import re
import markdown
from flask import Flask, request, jsonify, render_template

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from xparser.parser import parse, ParseResult
from web.parser_contract import (
    UnsupportedUrlError,
    build_capabilities_payload,
    build_health_payload,
    contract_error_response,
    contract_success_response,
    create_request_id,
    extract_language_hint,
    resolve_source_url,
    to_parsed_content_payload,
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__, template_folder='templates')


# Jinja2 自定义过滤器
@app.template_filter('format_number')
def format_number(value):
    """格式化数字，添加 K/M 后缀"""
    if not value:
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def convert_content_to_html(content: str, images: list = None) -> str:
    """
    将推文内容转换为美观的 HTML

    - 解析 Markdown
    - 保留图片在原文中的位置
    - 清理噪音
    """
    if not content:
        return ""

    # 清理开头的噪音
    lines = content.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 跳过开头的标题噪音
        if stripped.startswith('# Tw93 on X:') or stripped.startswith('# []('):
            start_idx = i + 1
            continue
        if stripped and not stripped.startswith('# Tw93') and not stripped.startswith('# []('):
            start_idx = i
            break

    content = '\n'.join(lines[start_idx:])

    # 转换图片链接标记为 HTML img 标签，保留在原文位置
    # 格式: [![Image N: Image](url)](link) -> <img src="url" class="article-image">
    content = re.sub(
        r'\[!\[Image[^\]]*\]\(([^)]+)\)\]\([^)]+\)',
        r'<img src="\1" alt="推文图片" class="article-image" loading="lazy">',
        content
    )
    # 格式: ![Image N: Image](url) -> <img src="url" class="article-image">
    content = re.sub(
        r'!\[Image[^\]]*\]\(([^)]+)\)',
        r'<img src="\1" alt="推文图片" class="article-image" loading="lazy">',
        content
    )

    # 移除作者链接
    content = re.sub(r'\[[\w\s]+\]\(https://x\.com/[\w_]+\)', '', content)

    # 移除空链接
    content = re.sub(r'\[\]\([^)]+\)', '', content)

    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 转换 Markdown 为 HTML
    html = markdown.markdown(
        content,
        extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'toc'
        ]
    )

    return html


@app.route("/", methods=["GET"])
def index():
    """可视化首页"""
    return render_template("index.html")


@app.route("/parse", methods=["GET"])
def parse_page():
    """
    解析推文并可视化展示
    """
    url = request.args.get("url", "").strip()

    if not url:
        return render_template("index.html")

    # 解析推文
    logger.info(f"解析请求: {url}")
    result = parse(url)

    if not result.success:
        return render_template(
            "index.html",
            url=url,
            error=result.error
        )

    tweet = result.tweet

    # 准备模板数据
    tweet_data = {
        "url": tweet.url,
        "username": tweet.username,
        "display_name": tweet.display_name,
        "author_avatar": tweet.author_avatar,
        "title": tweet.title,
        "created_at": tweet.created_at,
        "cover_image": tweet.images[0] if tweet.images else None,
        "metrics": tweet.metrics,
        "content_html": convert_content_to_html(tweet.content_clean, tweet.images),
    }

    return render_template(
        "index.html",
        url=url,
        tweet=tweet_data,
        title=tweet.title or f"@{tweet.username} 的推文"
    )


@app.route("/api/parse", methods=["POST"])
def parse_tweet_api():
    """
    解析推文 (JSON API)

    请求体:
        {
            "url": "https://x.com/username/status/123456789"
        }

    响应:
        {
            "success": true,
            "content": "...",
            "metrics": { ... }
        }
    """
    # 获取请求数据
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "请求体不能为空"
        }), 400

    url = data.get("url")
    if not url:
        return jsonify({
            "success": False,
            "error": "缺少 url 参数"
        }), 400

    # 解析推文
    logger.info(f"解析请求: {url}")

    try:
        result: ParseResult = parse(url)

        if not result.success:
            return jsonify({
                "success": False,
                "error": result.error
            }), 400

        return jsonify(result.to_dict())

    except Exception as e:
        logger.exception("解析失败")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/v1/health", methods=["GET"])
def parser_health():
    """统一 parser 健康检查"""
    return contract_success_response(create_request_id(), build_health_payload())


@app.route("/api/v1/capabilities", methods=["GET"])
def parser_capabilities():
    """统一 parser 能力声明"""
    return contract_success_response(create_request_id(), build_capabilities_payload())


@app.route("/api/v1/parse", methods=["POST"])
def parser_parse():
    """统一 parser 解析入口"""
    payload = request.get_json(silent=True)
    request_id = ((payload or {}).get("requestId") or "").strip() or create_request_id()

    try:
        url = resolve_source_url(payload)
    except UnsupportedUrlError as exc:
        return contract_error_response(request_id, "UNSUPPORTED_URL", str(exc), 400, retryable=False)
    except ValueError as exc:
        return contract_error_response(request_id, "INVALID_INPUT", str(exc), 400, retryable=False)

    try:
        result: ParseResult = parse(url)
        if not result.success:
            return contract_error_response(
                request_id,
                "UPSTREAM_CHANGED",
                result.error or "解析失败",
                422,
                retryable=True,
            )
        return contract_success_response(request_id, to_parsed_content_payload(result, extract_language_hint(payload)))
    except Exception as e:
        logger.exception("统一 parser 解析失败")
        return contract_error_response(request_id, "INTERNAL_ERROR", str(e), 500, retryable=True)


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "service": "x-parser",
        "version": "1.0.0"
    })


@app.route("/check-key", methods=["GET"])
def check_key():
    """检查 API Key 配置"""
    api_key = os.getenv("TAVILY_API_KEY")
    return jsonify({
        "configured": bool(api_key),
        "key_length": len(api_key) if api_key else 0
    })


@app.route("/parse", methods=["POST"])
def parse_tweet():
    """
    解析推文 (兼容旧 API)
    """
    return parse_tweet_api()


@app.route("/parse/batch", methods=["POST"])
def parse_batch():
    """
    批量解析推文

    请求体:
        {
            "urls": ["url1", "url2", ...]
        }
    """
    from xparser.parser import parse_batch

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "请求体不能为空"
        }), 400

    urls = data.get("urls")
    if not urls or not isinstance(urls, list):
        return jsonify({
            "success": False,
            "error": "缺少 urls 参数或格式错误"
        }), 400

    logger.info(f"批量解析请求: {len(urls)} 个 URL")

    try:
        results = parse_batch(urls)
        return jsonify({
            "success": True,
            "total": len(results),
            "results": [r.to_dict() for r in results]
        })

    except Exception as e:
        logger.exception("批量解析失败")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "接口不存在"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "success": False,
        "error": "服务器内部错误"
    }), 500


def main():
    """启动服务"""
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print(f"""
╔══════════════════════════════════════════╗
║        X/Twitter Parser Service          ║
╠══════════════════════════════════════════╣
║  可视化:  http://0.0.0.0:{port:<5}              ║
║  API:     POST /api/parse                 ║
║  健康检查: GET  /health                   ║
╚══════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()