"""
解析器模块 - 主解析入口

提供简洁的 API 用于解析 Twitter/X 推文。
"""
import logging
import time
from typing import Optional, Callable

from .models import TweetInfo, ParseResult
from .url_detector import detect_url, URLInfo
from .crawler import TavilyCrawler, create_crawler
from .utils import is_probable_x_shell


logger = logging.getLogger(__name__)


def _has_extractable_content(tweet: TweetInfo) -> bool:
    """避免把只有 tweet id 的空结果当成成功解析。"""
    results = tweet.raw_data.get("results")
    raw_content = ""
    if isinstance(results, list) and results:
        first_result = results[0] or {}
        if isinstance(first_result, dict):
            raw_content = (first_result.get("raw_content") or "").strip()

    cleaned_content = (tweet.content_clean or "").strip()
    is_shell = is_probable_x_shell(raw_content, cleaned_content)

    if cleaned_content and not is_shell:
        return True

    raw_text = (tweet.content or "").strip()
    if raw_text and not is_shell:
        return True

    return False


def parse(
    url: str,
    api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> ParseResult:
    """
    解析 Twitter/X 推文

    Args:
        url: 推文链接（支持 twitter.com 和 x.com）
        api_key: 可选的 Tavily API Key（默认从环境变量读取）
        progress_callback: 进度回调函数

    Returns:
        ParseResult 对象

    Example:
        result = parse("https://x.com/elonmusk/status/123456789")
        if result.success:
            print(result.tweet.content_clean)
    """
    start_time = time.time()
    result = ParseResult()

    def emit_log(msg: str, level: str = "info"):
        """发送日志"""
        if level == "info":
            logger.info(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)

        if progress_callback:
            progress_callback({"type": "log", "message": msg, "level": level})

    # 1. URL 检测
    emit_log("正在检测 URL...")
    url_info = detect_url(url)

    if not url_info.is_valid:
        result.error = url_info.error or "无效的 URL"
        result.processing_time = time.time() - start_time
        emit_log(f"❌ URL 检测失败: {result.error}", "error")
        return result

    if not url_info.tweet_id:
        result.error = "非推文链接"
        result.processing_time = time.time() - start_time
        emit_log(f"❌ {result.error}", "error")
        return result

    emit_log(f"✅ 检测到推文: @{url_info.username}/status/{url_info.tweet_id}")

    # 2. 创建爬虫
    try:
        crawler = create_crawler(api_key=api_key)
    except ImportError as e:
        result.error = f"依赖缺失: {e}"
        result.processing_time = time.time() - start_time
        emit_log(f"❌ {result.error}", "error")
        return result
    except ValueError as e:
        result.error = str(e)
        result.processing_time = time.time() - start_time
        emit_log(f"❌ {result.error}", "error")
        return result

    # 3. 获取推文
    emit_log("正在获取推文内容...")
    if progress_callback:
        progress_callback({"type": "progress", "stage": "fetching"})

    tweet_info = crawler.fetch_tweet(url_info.url)

    if not tweet_info:
        result.error = "获取推文失败"
        result.processing_time = time.time() - start_time
        emit_log(f"❌ {result.error}", "error")
        return result

    if not _has_extractable_content(tweet_info):
        result.error = "正文提取为空"
        result.processing_time = time.time() - start_time
        emit_log(f"❌ {result.error}", "error")
        return result

    # 4. 返回结果
    result.success = True
    result.tweet = tweet_info
    result.processing_time = time.time() - start_time
    result.source = "tavily"

    if progress_callback:
        progress_callback({
            "type": "data",
            "tweet": tweet_info.to_dict()
        })

    emit_log(f"✅ 解析完成，耗时 {result.processing_time:.2f}s")

    return result


def parse_batch(
    urls: list,
    api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> list:
    """
    批量解析推文

    Args:
        urls: 推文链接列表
        api_key: 可选的 Tavily API Key
        progress_callback: 进度回调

    Returns:
        ParseResult 列表
    """
    results = []
    total = len(urls)

    for i, url in enumerate(urls, 1):
        if progress_callback:
            progress_callback({
                "type": "progress",
                "current": i,
                "total": total,
                "url": url
            })

        result = parse(url, api_key=api_key, progress_callback=progress_callback)
        results.append(result)

    return results


class Parser:
    """
    解析器类（面向对象接口）

    适用于需要复用同一个爬虫实例的场景。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化解析器

        Args:
            api_key: 可选的 Tavily API Key
        """
        self._crawler = create_crawler(api_key=api_key)

    def parse(self, url: str) -> ParseResult:
        """
        解析推文

        Args:
            url: 推文链接

        Returns:
            ParseResult 对象
        """
        start_time = time.time()
        result = ParseResult()

        # URL 检测
        url_info = detect_url(url)

        if not url_info.is_valid or not url_info.tweet_id:
            result.error = url_info.error or "无效的推文链接"
            result.processing_time = time.time() - start_time
            return result

        # 获取推文
        tweet_info = self._crawler.fetch_tweet(url_info.url)

        if not tweet_info:
            result.error = "获取推文失败"
            result.processing_time = time.time() - start_time
            return result

        if not _has_extractable_content(tweet_info):
            result.error = "正文提取为空"
            result.processing_time = time.time() - start_time
            return result

        result.success = True
        result.tweet = tweet_info
        result.processing_time = time.time() - start_time
        result.source = "tavily"

        return result

    def parse_batch(self, urls: list) -> list:
        """
        批量解析

        Args:
            urls: URL 列表

        Returns:
            ParseResult 列表
        """
        return [self.parse(url) for url in urls]
