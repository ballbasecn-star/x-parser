"""
数据模型定义

定义推文信息、解析结果等核心数据结构。
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class URLType(Enum):
    """URL 类型枚举"""
    TWITTER = "twitter"
    X = "x"
    UNKNOWN = "unknown"


@dataclass
class TweetMetrics:
    """推文互动数据"""
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    views: int = 0
    bookmarks: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    def format_output(self) -> str:
        """格式化输出"""
        parts = []
        if self.views:
            parts.append(f"👁️ {self._format_count(self.views)}")
        if self.likes:
            parts.append(f"❤️ {self._format_count(self.likes)}")
        if self.retweets:
            parts.append(f"🔄 {self._format_count(self.retweets)}")
        if self.replies:
            parts.append(f"💬 {self._format_count(self.replies)}")
        if self.quotes:
            parts.append(f"📢 {self._format_count(self.quotes)}")
        if self.bookmarks:
            parts.append(f"🔖 {self._format_count(self.bookmarks)}")
        return " | ".join(parts) if parts else "暂无数据"

    @staticmethod
    def _format_count(count: int) -> str:
        """格式化数字（带 K/M 后缀）"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return str(count)


@dataclass
class TweetInfo:
    """推文完整信息"""

    # 基本信息
    tweet_id: str = ""
    url: str = ""

    # 作者信息
    username: str = ""
    display_name: str = ""
    author_avatar: Optional[str] = None

    # 内容
    content: str = ""           # 原始推文内容
    content_clean: str = ""     # 清洗后的纯文本
    title: Optional[str] = None  # 长文章标题

    # 时间
    created_at: str = ""
    created_timestamp: Optional[int] = None

    # 媒体
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 互动数据
    metrics: TweetMetrics = field(default_factory=TweetMetrics)

    # 标签
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)

    # 引用推文
    is_quote: bool = False
    quoted_tweet: Optional['TweetInfo'] = None

    # 回复
    is_reply: bool = False
    reply_to_id: Optional[str] = None

    # 元数据
    lang: str = ""
    source: str = ""  # twitter / x

    # 原始数据
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_long_article(self) -> bool:
        """判断是否为长文章"""
        return len(self.content) > 280 or bool(self.title)

    @property
    def author_url(self) -> str:
        """作者主页 URL"""
        if self.username:
            return f"https://x.com/{self.username}"
        return ""

    @property
    def created_at_formatted(self) -> str:
        """格式化发布时间"""
        if self.created_timestamp:
            try:
                return datetime.fromtimestamp(self.created_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError):
                pass
        return self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - 简化输出，只保留 content 和 metrics"""
        return {
            "content": self.content_clean,
            "metrics": self.metrics.to_dict(),
        }

    def format_output(self) -> str:
        """格式化输出为可读文本"""
        lines = []
        lines.append("=" * 60)
        lines.append("🐦 推文信息")
        lines.append("=" * 60)

        # 作者信息
        if self.display_name or self.username:
            author_str = f"👤 作者: {self.display_name}"
            if self.username:
                author_str += f" (@{self.username})"
            lines.append(author_str)

        # 推文 ID
        if self.tweet_id:
            lines.append(f"🔗 推文ID: {self.tweet_id}")

        # 时间
        if self.created_at:
            lines.append(f"📅 发布时间: {self.created_at_formatted}")

        # 互动数据
        metrics_str = self.metrics.format_output()
        if metrics_str and metrics_str != "暂无数据":
            lines.append(f"\n📊 数据: {metrics_str}")

        # 标签
        if self.hashtags:
            lines.append(f"\n🏷️ 标签: {' '.join(self.hashtags)}")

        # 标题（长文章）
        if self.title:
            lines.append(f"\n📌 标题: {self.title}")

        # 内容
        if self.content_clean:
            lines.append(f"\n📝 内容:")
            lines.append("-" * 40)
            lines.append(self.content_clean)
            lines.append("-" * 40)

        # 媒体
        if self.images:
            lines.append(f"\n🖼️ 图片 ({len(self.images)} 张):")
            for i, img in enumerate(self.images[:5], 1):
                lines.append(f"   {i}. {img[:60]}...")
            if len(self.images) > 5:
                lines.append(f"   ... 还有 {len(self.images) - 5} 张")

        if self.videos:
            lines.append(f"\n🎬 视频 ({len(self.videos)} 个):")
            for i, vid in enumerate(self.videos, 1):
                lines.append(f"   {i}. {vid[:60]}...")

        # 原始链接
        if self.url:
            lines.append(f"\n🔗 原链接: {self.url}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


@dataclass
class ParseResult:
    """解析结果"""
    success: bool = False
    tweet: Optional[TweetInfo] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    source: str = ""  # tavily / api / cache

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - 简化输出"""
        if self.success and self.tweet:
            return {
                "success": True,
                "content": self.tweet.content_clean,
                "metrics": self.tweet.metrics.to_dict(),
            }
        else:
            return {
                "success": False,
                "error": self.error,
            }