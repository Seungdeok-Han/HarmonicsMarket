from app.extensions import db
from app.models import CommunityPost, User
from app.services.community import import_from_json, serialize_post


def test_sns_feed_uses_db(client, app):
    with app.app_context():
        user = User(username='poster')
        user.set_password('pw')
        db.session.add(user)
        db.session.commit()
        db.session.add(CommunityPost(user_id=user.id, caption='hello community', image='', media=[]))
        db.session.commit()

    r = client.get('/sns')
    assert r.status_code == 200
    assert b'hello community' in r.data


def test_import_json_dedupes_likes(app):
    payload = [
        {
            'id': 1,
            'username': 'u1',
            'user_id': 1,
            'image': '',
            'media': [],
            'caption': 'c1',
            'created_at': '2025-01-01 00:00:00',
            'likes': [1, 1, 2, {'user_id': 2}],
            'comments': [],
        }
    ]
    with app.app_context():
        for name in ['u1', 'u2']:
            u = User(username=name)
            u.set_password('pw')
            db.session.add(u)
        db.session.commit()
        n = import_from_json(payload)
        assert n == 1
        post = CommunityPost.query.first()
        assert post.likes.count() == 2
        data = serialize_post(post)
        assert data['like_count'] == 2
