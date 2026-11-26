"""Core marketplace, profile, messaging HTTP, practice, and notification routes."""
import csv
import datetime
import json
import os

import google.generativeai as genai
from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    BrandInfo,
    Comment,
    CommunityPost,
    Follow,
    GenreTag,
    InstrumentPost,
    Like,
    Message,
    MyInstrument,
    Notification,
    PracticeLog,
    PracticeRecommendation,
    PracticeSong,
    PracticeTechnique,
    User,
)
from app.routes import main
from app.routes.youtube import get_model_famous_users, search_youtube_videos
from app.services.community import serialize_post
from app.services.notifications import create_notification
from app.utils.uploads import ALLOWED_IMAGE_EXT, save_uploads

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@main.route('/')
def index():
    selected_brand_id = request.args.get('brand', type=int)
    search_query = request.args.get('q', '').strip()
    sort = request.args.get('sort', '')
    selected_shape = request.args.get('shape', '').strip()
    selected_condition = request.args.get('condition', '').strip()
    author_id = request.args.get('author_id', type=int)

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
        condition_order = ['최상', '양호', '사용감 있음', '수리 필요']
        query = query.order_by(db.case(
            {v: i for i, v in enumerate(condition_order)},
            value=InstrumentPost.condition,
        ))
    elif sort == 'condition_worst':
        condition_order = ['수리 필요', '사용감 있음', '양호', '최상']
        query = query.order_by(db.case(
            {v: i for i, v in enumerate(condition_order)},
            value=InstrumentPost.condition,
        ))
    elif sort == 'shape_asc':
        query = query.order_by(InstrumentPost.shape.asc())
    elif sort == 'shape_desc':
        query = query.order_by(InstrumentPost.shape.desc())
    else:
        query = query.order_by(InstrumentPost.created_at.desc())

    all_genre_tags = GenreTag.query.all()
    genre_set = set()
    for gt in all_genre_tags:
        for g in gt.genres.split(','):
            genre_set.add(g.strip())
    all_genres = sorted([g for g in genre_set if g])

    selected_genres = request.args.getlist('genres')
    if selected_genres:
        genre_tag_matches = GenreTag.query.filter(
            db.or_(*[GenreTag.genres.ilike(f'%{g}%') for g in selected_genres])
        ).all()
        brand_model_pairs = set((gt.brand, gt.model_name) for gt in genre_tag_matches)
        query = query.join(BrandInfo, InstrumentPost.brand_id == BrandInfo.id)
        query = query.filter(
            db.or_(*[
                db.and_(BrandInfo.name == brand, (InstrumentPost.model_name == model if model else True))
                for (brand, model) in brand_model_pairs
            ])
        )

    if author_id:
        query = query.filter(InstrumentPost.user_id == author_id)

    page = request.args.get('page', 1, type=int)
    per_page = 8
    posts_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    all_brands = BrandInfo.query.all()

    args = request.args.to_dict()
    args.pop('page', None)

    return render_template(
        'index.html',
        posts=posts_paginated.items,
        posts_paginated=posts_paginated,
        all_brands=all_brands,
        selected_brand_id=selected_brand_id,
        search_query=search_query,
        sort=sort,
        selected_shape=selected_shape,
        selected_condition=selected_condition,
        all_genres=all_genres,
        selected_genres=selected_genres,
        args=args,
    )


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

        custom_brand = request.form.get('custom_brand')
        if brand_id == 'custom' and custom_brand:
            brand = BrandInfo.query.filter_by(name=custom_brand).first()
            if not brand:
                brand = BrandInfo(name=custom_brand)
                db.session.add(brand)
                db.session.commit()
            brand_id = brand.id
        else:
            if not brand_id.isdigit():
                brand_obj = BrandInfo.query.filter_by(name=brand_id).first()
                if brand_obj:
                    brand_id = brand_obj.id
                else:
                    flash('선택한 브랜드가 존재하지 않습니다.', 'danger')
                    return redirect(url_for('main.add_post'))
            else:
                brand_id = int(brand_id)

        images = request.files.getlist('images[]')
        image_filenames = save_uploads(images, allowed=ALLOWED_IMAGE_EXT)

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
            status='available',
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('main.index'))

    brands = BrandInfo.query.order_by(BrandInfo.name).all()
    return render_template('add.html', brands=brands)


