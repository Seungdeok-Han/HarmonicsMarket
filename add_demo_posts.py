"""SNS 시연용 게시글 추가 스크립트"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import random

# Flask app 초기화
from app import create_app, db
from app.models import User, InstrumentPost, BrandInfo, Comment, Like

# 이미지 저장 경로
UPLOAD_DIR = Path(__file__).parent / "app" / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_placeholder_image(filename, color, text):
    """플레이스홀더 악기 이미지 생성"""
    img = Image.new('RGB', (800, 600), color=color)
    draw = ImageDraw.Draw(img)
    
    # 텍스트 추가
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # 텍스트 중앙 배치
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((800 - text_width) // 2, (600 - text_height) // 2)
    
    draw.text(position, text, fill='white', font=font)
    
    # 파일 저장
    filepath = UPLOAD_DIR / filename
    img.save(filepath)
    print(f"[생성] {filename}")
    return filename


def add_demo_data():
    app = create_app()
    
    with app.app_context():
        # 1. 테스트 사용자 확인/생성
        users = []
        for username in ['demo_user1', 'demo_user2', 'demo_user3', 'guitar_lover', 'bass_player']:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password('demo1234')
                db.session.add(user)
                print(f"[생성] 사용자: {username}")
            users.append(user)
        
        db.session.commit()
        
        # 2. 브랜드 확인/생성
        brands_data = [
            {'name': 'Fender', 'origin_country': 'USA', 'description': '일렉트릭 기타의 전설'},
            {'name': 'Gibson', 'origin_country': 'USA', 'description': '레스폴의 명가'},
            {'name': 'Ibanez', 'origin_country': 'Japan', 'description': '다양한 장르를 아우르는 브랜드'},
            {'name': 'Martin', 'origin_country': 'USA', 'description': '어쿠스틱 기타의 명가'},
            {'name': 'Yamaha', 'origin_country': 'Japan', 'description': '믿을 수 있는 품질'},
        ]
        
        brands = []
        for brand_data in brands_data:
            brand = BrandInfo.query.filter_by(name=brand_data['name']).first()
            if not brand:
                brand = BrandInfo(**brand_data)
                db.session.add(brand)
                print(f"[생성] 브랜드: {brand_data['name']}")
            brands.append(brand)
        
        db.session.commit()
        
        # 3. 시연용 게시글 생성
        posts_data = [
            {
                'title': 'Fender Stratocaster 판매합니다 ',
                'brand': 'Fender',
                'model_name': 'Stratocaster Standard',
                'shape': 'Stratocaster',
                'condition': 85,
                'description': '3년 정도 사용한 펜더 스트랫입니다. 관리 잘 했고 큰 흠집 없어요. 소프트 케이스 포함입니다!',
                'price': 85,
                'color': '#E74C3C',
                'image_text': 'Fender\nStrat',
            },
            {
                'title': 'Gibson Les Paul 급매 ',
                'brand': 'Gibson',
                'model_name': 'Les Paul Standard',
                'shape': 'Les Paul',
                'condition': 90,
                'description': '깁슨 레스폴 스탠다드입니다. 거의 새것 수준이고 하드케이스 포함해서 드립니다. 직거래 환영!',
                'price': 250,
                'color': '#8E44AD',
                'image_text': 'Gibson\nLes Paul',
            },
            {
                'title': 'Ibanez RG 시리즈 판매',
                'brand': 'Ibanez',
                'model_name': 'RG350DXZ',
                'shape': 'RG',
                'condition': 75,
                'description': '메탈 연주하기 좋은 아이바네즈 RG입니다. 넥이 얇아서 연주하기 편해요. 사용감 있지만 기능은 완벽합니다.',
                'price': 45,
                'color': '#3498DB',
                'image_text': 'Ibanez\nRG',
            },
            {
                'title': 'Martin 어쿠스틱 기타 팝니다 ',
                'brand': 'Martin',
                'model_name': 'D-28',
                'shape': 'Dreadnought',
                'condition': 95,
                'description': '마틴 D-28 모델입니다. 음색이 정말 좋고 거의 사용 안 해서 상태 최상입니다. 하드케이스 포함!',
                'price': 320,
                'color': '#E67E22',
                'image_text': 'Martin\nD-28',
            },
            {
                'title': 'Yamaha 베이스 기타 판매합니다',
                'brand': 'Yamaha',
                'model_name': 'TRBX304',
                'shape': 'Bass',
                'condition': 80,
                'description': '야마하 베이스 기타입니다. 초보자부터 중급자까지 사용하기 좋은 모델이에요. 깨끗하게 관리했습니다.',
                'price': 52,
                'color': '#1ABC9C',
                'image_text': 'Yamaha\nBass',
            },
            {
                'title': 'Fender Telecaster 빈티지 스타일 ',
                'brand': 'Fender',
                'model_name': 'Telecaster Classic',
                'shape': 'Telecaster',
                'condition': 88,
                'description': '빈티지 스타일의 텔레캐스터입니다. 컨트리, 블루스 연주에 최적화되어 있어요. 사운드 정말 좋습니다!',
                'price': 95,
                'color': '#F39C12',
                'image_text': 'Fender\nTele',
            },
            {
                'title': 'Ibanez 어쿠스틱 기타 초보용',
                'brand': 'Ibanez',
                'model_name': 'AW54',
                'shape': 'Dreadnought',
                'condition': 70,
                'description': '초보자 연습용으로 좋은 아이바네즈 어쿠스틱입니다. 가격도 저렴하고 연주하기 편해요.',
                'price': 18,
                'color': '#16A085',
                'image_text': 'Ibanez\nAcoustic',
            },
            {
                'title': 'Gibson SG 모델 판매 ',
                'brand': 'Gibson',
                'model_name': 'SG Standard',
                'shape': 'SG',
                'condition': 82,
                'description': '깁슨 SG 스탠다드입니다. 가볍고 연주하기 편한 모델이에요. 락 사운드 최고입니다!',
                'price': 180,
                'color': '#C0392B',
                'image_text': 'Gibson\nSG',
            },
        ]
        
        # 게시글 생성
        created_posts = []
        for i, post_data in enumerate(posts_data):
            # 이미지 생성
            image_filename = f"demo_guitar_{i+1}.jpg"
            create_placeholder_image(
                image_filename,
                post_data['color'],
                post_data['image_text']
            )
            
            # 브랜드 찾기
            brand = BrandInfo.query.filter_by(name=post_data['brand']).first()
            
            # 게시글 생성
            post = InstrumentPost(
                title=post_data['title'],
                brand_id=brand.id if brand else None,
                model_name=post_data['model_name'],
                shape=post_data['shape'],
                condition=post_data['condition'],
                description=post_data['description'],
                price=post_data['price'],
                user_id=users[i % len(users)].id,
                images=[image_filename],
                views=random.randint(10, 150),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                status='available'
            )
            db.session.add(post)
            created_posts.append(post)
            print(f"[생성] 게시글: {post_data['title']}")
        
        db.session.commit()
        
        # 4. 댓글 추가
        comments_data = [
            "이거 상태 좋아보이네요! 직거래 가능할까요?",
            "가격 네고 가능한가요?",
            "와 이거 정말 갖고 싶네요 ㅠㅠ",
            "사진 더 보여주실 수 있나요?",
            "연락 드렸습니다!",
            "멋진 기타네요 👍",
            "아직 판매 중이신가요?",
            "케이스 포함인가요?",
        ]
        
        for post in created_posts[:5]:  # 처음 5개 게시글에만 댓글
            for _ in range(random.randint(1, 3)):
                comment = Comment(
                    content=random.choice(comments_data),
                    user_id=random.choice(users).id,
                    post_id=post.id,
                    created_at=post.created_at + timedelta(hours=random.randint(1, 48))
                )
                db.session.add(comment)
        
        db.session.commit()
        
        # 5. 좋아요 추가
        for post in created_posts:
            for _ in range(random.randint(2, 8)):
                user = random.choice(users)
                existing_like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()
                if not existing_like:
                    like = Like(user_id=user.id, post_id=post.id)
                    db.session.add(like)
        
        db.session.commit()
        
        print(f"\n✅ 시연용 데이터 생성 완료!")
        print(f"   - 사용자: {len(users)}명")
        print(f"   - 브랜드: {len(brands)}개")
        print(f"   - 게시글: {len(created_posts)}개")
        print(f"   - 이미지: {len(created_posts)}개")
        print(f"\nSNS 탭에서 확인해보세요!")


if __name__ == '__main__':
    add_demo_data()
