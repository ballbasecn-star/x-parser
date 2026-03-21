"""
URL 检测模块

检测和分类 URL 类型，提取 Twitter/X 链接中的信息。
"""
import re
from typing import Optional, Tuple
from dataclasses import dataclass

from .models import URLType


@dataclass
class URLInfo:
    """URL 解析结果"""
    url: str
    url_type: URLType
    username: Optional[str] = None
    tweet_id: Optional[str] = None
    is_valid: bool = True
    error: Optional[str] = None


class URLDetector:
    """
    URL 检测器

    支持的 URL 格式:
    - https://twitter.com/username/status/123456789
    - https://x.com/username/status/123456789
    - https://twitter.com/username (用户主页)
    """

    # Twitter/X 状态链接模式
    STATUS_PATTERNS = [
        # twitter.com 域名
        re.compile(
            r'https?://(?:www\.)?twitter\.com/([\w_]+)/status/(\d+)',
            re.IGNORECASE
        ),
        # x.com 域名
        re.compile(
            r'https?://(?:www\.)?x\.com/([\w_]+)/status/(\d+)',
            re.IGNORECASE
        ),
    ]

    # 用户主页模式
    PROFILE_PATTERNS = [
        re.compile(
            r'https?://(?:www\.)?twitter\.com/([\w_]+)/?$',
            re.IGNORECASE
        ),
        re.compile(
            r'https?://(?:www\.)?x\.com/([\w_]+)/?$',
            re.IGNORECASE
        ),
    ]

    # 通用 Twitter/X 域名检测
    TWITTER_DOMAINS = ['twitter.com', 'x.com', 'www.twitter.com', 'www.x.com']

    def detect(self, url: str) -> URLInfo:
        """
        检测 URL 类型并提取信息

        Args:
            url: 待检测的 URL 字符串

        Returns:
            URLInfo 对象
        """
        url = url.strip()

        # 检查是否为空
        if not url:
            return URLInfo(
                url="",
                url_type=URLType.UNKNOWN,
                is_valid=False,
                error="URL 为空"
            )

        # 规范化 URL（添加协议）
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # 尝试匹配推文状态链接
        for pattern in self.STATUS_PATTERNS:
            match = pattern.match(url)
            if match:
                username = match.group(1)
                tweet_id = match.group(2)
                url_type = URLType.X if 'x.com' in url.lower() else URLType.TWITTER
                return URLInfo(
                    url=url,
                    url_type=url_type,
                    username=username,
                    tweet_id=tweet_id,
                    is_valid=True
                )

        # 尝试匹配用户主页链接
        for pattern in self.PROFILE_PATTERNS:
            match = pattern.match(url)
            if match:
                username = match.group(1)
                url_type = URLType.X if 'x.com' in url.lower() else URLType.TWITTER
                return URLInfo(
                    url=url,
                    url_type=url_type,
                    username=username,
                    is_valid=True,
                    error="用户主页链接，非推文链接"
                )

        # 检查是否为 Twitter/X 域名
        is_twitter_url = any(domain in url.lower() for domain in self.TWITTER_DOMAINS)
        if is_twitter_url:
            return URLInfo(
                url=url,
                url_type=URLType.X if 'x.com' in url.lower() else URLType.TWITTER,
                is_valid=False,
                error="无法识别的 Twitter/X URL 格式"
            )

        # 非 Twitter/X 链接
        return URLInfo(
            url=url,
            url_type=URLType.UNKNOWN,
            is_valid=False,
            error="非 Twitter/X 链接"
        )

    def is_tweet_url(self, url: str) -> bool:
        """检查是否为有效的推文链接"""
        info = self.detect(url)
        return info.is_valid and info.tweet_id is not None

    def extract_tweet_id(self, url: str) -> Optional[str]:
        """从 URL 中提取推文 ID"""
        info = self.detect(url)
        return info.tweet_id

    def extract_username(self, url: str) -> Optional[str]:
        """从 URL 中提取用户名"""
        info = self.detect(url)
        return info.username


def detect_url(url: str) -> URLInfo:
    """
    便捷函数：检测 URL

    Args:
        url: URL 字符串

    Returns:
        URLInfo 对象
    """
    detector = URLDetector()
    return detector.detect(url)


def extract_tweet_info(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    便捷函数：从 URL 提取用户名和推文 ID

    Args:
        url: URL 字符串

    Returns:
        (username, tweet_id) 元组
    """
    info = detect_url(url)
    return info.username, info.tweet_id