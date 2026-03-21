"""
Flask Web 服务 - HTTP API 接口

启动服务:
    python -m web.app
    或
    flask --app web.app run --port 5000

API 端点:
    POST /parse          - 解析推文
    GET  /health         - 健康检查
    GET  /check-key      - 检查 API Key 配置
"""
import logging
import os
from flask import Flask, request, jsonify

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from xparser.parser import parse, ParseResult


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)


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
    解析推文

    请求体:
        {
            "url": "https://x.com/username/status/123456789"
        }

    响应:
        {
            "success": true,
            "tweet": { ... },
            "processing_time": 1.23
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
║        X/Twitter Parser API Service      ║
╠══════════════════════════════════════════╣
║  服务地址: http://0.0.0.0:{port:<5}              ║
║  健康检查: GET  /health                   ║
║  解析推文: POST /parse                    ║
╚══════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()