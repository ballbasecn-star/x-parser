#!/usr/bin/env python3
"""
X/Twitter 推文解析工具 - 命令行入口

用法:
    python main.py "https://x.com/username/status/123456789"
    python main.py --json "https://twitter.com/..."
    python main.py --check                              # 检查 API Key 配置
"""
import json
import logging
import sys
import os

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def check_api_key():
    """检查 API Key 配置"""
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        print(f"✅ TAVILY_API_KEY 已配置 (长度: {len(api_key)})")
        print(f"\n💡 现在可以解析推文:")
        print(f'   python main.py "https://x.com/username/status/123456789"')
    else:
        print("❌ TAVILY_API_KEY 未配置")
        print("\n📋 配置步骤:")
        print("1. 访问 https://tavily.com/ 注册账号")
        print("2. 在 Dashboard 获取 API Key")
        print("3. 设置环境变量:")
        print("   export TAVILY_API_KEY=your_key_here")
        print("4. 或创建 .env 文件:")
        print("   TAVILY_API_KEY=your_key_here")


def handle_parse(args):
    """处理推文解析"""
    import argparse
    from xparser.parser import parse

    parser = argparse.ArgumentParser(
        description="X/Twitter 推文解析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "https://x.com/elonmusk/status/123456789"
  python main.py --json "https://twitter.com/..."
  python main.py --check
        """,
    )
    parser.add_argument("url", nargs="?", help="推文链接 (twitter.com 或 x.com)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--check", action="store_true", help="检查 API Key 配置")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志输出")
    parser.add_argument("--debug", action="store_true", help="调试模式，显示原始数据")

    parsed = parser.parse_args(args)

    # 检查模式
    if parsed.check:
        check_api_key()
        return

    setup_logging(parsed.verbose or parsed.debug)

    # 获取 URL
    url = parsed.url
    if not url:
        print("📋 请输入推文链接（输入后按回车）:")
        print("-" * 40)
        try:
            url = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            sys.exit(0)

    if not url:
        print("❌ 未输入任何内容")
        sys.exit(1)

    # 解析
    print(f"\n🔍 正在解析推文...\n")

    result = parse(url)

    if not result.success:
        print(f"❌ 解析失败: {result.error}")
        sys.exit(1)

    # 调试模式：显示原始数据
    if parsed.debug and result.tweet and result.tweet.raw_data:
        print("=" * 60)
        print("🔍 调试信息 - RAW CONTENT")
        print("=" * 60)
        raw = result.tweet.raw_data
        if 'results' in raw and raw['results']:
            raw_content = raw['results'][0].get('raw_content', '')
            # 打印包含数字的行
            import re
            for line in raw_content.split('\n'):
                # 找包含数字或链接格式的行
                if re.search(r'\d+|replies|retweets|likes|views|quotes|bookmarks', line, re.I):
                    print(line.strip()[:200])
        print("=" * 60)
        print()

    # 输出结果
    if parsed.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.tweet.format_output())


def main():
    """主入口"""
    args = sys.argv[1:]

    if not args:
        # 无参数，显示帮助
        print(__doc__)
        print("\n运行 --help 查看更多选项")
        sys.exit(0)

    handle_parse(args)


if __name__ == "__main__":
    main()