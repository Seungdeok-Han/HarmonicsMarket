"""Integration test using Flask test client to register, login and send messages."""
from app import create_app, db
from app.models import User, Message

app = create_app()

with app.test_client() as c:
    with app.app_context():
        # ensure clean test users
        User.query.filter(User.username.in_(['tester1','tester2'])).delete(synchronize_session=False)
        db.session.commit()

    # register tester1
    rv = c.post('/register', data={'username':'tester1','password':'pass'}, follow_redirects=True)
    # register tester2
    rv = c.post('/register', data={'username':'tester2','password':'pass'}, follow_redirects=True)

    # login as tester1
    rv = c.post('/login', data={'username':'tester1','password':'pass'}, follow_redirects=True)
    assert '로그인'.encode('utf-8') not in rv.data

    # find tester2 id
    with app.app_context():
        t2 = User.query.filter_by(username='tester2').first()
        assert t2 is not None
        t2id = t2.id

    # send message to tester2
    rv = c.post(f'/messages/{t2id}', data={'content':'안녕하세요 테스트 메시지'}, follow_redirects=True)
    assert '메시지를 보냈습니다'.encode('utf-8') in rv.data

    # logout and login as tester2
    c.get('/logout', follow_redirects=True)
    c.post('/login', data={'username':'tester2','password':'pass'}, follow_redirects=True)

    # check messages list
    rv = c.get('/messages')
    assert 'tester1'.encode('utf-8') in rv.data

    # view conversation with tester1
    with app.app_context():
        t1 = User.query.filter_by(username='tester1').first()
        t1id = t1.id
    rv = c.get(f'/messages/{t1id}')
    # (no strict asserts here, just ensure endpoint works)
    print('Messages endpoints exercised; check browser for manual verification.')
