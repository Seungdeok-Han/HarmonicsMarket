from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import datetime
import requests
import csv
from functools import lru_cache
import json
import google.generativeai as genai
from app.models import Comment, db
from . import db, socketio
from .models import InstrumentPost, BrandInfo, GenreTag, Like, MyInstrument, User, Message, Notification, Follow, PracticeRecommendation, PracticeSong, PracticeTechnique, PracticeLog
from flask_socketio import emit, join_room, leave_room, rooms


YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

main = Blueprint('main', __name__)

# --- Simple file-backed SNS storage (MVP) ---
SNS_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sns_posts.json'))

def read_sns_posts():
    try:
        with open(SNS_DATA_PATH, 'r', encoding='utf-8') as f:
            posts = json.load(f)
            # ensure descending by created_at
            posts.sort(key=lambda p: p.get('created_at', ''), reverse=True)
            return posts
    except Exception:
        return []

def write_sns_posts(posts):
    try:
        with open(SNS_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('SNS write error:', e)


@main.route('/')
def index():
    selected_brand_id = request.args.get('brand', type=int)
    search_query = request.args.get('q', '').strip()
    sort = request.args.get('sort', '')
    selected_shape = request.args.get('shape', '').strip()
    selected_condition = request.args.get('condition', '').strip()
    author_id = request.args.get('author_id', type=int)  # filter by author posts if provided

    query = InstrumentPost.query

    if selected_brand_id:
        query = query.filter_by(brand_id=selected_brand_id)
    if search_query:
        query = query.filter(
            InstrumentPost.title.ilike(f'%{search_query}%') |
            InstrumentPost.model_name.ilike(f'%{search_query}%')
        )
    if selected_shape:
        query = query.filter_by(shape=selected_shape)
    if selected_condition == '80up':
        query = query.filter(InstrumentPost.condition >= 80)
    elif selected_condition == '60up':
        query = query.filter(InstrumentPost.condition >= 60, InstrumentPost.condition < 80)
    elif selected_condition == '40up':
        query = query.filter(InstrumentPost.condition >= 40, InstrumentPost.condition < 60)
    elif selected_condition == 'under40':
        query = query.filter(InstrumentPost.condition < 40)

    if sort == 'views_desc':
        query = query.order_by(InstrumentPost.views.desc())
    elif sort == 'views_asc':
        query = query.order_by(InstrumentPost.views.asc())
    elif sort == 'price_desc':
        query = query.order_by(InstrumentPost.price.desc())
    elif sort == 'price_asc':
        query = query.order_by(InstrumentPost.price.asc())
    elif sort == 'condition_best':
        # 손상도: 최상 > 양호 > 사용감 있음 > 수리 필요 (내림차순)
        condition_order = ['최상', '양호', '사용감 있음', '수리 필요']
        query = query.order_by(db.case(
            {v: i for i, v in enumerate(condition_order)},
            value=InstrumentPost.condition
        ))
    elif sort == 'condition_worst':
        # 손상도: 수리 필요 > 사용감 있음 > 양호 > 최상 (내림차순)
        condition_order = ['수리 필요', '사용감 있음', '양호', '최상']
        query = query.order_by(db.case(
            {v: i for i, v in enumerate(condition_order)},
            value=InstrumentPost.condition
        ))
    elif sort == 'shape_asc':
        query = query.order_by(InstrumentPost.shape.asc())
    elif sort == 'shape_desc':
        query = query.order_by(InstrumentPost.shape.desc())
    else:
        query = query.order_by(InstrumentPost.created_at.desc())  # 기본 정렬

    # --- 장르별 필터 robust하게 수정 ---
    all_genre_tags = GenreTag.query.all()
    genre_set = set()
    for gt in all_genre_tags:
        for g in gt.genres.split(','):
            genre_set.add(g.strip())
    all_genres = sorted([g for g in genre_set if g])

    # robust 장르 필터: brand/model_name이 모두 빈 문자열인 경우(즉, 전체 브랜드/모델에 대한 장르)도 포함
    selected_genres = request.args.getlist('genres')
    if selected_genres:
        genre_tag_matches = GenreTag.query.filter(
            db.or_(*[GenreTag.genres.ilike(f"%{g}%") for g in selected_genres])
        ).all()
        # (brand, model_name) 쌍 중 model_name이 빈 문자열이면 해당 브랜드 전체 허용
        brand_model_pairs = set((gt.brand, gt.model_name) for gt in genre_tag_matches)
        query = query.join(BrandInfo, InstrumentPost.brand_id == BrandInfo.id)
        # 조건: (브랜드명, 모델명) 완전일치 or (브랜드명 일치 & model_name=="")
        query = query.filter(
            db.or_(*[
                db.and_(BrandInfo.name == brand, (InstrumentPost.model_name == model if model else True))
                for (brand, model) in brand_model_pairs
            ])
        )

    # filter by author if requested
    if author_id:
        query = query.filter(InstrumentPost.user_id == author_id)

    page = request.args.get('page', 1, type=int)
    per_page = 8  # 한 페이지에 8개씩
    posts_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    all_brands = BrandInfo.query.all()

    args = request.args.to_dict()
    args.pop('page', None)

    return render_template('index.html', posts=posts_paginated.items, posts_paginated=posts_paginated, all_brands=all_brands,
                           selected_brand_id=selected_brand_id,
                           search_query=search_query,
                           sort=sort,
                           selected_shape=selected_shape,
                           selected_condition=selected_condition,
                           all_genres=all_genres,
                           selected_genres=selected_genres,
                           args=args)

@main.route('/add', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        brand_id = request.form['brand_id']
        model_name = request.form['model_name']
        shape = request.form['shape']
        condition = request.form['condition']
        price = request.form['price']
        description = request.form['description']

        # 기타(직접입력) 처리
        custom_brand = request.form.get('custom_brand')
        if brand_id == 'custom' and custom_brand:
            brand = BrandInfo.query.filter_by(name=custom_brand).first()
            if not brand:
                brand = BrandInfo(name=custom_brand)
                db.session.add(brand)
                db.session.commit()
            brand_id = brand.id
        else:
            # brand_id가 실제로는 브랜드 이름(문자열)일 수 있으므로 변환
            if not brand_id.isdigit():
                brand_obj = BrandInfo.query.filter_by(name=brand_id).first()
                if brand_obj:
                    brand_id = brand_obj.id
                else:
                    # 없는 브랜드면 예외 처리
                    flash('선택한 브랜드가 존재하지 않습니다.', 'danger')
                    return redirect(url_for('main.add_post'))
            else:
                brand_id = int(brand_id)

        images = request.files.getlist('images[]')
        image_filenames = []

        for image in images:
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(current_app.root_path, 'static/uploads', filename))
                image_filenames.append(filename)

        new_post = InstrumentPost(
            title=title,
            brand_id=int(brand_id),
            model_name=model_name,
            shape=shape,
            condition=condition,
            description=description,
            price=price,
            user_id=current_user.id,
            images=image_filenames,
            status='available'  # 거래 가능으로 기본값
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('main.index'))

    # BrandInfo DB에 있는 모든 브랜드를 알파벳순으로 가져옴 (id, name, description 모두)
    brands = BrandInfo.query.order_by(BrandInfo.name).all()
    return render_template('add.html', brands=brands)

@main.route('/api/info/<string:category>/<int:id>')
def get_info(category, id):
    if category == 'brand':
        brand = BrandInfo.query.get_or_404(id)
        return jsonify({
            'title': brand.name,
            'description': brand.description or '정보 없음'
        })
    return jsonify({'error': 'invalid category'}), 400

@main.route('/api/info/brand/<int:brand_id>')
def brand_info(brand_id):
    brand = BrandInfo.query.get_or_404(brand_id)
    return jsonify({
        "title": brand.name,
        "description": brand.description or "정보 없음"
    })


@main.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = InstrumentPost.query.get_or_404(post_id)

    # 작성자인지 확인
    if post.user_id != current_user.id:
        flash('삭제 권한이 없습니다.', 'danger')
        return redirect(url_for('main.index'))

    # 댓글도 함께 삭제
    Comment.query.filter_by(post_id=post_id).delete()
    db.session.delete(post)
    db.session.commit()
    flash('글이 삭제되었습니다.', 'success')
    return redirect(url_for('main.index'))

@main.route('/post/<int:post_id>', methods=['GET'])
def view_post(post_id):
    post = InstrumentPost.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id, parent_id=None).order_by(Comment.created_at.asc()).all()
    for comment in comments:
        comment.replies_list = comment.replies.order_by(Comment.created_at.asc()).all()

    from_like = request.args.get("from_like")
    if not from_like:
        post.views = (post.views or 0) + 1
        db.session.commit()

    youtube_query = ""
    if post.brand and post.brand.name:
        youtube_query += post.brand.name
    if post.model_name:
        youtube_query += f" {post.model_name}"
    youtube_links = search_youtube_videos(youtube_query.strip())

    liked = current_user.is_authenticated and any(like.user_id == current_user.id for like in post.likes)

    genre_tags = None
    genre_obj = None
    if post.brand and post.model_name:
        genre_obj = GenreTag.query.filter_by(brand=post.brand.name, model_name=post.model_name).first()
    if genre_obj:
        genre_tags = genre_obj.genres.split(',')
    else:
        if post.brand:
            brand_genre_obj = GenreTag.query.filter_by(brand=post.brand.name, model_name="").first()
            if brand_genre_obj:
                genre_tags = brand_genre_obj.genres.split(',')
            else:
                genre_tags = None
        else:
            genre_tags = None

    similar_query = InstrumentPost.query.filter(InstrumentPost.id != post.id)
    if post.brand_id:
        similar_query = similar_query.filter_by(brand_id=post.brand_id)
    if post.shape:
        similar_query = similar_query.filter_by(shape=post.shape)
    if genre_tags:
        genre_like = [GenreTag.genres.ilike(f"%{g.strip()}%") for g in genre_tags]
        genre_post_ids = [gt.id for gt in GenreTag.query.filter(db.or_(*genre_like)).all()]
        similar_query = similar_query.filter(InstrumentPost.id.in_(genre_post_ids))
    similar_posts = similar_query.order_by(db.func.random()).limit(4).all()

    # 모델별 famous_users 전달
    famous_users_for_model = None
    if post.brand and post.model_name:
        famous_users_map = get_model_famous_users()
        famous_users_for_model = famous_users_map.get((post.brand.name, post.model_name))

    return render_template(
        'view_post.html',
        post=post,
        youtube_links=youtube_links,
        comments=comments,
        liked=liked,
        genre_tags=genre_tags,
        similar_posts=similar_posts,
        famous_users_for_model=famous_users_for_model
    )


