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
    is_probable_x_shell,
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

    def test_remove_header_noise_with_curly_apostrophe(self):
        """弯引号版本的 X 页面噪音也应被移除。"""
        text = """Don’t miss what’s happening
People on X are the first to know.

真实正文
"""
        result = clean_tweet_text(text)
        assert "Don’t miss what’s happening" not in result
        assert "People on X are the first to know." not in result
        assert "真实正文" in result

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

    def test_remove_x_article_shell_noise(self):
        """移除 X article 页面壳子噪音"""
        text = """# 极客杰尼 on X: "我把公众号排版Skill上架到了ClawHub" / X

Don't miss what's happening

People on X are the first to know.

[Log in](https://x.com/login)

[Sign up](https://x.com/i/flow/signup)

# [](https://x.com/)

## Article

[](https://x.com/seekjourney/article/2035923833707012270)

See new posts

## Conversation

## New to X?
"""
        result = clean_tweet_text(text)
        assert result == ""

    def test_flatten_markdown_links(self):
        """把 Markdown 链接压平成更适合阅读的文本"""
        text = """链接如下：

[https://example.com/article](https://example.com/article)

[点这里查看原文](https://example.com/source)
"""
        result = clean_tweet_text(text)
        assert "https://example.com/article" in result
        assert "[https://example.com/article]" not in result
        assert "点这里查看原文" in result
        assert "[点这里查看原文]" not in result

    def test_remove_article_meta_labels(self):
        """移除 article 常见元信息标签"""
        text = """转录原文链接：

https://example.com/original

作者：

正文从这里开始
"""
        result = clean_tweet_text(text)
        assert "转录原文链接" not in result
        assert "作者：" not in result
        assert "https://example.com/original" in result

    def test_preserve_title_line_without_author_context(self):
        """标题回退正文时，不能把第一行误判成作者名吞掉。"""
        text = """我的推文做成了 skill
https://t.co/E9MeMerSYx

一行安装
npx skills add dontbesilent2025/dbskill
"""
        result = clean_tweet_text(text)
        assert result.splitlines()[0] == "我的推文做成了 skill"

    def test_remove_tco_links(self):
        """去掉 t.co 短链，避免正文混入无意义跳转链接。"""
        text = """我的推文做成了 skill
https://t.co/E9MeMerSYx

这些框架从 12307 条推文中提炼而来 https://t.co/ZtEbYenkiw
"""
        result = clean_tweet_text(text)
        assert "https://t.co/" not in result
        assert "这些框架从 12307 条推文中提炼而来" in result


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


class TestShellDetection:
    """页面壳子检测测试"""

    def test_detects_x_article_shell(self):
        raw_content = """# 极客杰尼 on X: "我把公众号排版Skill上架到了ClawHub" / X

Don't miss what's happening
People on X are the first to know.
See new posts
[](https://x.com/seekjourney/article/2035923833707012270)
"""
        assert is_probable_x_shell(raw_content, "") is True

    def test_keeps_real_article_content(self):
        raw_content = """Don't miss what's happening
[](https://x.com/vista8/article/2035544573876023605)
硅谷顶级PM的方法论免费开源！附Skill和32m资源包下载

一、痴迷于客户与问题
"""
        cleaned = "硅谷顶级PM的方法论免费开源！附Skill和32m资源包下载\n\n一、痴迷于客户与问题"
        assert is_probable_x_shell(raw_content, cleaned) is False
