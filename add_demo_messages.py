"""메시지함에 시연용 메시지 대화 추가 스크립트"""
from datetime import datetime, timedelta
import random

from app import create_app, db
from app.models import User, Message


def add_demo_messages():
    app = create_app()
    
    with app.app_context():
        # 로그인한 사용자 (gkstmdejr99)
        main_user = User.query.filter_by(username='gkstmdejr99').first()
        if not main_user:
            print("⚠️  gkstmdejr99 사용자를 찾을 수 없습니다.")
            return
        
        # 커뮤니티에서 만든 다양한 사용자들 가져오기 (없으면 생성)
        community_users_data = [
            {'username': 'guitar_lover_99', 'user_id': 101},
            {'username': 'rockstar_wannabe', 'user_id': 102},
            {'username': 'acoustic_dreamer', 'user_id': 103},
            {'username': 'blues_master', 'user_id': 104},
            {'username': 'finger_style_pro', 'user_id': 105},
            {'username': 'jazz_guitarist', 'user_id': 106},
            {'username': 'metal_shredder', 'user_id': 107},
            {'username': 'vintage_collector', 'user_id': 108},
        ]
        
        demo_users = []
        for user_data in community_users_data:
            user = User.query.filter_by(username=user_data['username']).first()
            if not user:
                # 사용자 생성
                user = User(username=user_data['username'])
                user.set_password('demo1234')
                db.session.add(user)
                print(f"[생성] 사용자: {user_data['username']}")
            demo_users.append(user)
        
        db.session.commit()
        
        # 다양한 사용자들과의 자연스러운 메시지 대화 시나리오
        message_conversations = [
            {
                'other_user_idx': 0,  # guitar_lover_99
                'messages': [
                    {'sender': 'other', 'content': '안녕하세요! 새벽 연습 게시글 봤어요. 저도 새벽파인데 ㅎㅎ', 'hours_ago': 20},
                    {'sender': 'main', 'content': '오 반가워요! 새벽에 연습하면 집중도 잘되고 좋죠 😊', 'hours_ago': 19},
                    {'sender': 'other', 'content': '맞아요! 주로 몇시쯤 하세요?', 'hours_ago': 18},
                    {'sender': 'main', 'content': '보통 새벽 2-4시 사이에요. 소음 걱정 없고 좋아요', 'hours_ago': 17},
                ]
            },
            {
                'other_user_idx': 1,  # rockstar_wannabe
                'messages': [
                    {'sender': 'other', 'content': '밴드 합주 사진 멋있던데요! 무슨 곡 연습하셨어요?', 'hours_ago': 48},
                    {'sender': 'main', 'content': '감사합니다! 주로 니르바나랑 그린데이 곡들요 🤘', 'hours_ago': 47},
                    {'sender': 'other', 'content': '와 완전 제 취향이에요! 혹시 멤버 더 구하시나요?', 'hours_ago': 46},
                    {'sender': 'main', 'content': '지금은 인원 다 찼는데, 나중에 세션 같이 해요!', 'hours_ago': 45},
                    {'sender': 'other', 'content': '좋아요! 연락 기다릴게요 🎸', 'hours_ago': 44},
                ]
            },
            {
                'other_user_idx': 2,  # acoustic_dreamer
                'messages': [
                    {'sender': 'main', 'content': '카페 공연 어떻게 되셨어요? 궁금해요!', 'hours_ago': 15},
                    {'sender': 'other', 'content': '오늘 했는데 너무 떨렸어요 ㅠㅠ 그래도 재밌었어요!', 'hours_ago': 14},
                    {'sender': 'main', 'content': '대단해요! 저도 버스킹 해보고 싶은데 용기가 안나서 ㅎㅎ', 'hours_ago': 13},
                    {'sender': 'other', 'content': '같이 하면 덜 떨려요! 다음에 같이 해봐요', 'hours_ago': 12},
                    {'sender': 'main', 'content': '오 좋은 생각이네요! 그럼 연습 같이 해봐요 ☕', 'hours_ago': 11},
                ]
            },
            {
                'other_user_idx': 3,  # blues_master
                'messages': [
                    {'sender': 'main', 'content': '블루스 연주 영상 봤어요! 펜딩 정말 부드럽더라구요 👍', 'hours_ago': 72},
                    {'sender': 'other', 'content': '감사합니다! 스티비 레이 본 스타일 많이 연습했어요', 'hours_ago': 71},
                    {'sender': 'main', 'content': '혹시 펜딩 연습 팁 알려주실 수 있나요?', 'hours_ago': 70},
                    {'sender': 'other', 'content': '손목 힘을 빼고 리듬에 몸을 맡기는게 중요해요. 메트로놈 필수!', 'hours_ago': 69},
                    {'sender': 'main', 'content': '오 감사합니다! 연습해볼게요 🎵', 'hours_ago': 68},
                ]
            },
            {
                'other_user_idx': 4,  # finger_style_pro
                'messages': [
                    {'sender': 'other', 'content': '핑거스타일 배우고 싶으신가요? 초급 레슨 해드릴 수 있어요', 'hours_ago': 96},
                    {'sender': 'main', 'content': '정말요? 관심있어요! 어떻게 시작하면 좋을까요?', 'hours_ago': 95},
                    {'sender': 'other', 'content': '먼저 Travis Picking부터 시작하는게 좋아요', 'hours_ago': 94},
                    {'sender': 'main', 'content': '추천 연습곡 있으신가요?', 'hours_ago': 93},
                    {'sender': 'other', 'content': 'Dust in the Wind 추천드려요. 기초 익히기 딱이에요!', 'hours_ago': 92},
                ]
            },
            {
                'other_user_idx': 5,  # jazz_guitarist
                'messages': [
                    {'sender': 'other', 'content': '재즈 클럽 공연 너무 멋있었어요! 즉흥 연주 대박이었어요', 'hours_ago': 5},
                    {'sender': 'main', 'content': '와 감사합니다! 재즈는 즉흥이 재밌죠 🎺', 'hours_ago': 4},
                    {'sender': 'other', 'content': '다음 공연 언제예요? 꼭 가보고 싶어요', 'hours_ago': 3},
                    {'sender': 'main', 'content': '다음주 금요일이에요. 홍대 재즈바에서 합니다!', 'hours_ago': 2},
                ]
            },
            {
                'other_user_idx': 6,  # metal_shredder
                'messages': [
                    {'sender': 'main', 'content': '스윕 피킹 영상 봤는데 미쳤어요... 어떻게 그렇게 빨라요? 🔥', 'hours_ago': 30},
                    {'sender': 'other', 'content': 'ㅋㅋㅋ 감사합니다! 매일 1시간씩 연습했어요', 'hours_ago': 29},
                    {'sender': 'main', 'content': '연습 방법 좀 공유해주실 수 있나요?', 'hours_ago': 28},
                    {'sender': 'other', 'content': '천천히 시작해서 속도 점점 올리는게 핵심이에요. 메트로놈 60부터!', 'hours_ago': 27},
                ]
            },
            {
                'other_user_idx': 7,  # vintage_collector
                'messages': [
                    {'sender': 'other', 'content': '혹시 빈티지 기타 관심 있으세요? 70년대 깁슨 입고했어요', 'hours_ago': 120},
                    {'sender': 'main', 'content': '관심 있어요! 어떤 모델이에요?', 'hours_ago': 119},
                    {'sender': 'other', 'content': 'Les Paul Custom 1972년식이에요. 상태 좋아요!', 'hours_ago': 118},
                    {'sender': 'main', 'content': '가격이 어떻게 되나요?', 'hours_ago': 117},
                    {'sender': 'other', 'content': '쪽지로 자세히 보내드릴게요. 실물 보시면 반할걸요? 😊', 'hours_ago': 116},
                ]
            },
        ]
        
        added_count = 0
        now = datetime.now()
        
        for conv in message_conversations:
            if conv['other_user_idx'] >= len(demo_users):
                continue
                
            other_user = demo_users[conv['other_user_idx']]
            
            for msg_data in conv['messages']:
                # 발신자/수신자 결정
                if msg_data['sender'] == 'main':
                    sender_id = main_user.id
                    recipient_id = other_user.id
                else:
                    sender_id = other_user.id
                    recipient_id = main_user.id
                
                # 메시지 생성
                created_time = now - timedelta(hours=msg_data['hours_ago'])
                
                # 읽음 처리 (일부는 읽음, 일부는 안 읽음)
                read_time = None
                if msg_data['hours_ago'] > 24:  # 24시간 이상 된 메시지는 읽음 처리
                    read_time = created_time + timedelta(minutes=random.randint(5, 60))
                elif msg_data['sender'] == 'main':  # 내가 보낸 메시지도 읽음 처리
                    read_time = created_time + timedelta(minutes=random.randint(1, 30))
                
                message = Message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    content=msg_data['content'],
                    created_at=created_time,
                    read_at=read_time
                )
                db.session.add(message)
                added_count += 1
            
            print(f"[생성] {main_user.username} ↔️ {other_user.username} 대화 ({len(conv['messages'])}개 메시지)")
        
        db.session.commit()
        
        print(f"\n✅ 메시지 추가 완료!")
        print(f"   - 대화 상대: {len(message_conversations)}명")
        print(f"   - 총 메시지: {added_count}개")
        print(f"   - 대화 주제: 연습 팁, 밴드 합주, 공연, 레슨, 악기 거래 등")
        print(f"\n💬 메시지함에서 확인해보세요!")


if __name__ == '__main__':
    add_demo_messages()
