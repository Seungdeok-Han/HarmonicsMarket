from app.extensions import db
from app.models import BrandInfo, InstrumentPost, User


def _register_and_login(client, username='seller1', password='secret123'):
    client.post('/register', data={'username': username, 'password': password})
    client.post('/login', data={'username': username, 'password': password})
    return username


def test_index_ok(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'Harmonics' in r.data or '중고'.encode() in r.data


def test_create_listing_and_view(client, app):
    _register_and_login(client)
    with app.app_context():
        brand = BrandInfo(name='Fender')
        db.session.add(brand)
        db.session.commit()
        brand_id = brand.id

    r = client.post(
        '/add',
        data={
            'title': 'Strat for sale',
            'brand_id': str(brand_id),
            'model_name': 'Player Strat',
            'shape': 'Stratocaster',
            'condition': '85',
            'price': '120',
            'description': 'Good condition',
        },
        follow_redirects=True,
    )
    assert r.status_code == 200

    with app.app_context():
        post = InstrumentPost.query.filter_by(title='Strat for sale').first()
        assert post is not None
        post_id = post.id

    detail = client.get(f'/post/{post_id}')
    assert detail.status_code == 200
    assert b'Strat for sale' in detail.data


def test_message_listing_context(client, app):
    with app.app_context():
        seller = User(username='seller_x')
        seller.set_password('pw')
        buyer = User(username='buyer_x')
        buyer.set_password('pw')
        brand = BrandInfo(name='Gibson')
        db.session.add_all([seller, buyer, brand])
        db.session.commit()
        post = InstrumentPost(
            title='Les Paul Standard',
            brand_id=brand.id,
            model_name='Standard',
            shape='Les Paul',
            condition=90,
            price=250,
            description='desc',
            user_id=seller.id,
            status='available',
        )
        db.session.add(post)
        db.session.commit()
        seller_id, post_id = seller.id, post.id

    client.post('/login', data={'username': 'buyer_x', 'password': 'pw'})
    r = client.get(f'/messages/{seller_id}?listing={post_id}')
    assert r.status_code == 200
    assert b'Les Paul Standard' in r.data
    assert '문의 중인 매물'.encode() in r.data
