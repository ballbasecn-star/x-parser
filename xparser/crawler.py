"""
爬虫模块 - 使用 Tavily API 提取推文内容

通过 Tavily 的 extract 端点获取 Twitter/X 页面内容，
无需 Twitter API 密钥或登录凭证。

API 文档: https://docs.tavily.com/documentation/api-reference/endpoint/extract
"""
import os
import re
import time
import logging
from typing import Dict, Any, Optional, List

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None

from .models import TweetInfo, TweetMetrics
from .utils import (
    parse_count,
    clean_tweet_text,
    extract_article_title,
    extract_hashtags,
    extract_mentions,
    parse_title_string,
    filter_content_images,
)


logger = logging.getLogger(__name__)


class TavilyCrawler:
    """
    基于 Tavily API 的推文爬虫

    特点:
    - 无需 Twitter 账号或 API 密钥
    - 支持普通推文和长文章
    - 自动提取图片、视频
    - 提取互动数据
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化爬虫

        Args:
            api_key: Tavily API Key（可选，默认从环境变量读取）

        Raises:
            ImportError: tavily-python 未安装
            ValueError: API Key 未配置
        """
        if not TAVILY_AVAILABLE:
            raise ImportError(
                "tavily-python 未安装。请运行: pip install tavily-python"
            )

        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY 未配置。请:\n"
                "1. 访问 https://tavily.com/ 获取 API Key\n"
                "2. 设置环境变量: export TAVILY_API_KEY=your_key\n"
                "3. 或创建 .env 文件"
            )

        self.client = TavilyClient(api_key=self.api_key)

    def fetch_tweet(self, url: str) -> Optional[TweetInfo]:
        """
        获取推文信息

        Args:
            url: 推文链接

        Returns:
            TweetInfo 对象，失败返回 None
        """
        start_time = time.time()

        try:
            # 调用 Tavily extract API
            logger.info(f"正在获取推文: {url}")
            response = self.client.extract(
                url,
                extract_depth="advanced",
                include_images=True,
                include_image_description=True,
            )

            # 解析响应
            tweet_info = self._parse_response(response, url)

            elapsed = time.time() - start_time
            logger.info(f"推文获取完成，耗时 {elapsed:.2f}s")

            return tweet_info

        except Exception as e:
            logger.error(f"获取推文失败: {e}")
            return None

    def _parse_response(self, response: Dict[str, Any], url: str) -> TweetInfo:
        """
        解析 Tavily API 响应

        Args:
            response: API 响应数据
            url: 原始 URL

        Returns:
            TweetInfo 对象
        """
        tweet_info = TweetInfo(url=url)

        # 从 URL 提取基本信息
        self._extract_from_url(tweet_info, url)
        # 即使提取失败，也保留原始响应，方便上层判断是真空结果还是字段映射缺失。
        tweet_info.raw_data = response or {}

        # 解析 API 响应
        results = response.get("results", [])
        if not results:
            logger.warning("API 响应为空")
            return tweet_info

        first_result = results[0]

        # 提取标题
        title = first_result.get("title", "")
        if title:
            display_name, _ = parse_title_string(title)
            tweet_info.display_name = display_name

        # 先从 Tavily 常见字段里挑一个最可信的正文候选，再统一做清洗。
        raw_content = self._resolve_primary_content(first_result, title)
        if raw_content:
            # 清洗文本
            tweet_info.content = raw_content
            tweet_info.content_clean = clean_tweet_text(raw_content)

            # 提取文章标题
            article_title = extract_article_title(tweet_info.content_clean)
            if article_title:
                tweet_info.title = article_title

            # 提取标签和提及
            tweet_info.hashtags = extract_hashtags(tweet_info.content_clean)
            tweet_info.mentions = extract_mentions(tweet_info.content_clean)

            # 提取互动数据
            metrics = self._extract_metrics(raw_content)
            tweet_info.metrics = metrics

            # 提取时间
            created_at = self._extract_datetime(raw_content)
            if created_at:
                tweet_info.created_at = created_at

        # 提取图片
        images = first_result.get("images", [])
        if isinstance(images, list):
            tweet_info.images = filter_content_images(images)

        # 提取视频（如果有）
        # Tavily 可能不直接返回视频，需要从内容中提取
        videos = self._extract_videos(raw_content)
        tweet_info.videos = videos

        return tweet_info

    def _resolve_primary_content(self, result: Dict[str, Any], title: str) -> str:
        """优先从正文相关字段提取文本，避免只拿到 tweet id 也被当成成功。"""
        for field_name in ("raw_content", "content", "text", "excerpt", "snippet"):
            value = result.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()

        _, title_content = parse_title_string(title)
        if title_content and not re.fullmatch(r"\d{6,}", title_content):
            return title_content.strip()

        return ""

    def _extract_from_url(self, tweet_info: TweetInfo, url: str) -> None:
        """从 URL 提取基本信息"""
        # 提取用户名
        username_match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status', url)
        if username_match:
            tweet_info.username = username_match.group(1)

        # 提取推文 ID
        id_match = re.search(r'/status/(\d+)', url)
        if id_match:
            tweet_info.tweet_id = id_match.group(1)

        # 设置来源
        tweet_info.source = "x" if "x.com" in url.lower() else "twitter"

    def _extract_metrics(self, raw_content: str) -> TweetMetrics:
        """
        从原始内容中提取互动数据

        支持格式:
        - 四个数字格式（Tavily 返回的格式）:
          164
          1.9K
          7.6K
          [2.4M](https://x.com/.../analytics)
        - 链接格式: [164](https://x.com/.../replies)
        - 单独格式: "1,234 replies", "5,678 likes"
        """
        metrics = TweetMetrics()

        if not raw_content:
            return metrics

        # 调试：打印 raw_content 的关键部分
        logger.debug(f"=== RAW CONTENT (前 3000 字符) ===\n{raw_content[:3000]}")

        # ========== 格式1：四个数字格式（Tavily 返回的格式）==========
        # 顺序: replies, reposts, likes, views
        # 格式示例:
        # 164
        # 1.9K
        # 7.6K
        # [2.4M](https://x.com/.../analytics)
        four_numbers_pattern = r'''
            (\d+)\s*\n\s*                           # replies (纯数字)
            ([\d\.]+[KM]?)\s*\n\s*                  # reposts (可能带 K/M)
            ([\d\.]+[KM]?)\s*\n\s*                  # likes (可能带 K/M)
            \[([\d\.]+[KM]?)\]\(https://x\.com/[^/]+/status/\d+/analytics\)  # views (链接格式)
        '''
        match = re.search(four_numbers_pattern, raw_content, re.VERBOSE | re.IGNORECASE)
        if match:
            metrics.replies = int(match.group(1))
            metrics.retweets = parse_count(match.group(2))
            metrics.likes = parse_count(match.group(3))
            metrics.views = parse_count(match.group(4))
            logger.debug(f"四数字格式匹配: replies={metrics.replies}, retweets={metrics.retweets}, likes={metrics.likes}, views={metrics.views}")
            return metrics

        # ========== 格式2：链接格式（带明确标签）==========
        # 格式: [数字](https://x.com/用户名/status/ID/replies)
        link_patterns = [
            (r'\[(\d+)\]\(https://x\.com/[^/]+/status/\d+/replies\)', 'replies'),
            (r'\[(\d+)\]\(https://x\.com/[^/]+/status/\d+/retweets\)', 'retweets'),
            (r'\[(\d+)\]\(https://x\.com/[^/]+/status/\d+/likes\)', 'likes'),
            (r'\[(\d+)\]\(https://x\.com/[^/]+/status/\d+/quotes\)', 'quotes'),
        ]

        for pattern, attr in link_patterns:
            match = re.search(pattern, raw_content)
            if match:
                value = int(match.group(1))
                setattr(metrics, attr, value)
                logger.debug(f"链接格式匹配: {attr}={value}")

        # ========== 格式3：紧凑格式（四个数字连在一起）==========
        compact_match = re.search(
            r'(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+[KM]?)',
            raw_content
        )
        if compact_match:
            metrics.replies = int(compact_match.group(1))
            metrics.retweets = int(compact_match.group(2))
            metrics.quotes = int(compact_match.group(3))
            metrics.views = parse_count(compact_match.group(4))
            logger.debug(f"紧凑格式匹配: replies={metrics.replies}, retweets={metrics.retweets}, quotes={metrics.quotes}, views={metrics.views}")

        # ========== 格式4：单独格式（带标签）==========
        patterns = [
            # 英文格式
            (r'([\d,\.]+[KM]?)\s*replies?', 'replies', True),
            (r'([\d,\.]+[KM]?)\s*reposts?', 'retweets', True),
            (r'([\d,\.]+[KM]?)\s*retweets?', 'retweets', True),
            (r'([\d,\.]+[KM]?)\s*quotes?', 'quotes', True),
            (r'([\d,\.]+[KM]?)\s*likes?', 'likes', True),
            (r'([\d,\.]+[KM]?)\s*views?', 'views', True),
            (r'([\d,\.]+[KM]?)\s*bookmarks?', 'bookmarks', True),
            # 中文格式
            (r'([\d,\.]+[KM]?万?)\s*回复', 'replies', True),
            (r'([\d,\.]+[KM]?万?)\s*转[发帖]', 'retweets', True),
            (r'([\d,\.]+[KM]?万?)\s*引用', 'quotes', True),
            (r'([\d,\.]+[KM]?万?)\s*喜欢', 'likes', True),
            (r'([\d,\.]+[KM]?万?)\s*查看', 'views', True),
            (r'([\d,\.]+[KM]?万?)\s*书签', 'bookmarks', True),
        ]

        for pattern, attr, case_insensitive in patterns:
            flags = re.IGNORECASE if case_insensitive else 0
            match = re.search(pattern, raw_content, flags)
            if match:
                value = parse_count(match.group(1))
                current = getattr(metrics, attr)
                if current == 0:
                    setattr(metrics, attr, value)
                    logger.debug(f"单独格式匹配: {attr}={value}")

        logger.debug(f"最终 metrics: {metrics.to_dict()}")
        return metrics

    def _extract_datetime(self, raw_content: str) -> str:
        """提取发布时间"""
        if not raw_content:
            return ""

        # 匹配格式: "10:30 AM · Feb 10"
        patterns = [
            r'(\d{1,2}:\d{2}\s*[AP]M\s*·\s*\w+\s+\d+)',
            r'(\w+\s+\d+,\s+\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_content)
            if match:
                return match.group(1)

        return ""

    def _extract_videos(self, raw_content: str) -> List[str]:
        """从内容中提取视频链接"""
        if not raw_content:
            return []

        videos = []

        # 匹配视频 URL 模式
        video_patterns = [
            r'https?://video\.twimg\.com/[^\s\)]+',
            r'https?://pbs\.twimg\.com/amplify_video[^\s\)]+',
        ]

        for pattern in video_patterns:
            matches = re.findall(pattern, raw_content)
            videos.extend(matches)

        return list(set(videos))  # 去重


def create_crawler(api_key: Optional[str] = None) -> TavilyCrawler:
    """
    创建爬虫实例

    Args:
        api_key: 可选的 API Key

    Returns:
        TavilyCrawler 实例
    """
    return TavilyCrawler(api_key=api_key)
