from app.extensions import db
from app.models import CommunityPost


def test_sns_feed_accessible(client):
    r = client.get('/sns')
    assert r.status_code == 200


def test_sns_create_requires_login(client):
    r = client.get('/sns/create')
    assert r.status_code in (302, 301)


def test_sns_create_and_like(client, app):
    client.post('/register', data={'username': 'tester', 'password': 'secret123'})
    client.post('/login', data={'username': 'tester', 'password': 'secret123'})

    r = client.post('/sns/create', data={'caption': 'hello'}, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        post = CommunityPost.query.filter_by(caption='hello').first()
        assert post is not None
        pid = post.id

    like = client.post(f'/sns/like/{pid}')
    assert like.status_code == 200
    data = like.get_json()
    assert data['like_count'] == 1
    assert data['liked'] is True
