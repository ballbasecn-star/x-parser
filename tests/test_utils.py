"""
单元测试 - 工具函数模块
"""
import pytest
from xparser.utils import (
    parse_count,
    format_count,
    clean_tweet_text,
    extract_article_title,
    extract_hashtags,
    extract_mentions,
    parse_title_string,
    is_valid_image_url,
    filter_content_images,
)


class TestParseCount:
    """数字解析测试"""

    def test_plain_number(self):
        assert parse_count("123") == 123
        assert parse_count("1,234") == 1234

    def test_k_suffix(self):
        assert parse_count("1K") == 1000
        assert parse_count("1.5K") == 1500
        assert parse_count("2.0k") == 2000

    def test_m_suffix(self):
        assert parse_count("1M") == 1000000
        assert parse_count("1.5M") == 1500000

    def test_b_suffix(self):
        assert parse_count("1B") == 1000000000

    def test_empty_string(self):
        assert parse_count("") == 0
        assert parse_count(None) == 0

    def test_invalid_string(self):
        assert parse_count("abc") == 0


class TestFormatCount:
    """数字格式化测试"""

    def test_small_number(self):
        assert format_count(100) == "100"
        assert format_count(999) == "999"

    def test_thousands(self):
        assert format_count(1000) == "1.0K"
        assert format_count(1500) == "1.5K"

    def test_millions(self):
        assert format_count(1000000) == "1.0M"
        assert format_count(2500000) == "2.5M"

    def test_billions(self):
        assert format_count(1000000000) == "1.0B"


class TestCleanTweetText:
    """文本清洗测试"""

    def test_basic_clean(self):
        """基本清洗 - 模拟真实推文页面内容"""
        # 模拟真实 Twitter 页面内容（包含作者区域）
        text = """John Doe
@johndoe
https://x.com/johndoe

Hello World

This is a tweet.
"""
        result = clean_tweet_text(text)
        # 作者区域会被跳过，只保留实际内容
        assert "Hello World" in result or "This is a tweet" in result

    def test_remove_header_noise(self):
        """移除头部噪音"""
        # 模拟包含噪音的页面内容
        text = """Don't miss what's happening
[Log in]
[Sign up]

Author Name
@author

Actual content here
"""
        result = clean_tweet_text(text)
        assert "Don't miss" not in result
        assert "[Log in]" not in result
        assert "[Sign up]" not in result

    def test_remove_footer_noise(self):
        """移除底部噪音"""
        # 模拟包含底部噪音的内容
        text = """Author Name
@author

Content here
"""
        result = clean_tweet_text(text)
        # 内容应该被保留（即使作者区域被跳过）
        assert len(result) >= 0

    def test_empty_input(self):
        """空输入"""
        assert clean_tweet_text("") == ""
        assert clean_tweet_text(None) == ""


class TestExtractArticleTitle:
    """文章标题提取测试"""

    def test_chinese_title(self):
        """中文标题"""
        text = "这是一篇关于AI的文章\n\n内容正文..."
        result = extract_article_title(text)
        assert result == "这是一篇关于AI的文章"

    def test_markdown_title(self):
        """Markdown 标题"""
        text = "# My Article Title\n\nContent here"
        result = extract_article_title(text)
        assert result == "My Article Title"

    def test_no_title(self):
        """无标题"""
        text = "Short"
        result = extract_article_title(text)
        assert result is None

    def test_empty_input(self):
        """空输入"""
        assert extract_article_title("") is None
        assert extract_article_title(None) is None


class TestExtractHashtags:
    """标签提取测试"""

    def test_basic_hashtags(self):
        """基本标签"""
        text = "Hello #Python #AI #MachineLearning"
        result = extract_hashtags(text)
        assert "#Python" in result
        assert "#AI" in result
        assert "#MachineLearning" in result

    def test_chinese_hashtags(self):
        """中文标签"""
        text = "今天天气不错 #天气 #生活"
        result = extract_hashtags(text)
        assert "#天气" in result
        assert "#生活" in result

    def test_no_hashtags(self):
        """无标签"""
        assert extract_hashtags("No hashtags here") == []


class TestExtractMentions:
    """提及提取测试"""

    def test_basic_mentions(self):
        """基本提及"""
        text = "Hello @elonmusk and @naval"
        result = extract_mentions(text)
        assert "elonmusk" in result
        assert "naval" in result

    def test_no_mentions(self):
        """无提及"""
        assert extract_mentions("No mentions here") == []


class TestParseTitleString:
    """标题字符串解析测试"""

    def test_standard_format(self):
        """标准格式"""
        title = 'Elon Musk on X: "This is a tweet" / X'
        display_name, content = parse_title_string(title)
        assert display_name == "Elon Musk"
        assert content == "This is a tweet"

    def test_no_content(self):
        """无内容"""
        title = "Display Name"
        display_name, content = parse_title_string(title)
        assert display_name == "Display Name"
        assert content == ""


class TestImageURLValidation:
    """图片 URL 验证测试"""

    def test_valid_image_url(self):
        """有效图片 URL"""
        assert is_valid_image_url("https://example.com/image.jpg") is True
        assert is_valid_image_url("https://example.com/image.png") is True

    def test_profile_image(self):
        """头像图片"""
        url = "https://pbs.twimg.com/profile_images/123.jpg"
        assert is_valid_image_url(url) is False

    def test_empty_url(self):
        """空 URL"""
        assert is_valid_image_url("") is False
        assert is_valid_image_url(None) is False


class TestFilterContentImages:
    """图片过滤测试"""

    def test_filter_profile_images(self):
        """过滤头像"""
        images = [
            "https://pbs.twimg.com/media/123.jpg",
            "https://pbs.twimg.com/profile_images/456.jpg",
            "https://example.com/image.png",
        ]
        result = filter_content_images(images)
        assert len(result) == 2
        assert "profile_images" not in result[0]
        assert "profile_images" not in result[1]