@main.route('/user/<int:user_id>')
def user_profile(user_id):
    """사용자 프로필: 중고 거래 글 + SNS 글을 함께 표시"""
    user = User.query.get_or_404(user_id)
    # 중고 거래 글 (InstrumentPost)
    instrument_posts = InstrumentPost.query.filter_by(user_id=user_id).order_by(InstrumentPost.created_at.desc()).all()
    # SNS 글
    sns_posts = read_sns_posts()
    user_sns_posts = [p for p in sns_posts if p.get('user_id') == user_id]
    # friendly time for SNS posts
    now = datetime.datetime.now()
    for p in user_sns_posts:
        try:
            created = datetime.datetime.strptime(p.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            delta = now - created
            if delta.days >= 1:
                p['time_ago'] = f"{delta.days}일 전"
            elif delta.seconds >= 3600:
                p['time_ago'] = f"{delta.seconds//3600}시간 전"
            elif delta.seconds >= 60:
                p['time_ago'] = f"{delta.seconds//60}분 전"
            else:
                p['time_ago'] = "방금"
        except Exception:
            p['time_ago'] = p.get('created_at', '')
        # compute like_count and liked status
        p['like_count'] = len(p.get('likes', []))
        uid = getattr(current_user, 'id', None)
        p['liked'] = uid is not None and uid in p.get('likes', [])
    return render_template('user_profile.html', user=user, instrument_posts=instrument_posts, sns_posts=user_sns_posts)


@main.route('/messages')
@login_required
def messages():
    # list conversation partners for current user
    # get distinct partner ids
    sent = Message.query.with_entities(Message.recipient_id).filter(Message.sender_id==current_user.id)
    received = Message.query.with_entities(Message.sender_id).filter(Message.recipient_id==current_user.id)
    partner_ids = set([r[0] for r in sent.union_all(received).all()])
    partners = []
    for pid in partner_ids:
        user = User.query.get(pid)
        if not user: continue
        last_msg = Message.query.filter(
            ((Message.sender_id==current_user.id) & (Message.recipient_id==pid)) |
            ((Message.sender_id==pid) & (Message.recipient_id==current_user.id))
        ).order_by(Message.created_at.desc()).first()
        unread_count = Message.query.filter_by(sender_id=pid, recipient_id=current_user.id, read_at=None).count()
        partners.append({'user': user, 'last_msg': last_msg, 'unread': unread_count})
    # sort by last message time
    partners.sort(key=lambda p: p['last_msg'].created_at if p['last_msg'] else None, reverse=True)
    return render_template('messages.html', partners=partners)


@main.route('/messages/<int:other_id>', methods=['GET','POST'])
@login_required
def message_user(other_id):
    if other_id == current_user.id:
        flash('자기 자신에게 메시지를 보낼 수 없습니다.', 'warning')
        return redirect(url_for('main.messages'))
    other = User.query.get_or_404(other_id)
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('메시지는 비어 있을 수 없습니다.', 'danger')
            return redirect(url_for('main.message_user', other_id=other_id))
        m = Message(sender_id=current_user.id, recipient_id=other_id, content=content)
        db.session.add(m)
        db.session.commit()
        
        # 메시지 알림 생성
        create_notification(
            user_id=other_id,
            notification_type='message',
            related_user_id=current_user.id
        )
        
        flash('메시지를 보냈습니다.', 'success')
        return redirect(url_for('main.message_user', other_id=other_id))

    # mark unread messages from other as read
    unread = Message.query.filter_by(sender_id=other_id, recipient_id=current_user.id, read_at=None).all()
    now = datetime.datetime.utcnow()
    for u in unread:
        u.read_at = now
    if unread:
        db.session.commit()
        
        # 메시지 관련 알림도 읽음 처리
        Notification.query.filter_by(
            user_id=current_user.id,
            type='message',
            related_user_id=other_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()

    # fetch conversation
    conv = Message.query.filter(
        ((Message.sender_id==current_user.id) & (Message.recipient_id==other_id)) |
        ((Message.sender_id==other_id) & (Message.recipient_id==current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template('conversation.html', other=other, conv=conv)


def search_youtube_videos(query, max_results=2):
    if not YOUTUBE_API_KEY:
        print("⚠️ YouTube API Key가 설정되지 않았습니다!")
        return []
    
    url = "https://www.googleapis.com/youtube/v3/search"
    
    params = {
        "part": "snippet",
        "q": f"{query} guitar tone review demo",
        "type": "video",
        "key": YOUTUBE_API_KEY,
        "maxResults": max_results
    }
    try:
        print(f"🔍 YouTube 검색 (한국어): {query}")
        response = requests.get(url, params=params, timeout=5)
        print(f"📡 YouTube API 상태 코드: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ YouTube API 에러 응답: {response.text}")
            return []
            
        response.raise_for_status()
        results = response.json().get("items", [])
        print(f"✅ YouTube 검색 결과: {len(results)}개")
        
        if len(results) == 0:
            print(f"🔄 영어로 재검색 시도...")
            params_en = {
                "part": "snippet",
                "q": f"{query} guitar tutorial",
                "type": "video",
                "key": YOUTUBE_API_KEY,
                "maxResults": max_results,
                "relevanceLanguage": "en"
            }
            response_en = requests.get(url, params=params_en, timeout=5)
            if response_en.status_code == 200:
                results = response_en.json().get("items", [])
                print(f"✅ 영어 검색 결과: {len(results)}개")
        
        return [
            f"https://www.youtube.com/embed/{item['id']['videoId']}"
            for item in results if 'id' in item and 'videoId' in item['id']
        ]
    except Exception as e:
        print(f"❌ YouTube API Error: {e}")
        return []


@main.route('/sns')
def sns_feed():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    all_posts = read_sns_posts()
    now = datetime.datetime.now()
    for p in all_posts:
        likes = p.get('likes', [])
        p['like_count'] = len(likes)
        uid = getattr(current_user, 'id', None)
        p['liked'] = uid is not None and uid in likes
        try:
            created = datetime.datetime.strptime(p.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            delta = now - created
            if delta.days >= 1:
                p['time_ago'] = f"{delta.days}일 전"
            elif delta.seconds >= 3600:
                p['time_ago'] = f"{delta.seconds//3600}시간 전"
            elif delta.seconds >= 60:
                p['time_ago'] = f"{delta.seconds//60}분 전"
            else:
                p['time_ago'] = "방금"
        except Exception:
            p['time_ago'] = p.get('created_at', '')
    
    start = (page - 1) * per_page
    end = start + per_page
    posts = all_posts[start:end]
    has_more = end < len(all_posts)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'posts': posts,
            'has_more': has_more,
            'next_page': page + 1
        })
    
    return render_template('sns.html', posts=posts, has_more=has_more)


@main.route('/user/summary/<int:user_id>')
def user_summary(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error':'not found'}), 404
    # instruments (up to 4)
    total_instruments = MyInstrument.query.filter_by(user_id=user_id).count()
    # 대표 악기를 우선으로 정렬
    my_instruments = MyInstrument.query.filter_by(user_id=user_id).order_by(MyInstrument.is_featured.desc(), MyInstrument.id.desc()).limit(4).all()
    instruments = [
        {
            'brand': mi.brand,
            'model': mi.model_name,
            'img': (mi.images[0] if mi.images else None),
            'is_featured': bool(getattr(mi, 'is_featured', False))
        }
        for mi in my_instruments
    ]
    # posts count
    posts_count = InstrumentPost.query.filter_by(user_id=user_id).count()
    # sns posts count
    sns_posts = read_sns_posts()
    sns_count = sum(1 for p in sns_posts if p.get('user_id') == user_id)
    # recent posts (both instrument + sns) - latest 5
    recent_items = []
    recent_instrument = InstrumentPost.query.filter_by(user_id=user_id).order_by(InstrumentPost.created_at.desc()).limit(5).all()
    for p in recent_instrument:
        ts = p.created_at.timestamp() if getattr(p, 'created_at', None) else 0
        recent_items.append({
            'title': p.title,
            'url': url_for('main.view_post', post_id=p.id),
            'ts': ts
        })
    for sp in sns_posts:
        if sp.get('user_id') == user_id:
            try:
                ts = datetime.datetime.strptime(sp.get('created_at', ''), '%Y-%m-%d %H:%M:%S').timestamp()
            except Exception:
                ts = 0
            title = sp.get('caption') or '(무제)'
            recent_items.append({
                'title': title,
                'url': url_for('main.sns_feed') + f"?post_id={sp.get('id')}",
                'ts': ts
            })
    recent_items.sort(key=lambda x: x['ts'], reverse=True)
    recent_posts = []
    for item in recent_items[:5]:
        title = item['title'] or ''
        if len(title) > 60:
            title = title[:60] + '…'
        recent_posts.append({'title': title, 'url': item['url']})
    return jsonify({
        'id': user.id,
        'username': user.username,
        'instruments': instruments,
        'instrument_count': total_instruments,
        'posts_count': posts_count,
        'sns_count': sns_count,
        'recent_posts': recent_posts
    })


@main.route('/sns/create', methods=['GET', 'POST'])
@login_required
def sns_create():
    if request.method == 'POST':
        caption = request.form.get('caption', '').strip()
        # Support multiple files (images/videos) from split inputs; fallback to 'media'
        files_images = request.files.getlist('images') or []
        files_videos = request.files.getlist('videos') or []
        fallback_media = request.files.getlist('media') or []
        files = []
        files.extend(files_images)
        files.extend(files_videos)
        if not files:
            files = fallback_media

        media_list = []
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_path, exist_ok=True)
        for f in files:
            if not f or not getattr(f, 'filename', None):
                continue
            fn = secure_filename(f.filename)
            # Avoid collisions: prepend timestamp
            ts_prefix = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            safe_name = f"{ts_prefix}_{fn}"
            f.save(os.path.join(upload_path, safe_name))
            ext = os.path.splitext(fn)[1].lower()
            mtype = 'video' if ext in {'.mp4', '.mov', '.m4v', '.avi', '.wmv', '.webm', '.mkv'} else 'image'
            media_list.append({'type': mtype, 'filename': safe_name})

        posts = read_sns_posts()
        new_id = (max([p.get('id', 0) for p in posts]) + 1) if posts else 1
        new_post = {
            'id': new_id,
            'username': getattr(current_user, 'username', '익명'),
            'user_id': getattr(current_user, 'id', None),
            # Back-compat: keep 'image' for modal preview (first image if any)
            'image': next((m['filename'] for m in media_list if m.get('type') == 'image'), ''),
            'media': media_list,
            'caption': caption,
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'likes': [],
            'comments': []
        }
        posts.insert(0, new_post)
        write_sns_posts(posts)
        flash('게시물이 업로드되었습니다.', 'success')
        return redirect(url_for('main.sns_feed'))
    return render_template('sns_create.html')


@main.route('/sns/like/<int:post_id>', methods=['POST'])
@login_required
def sns_like(post_id):
    posts = read_sns_posts()
    for p in posts:
        if p.get('id') == post_id:
            likes = p.get('likes', [])
            uid = getattr(current_user, 'id', None)
            if uid is None:
                return jsonify({'error': 'not logged in'}), 401
            if uid in likes:
                likes.remove(uid)
                liked = False
            else:
                likes.append(uid)
                liked = True
                # SNS 글 작성자에게 좋아요 알림 생성
                post_user_id = p.get('user_id')
                if post_user_id and post_user_id != uid:
                    create_notification(post_user_id, 'sns_like', related_user_id=uid, post_id=-post_id)  # 음수로 SNS 구분
            p['likes'] = likes
            write_sns_posts(posts)
            return jsonify({'like_count': len(likes), 'liked': liked})
    return jsonify({'error': 'not found'}), 404


@main.route('/sns/<int:post_id>')
def sns_post_detail(post_id):
    posts = read_sns_posts()
    for p in posts:
        if p.get('id') == post_id:
            # ensure comments exist
            p['comments'] = p.get('comments', [])
            # compute friendly time for post and comments
            now = datetime.datetime.now()
            try:
                created = datetime.datetime.strptime(p.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
                delta = now - created
                if delta.days >= 1:
                    p['time_ago'] = f"{delta.days}일 전"
                elif delta.seconds >= 3600:
                    p['time_ago'] = f"{delta.seconds//3600}시간 전"
                elif delta.seconds >= 60:
                    p['time_ago'] = f"{delta.seconds//60}분 전"
                else:
                    p['time_ago'] = "방금"
            except Exception:
                p['time_ago'] = p.get('created_at', '')

            for c in p['comments']:
                try:
                    c_created = datetime.datetime.strptime(c.get('created_at',''), '%Y-%m-%d %H:%M:%S')
                    d = now - c_created
                    if d.days >= 1:
                        c['time_ago'] = f"{d.days}일 전"
                    elif d.seconds >= 3600:
                        c['time_ago'] = f"{d.seconds//3600}시간 전"
                    elif d.seconds >= 60:
                        c['time_ago'] = f"{d.seconds//60}분 전"
                    else:
                        c['time_ago'] = "방금"
                except Exception:
                    c['time_ago'] = c.get('created_at','')
            return jsonify(p)
    return jsonify({'error':'not found'}), 404


@main.route('/sns/<int:post_id>/comment', methods=['POST'])
@login_required
def sns_add_comment(post_id):
    """Add a comment or reply. Accepts JSON: {content: str, parent_id: optional int} """
    data = request.get_json() or {}
    content = data.get('content','').strip()
    parent_id = data.get('parent_id')
    if not content:
        return jsonify({'error':'no content'}), 400
    posts = read_sns_posts()
    for p in posts:
        if p.get('id') == post_id:
            comments = p.get('comments', [])
            new_id = (max([c.get('id',0) for c in comments])+1) if comments else 1
            comment = {
                'id': new_id,
                'user_id': current_user.id,
                'username': getattr(current_user, 'username','익명'),
                'content': content,
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parent_id': parent_id,
                'likes': []
            }
            comments.append(comment)
            p['comments'] = comments
            write_sns_posts(posts)
            
            # 댓글 알림 생성 (글 작성자에게)
            post_user_id = p.get('user_id')
            if post_user_id and post_user_id != current_user.id:
                create_notification(post_user_id, 'comment', related_user_id=current_user.id, post_id=-post_id, comment_id=new_id)
            
            comment['time_ago'] = '방금'
            return jsonify(comment), 201
    return jsonify({'error':'not found'}), 404


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/edit', methods=['POST'])
@login_required
def sns_edit_comment(post_id, comment_id):
    data = request.get_json() or {}
    content = data.get('content','').strip()
    if not content:
        return jsonify({'error':'no content'}), 400
    posts = read_sns_posts()
    for p in posts:
        if p.get('id') == post_id:
            for c in p.get('comments', []):
                if c.get('id') == comment_id:
                    if c.get('user_id') != current_user.id:
                        return jsonify({'error':'forbidden'}), 403
                    c['content'] = content
                    c['edited_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    write_sns_posts(posts)
                    return jsonify(c)
            return jsonify({'error':'comment not found'}), 404
    return jsonify({'error':'post not found'}), 404


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def sns_delete_comment(post_id, comment_id):
    posts = read_sns_posts()
    for p in posts:
        if p.get('id') == post_id:
            comments = p.get('comments', [])
            # find comment
            target = None
            for c in comments:
                if c.get('id') == comment_id:
                    target = c
                    break
            if not target:
                return jsonify({'error':'comment not found'}), 404
            if target.get('user_id') != current_user.id:
                return jsonify({'error':'forbidden'}), 403
            # delete target and any replies recursively
            def delete_recursive(cid):
                nonlocal comments
                to_delete = [c for c in comments if c.get('id') == cid]
                for td in to_delete:
                    comments = [c for c in comments if c.get('id') != td.get('id')]
                    # find replies
                    replies = [c for c in list(comments) if c.get('parent_id') == td.get('id')]
                    for r in replies:
                        delete_recursive(r.get('id'))
            delete_recursive(comment_id)
            p['comments'] = comments
            write_sns_posts(posts)
            return jsonify({'success':True})
    return jsonify({'error':'post not found'}), 404


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def sns_like_comment(post_id, comment_id):
    posts = read_sns_posts()
    uid = getattr(current_user, 'id', None)
    for p in posts:
        if p.get('id') == post_id:
            for c in p.get('comments', []):
                if c.get('id') == comment_id:
                    likes = c.get('likes', [])
                    if uid in likes:
                        likes.remove(uid)
                        liked = False
                    else:
                        likes.append(uid)
                        liked = True
                        # 댓글 작성자에게 좋아요 알림 생성
                        comment_user_id = c.get('user_id')
                        if comment_user_id and comment_user_id != uid:
                            create_notification(comment_user_id, 'comment_like', related_user_id=uid, post_id=-post_id, comment_id=comment_id)
                    c['likes'] = likes
                    write_sns_posts(posts)
                    return jsonify({'like_count': len(likes), 'liked': liked})
            return jsonify({'error':'comment not found'}), 404
    return jsonify({'error':'post not found'}), 404

from flask import jsonify

@main.route('/like/<int:post_id>', methods=['POST'])
@login_required
def toggle_like(post_id):
    post = InstrumentPost.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first()
    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        db.session.add(Like(post_id=post.id, user_id=current_user.id))
        liked = True
    db.session.commit()
    return jsonify(liked=liked, like_count=len(post.likes))

@main.route('/sns/<int:post_id>/delete', methods=['POST'])
@login_required
def sns_delete_post(post_id):
    """SNS 게시물을 삭제합니다. 작성자만 삭제 가능하며, 업로드된 미디어 파일도 함께 제거합니다."""
    posts = read_sns_posts()
    target = None
    for p in posts:
        if p.get('id') == post_id:
            target = p
            break
    if not target:
        return jsonify({'error': 'not found'}), 404
    # 권한 확인
    if target.get('user_id') != getattr(current_user, 'id', None):
        return jsonify({'error': 'forbidden'}), 403
    # 업로드된 파일 제거 (가능하면)
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
    media = target.get('media') or []
    for m in media:
        fn = m.get('filename')
        if fn:
            fp = os.path.join(upload_path, fn)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass
    legacy_img = target.get('image')
    if legacy_img:
        fp = os.path.join(upload_path, legacy_img)
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except Exception:
                pass
    # 데이터에서 삭제 후 저장
    posts = [p for p in posts if p.get('id') != post_id]
    write_sns_posts(posts)
    return jsonify({'success': True})

@main.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify(success=False), 400
    comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    return jsonify(
        success=True,
        comment_id=comment.id,
        username=current_user.username,
        timestamp=comment.created_at.strftime('%Y-%m-%d %H:%M'),
        content=comment.content,
        can_delete=(current_user.id == comment.user_id)
    )

@main.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'success': False}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({'success': True})


@main.route('/mypage', methods=['GET', 'POST'])
@login_required
def mypage():
    if request.method == 'POST':
        brand = request.form['brand']
        model_name = request.form['model_name']
        description = request.form.get('description', '')
        images = request.files.getlist('images[]')
        image_filenames = []
        for image in images:
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(current_app.root_path, 'static/uploads', filename))
                image_filenames.append(filename)
        my_instrument = MyInstrument(
            user_id=current_user.id,
            brand=brand,
            model_name=model_name,
            images=image_filenames,
            description=description
        )
        db.session.add(my_instrument)
        db.session.commit()
        flash('내 악기가 등록되었습니다!', 'success')
        return redirect(url_for('main.mypage', tab='gear'))
    my_instruments = MyInstrument.query.filter_by(user_id=current_user.id).all()
    # 브랜드 목록 전달
    brands = BrandInfo.query.order_by(BrandInfo.name).all()
    # 좋아요한 글, 내가 쓴 글도 함께 전달
    my_posts = InstrumentPost.query.filter_by(user_id=current_user.id).all()
    liked_posts = []
    if hasattr(current_user, 'likes'):
        liked_posts = [like.post for like in current_user.likes]
    # SNS 글 (내가 쓴 글)
    sns_posts = read_sns_posts()
    my_sns_posts = [p for p in sns_posts if p.get('user_id') == current_user.id]
    # friendly time for SNS posts
    now = datetime.datetime.now()
    for p in my_sns_posts:
        try:
            created = datetime.datetime.strptime(p.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            delta = now - created
            if delta.days >= 1:
                p['time_ago'] = f"{delta.days}일 전"
            elif delta.seconds >= 3600:
                p['time_ago'] = f"{delta.seconds//3600}시간 전"
            elif delta.seconds >= 60:
                p['time_ago'] = f"{delta.seconds//60}분 전"
            else:
                p['time_ago'] = "방금"
        except Exception:
            p['time_ago'] = p.get('created_at', '')
    return render_template('mypage.html', my_instruments=my_instruments, brands=brands, my_posts=my_posts, liked_posts=liked_posts, my_sns_posts=my_sns_posts)

@main.route('/mypage/delete/<int:instrument_id>', methods=['POST'])
@login_required
def delete_my_instrument(instrument_id):
    instrument = MyInstrument.query.get_or_404(instrument_id)
    if instrument.user_id != current_user.id:
        flash('삭제 권한이 없습니다.', 'danger')
        return redirect(url_for('main.mypage'))
    db.session.delete(instrument)
    db.session.commit()
    flash('내 악기가 삭제되었습니다.', 'success')
    return redirect(url_for('main.mypage', tab='gear'))

@main.route('/mypage/instrument/<int:instrument_id>/feature', methods=['POST'])
@login_required
def feature_my_instrument(instrument_id):
    instrument = MyInstrument.query.get_or_404(instrument_id)
    if instrument.user_id != current_user.id:
        flash('대표 지정 권한이 없습니다.', 'danger')
        return redirect(url_for('main.mypage'))
    # 같은 사용자 악기들의 대표 표시 초기화
    MyInstrument.query.filter_by(user_id=current_user.id, is_featured=True).update({MyInstrument.is_featured: False})
    instrument.is_featured = True
    db.session.commit()
    flash('대표 악기로 설정되었습니다.', 'success')
    return redirect(url_for('main.mypage', tab='gear'))

@main.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = InstrumentPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('수정 권한이 없습니다.', 'danger')
        return redirect(url_for('main.view_post', post_id=post_id))
    if request.method == 'POST':
        post.title = request.form['title']
        post.brand_id = int(request.form['brand_id']) if request.form['brand_id'] != 'custom' else post.brand_id
        post.model_name = request.form['model_name']
        post.shape = request.form['shape']
        post.condition = request.form['condition']
        post.price = request.form['price']
        post.description = request.form['description']
        post.status = request.form['status']  # 거래 상태 수정
        db.session.commit()
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('main.view_post', post_id=post.id))
    brands = BrandInfo.query.order_by(BrandInfo.name).all()
    return render_template('edit_post.html', post=post, brands=brands)

@main.route('/api/price_history', methods=['GET'])
def price_history():
    brand_id = request.args.get('brand_id', type=int)
    model_name = request.args.get('model_name', '').strip()
    if not brand_id or not model_name:
        return jsonify({'error': '브랜드와 모델명을 입력하세요.'}), 400
    # 거래 완료된 동일 모델의 최근 거래가(최대 20개, 최신순)
    posts = InstrumentPost.query.filter_by(brand_id=brand_id, model_name=model_name, status='sold').order_by(InstrumentPost.created_at.desc()).limit(20).all()
    if not posts:
        return jsonify({'labels': [], 'prices': []})
    labels = [p.created_at.strftime('%Y-%m-%d') for p in posts][::-1]
    prices = [float(p.price) for p in posts][::-1]
    return jsonify({'labels': labels, 'prices': prices})

@main.route('/api/models_by_brand', methods=['GET'])
def models_by_brand():
    brand = request.args.get('brand', '').strip()
    if not brand:
        return jsonify({'models': []})
    csv_path = os.path.join(current_app.root_path, 'GuitarModels.csv')
    models = []
    try:
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                maker = row.get('Maker', '').strip().lower()
                if maker == brand.lower():
                    model = row.get('Model', '').strip()
                    if model:
                        models.append(model)
    except Exception as e:
        print('CSV read error:', e)
        return jsonify({'models': []})
    return jsonify({'models': models})

def get_model_famous_users():
    famous_users_map = {}
    with open(os.path.join(os.path.dirname(__file__), 'GuitarModels.csv'), encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = row.get('Maker', '').strip()
            model = row.get('Model', '').strip()
            users = [row.get('NotableUser1', '').strip(), row.get('NotableUser2', '').strip(), row.get('NotableUser3', '').strip()]
            users = [u for u in users if u]
            if brand and model and users:
                famous_users_map[(brand, model)] = ', '.join(users)
    return famous_users_map

# ===== 알림 시스템 =====
@main.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """사용자의 알림 목록 조회 (미읽 우선)"""
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.is_read.asc(), Notification.created_at.desc()
    ).all()
    result = []
    for n in notifications:
        item = {
            'id': n.id,
            'type': n.type,
            'related_user_id': n.related_user_id,
            'related_username': n.related_user.username if n.related_user else '알수없음',
            'post_id': n.post_id,
            'comment_id': n.comment_id,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        result.append(item)
    return jsonify(result)

@main.route('/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_notification_count():
    """미읽 알림 개수 조회"""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})

@main.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """알림을 읽음으로 표시"""
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

def create_notification(user_id, notification_type, related_user_id=None, post_id=None, comment_id=None):
    """알림 생성 헬퍼"""
    if user_id == related_user_id:  # 자신에게는 알림 안함
        return
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        related_user_id=related_user_id,
        post_id=post_id,
        comment_id=comment_id
    )
    db.session.add(notification)
    db.session.commit()

# ===== 팔로우 시스템 =====
@main.route('/user/<int:user_id>/follow', methods=['POST'])
@login_required
def follow_user(user_id):
    """사용자 팔로우"""
    if user_id == current_user.id:
        return jsonify({'error': '자신을 팔로우할 수 없습니다'}), 400
    
    target_user = User.query.get_or_404(user_id)
    existing = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'following': False, 'followers_count': target_user.followers.count()})
    else:
        follow = Follow(follower_id=current_user.id, following_id=user_id)
        db.session.add(follow)
        db.session.commit()
        # 팔로우 알림 생성
        create_notification(user_id, 'follow', related_user_id=current_user.id)
        return jsonify({'following': True, 'followers_count': target_user.followers.count()})

@main.route('/user/<int:user_id>/is-following', methods=['GET'])
@login_required
def is_following(user_id):
    """특정 사용자를 팔로우하는지 확인"""
    following = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first() is not None
    user = User.query.get_or_404(user_id)
    return jsonify({
        'following': following,
        'followers_count': user.followers.count(),
        'following_count': user.following.count()
    })

@main.route('/user/<int:user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    """사용자의 팔로워/팔로우 통계"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'followers_count': user.followers.count(),
        'following_count': user.following.count()
    })


