"""Simple script to test message creation and retrieval."""
from app import create_app, db
from app.models import User, Message

app = create_app()

with app.app_context():
    # ensure two test users exist
    u1 = User.query.filter_by(username='alice').first()
    if not u1:
        u1 = User(username='alice')
        u1.set_password('pass')
        db.session.add(u1)
    u2 = User.query.filter_by(username='bob').first()
    if not u2:
        u2 = User(username='bob')
        u2.set_password('pass')
        db.session.add(u2)
    db.session.commit()

    # create a message from alice to bob
    m = Message(sender_id=u1.id, recipient_id=u2.id, content='안녕하세요, 상품 문의드립니다.')
    db.session.add(m)
    db.session.commit()

    # fetch conversation
    conv = Message.query.filter(
        ((Message.sender_id==u1.id) & (Message.recipient_id==u2.id)) |
        ((Message.sender_id==u2.id) & (Message.recipient_id==u1.id))
    ).order_by(Message.created_at.asc()).all()

    print('Conversation alice <-> bob:')
    for msg in conv:
        s = 'alice' if msg.sender_id==u1.id else 'bob'
        print(f"[{msg.created_at}] {s}: {msg.content}")
