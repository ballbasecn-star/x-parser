"""
工具函数模块

提供文本处理、数字解析等通用工具函数。
"""
import re
from typing import Optional, List, Tuple


_X_SHELL_NOISE_MARKERS = [
    "Don't miss what's happening",
    "People on X are the first to know",
    "[Log in]",
    "[Sign up]",
    "Create account",
    "See new posts",
    "Conversation",
    "New to X?",
]


def _normalize_shell_marker_text(text: str) -> str:
    """统一引号等符号，避免 Tavily 返回弯引号时漏掉页面噪音匹配。"""
    return (text or "").replace("’", "'").replace("‘", "'")


def parse_count(text: str) -> int:
    """
    解析数字字符串（支持 K/M/B 后缀）

    Examples:
        parse_count("1.2K") -> 1200
        parse_count("3.5M") -> 3500000
        parse_count("1,234") -> 1234

    Args:
        text: 数字字符串

    Returns:
        整数值
    """
    if not text:
        return 0

    text = text.strip().replace(',', '').replace(' ', '')

    multipliers = {
        'K': 1000,
        'k': 1000,
        'M': 1000000,
        'm': 1000000,
        'B': 1000000000,
        'b': 1000000000,
    }

    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return 0

    try:
        return int(text)
    except ValueError:
        return 0