# ===== 기타 연습 추천 시스템 =====
@main.route('/guitar-practice', methods=['GET', 'POST'])
@login_required
def guitar_practice():
    """AI 기반 기타 연습 추천"""
    if request.method == 'POST':
        experience = request.form.get('experience')
        genre = request.form.get('genre')
        guitar_type = request.form.get('guitar_type')
        goals = request.form.get('goals', '')
        specific_song = request.form.get('specific_song', '')
        
        try:
            # AI로 추천 받기
            recommendation = get_ai_practice_recommendation(experience, genre, guitar_type, goals, specific_song)
            
            # 각 곡과 주법에 대한 YouTube 영상 검색
            for song in recommendation['songs']:
                query = f"{song['title']} {song['artist']} guitar tutorial"
                song['videos'] = search_youtube_videos(query, max_results=2)
            
            for technique in recommendation['techniques']:
                query = f"{technique['name']} guitar technique tutorial"
                technique['videos'] = search_youtube_videos(query, max_results=2)
            
            return render_template('guitar_practice.html', 
                                 recommendation=recommendation,
                                 experience=experience,
                                 genre=genre,
                                 guitar_type=guitar_type,
                                 goals=goals,
                                 specific_song=specific_song)
        
        except Exception as e:
            print(f"❌ 추천 생성 오류: {e}")
            flash('추천을 생성하는 중 오류가 발생했습니다. 다시 시도해주세요.', 'danger')
            return redirect(url_for('main.guitar_practice'))
    
    return render_template('guitar_practice.html')


