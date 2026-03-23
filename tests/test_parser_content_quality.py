import unittest
from unittest.mock import Mock, patch

from xparser.crawler import TavilyCrawler
from xparser.models import TweetInfo, URLType
from xparser.parser import parse
from xparser.url_detector import URLInfo


class TavilyCrawlerResponseTest(unittest.TestCase):
    def test_parse_response_falls_back_to_content_field(self):
        crawler = TavilyCrawler.__new__(TavilyCrawler)

        response = {
            "results": [
                {
                    "title": "Naval on X: Building products in public",
                    "content": "Building products in public is still the fastest feedback loop.",
                    "images": ["https://example.com/image.jpg"],
                }
            ]
        }

        tweet = crawler._parse_response(response, "https://x.com/naval/status/1234567890")

        self.assertEqual(tweet.tweet_id, "1234567890")
        self.assertIn("Building products in public", tweet.content)
        self.assertTrue(tweet.content_clean)
        self.assertEqual(tweet.images, ["https://example.com/image.jpg"])
        self.assertEqual(tweet.raw_data, response)


class ParserValidationTest(unittest.TestCase):
    @patch("xparser.parser.create_crawler")
    @patch("xparser.parser.detect_url")
    def test_parse_returns_error_when_content_missing(self, mock_detect_url, mock_create_crawler):
        mock_detect_url.return_value = URLInfo(
            url="https://x.com/naval/status/1234567890",
            url_type=URLType.X,
            username="naval",
            tweet_id="1234567890",
            is_valid=True,
        )
        mock_create_crawler.return_value = Mock(
            fetch_tweet=Mock(
                return_value=TweetInfo(
                    tweet_id="1234567890",
                    url="https://x.com/naval/status/1234567890",
                    username="naval",
                    raw_data={"results": []},
                )
            )
        )

        result = parse("https://x.com/naval/status/1234567890")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "正文提取为空")


if __name__ == "__main__":
    unittest.main()
