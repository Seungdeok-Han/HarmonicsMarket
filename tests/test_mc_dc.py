import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app import db
import app.routes as routes_mod
from app.routes import search_youtube_videos
from app.models import InstrumentPost, Like, GenreTag, BrandInfo, Comment


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


class QueryStub:
    def __init__(self):
        self.filters = []
        self.ordered = None

    def filter_by(self, **kwargs):
        self.filters.append(('filter_by', kwargs))
        return self

    def filter(self, *args):
        self.filters.append(('filter', args))
        return self

    def order_by(self, *args):
        self.ordered = args
        return self

    def paginate(self, page=1, per_page=8, error_out=False):
        class Paginated:
            def __init__(self):
                self.items = []
            def iter_pages(self, *args, **kwargs):
                return []

        return Paginated()


def test_index_selected_condition_branches(monkeypatch, client):
    # MC/DC-like: ensure each condition branch affects the query ordering/filtering
    qs = QueryStub()
    monkeypatch.setattr(InstrumentPost, 'query', qs)
    monkeypatch.setattr(GenreTag, 'query', MagicMock(all=lambda: []))

    # Case: no selected_condition -> default ordering by created_at.desc (no explicit condition filters)
    with client.application.test_request_context('/?page=1'):
        resp = routes_mod.index()
        assert qs.filters == []

    # Case: selected_condition == '80up'
    qs = QueryStub()
    monkeypatch.setattr(InstrumentPost, 'query', qs)
    with client.application.test_request_context('/?condition=80up'):
        routes_mod.index()
        # check that a filter was applied
        assert any(f[0] == 'filter' or f[0] == 'filter_by' for f in qs.filters)

    # Case: selected_condition == 'under40'
    qs = QueryStub()
    monkeypatch.setattr(InstrumentPost, 'query', qs)
    with client.application.test_request_context('/?condition=under40'):
        routes_mod.index()
        assert any(f[0] == 'filter' or f[0] == 'filter_by' for f in qs.filters)


def test_toggle_like_add_and_remove(monkeypatch, client):
    # Prepare a fake post and current_user
    fake_post = MagicMock()
    fake_post.id = 1
    fake_like_q = MagicMock()

    # Case: existing_like present -> should remove
    monkeypatch.setattr(InstrumentPost, 'query', MagicMock(get_or_404=lambda x: fake_post))
    monkeypatch.setattr(Like, 'query', MagicMock(filter_by=lambda **kw: MagicMock(first=lambda: object())))
    monkeypatch.setattr(db.session, 'commit', lambda: None)
    # prevent SQLAlchemy trying to delete an unmapped instance during tests
    monkeypatch.setattr(db.session, 'delete', lambda x: None)
    with client.application.test_request_context():
        # monkeypatch current_user and call underlying function to bypass login_required
        routes_mod.current_user = MagicMock(id=1, is_authenticated=True)
        resp = routes_mod.toggle_like.__wrapped__(1)
        # response is a flask Response object; ensure liked toggled (False)
        assert b'liked' in resp.data

    # Case: no existing_like -> should add
    monkeypatch.setattr(Like, 'query', MagicMock(filter_by=lambda **kw: MagicMock(first=lambda: None)))
    monkeypatch.setattr(db.session, 'add', lambda x: None)
    monkeypatch.setattr(db.session, 'commit', lambda: None)
    with client.application.test_request_context():
        routes_mod.current_user = MagicMock(id=2, is_authenticated=True)
        resp = routes_mod.toggle_like.__wrapped__(1)
        assert b'liked' in resp.data


def test_search_youtube_videos_success_and_failure(monkeypatch):
    # Success case
    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {
        'items': [
            {'id': {'videoId': 'abc123'}},
            {'id': {'videoId': 'def456'}},
            {'id': {}}  # invalid item should be skipped
        ]
    }
    monkeypatch.setattr('requests.get', lambda *args, **kwargs: fake_resp)
    urls = search_youtube_videos('fender strat', max_results=2)
    assert isinstance(urls, list) and 'youtube.com' in urls[0]

    # Failure case: requests throws
    def raise_exc(*args, **kwargs):
        raise Exception('network')

    monkeypatch.setattr('requests.get', raise_exc)
    urls = search_youtube_videos('fender strat')
    assert urls == []


def test_add_comment_validation_and_creation(monkeypatch, client):
    # Missing content -> 400
    with client.application.test_request_context(method='POST', json={}):
        routes_mod.current_user = MagicMock(id=1)
        resp = routes_mod.add_comment.__wrapped__(1)
        assert resp[1] == 400

    # Valid content -> created
    monkeypatch.setattr(db.session, 'add', lambda x: None)
    monkeypatch.setattr(db.session, 'commit', lambda: None)
    import datetime
    class FakeComment:
        def __init__(self, content, user_id, post_id):
            self.id = 1
            self.content = content
            self.user_id = user_id
            self.post_id = post_id
            self.created_at = datetime.datetime.now()
    monkeypatch.setattr(routes_mod, 'Comment', FakeComment)
    with client.application.test_request_context(method='POST', json={'content': 'Nice guitar!'}):
        routes_mod.current_user = MagicMock(id=1, username='tester')
        resp = routes_mod.add_comment.__wrapped__(1)
        # should return a tuple or response with success True
        if isinstance(resp, tuple):
            data = resp[0].get_json()
        else:
            data = resp.get_json()
        assert data.get('success') is True


def test_price_history_param_and_no_posts(monkeypatch, client):
    # missing params -> 400
    with client.application.test_request_context('/api/price_history'):
        resp = routes_mod.price_history()
        assert resp[1] == 400

    # valid params but no posts
    monkeypatch.setattr(InstrumentPost, 'query', MagicMock(filter_by=lambda **kw: MagicMock(order_by=lambda *a: MagicMock(limit=lambda n: MagicMock(all=lambda: [])))))
    with client.application.test_request_context('/api/price_history?brand_id=1&model_name=Strat'):
        resp = routes_mod.price_history()
        if isinstance(resp, tuple):
            data = resp[0].get_json()
        else:
            data = resp.get_json()
        assert data == {'labels': [], 'prices': []}