def get_ai_practice_recommendation(experience, genre, guitar_type, goals, specific_song=''):
    """Gemini를 사용하여 맞춤형 연습 추천"""
    
    # Gemini API 설정
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다")
        raise ValueError("GEMINI_API_KEY가 환경 변수에 설정되지 않았습니다")
    
    genai.configure(api_key=gemini_api_key)
    
    # 특정 곡이 입력되면 장르를 무시하고 해당 곡만 추천
    if specific_song:
        genre_info = f"특정 곡: {specific_song} (이 곡만 연습하고 싶어함)"
        songs_count = "1개 (입력한 곡만)"
    else:
        genre_info = f"선호 장르: {genre}"
        songs_count = "3개"
    
    prompt = f"""
당신은 전문 기타 강사입니다. 다음 학생에게 맞춤형 연습 계획을 추천해주세요:

- 기타 경력: {experience}
- {genre_info}
- 기타 종류: {guitar_type}
- 연습 목표: {goals if goals else '없음'}

다음 형식의 JSON으로만 답변해주세요 (다른 설명 없이):
{{
  "songs": [
    {{
      "title": "곡 제목",
      "artist": "아티스트",
      "difficulty": "초급/중급/고급",
      "reason": "이 곡을 추천하는 이유 (1-2문장)"
    }}
  ],
  "techniques": [
    {{
      "name": "주법 이름",
      "description": "주법 설명 (2-3문장)",
      "practice_time": "하루 권장 연습 시간"
    }}
  ],
  "tips": [
    "연습 팁 1",
    "연습 팁 2",
    "연습 팁 3"
  ]
}}

- songs는 {songs_count} 추천

- techniques는 3-4개 추천
- 학생의 실력에 맞는 곡과 주법을 추천하되, 약간의 도전 과제도 포함
- 한국어로 답변
"""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        # 응답 텍스트에서 JSON 추출
        text = response.text.strip()
        # ```json ``` 마크다운 제거
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:].strip()
        
        result = json.loads(text)
        print(f"✅ Gemini AI 추천 생성 완료")
        return result
    
    except Exception as e:
        print(f"❌ Gemini API 오류: {e}")
        # 폴백: 기본 추천
        return {
            "songs": [
                {
                    "title": "호텔 캘리포니아",
                    "artist": "Eagles",
                    "difficulty": "중급",
                    "reason": "기타 연주의 기초를 모두 담고 있는 명곡입니다."
                }
            ],
            "techniques": [
                {
                    "name": "핑거링 연습",
                    "description": "손가락의 독립성을 키우는 기본 테크닉입니다.",
                    "practice_time": "하루 15분"
                }
            ],
            "tips": ["매일 꾸준히 연습하세요", "메트로놈을 활용하세요"]
        }


