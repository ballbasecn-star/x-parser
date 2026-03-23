from unittest.mock import patch

from web.app import app
from xparser.models import ParseResult, TweetInfo, TweetMetrics


@patch('web.app.parse')
def test_parser_parse_returns_contract_payload(mock_parse):
    client = app.test_client()
    mock_parse.return_value = ParseResult(
        success=True,
        tweet=TweetInfo(
            tweet_id='1234567890',
            url='https://x.com/test/status/1234567890',
            username='test',
            display_name='测试作者',
            content='原始内容',
            content_clean='清洗后的内容',
            title='测试线程',
            created_at='2026-03-23 12:00:00',
            images=['https://example.com/image.jpg'],
            metrics=TweetMetrics(likes=12, retweets=3, replies=4, views=100, bookmarks=2),
            hashtags=['AI'],
            lang='zh-CN',
        ),
        source='test',
        processing_time=0.12,
    )

    response = client.post(
        '/api/v1/parse',
        json={
            'requestId': 'req_x_parse',
            'input': {
                'sourceText': '看看这个 https://x.com/test/status/1234567890',
                'platformHint': 'x',
            },
            'options': {
                'languageHint': 'zh-CN',
            },
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    assert body['data']['externalId'] == '1234567890'
    assert body['data']['canonicalUrl'] == 'https://x.com/test/status/1234567890'
    assert body['meta']['requestId'] == 'req_x_parse'


def test_parser_health_returns_contract_envelope():
    client = app.test_client()
    response = client.get('/api/v1/health')

    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    assert body['data']['status'] == 'UP'


def test_parser_capabilities_returns_contract_payload():
    client = app.test_client()
    response = client.get('/api/v1/capabilities')

    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    assert body['data']['platform'] == 'x'
    assert 'thread' in body['data']['supportedSourceTypes']


def test_parser_parse_rejects_unsupported_url():
    client = app.test_client()
    response = client.post(
        '/api/v1/parse',
        json={
            'requestId': 'req_x_bad_url',
            'input': {
                'sourceUrl': 'https://example.com/not-x',
            },
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body['success'] is False
    assert body['error']['code'] == 'UNSUPPORTED_URL'
