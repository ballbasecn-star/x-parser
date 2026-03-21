"""
单元测试 - URL 检测模块
"""
import pytest
from xparser.url_detector import URLDetector, detect_url, extract_tweet_info
from xparser.models import URLType


class TestURLDetector:
    """URL 检测器测试"""

    def setup_method(self):
        self.detector = URLDetector()

    def test_x_com_status_url(self):
        """测试 x.com 推文链接"""
        url = "https://x.com/elonmusk/status/123456789012"
        info = self.detector.detect(url)

        assert info.is_valid is True
        assert info.url_type == URLType.X
        assert info.username == "elonmusk"
        assert info.tweet_id == "123456789012"

    def test_twitter_com_status_url(self):
        """测试 twitter.com 推文链接"""
        url = "https://twitter.com/elonmusk/status/123456789012"
        info = self.detector.detect(url)

        assert info.is_valid is True
        assert info.url_type == URLType.TWITTER
        assert info.username == "elonmusk"
        assert info.tweet_id == "123456789012"

    def test_x_com_with_www(self):
        """测试带 www 的 x.com 链接"""
        url = "https://www.x.com/username/status/999888777"
        info = self.detector.detect(url)

        assert info.is_valid is True
        assert info.username == "username"
        assert info.tweet_id == "999888777"

    def test_http_scheme(self):
        """测试 http 协议"""
        url = "http://x.com/test/status/111"
        info = self.detector.detect(url)

        assert info.is_valid is True
        assert info.tweet_id == "111"

    def test_profile_url(self):
        """测试用户主页链接"""
        url = "https://x.com/elonmusk"
        info = self.detector.detect(url)

        # 主页链接是有效的 X 链接，但不是推文链接
        assert info.is_valid is True  # 是有效的 X 链接
        assert info.username == "elonmusk"
        assert info.tweet_id is None  # 但没有推文 ID
        assert info.error == "用户主页链接，非推文链接"

    def test_invalid_url(self):
        """测试无效 URL"""
        info = self.detector.detect("https://example.com/page")

        assert info.is_valid is False
        assert info.url_type == URLType.UNKNOWN

    def test_empty_url(self):
        """测试空 URL"""
        info = self.detector.detect("")

        assert info.is_valid is False

    def test_url_without_scheme(self):
        """测试无协议的 URL"""
        # 应该自动添加 https://
        url = "x.com/username/status/123"
        info = self.detector.detect(url)

        assert info.is_valid is True
        assert info.tweet_id == "123"

    def test_is_tweet_url(self):
        """测试 is_tweet_url 方法"""
        assert self.detector.is_tweet_url("https://x.com/u/status/1") is True
        assert self.detector.is_tweet_url("https://x.com/u") is False
        assert self.detector.is_tweet_url("https://example.com") is False

    def test_extract_tweet_id(self):
        """测试 extract_tweet_id 方法"""
        tweet_id = self.detector.extract_tweet_id(
            "https://x.com/username/status/123456789"
        )
        assert tweet_id == "123456789"

    def test_extract_username(self):
        """测试 extract_username 方法"""
        username = self.detector.extract_username(
            "https://twitter.com/testuser/status/123"
        )
        assert username == "testuser"


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_detect_url(self):
        """测试 detect_url 函数"""
        info = detect_url("https://x.com/test/status/123")
        assert info.is_valid is True
        assert info.tweet_id == "123"

    def test_extract_tweet_info(self):
        """测试 extract_tweet_info 函数"""
        username, tweet_id = extract_tweet_info(
            "https://twitter.com/myuser/status/999888"
        )
        assert username == "myuser"
        assert tweet_id == "999888"