@main.route('/api/info/<string:category>/<int:id>')
def get_info(category, id):
    if category == 'brand':
        brand = BrandInfo.query.get_or_404(id)
        return jsonify({
            'title': brand.name,
            'description': brand.description or '정보 없음',
        })
    return jsonify({'error': 'invalid category'}), 400


@main.route('/api/info/brand/<int:brand_id>')
def brand_info(brand_id):
    brand = BrandInfo.query.get_or_404(brand_id)
    return jsonify({
        'title': brand.name,
        'description': brand.description or '정보 없음',
    })


@main.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = InstrumentPost.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        flash('삭제 권한이 없습니다.', 'danger')
        return redirect(url_for('main.index'))

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

    from_like = request.args.get('from_like')
    if not from_like:
        post.views = (post.views or 0) + 1
        db.session.commit()

    youtube_query = ''
    if post.brand and post.brand.name:
        youtube_query += post.brand.name
    if post.model_name:
        youtube_query += f' {post.model_name}'
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
            brand_genre_obj = GenreTag.query.filter_by(brand=post.brand.name, model_name='').first()
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
        genre_like = [GenreTag.genres.ilike(f'%{g.strip()}%') for g in genre_tags]
        genre_post_ids = [gt.id for gt in GenreTag.query.filter(db.or_(*genre_like)).all()]
        similar_query = similar_query.filter(InstrumentPost.id.in_(genre_post_ids))
    similar_posts = similar_query.order_by(db.func.random()).limit(4).all()

    famous_users_for_model = None
    if post.brand and post.model_name:
        famous_users_map = get_model_famous_users()
        famous_users_for_model = famous_users_map.get((post.brand.name, post.model_name))

    seller_listings = post.user.active_listing_count if post.user else 0
    seller_sold = post.user.sold_count if post.user else 0

    return render_template(
        'view_post.html',
        post=post,
        youtube_links=youtube_links,
        comments=comments,
        liked=liked,
        genre_tags=genre_tags,
        similar_posts=similar_posts,
        famous_users_for_model=famous_users_for_model,
        seller_listings=seller_listings,
        seller_sold=seller_sold,
    )


@main.route('/user/<int:user_id>')
def user_profile(user_id):
    """사용자 프로필: 중고 거래 글 + SNS 글을 함께 표시"""
    user = User.query.get_or_404(user_id)
    instrument_posts = InstrumentPost.query.filter_by(user_id=user_id).order_by(InstrumentPost.created_at.desc()).all()
    community_models = (
        CommunityPost.query.filter_by(user_id=user_id)
        .order_by(CommunityPost.created_at.desc())
        .all()
    )
    user_sns_posts = [serialize_post(p, include_comments=True) for p in community_models]
    return render_template(
        'user_profile.html',
        user=user,
        instrument_posts=instrument_posts,
        sns_posts=user_sns_posts,
    )