# ===== 연습 기록 저장/관리 =====
@main.route('/practice/save', methods=['POST'])
@login_required
def save_practice_recommendation():
    """추천 결과 저장"""
    try:
        data = request.get_json()
        
        # PracticeRecommendation 생성
        recommendation = PracticeRecommendation(
            user_id=current_user.id,
            experience=data.get('experience'),
            genre=data.get('genre'),
            guitar_type=data.get('guitar_type'),
            goals=data.get('goals'),
            specific_song=data.get('specific_song'),
            tips=data.get('tips', [])
        )
        db.session.add(recommendation)
        db.session.flush()  # ID 생성
        
        # 곡들 저장
        for song in data.get('songs', []):
            practice_song = PracticeSong(
                recommendation_id=recommendation.id,
                title=song['title'],
                artist=song.get('artist'),
                difficulty=song.get('difficulty'),
                reason=song.get('reason'),
                videos=song.get('videos', [])
            )
            db.session.add(practice_song)
        
        # 주법들 저장
        for technique in data.get('techniques', []):
            practice_technique = PracticeTechnique(
                recommendation_id=recommendation.id,
                name=technique['name'],
                description=technique.get('description'),
                practice_time=technique.get('practice_time'),
                videos=technique.get('videos', [])
            )
            db.session.add(practice_technique)
        
        db.session.commit()
        return jsonify({'success': True, 'id': recommendation.id})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 추천 저장 오류: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/practice/my-list')
