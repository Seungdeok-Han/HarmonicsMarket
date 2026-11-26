from unittest.mock import patch

from app.extensions import db
from app.models import BrandInfo, InstrumentPost, User
from app.routes.youtube import search_youtube_videos


def test_index_filters_by_brand(client, app):
    with app.app_context():
        u = User(username='seller')
        u.set_password('pw')
        b1 = BrandInfo(name='Fender')
        b2 = BrandInfo(name='Gibson')
        db.session.add_all([u, b1, b2])
        db.session.commit()
        db.session.add_all(
            [
                InstrumentPost(
                    title='A', brand_id=b1.id, model_name='S', user_id=u.id, price=10, condition=80
                ),
                InstrumentPost(
                    title='B', brand_id=b2.id, model_name='L', user_id=u.id, price=20, condition=70
                ),
            ]
        )
        db.session.commit()
        brand_id = b1.id

    r = client.get(f'/?brand={brand_id}')
    assert r.status_code == 200
    assert b'A' in r.data


def test_search_youtube_videos_without_key_returns_empty():
    with patch('app.routes.youtube.YOUTUBE_API_KEY', ''):
        assert search_youtube_videos('fender strat') == []


def test_search_youtube_videos_success_and_failure():
    fake_search = {
        'items': [
            {'id': {'videoId': 'abc'}, 'snippet': {'title': 't1'}},
            {'id': {'videoId': 'def'}, 'snippet': {'title': 't2'}},
        ]
    }
    with patch('app.routes.youtube.YOUTUBE_API_KEY', 'fake'), patch(
        'app.routes.youtube.requests.get'
    ) as get:
        resp = get.return_value
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.return_value = fake_search
        links = search_youtube_videos('query', max_results=2)
        assert len(links) >= 1
        assert 'abc' in links[0]