@main.route('/messages')
@login_required
def messages():
    sent = Message.query.with_entities(Message.recipient_id).filter(Message.sender_id == current_user.id)
    received = Message.query.with_entities(Message.sender_id).filter(Message.recipient_id == current_user.id)
    partner_ids = set([r[0] for r in sent.union_all(received).all()])
    partners = []
    for pid in partner_ids:
        user = User.query.get(pid)
        if not user:
            continue
        last_msg = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == pid)) |
            ((Message.sender_id == pid) & (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        unread_count = Message.query.filter_by(sender_id=pid, recipient_id=current_user.id, read_at=None).count()
        partners.append({'user': user, 'last_msg': last_msg, 'unread': unread_count})
    partners.sort(key=lambda p: p['last_msg'].created_at if p['last_msg'] else None, reverse=True)
    return render_template('messages.html', partners=partners)


@main.route('/messages/<int:other_id>', methods=['GET', 'POST'])
@login_required
def message_user(other_id):
    if other_id == current_user.id:
        flash('자기 자신에게 메시지를 보낼 수 없습니다.', 'warning')
        return redirect(url_for('main.messages'))
    other = User.query.get_or_404(other_id)

    listing_id = request.args.get('listing', type=int) or request.form.get('listing', type=int)
    listing = InstrumentPost.query.get(listing_id) if listing_id else None

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('메시지는 비어 있을 수 없습니다.', 'danger')
            return redirect(url_for('main.message_user', other_id=other_id, listing=listing_id or None))

        related_post_id = None
        if listing and listing.id:
            related_post_id = listing.id
            # Prepend a short context line once when starting from a listing
            existing_related = Message.query.filter(
                Message.related_post_id == listing.id,
                ((Message.sender_id == current_user.id) & (Message.recipient_id == other_id)) |
                ((Message.sender_id == other_id) & (Message.recipient_id == current_user.id)),
            ).first()
            if not existing_related:
                title = listing.title or '게시글'
                content = f'[관련 매물: {title}]\n{content}'

        m = Message(
            sender_id=current_user.id,
            recipient_id=other_id,
            content=content,
            related_post_id=related_post_id,
        )
        db.session.add(m)
        db.session.commit()

        create_notification(
            user_id=other_id,
            notification_type='message',
            related_user_id=current_user.id,
        )

        flash('메시지를 보냈습니다.', 'success')
        return redirect(url_for('main.message_user', other_id=other_id, listing=listing_id or None))

    unread = Message.query.filter_by(sender_id=other_id, recipient_id=current_user.id, read_at=None).all()
    now = datetime.datetime.utcnow()
    for u in unread:
        u.read_at = now
    if unread:
        db.session.commit()

        Notification.query.filter_by(
            user_id=current_user.id,
            type='message',
            related_user_id=other_id,
            is_read=False,
        ).update({'is_read': True})
        db.session.commit()

    conv = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other_id)) |
        ((Message.sender_id == other_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template('conversation.html', other=other, conv=conv, listing=listing)


@main.route('/user/summary/<int:user_id>')
def user_summary(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'not found'}), 404

    total_instruments = MyInstrument.query.filter_by(user_id=user_id).count()
    my_instruments = (
        MyInstrument.query.filter_by(user_id=user_id)
        .order_by(MyInstrument.is_featured.desc(), MyInstrument.id.desc())
        .limit(4)
        .all()
    )
    instruments = [
        {
            'brand': mi.brand,
            'model': mi.model_name,
            'img': (mi.images[0] if mi.images else None),
            'is_featured': bool(getattr(mi, 'is_featured', False)),
        }
        for mi in my_instruments
    ]
    posts_count = InstrumentPost.query.filter_by(user_id=user_id).count()
    community_posts = CommunityPost.query.filter_by(user_id=user_id).all()
    sns_count = len(community_posts)

    recent_items = []
    recent_instrument = (
        InstrumentPost.query.filter_by(user_id=user_id)
        .order_by(InstrumentPost.created_at.desc())
        .limit(5)
        .all()
    )
    for p in recent_instrument:
        ts = p.created_at.timestamp() if getattr(p, 'created_at', None) else 0
        recent_items.append({
            'title': p.title,
            'url': url_for('main.view_post', post_id=p.id),
            'ts': ts,
        })
    for sp in community_posts:
        ts = sp.created_at.timestamp() if sp.created_at else 0
        title = sp.caption or '(무제)'
        recent_items.append({
            'title': title,
            'url': url_for('main.sns_feed') + f'?post_id={sp.id}',
            'ts': ts,
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
        'recent_posts': recent_posts,
    })


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


@main.route('/post/<int:post_id>/comment', methods=['POST'])
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
        can_delete=(current_user.id == comment.user_id),
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
        image_filenames = save_uploads(images, allowed=ALLOWED_IMAGE_EXT)
        my_instrument = MyInstrument(
            user_id=current_user.id,
            brand=brand,
            model_name=model_name,
            images=image_filenames,
            description=description,
        )
        db.session.add(my_instrument)
        db.session.commit()
        flash('내 악기가 등록되었습니다!', 'success')
        return redirect(url_for('main.mypage', tab='gear'))

    my_instruments = MyInstrument.query.filter_by(user_id=current_user.id).all()
    brands = BrandInfo.query.order_by(BrandInfo.name).all()
    my_posts = InstrumentPost.query.filter_by(user_id=current_user.id).all()
    liked_posts = []
    if hasattr(current_user, 'likes'):
        liked_posts = [like.post for like in current_user.likes]

    community_models = (
        CommunityPost.query.filter_by(user_id=current_user.id)
        .order_by(CommunityPost.created_at.desc())
        .all()
    )
    my_sns_posts = [serialize_post(p, include_comments=True) for p in community_models]
    return render_template(
        'mypage.html',
        my_instruments=my_instruments,
        brands=brands,
        my_posts=my_posts,
        liked_posts=liked_posts,
        my_sns_posts=my_sns_posts,
    )


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
        post.status = request.form['status']
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
    posts = (
        InstrumentPost.query.filter_by(brand_id=brand_id, model_name=model_name, status='sold')
        .order_by(InstrumentPost.created_at.desc())
        .limit(20)
        .all()
    )
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
            'community_post_id': n.community_post_id,
            'comment_id': n.comment_id,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
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
        'following_count': user.following.count(),
    })


