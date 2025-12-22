"""시연용 SNS 게시글과 메시지 추가 스크립트"""
import json
import os
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Message

# SNS 게시글 추가
def add_demo_sns_posts():
    sns_path = os.path.join('data', 'sns_posts.json')
    
    # 기존 데이터 읽기
    if os.path.exists(sns_path):
        with open(sns_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    else:
        posts = []
    
    # 현재 최대 ID 찾기
    max_id = max([p['id'] for p in posts], default=0)
    
    # 시연용 게시글 추가
    demo_posts = [
        {
            "id": max_id + 1,
            "username": "데모유저1",
            "user_id": 999,  # 임시 유저 ID
            "image": "",
            "media": [],
            "caption": "새로 산 펜더 스트랫 🎸 소리가 정말 좋네요! #펜더 #일렉기타",
            "created_at": (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [],
            "comments": [
                {
                    "id": 1,
                    "user_id": 1,
                    "username": "gkstmdejr99",
                    "content": "멋지네요! 어떤 모델이에요?",
                    "created_at": (datetime.now() - timedelta(hours=1, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                },
                {
                    "id": 2,
                    "user_id": 999,
                    "username": "데모유저1",
                    "content": "American Professional II입니다!",
                    "created_at": (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": 1
                }
            ]
        },
        {
            "id": max_id + 2,
            "username": "기타매니아",
            "user_id": 998,
            "image": "",
            "media": [],
            "caption": "오늘 연습 세션 완료! 드디어 어려운 솔로 파트를 마스터했어요 💪",
            "created_at": (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1],
            "comments": [
                {
                    "id": 1,
                    "user_id": 1,
                    "username": "gkstmdejr99",
                    "content": "대단해요! 어떤 곡이에요?",
                    "created_at": (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                }
            ]
        },
        {
            "id": max_id + 3,
            "username": "재즈기타리스트",
            "user_id": 997,
            "image": "",
            "media": [],
            "caption": "깁슨 ES-335 빈티지 사운드가 일품이네요 🎵 재즈 연주하기 정말 좋아요",
            "created_at": (datetime.now() - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1, 998],
            "comments": []
        },
        {
            "id": max_id + 4,
            "username": "음악스튜디오",
            "user_id": 996,
            "image": "",
            "media": [],
            "caption": "신곡 녹음 중입니다! 어쿠스틱 기타 사운드 체크 🎼",
            "created_at": (datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1],
            "comments": [
                {
                    "id": 1,
                    "user_id": 1,
                    "username": "gkstmdejr99",
                    "content": "기대되네요!",
                    "created_at": (datetime.now() - timedelta(hours=11)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                }
            ]
        },
        {
            "id": max_id + 5,
            "username": "락밴드드러머",
            "user_id": 995,
            "image": "",
            "media": [],
            "caption": "주말 공연 준비 완료! 오늘 밤 클럽에서 봐요 🤘",
            "created_at": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1, 998, 999],
            "comments": [
                {
                    "id": 1,
                    "user_id": 998,
                    "username": "기타매니아",
                    "content": "꼭 갈게요!",
                    "created_at": (datetime.now() - timedelta(hours=20)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                }
            ]
        },
        {
            "id": max_id + 6,
            "username": "클래식기타",
            "user_id": 994,
            "image": "",
            "media": [],
            "caption": "라미레즈 기타로 바흐 연주 중... 집중력 100% 🎻",
            "created_at": (datetime.now() - timedelta(days=1, hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1],
            "comments": []
        },
        {
            "id": max_id + 7,
            "username": "베이스연주자",
            "user_id": 993,
            "image": "",
            "media": [],
            "caption": "새 베이스 픽업 교체 완료! 톤이 완전 달라졌어요 🔊",
            "created_at": (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1, 999],
            "comments": [
                {
                    "id": 1,
                    "user_id": 1,
                    "username": "gkstmdejr99",
                    "content": "어떤 픽업으로 바꾸셨어요?",
                    "created_at": (datetime.now() - timedelta(days=1, hours=22)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                },
                {
                    "id": 2,
                    "user_id": 993,
                    "username": "베이스연주자",
                    "content": "세이모어 던컨 SPB-3으로 바꿨어요!",
                    "created_at": (datetime.now() - timedelta(days=1, hours=20)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": 1
                }
            ]
        },
        {
            "id": max_id + 8,
            "username": "어쿠스틱러버",
            "user_id": 992,
            "image": "",
            "media": [],
            "caption": "마틴 D-28 드디어 구매했습니다! 평생 꿈꾸던 기타예요 😭✨",
            "created_at": (datetime.now() - timedelta(days=2, hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1, 998, 999, 997],
            "comments": [
                {
                    "id": 1,
                    "user_id": 998,
                    "username": "기타매니아",
                    "content": "축하드려요! 정말 좋은 기타죠!",
                    "created_at": (datetime.now() - timedelta(days=2, hours=6)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                }
            ]
        },
        {
            "id": max_id + 9,
            "username": "메탈기타",
            "user_id": 991,
            "image": "",
            "media": [],
            "caption": "7현 기타로 다운튜닝 연습 중... 손가락이 아파 😅",
            "created_at": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1],
            "comments": []
        },
        {
            "id": max_id + 10,
            "username": "플라멩코",
            "user_id": 990,
            "image": "",
            "media": [],
            "caption": "스페인 세비야에서 플라멩코 레슨 받고 있어요! 🇪🇸💃",
            "created_at": (datetime.now() - timedelta(days=3, hours=12)).strftime('%Y-%m-%d %H:%M:%S'),
            "likes": [1, 998, 997, 994],
            "comments": [
                {
                    "id": 1,
                    "user_id": 1,
                    "username": "gkstmdejr99",
                    "content": "우와 부럽네요!",
                    "created_at": (datetime.now() - timedelta(days=3, hours=10)).strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": [],
                    "parent_id": None
                }
            ]
        }
    ]
    
    # 기존 posts의 앞에 추가 (최신순)
    posts = demo_posts + posts
    
    # 저장
    os.makedirs('data', exist_ok=True)
    with open(sns_path, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(demo_posts)}개의 SNS 게시글이 추가되었습니다!")


# 메시지 추가
def add_demo_messages():
    app = create_app()
    with app.app_context():
        # 현재 로그인 유저 확인 (ID=1 가정)
        current_user = User.query.get(1)
        if not current_user:
            print("❌ 유저 ID 1을 찾을 수 없습니다. 먼저 로그인하세요.")
            return
        
        # 데모 유저들 생성 또는 확인
        demo_users = []
        demo_usernames = ['악기판매자', '기타수리샵', '음악학원']
        
        for username in demo_usernames:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password('demo1234')  # 데모 비밀번호
                db.session.add(user)
                demo_users.append(user)
            else:
                demo_users.append(user)
        
        db.session.commit()
        
        # 메시지 추가
        messages_data = [
            # 악기판매자와의 대화
            {
                'sender': demo_users[0],
                'recipient': current_user,
                'content': '안녕하세요! 펜더 스트랫 아직 판매 가능한가요?',
                'time_delta': timedelta(hours=3)
            },
            {
                'sender': current_user,
                'recipient': demo_users[0],
                'content': '네, 아직 판매 중입니다!',
                'time_delta': timedelta(hours=2, minutes=50)
            },
            {
                'sender': demo_users[0],
                'recipient': current_user,
                'content': '직거래 가능할까요? 서울 강남에서 만날 수 있어요.',
                'time_delta': timedelta(hours=2, minutes=30)
            },
            {
                'sender': current_user,
                'recipient': demo_users[0],
                'content': '네 가능합니다. 주말에 시간 괜찮으세요?',
                'time_delta': timedelta(hours=2)
            },
            
            # 기타수리샵과의 대화
            {
                'sender': demo_users[1],
                'recipient': current_user,
                'content': '기타 수리 문의드립니다. 넥 조정 가능한가요?',
                'time_delta': timedelta(days=1, hours=5)
            },
            {
                'sender': current_user,
                'recipient': demo_users[1],
                'content': '네, 어떤 증상이신가요?',
                'time_delta': timedelta(days=1, hours=4)
            },
            {
                'sender': demo_users[1],
                'recipient': current_user,
                'content': '프렛 버즈가 심해서요. 12프렛 이상에서 많이 울려요.',
                'time_delta': timedelta(days=1, hours=3)
            },
            
            # 음악학원과의 대화
            {
                'sender': demo_users[2],
                'recipient': current_user,
                'content': '안녕하세요. 기타 레슨 관심 있으신가요?',
                'time_delta': timedelta(days=2, hours=8)
            },
            {
                'sender': current_user,
                'recipient': demo_users[2],
                'content': '일렉기타 레슨 받고 싶은데 초보도 가능한가요?',
                'time_delta': timedelta(days=2, hours=7)
            },
            {
                'sender': demo_users[2],
                'recipient': current_user,
                'content': '물론이죠! 초보자 수업 많이 진행하고 있습니다. 주 1회 월 20만원입니다.',
                'time_delta': timedelta(days=2, hours=6)
            },
            {
                'sender': current_user,
                'recipient': demo_users[2],
                'content': '시간표 좀 보내주실 수 있나요?',
                'time_delta': timedelta(days=2, hours=5)
            }
        ]
        
        # 메시지 추가
        now = datetime.now()
        for msg_data in messages_data:
            message = Message(
                sender_id=msg_data['sender'].id,
                recipient_id=msg_data['recipient'].id,
                content=msg_data['content'],
                created_at=now - msg_data['time_delta']
            )
            db.session.add(message)
        
        db.session.commit()
        print(f"✅ {len(messages_data)}개의 메시지가 추가되었습니다!")
        print(f"✅ 데모 유저 {len(demo_users)}명이 생성되었습니다:")
        for user in demo_users:
            print(f"   - {user.username} (ID: {user.id})")


if __name__ == '__main__':
    print("🎸 시연용 데이터 추가 중...\n")
    add_demo_sns_posts()
    print()
    add_demo_messages()
    print("\n✨ 모든 시연용 데이터가 추가되었습니다!")