@login_required
def my_practice_list():
    """내 연습 기록 목록"""
    recommendations = PracticeRecommendation.query.filter_by(user_id=current_user.id)\
        .order_by(PracticeRecommendation.created_at.desc()).all()
    return render_template('my_practice_list.html', recommendations=recommendations)


@main.route('/practice/detail/<int:rec_id>')
@login_required
def practice_detail(rec_id):
    """저장된 추천 상세보기"""
    recommendation = PracticeRecommendation.query.get_or_404(rec_id)
    
    if recommendation.user_id != current_user.id:
        flash('접근 권한이 없습니다.', 'danger')
        return redirect(url_for('main.my_practice_list'))
    
    songs = recommendation.songs.all()
    techniques = recommendation.techniques.all()
    
    return render_template('practice_detail.html', 
                         recommendation=recommendation,
                         songs=songs,
                         techniques=techniques)


@main.route('/practice/update-status', methods=['POST'])
@login_required
def update_practice_status():
    """진행도 업데이트"""
    try:
        data = request.get_json()
        item_type = data.get('type')  # 'song' or 'technique'
        item_id = data.get('id')
        status = data.get('status')  # not_started, practicing, completed, paused
        
        if item_type == 'song':
            item = PracticeSong.query.get_or_404(item_id)
        else:
            item = PracticeTechnique.query.get_or_404(item_id)
        
        # 권한 확인
        if item.recommendation.user_id != current_user.id:
            return jsonify({'success': False, 'error': '권한 없음'}), 403
        
        item.status = status
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 상태 업데이트 오류: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/practice/delete/<int:rec_id>', methods=['POST'])
@login_required
def delete_practice_recommendation(rec_id):
    """추천 삭제"""
    recommendation = PracticeRecommendation.query.get_or_404(rec_id)
    
    if recommendation.user_id != current_user.id:
        return jsonify({'success': False, 'error': '권한 없음'}), 403
    
    db.session.delete(recommendation)
    db.session.commit()
    
    return jsonify({'success': True})