@main.route('/user/<int:user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    """사용자의 팔로워/팔로우 통계"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'followers_count': user.followers.count(),
        'following_count': user.following.count(),
    })


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
            recommendation = get_ai_practice_recommendation(experience, genre, guitar_type, goals, specific_song)

            for song in recommendation['songs']:
                query = f"{song['title']} {song['artist']} guitar tutorial"
                song['videos'] = search_youtube_videos(query, max_results=2)

            for technique in recommendation['techniques']:
                query = f"{technique['name']} guitar technique tutorial"
                technique['videos'] = search_youtube_videos(query, max_results=2)

            return render_template(
                'guitar_practice.html',
                recommendation=recommendation,
                experience=experience,
                genre=genre,
                guitar_type=guitar_type,
                goals=goals,
                specific_song=specific_song,
            )

        except Exception as e:
            print(f'❌ 추천 생성 오류: {e}')
            flash('추천을 생성하는 중 오류가 발생했습니다. 다시 시도해주세요.', 'danger')
            return redirect(url_for('main.guitar_practice'))

    return render_template('guitar_practice.html')


def get_ai_practice_recommendation(experience, genre, guitar_type, goals, specific_song=''):
    """Gemini를 사용하여 맞춤형 연습 추천"""

    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        print('❌ GEMINI_API_KEY가 설정되지 않았습니다')
        raise ValueError('GEMINI_API_KEY가 환경 변수에 설정되지 않았습니다')

    genai.configure(api_key=gemini_api_key)

    if specific_song:
        genre_info = f'특정 곡: {specific_song} (이 곡만 연습하고 싶어함)'
        songs_count = '1개 (입력한 곡만)'
    else:
        genre_info = f'선호 장르: {genre}'
        songs_count = '3개'

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

        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:].strip()

        result = json.loads(text)
        print('✅ Gemini AI 추천 생성 완료')
        return result

    except Exception as e:
        print(f'❌ Gemini API 오류: {e}')
        return {
            'songs': [
                {
                    'title': '호텔 캘리포니아',
                    'artist': 'Eagles',
                    'difficulty': '중급',
                    'reason': '기타 연주의 기초를 모두 담고 있는 명곡입니다.',
                }
            ],
            'techniques': [
                {
                    'name': '핑거링 연습',
                    'description': '손가락의 독립성을 키우는 기본 테크닉입니다.',
                    'practice_time': '하루 15분',
                }
            ],
            'tips': ['매일 꾸준히 연습하세요', '메트로놈을 활용하세요'],
        }


