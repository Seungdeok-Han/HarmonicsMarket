import json
import os
import pytest
from unittest.mock import MagicMock

from app import create_app
import app.routes as routes_mod


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_sns_feed_accessible(client):
    r = client.get('/sns')
    assert r.status_code == 200


def test_sns_create_requires_login(client):
    r = client.get('/sns/create')
    # should redirect to login
    assert r.status_code in (302, 301)


def test_sns_create_and_like(monkeypatch, client, tmp_path):
    # use temporary data file
    tempfile = tmp_path / 'sns.json'
    monkeypatch.setattr(routes_mod, 'SNS_DATA_PATH', str(tempfile))
    # ensure file exists
    tempfile.write_text('[]', encoding='utf-8')

    # create post by calling wrapped function with test_request_context
    with client.application.test_request_context(method='POST', data={'caption': 'hello'}):
        routes_mod.current_user = MagicMock(is_authenticated=True, id=10, username='tester')
        resp = routes_mod.sns_create.__wrapped__()
        # redirect to feed
        assert resp.status_code in (302, 301)

    # now like the new post
    posts = json.loads(tempfile.read_text(encoding='utf-8'))
    assert len(posts) == 1
    pid = posts[0]['id']
    with client.application.test_request_context(method='POST'):
        routes_mod.current_user = MagicMock(is_authenticated=True, id=10, username='tester')
        resp = routes_mod.sns_like.__wrapped__(pid)
        data = resp.get_json() if hasattr(resp, 'get_json') else resp[0]
        assert data['like_count'] == 1