# ===== 연습 일지 =====
@main.route('/practice/log', methods=['GET', 'POST'])
@login_required
def practice_log():
    """연습 일지 작성/조회"""
    if request.method == 'POST':
        try:
            from datetime import date, datetime as dt
            
            log_date = request.form.get('date')
            if log_date:
                log_date = dt.strptime(log_date, '%Y-%m-%d').date()
            else:
                log_date = date.today()
            
            # 기존 로그가 있으면 업데이트, 없으면 생성
            log = PracticeLog.query.filter_by(user_id=current_user.id, date=log_date).first()
            
            if not log:
                log = PracticeLog(user_id=current_user.id, date=log_date)
                db.session.add(log)
            
            log.duration_minutes = request.form.get('duration_minutes', type=int)
            log.songs_practiced = request.form.get('songs_practiced')
            log.notes = request.form.get('notes')
            
            db.session.commit()
            flash('연습 일지가 저장되었습니다.', 'success')
            return redirect(url_for('main.practice_log'))
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ 일지 저장 오류: {e}")
            flash('일지 저장 중 오류가 발생했습니다.', 'danger')
    
    # 최근 30일 로그 가져오기
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    
    logs = PracticeLog.query.filter(
        PracticeLog.user_id == current_user.id,
        PracticeLog.date >= start_date,
        PracticeLog.date <= end_date
    ).order_by(PracticeLog.date.desc()).all()
    
    # 스트릭 계산 (연속 연습일)
    streak = calculate_practice_streak(current_user.id)
    
    # 총 연습 시간
    total_minutes = db.session.query(db.func.sum(PracticeLog.duration_minutes))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('practice_log.html', 
                         logs=logs, 
                         streak=streak, 
                         total_minutes=total_minutes)