def format_count(count: int) -> str:
    """
    格式化数字（添加 K/M 后缀）

    Examples:
        format_count(1500) -> "1.5K"
        format_count(2000000) -> "2.0M"

    Args:
        count: 整数值

    Returns:
        格式化字符串
    """
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def clean_tweet_text(raw_content: str) -> str:
    """
    清洗推文文本，去除噪音

    处理内容：
    - 移除页面导航元素
    - 移除作者信息区域
    - 移除互动数据
    - 移除图片链接标记
    - 保留实际内容

    Args:
        raw_content: 原始 HTML/Markdown 内容

    Returns:
        清洗后的纯文本
    """
    if not raw_content:
        return ""

    lines = raw_content.split('\n')
    content_lines = []

    # 状态跟踪
    in_content = False
    skipped_author = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        normalized = _normalize_shell_marker_text(stripped.lstrip('#').strip())

        # 跳过开头的空行
        if not in_content and not stripped:
            continue

        # ===== 跳过头部噪音 =====
        header_noise = [
            "Don't miss what's happening",
            'People on X are the first to know',
            '[Log in]',
            '[Sign up]',
            'Create account',
            'Article',
            'See new posts',
            'Conversation',
            '==========',
            '---------------',
        ]
        if any(noise in normalized for noise in header_noise):
            continue

        # X article 页面常见标题壳子，不属于正文。
        if " on X:" in normalized and normalized.endswith("/ X"):
            continue
        if normalized in {"Post", "Thread"}:
            continue
        if normalized in {"转录原文链接：", "转录原文链接", "原文链接：", "原文链接", "作者：", "作者"}:
            continue

        # 跳过导航链接
        if re.match(r'^(?:#+\s*)?\[\]\(https://x\.com/\)', stripped):
            continue
        if '/article/' in stripped and '[](https://' in stripped:
            continue

        # 跳过头像图片
        if 'pbs.twimg.com/profile_images' in line:
            continue

        # ===== 跳过作者区域 =====
        if not skipped_author and stripped:
            next_non_empty = ""
            for following in lines[index + 1:]:
                following_stripped = following.strip()
                if following_stripped:
                    next_non_empty = following_stripped
                    break
            is_display_name = (
                len(stripped) < 30 and
                not stripped.startswith('[') and
                not stripped.startswith('!') and
                not stripped.startswith('http') and
                not re.search(r'\d', stripped)
            )
            has_author_context = bool(
                re.match(r'^@[\w_]+$', next_non_empty)
                or re.match(r'^https?://x\.com/[\w_]+/?$', next_non_empty)
                or re.match(r'^\[[^\]]+\]\(https://x\.com/[\w_]+\)$', next_non_empty)
            )
            if is_display_name and has_author_context:
                skipped_author = True
                continue

        # 跳过 @username
        if re.match(r'^@[\w_]+$', stripped):
            continue

        # 跳过作者链接
        if re.search(r'^\[.+\]\(https://x\.com/', stripped) and '@' in stripped:
            skipped_author = True
            continue
        if re.match(r'^\[[^\]]+\]\(https://x\.com/[\w_]+\)$', stripped):
            continue

        # 跳过时间链接
        if re.search(r'^\[\w+\s+\d+(?:,?\s+\d+)?\]\(https://x\.com/', stripped):
            continue

        # 跳过 Show more/less
        if stripped in ['Show more', 'Show less', 'Show more…', 'Show less…']:
            continue

        # 跳过图片链接标记 [Image N: Image](url)
        if re.match(r'^\[Image\s*\d+:\s*Image\]\(https?://', stripped):
            continue
        if re.search(r'^\[Image\s*\d+:\s*Image\]\(https?://', stripped):
            continue

        # ===== 跳过互动数据 =====
        if re.match(r'^\[[\d\.]+[KM]?\]\(https://', stripped):
            continue

        if stripped.isdigit() and len(stripped) <= 5:
            continue

        if re.match(r'^[\d,\.\sKM]+$', stripped):
            continue

        if re.match(r'^[\d]+\s+[\d]+\s+[\d]+$', stripped):
            continue

        if re.match(r'^[-_]{3,}$', stripped):
            continue

        # ===== 跳过底部噪音 =====
        footer_markers = [
            '**Posted:**',
            'Translate post',
            'New to X?',
            'Trending now',
            '© 202',
            'Terms of Service',
            'Privacy Policy',
            'Cookie Policy',
            'Want to publish',
            'Upgrade to Premium',
            'More · · ·'
        ]
        if any(marker in line for marker in footer_markers):
            break

        # ===== 保留图片 Markdown =====
        if stripped.startswith('![') or '[![Image' in stripped:
            continue

        # 跳过原始图片 URL
        if re.match(r'^https?://pbs\.twimg\.com/media/', stripped):
            continue

        # ===== 收集内容 =====
        in_content = True

        if not stripped:
            if content_lines and content_lines[-1] != '\n\n':
                content_lines.append('\n\n')
            continue

        content_lines.append(stripped + '\n')

    # 合并内容
    content = ''.join(content_lines)

    # 清理多余空白
    # 把 Markdown 链接还原成更适合阅读的纯文本，减少详情页直接显示方括号噪音。
    content = re.sub(r'\[(https?://[^\]]+)\]\((https?://[^)]+)\)', r'\1', content)
    content = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1', content)
    # t.co 短链对阅读价值很低，优先去掉，避免标题回退正文时残留大量跳转链接。
    content = re.sub(r'(?m)^\s*https://t\.co/\S+\s*$', '', content)
    content = re.sub(r'\s*https://t\.co/\S+', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    return content


def is_probable_x_shell(raw_content: str, cleaned_content: str) -> bool:
    """
    判断当前结果是否只是 X 页面壳子，而不是真实正文。

    典型特征：
    - 原始内容里出现登录/注册/会话等页面文案
    - 同时带有 article 链接，但清洗后只剩一两行标题残留
    """
    if not raw_content:
        return False

    normalized_raw = _normalize_shell_marker_text(raw_content)
    noise_hits = sum(1 for marker in _X_SHELL_NOISE_MARKERS if marker in normalized_raw)
    has_article_link = "/article/" in raw_content

    lines = [line.strip() for line in (cleaned_content or "").splitlines() if line.strip()]
    short_shell = len(lines) <= 2 and len(cleaned_content.strip()) < 160

    return noise_hits >= 2 and has_article_link and short_shell


def extract_article_title(content: str) -> Optional[str]:
    """
    从推文内容中提取文章标题（长文章）

    判断规则：
    - 第一行包含中文
    - 长度适中（10-100 字符）
    - 或以 Markdown 标题格式开头

    Args:
        content: 推文内容

    Returns:
        标题或 None
    """
    if not content:
        return None

    lines = content.strip().split('\n')

    for i, line in enumerate(lines[:5]):
        stripped = line.strip()

        if not stripped:
            continue

        # 跳过图片标签
        if stripped.startswith('<img') or 'pbs.twimg.com' in stripped:
            continue

        # Markdown 标题
        if stripped.startswith('#'):
            title = stripped.lstrip('#').strip()
            if 5 < len(title) < 200:
                return title
            continue

        # 中文标题判断
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', stripped))
        ends_with_punct = bool(re.search(r'[。！？\.!?]$', stripped))
        reasonable_length = 10 < len(stripped) < 100

        if has_chinese and (ends_with_punct or reasonable_length):
            return stripped

        # 英文短标题
        if not has_chinese and reasonable_length and i == 0:
            return stripped

    return None


def extract_hashtags(text: str) -> List[str]:
    """
    提取文本中的话题标签

    Args:
        text: 推文文本

    Returns:
        标签列表（含 # 符号）
    """
    if not text:
        return []
    return re.findall(r'#[\w\u4e00-\u9fff]+', text)


def extract_mentions(text: str) -> List[str]:
    """
    提取文本中的 @ 提及

    Args:
        text: 推文文本

    Returns:
        用户名列表（不含 @ 符号）
    """
    if not text:
        return []
    matches = re.findall(r'@([\w_]+)', text)
    return matches


def parse_title_string(title: str) -> Tuple[str, str]:
    """
    解析 Tavily 返回的标题字符串

    格式: "DisplayName on X: \"Tweet Content\" / X"

    Args:
        title: 标题字符串

    Returns:
        (display_name, content) 元组
    """
    display_name = ""
    content = ""

    # 移除 " / X" 后缀
    title = title.replace(" / X", "").strip()

    if " on X:" in title:
        parts = title.split(" on X:", 1)
        display_name = parts[0].strip()
        remaining = parts[1].strip()

        # 移除引号
        if remaining.startswith('"') and remaining.endswith('"'):
            content = remaining[1:-1].strip()
        elif remaining.startswith('"'):
            content = remaining[1:].strip()
        else:
            content = remaining
    else:
        display_name = title

    return display_name, content


def is_valid_image_url(url: str) -> bool:
    """
    检查是否为有效的图片 URL

    Args:
        url: URL 字符串

    Returns:
        是否有效
    """
    if not url:
        return False

    # 检查扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    is_image = any(ext in url.lower() for ext in image_extensions)

    # 检查 Twitter 图片格式参数
    has_format = 'format=' in url.lower() and '&name=' in url

    # 排除头像
    is_profile = 'profile_images' in url

    return (is_image or has_format) and not is_profile


def filter_content_images(images: List[str]) -> List[str]:
    """
    过滤图片列表，只保留内容图片（排除头像）

    Args:
        images: 图片 URL 列表

    Returns:
        过滤后的列表
    """
    return [img for img in images if is_valid_image_url(img)]
