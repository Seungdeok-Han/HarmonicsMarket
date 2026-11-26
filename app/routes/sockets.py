"""Socket.IO handlers for realtime messaging."""
import datetime

from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from app.extensions import db, socketio
from app.models import Message, User
from app.services.notifications import create_notification


@socketio.on('connect')
def handle_connect():
    """사용자 연결"""
    if current_user.is_authenticated:
        user_room = f'user_{current_user.id}'
        join_room(user_room)
        print(f'✅ 사용자 {current_user.username}이(가) 연결됨')
        emit('connected', {'data': f'{current_user.username}이(가) 연결되었습니다'})


@socketio.on('disconnect')
def handle_disconnect():
    """사용자 연결 해제"""
    if current_user.is_authenticated:
        user_room = f'user_{current_user.id}'
        leave_room(user_room)
        print(f'❌ 사용자 {current_user.username}이(가) 연결 해제됨')


@socketio.on('send_message')
def handle_send_message(data):
    """실시간 메시지 전송"""
    if not current_user.is_authenticated:
        return False

    recipient_id = data.get('recipient_id')
    content = data.get('content', '').strip()

    if not content or not recipient_id:
        emit('error', {'message': '유효하지 않은 메시지'})
        return False

    recipient = User.query.get(recipient_id)
    if not recipient:
        emit('error', {'message': '수신자를 찾을 수 없습니다'})
        return False

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        created_at=datetime.datetime.utcnow(),
    )
    db.session.add(message)
    db.session.commit()

    create_notification(
        user_id=recipient_id,
        notification_type='message',
        related_user_id=current_user.id,
    )

    recipient_room = f'user_{recipient_id}'
    emit('new_message', {
        'id': message.id,
        'sender_id': current_user.id,
        'sender_name': current_user.username,
        'content': content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'read_at': None,
    }, room=recipient_room)

    emit('message_sent', {
        'id': message.id,
        'recipient_id': recipient_id,
        'content': content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    })

    print(f'💬 메시지 전송: {current_user.username} → {recipient.username}')
    return True


@socketio.on('mark_read')
def handle_mark_read(data):
    """메시지 읽음 표시"""
    if not current_user.is_authenticated:
        return False

    message_id = data.get('message_id')
    sender_id = data.get('sender_id')

    message = Message.query.get(message_id)
    if not message or message.recipient_id != current_user.id:
        return False

    message.read_at = datetime.datetime.utcnow()
    db.session.commit()

    sender_room = f'user_{sender_id}'
    emit('message_read', {
        'message_id': message_id,
        'read_at': message.read_at.strftime('%Y-%m-%d %H:%M:%S'),
    }, room=sender_room)

    print(f'👁️ 메시지 읽음: ID {message_id}')
    return True


@socketio.on('typing')
def handle_typing(data):
    """타이핑 중 상태 표시"""
    if not current_user.is_authenticated:
        return False

    recipient_id = data.get('recipient_id')
    is_typing = data.get('is_typing', True)

    if not recipient_id:
        return False

    recipient_room = f'user_{recipient_id}'
    emit('user_typing', {
        'sender_id': current_user.id,
        'sender_name': current_user.username,
        'is_typing': is_typing,
    }, room=recipient_room)

    return True


@socketio.on('join_conversation')
def handle_join_conversation(data):
    """대화방 입장"""
    if not current_user.is_authenticated:
        return False

    other_id = data.get('other_id')
    if not other_id:
        return False

    conversation_room = f'conv_{min(current_user.id, other_id)}_{max(current_user.id, other_id)}'
    join_room(conversation_room)

    print(f'🚪 {current_user.username}이(가) {other_id}와의 대화방 입장')
    return True


@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    """대화방 퇴장"""
    if not current_user.is_authenticated:
        return False

    other_id = data.get('other_id')
    if not other_id:
        return False

    conversation_room = f'conv_{min(current_user.id, other_id)}_{max(current_user.id, other_id)}'
    leave_room(conversation_room)

    print(f'🚪 {current_user.username}이(가) 대화방 퇴장')
    return True