@main.route('/practice/save', methods=['POST'])
@login_required
def save_practice_recommendation():
    """추천 결과 저장"""
    try:
        data = request.get_json()

        recommendation = PracticeRecommendation(
            user_id=current_user.id,
            experience=data.get('experience'),
            genre=data.get('genre'),
            guitar_type=data.get('guitar_type'),
            goals=data.get('goals'),
            specific_song=data.get('specific_song'),
            tips=data.get('tips', []),
        )
        db.session.add(recommendation)
        db.session.flush()

        for song in data.get('songs', []):
            practice_song = PracticeSong(
                recommendation_id=recommendation.id,
                title=song['title'],
                artist=song.get('artist'),
                difficulty=song.get('difficulty'),
                reason=song.get('reason'),
                videos=song.get('videos', []),
            )
            db.session.add(practice_song)

        for technique in data.get('techniques', []):
            practice_technique = PracticeTechnique(
                recommendation_id=recommendation.id,
                name=technique['name'],
                description=technique.get('description'),
                practice_time=technique.get('practice_time'),
                videos=technique.get('videos', []),
            )
            db.session.add(practice_technique)

        db.session.commit()
        return jsonify({'success': True, 'id': recommendation.id})

    except Exception as e:
        db.session.rollback()
        print(f'❌ 추천 저장 오류: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/practice/my-list')
@login_required
def my_practice_list():
    """내 연습 기록 목록"""
    recommendations = (
        PracticeRecommendation.query.filter_by(user_id=current_user.id)
        .order_by(PracticeRecommendation.created_at.desc())
        .all()
    )
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

    return render_template(
        'practice_detail.html',
        recommendation=recommendation,
        songs=songs,
        techniques=techniques,
    )


@main.route('/practice/update-status', methods=['POST'])
@login_required
def update_practice_status():
    """진행도 업데이트"""
    try:
        data = request.get_json()
        item_type = data.get('type')
        item_id = data.get('id')
        status = data.get('status')

        if item_type == 'song':
            item = PracticeSong.query.get_or_404(item_id)
        else:
            item = PracticeTechnique.query.get_or_404(item_id)

        if item.recommendation.user_id != current_user.id:
            return jsonify({'success': False, 'error': '권한 없음'}), 403

        item.status = status
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        print(f'❌ 상태 업데이트 오류: {e}')
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


@main.route('/practice/log', methods=['GET', 'POST'])
@login_required
def practice_log():
    """연습 일지 작성/조회"""
    if request.method == 'POST':
        try:
            from datetime import date
            from datetime import datetime as dt

            log_date = request.form.get('date')
            if log_date:
                log_date = dt.strptime(log_date, '%Y-%m-%d').date()
            else:
                log_date = date.today()

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
            print(f'❌ 일지 저장 오류: {e}')
            flash('일지 저장 중 오류가 발생했습니다.', 'danger')

    from datetime import date, timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=29)

    logs = PracticeLog.query.filter(
        PracticeLog.user_id == current_user.id,
        PracticeLog.date >= start_date,
        PracticeLog.date <= end_date,
    ).order_by(PracticeLog.date.desc()).all()

    streak = calculate_practice_streak(current_user.id)

    total_minutes = (
        db.session.query(db.func.sum(PracticeLog.duration_minutes))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    )

    return render_template(
        'practice_log.html',
        logs=logs,
        streak=streak,
        total_minutes=total_minutes,
    )


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

        if streak >= 365:
            break

    return streak