def calculate_practice_streak(user_id):
    """연속 연습일 계산"""
    from datetime import date, timedelta
    
    today = date.today()
    streak = 0
    current_date = today
    
    while True:
        log = PracticeLog.query.filter_by(user_id=user_id, date=current_date).first()
        if log:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
        
        # 최대 365일까지만 확인
        if streak >= 365:
            break
    
    return streak


# ===== 실시간 메시징 시스템 (WebSocket) =====

@socketio.on('connect')
def handle_connect():
    """사용자 연결"""
    if current_user.is_authenticated:
        user_room = f"user_{current_user.id}"
        join_room(user_room)
        print(f"✅ 사용자 {current_user.username}이(가) 연결됨")
        emit('connected', {'data': f'{current_user.username}이(가) 연결되었습니다'})


@socketio.on('disconnect')
def handle_disconnect():
    """사용자 연결 해제"""
    if current_user.is_authenticated:
        user_room = f"user_{current_user.id}"
        leave_room(user_room)
        print(f"❌ 사용자 {current_user.username}이(가) 연결 해제됨")


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
    
    # DB에 메시지 저장
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        created_at=datetime.datetime.utcnow()
    )
    db.session.add(message)
    db.session.commit()
    
    # 메시지 알림 생성
    create_notification(
        user_id=recipient_id,
        notification_type='message',
        related_user_id=current_user.id
    )
    
    # 수신자에게 실시간으로 메시지 전송
    recipient_room = f"user_{recipient_id}"
    emit('new_message', {
        'id': message.id,
        'sender_id': current_user.id,
        'sender_name': current_user.username,
        'content': content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'read_at': None
    }, room=recipient_room)
    
    # 발신자에게도 전송 확인
    emit('message_sent', {
        'id': message.id,
        'recipient_id': recipient_id,
        'content': content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    print(f"💬 메시지 전송: {current_user.username} → {recipient.username}")
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
    
    # 발신자에게 읽음 상태 알림
    sender_room = f"user_{sender_id}"
    emit('message_read', {
        'message_id': message_id,
        'read_at': message.read_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=sender_room)
    
    print(f"👁️ 메시지 읽음: ID {message_id}")
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
    
    # 상대방에게 타이핑 상태 전송
    recipient_room = f"user_{recipient_id}"
    emit('user_typing', {
        'sender_id': current_user.id,
        'sender_name': current_user.username,
        'is_typing': is_typing
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
    
    # 개인 대화방 생성/입장
    conversation_room = f"conv_{min(current_user.id, other_id)}_{max(current_user.id, other_id)}"
    join_room(conversation_room)
    
    print(f"🚪 {current_user.username}이(가) {other_id}와의 대화방 입장")
    return True


@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    """대화방 퇴장"""
    if not current_user.is_authenticated:
        return False
    
    other_id = data.get('other_id')
    if not other_id:
        return False
    
    conversation_room = f"conv_{min(current_user.id, other_id)}_{max(current_user.id, other_id)}"
    leave_room(conversation_room)
    
    print(f"🚪 {current_user.username}이(가) 대화방 퇴장")
    return True

