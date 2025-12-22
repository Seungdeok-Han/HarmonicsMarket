"""커뮤니티 SNS 피드에 시연용 게시글 추가 스크립트"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import random

# 경로 설정
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"
SNS_DATA_PATH = DATA_DIR / "sns_posts.json"

# 디렉토리 생성
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_sns_image(filename, color, main_text, sub_text=""):
    """SNS 피드용 이미지 생성"""
    img = Image.new('RGB', (800, 800), color=color)
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 메인 텍스트 중앙 배치
    bbox = draw.textbbox((0, 0), main_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    main_position = ((800 - text_width) // 2, 300)
    
    draw.text(main_position, main_text, fill='white', font=font_large)
    
    # 서브 텍스트
    if sub_text:
        bbox2 = draw.textbbox((0, 0), sub_text, font=font_small)
        text_width2 = bbox2[2] - bbox2[0]
        sub_position = ((800 - text_width2) // 2, 420)
        draw.text(sub_position, sub_text, fill='white', font=font_small)
    
    # 파일 저장
    filepath = UPLOAD_DIR / filename
    img.save(filepath)
    print(f"[생성] {filename}")
    return filename


def read_existing_posts():
    """기존 SNS 게시글 읽기"""
    try:
        with open(SNS_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_posts(posts):
    """SNS 게시글 저장"""
    with open(SNS_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def add_community_posts():
    """커뮤니티 피드에 자연스러운 게시글 추가"""
    
    # 기존 게시글 불러오기
    existing_posts = read_existing_posts()
    current_max_id = max([p.get('id', 0) for p in existing_posts], default=0)
    
    # 시연용 게시글 데이터
    demo_posts = [
        {
            'username': 'guitar_lover_99',
            'user_id': 101,
            'caption': '오늘 새벽 연습 세션 🌙 혼자 조용히 치는 시간이 제일 좋아요 #연습 #기타생활',
            'color': '#2C3E50',
            'main_text': '🎸',
            'sub_text': '새벽 연습',
        },
        {
            'username': 'rockstar_wannabe',
            'user_id': 102,
            'caption': '밴드 합주 끝나고 한컷! 오늘 정말 잘 맞았던 것 같아요 🤘 #밴드 #합주 #락음악',
            'color': '#C0392B',
            'main_text': '🤘',
            'sub_text': 'Band Practice',
        },
        {
            'username': 'acoustic_dreamer',
            'user_id': 103,
            'caption': '카페에서 어쿠스틱 공연 준비 중 ☕️ 떨리지만 기대돼요! #공연 #어쿠스틱 #버스킹',
            'color': '#16A085',
            'main_text': '☕🎵',
            'sub_text': 'Acoustic Live',
        },
        {
            'username': 'blues_master',
            'user_id': 104,
            'caption': '이 펜딩이 정말 끝내줘요... 블루스의 매력에 빠져듭니다 🎶 #블루스 #기타연주',
            'color': '#2980B9',
            'main_text': '🎵',
            'sub_text': 'Blues Soul',
        },
        {
            'username': 'finger_style_pro',
            'user_id': 105,
            'caption': '핑거스타일 새 곡 마스터! 2주 동안 연습한 보람이 있네요 😊 #핑거스타일 #어쿠스틱기타',
            'color': '#8E44AD',
            'main_text': '✨🎸',
            'sub_text': 'Fingerstyle',
        },
        {
            'username': 'jazz_guitarist',
            'user_id': 106,
            'caption': '재즈 클럽에서 즉흥 연주 🎺 관객들 반응이 너무 좋았어요! #재즈 #즉흥연주 #라이브',
            'color': '#D35400',
            'main_text': '🎺🎸',
            'sub_text': 'Jazz Session',
        },
        {
            'username': 'metal_shredder',
            'user_id': 107,
            'caption': '새로 익힌 스윕 피킹 테크닉! 손가락이 날아갈 것 같네요 🔥 #메탈 #테크닉 #연습',
            'color': '#E74C3C',
            'main_text': '🔥⚡',
            'sub_text': 'Metal Shred',
        },
        {
            'username': 'vintage_collector',
            'user_id': 108,
            'caption': '빈티지 기타 컬렉션 업데이트! 1970년대 깁슨 추가했어요 🎸 #빈티지 #컬렉션 #깁슨',
            'color': '#34495E',
            'main_text': '🏆',
            'sub_text': 'Vintage 1970s',
        },
        {
            'username': 'indie_music_fan',
            'user_id': 109,
            'caption': '인디 밴드 새 앨범 레코딩 중 🎙️ 우리 곡 듣고 싶으신 분? #인디음악 #레코딩 #밴드',
            'color': '#27AE60',
            'main_text': '🎙️🎸',
            'sub_text': 'Recording',
        },
        {
            'username': 'beginner_guitarist',
            'user_id': 110,
            'caption': '기타 시작한지 3개월! 첫 곡 완주 성공했어요 ㅠㅠ 감동 #기타초보 #연습 #성장',
            'color': '#F39C12',
            'main_text': '🎉✨',
            'sub_text': '3 Months',
        },
        {
            'username': 'song_writer_kim',
            'user_id': 111,
            'caption': '새 곡 작곡 중... 멜로디가 계속 머릿속을 맴도네요 🎼 #작곡 #송라이팅 #창작',
            'color': '#9B59B6',
            'main_text': '🎼',
            'sub_text': 'Songwriting',
        },
        {
            'username': 'classical_guitar_lover',
            'user_id': 112,
            'caption': '클래식 기타 독주회 준비 중입니다 🎻 바흐 곡 연습 중! #클래식기타 #독주회 #바흐',
            'color': '#1ABC9C',
            'main_text': '🎻🎸',
            'sub_text': 'Classical',
        },
    ]
    
    # 새 게시글 생성
    new_posts = []
    for i, post_data in enumerate(demo_posts):
        post_id = current_max_id + i + 1
        
        # 이미지 생성
        image_filename = f"community_{post_id}_{post_data['username']}.jpg"
        create_sns_image(
            image_filename,
            post_data['color'],
            post_data['main_text'],
            post_data['sub_text']
        )
        
        # 게시글 데이터 생성
        created_time = datetime.now() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        post = {
            'id': post_id,
            'username': post_data['username'],
            'user_id': post_data['user_id'],
            'image': image_filename,
            'media': [
                {
                    'type': 'image',
                    'filename': image_filename
                }
            ],
            'caption': post_data['caption'],
            'created_at': created_time.strftime('%Y-%m-%d %H:%M:%S'),
            'likes': [],
            'comments': []
        }
        
        new_posts.append(post)
        print(f"[생성] 게시글: {post_data['caption'][:30]}...")
    
    # 랜덤 좋아요 추가
    like_users = [
        {'id': 1, 'username': 'gkstmdejr99'},
        {'id': 101, 'username': 'guitar_lover_99'},
        {'id': 102, 'username': 'rockstar_wannabe'},
        {'id': 103, 'username': 'acoustic_dreamer'},
        {'id': 104, 'username': 'blues_master'},
    ]
    
    for post in new_posts:
        # 랜덤하게 좋아요 추가
        num_likes = random.randint(3, 15)
        post['likes'] = random.sample(like_users, min(num_likes, len(like_users)))
    
    # 랜덤 댓글 추가
    comments_pool = [
        "멋지네요! 👍",
        "정말 대단해요!",
        "저도 이렇게 되고 싶어요 ㅠㅠ",
        "부럽습니다!",
        "와 진짜 좋네요 🎸",
        "언제 한번 같이 연주해요!",
        "영상으로 보고 싶어요!",
        "최고예요!",
        "연습 화이팅!",
        "계속 응원할게요!"
    ]
    
    for post in new_posts[:6]:  # 처음 6개 게시글에만 댓글
        num_comments = random.randint(1, 3)
        comment_id_start = 1000 + post['id'] * 10
        
        for j in range(num_comments):
            commenter = random.choice(like_users)
            comment = {
                'id': comment_id_start + j,
                'user_id': commenter['id'],
                'username': commenter['username'],
                'content': random.choice(comments_pool),
                'created_at': (datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S') + 
                             timedelta(hours=random.randint(1, 12))).strftime('%Y-%m-%d %H:%M:%S'),
                'likes': [],
                'parent_id': None
            }
            post['comments'].append(comment)
    
    # 기존 게시글과 합치기 (새 게시글을 앞에 배치)
    all_posts = new_posts + existing_posts
    
    # 날짜순 정렬
    all_posts.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 저장
    save_posts(all_posts)
    
    print(f"\n✅ 커뮤니티 피드 게시글 생성 완료!")
    print(f"   - 새 게시글: {len(new_posts)}개")
    print(f"   - 총 게시글: {len(all_posts)}개")
    print(f"   - 이미지: {len(new_posts)}개 생성")
    print(f"\n🎸 커뮤니티 탭에서 확인해보세요!")


if __name__ == '__main__':
    add_community_posts()
