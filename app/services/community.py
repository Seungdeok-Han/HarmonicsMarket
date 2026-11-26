"""Community post helpers — DB-backed, JSON-shaped for existing frontend."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask_login import current_user

from app.extensions import db
from app.models import CommunityComment, CommunityCommentLike, CommunityLike, CommunityPost, User
from app.utils.timeago import time_ago


def ensure_user(user_id: Optional[int], username: Optional[str] = None) -> Optional[User]:
    """Find or create a user for seed/import. Does not force primary keys."""
    if user_id is None and not username:
        return None
    if user_id is not None:
        user = User.query.get(user_id)
        if user:
            return user
    name = username or (f'demo_user_{user_id}' if user_id is not None else 'demo_user')
    existing = User.query.filter_by(username=name).first()
    if existing:
        return existing
    base = name
    n = 1
    while User.query.filter_by(username=name).first():
        name = f'{base}_{n}'
        n += 1
    user = User(username=name)
    user.set_password(f'!demo-{user_id or name}!')
    db.session.add(user)
    db.session.flush()
    return user


def serialize_comment(c: CommunityComment, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    like_ids = [lk.user_id for lk in c.likes.all()]
    payload = {
        'id': c.id,
        'user_id': c.user_id,
        'username': c.user.username if c.user else '익명',
        'content': c.content,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else '',
        'parent_id': c.parent_id,
        'likes': like_ids,
        'time_ago': time_ago(c.created_at, now=now),
    }
    if c.edited_at:
        payload['edited_at'] = c.edited_at.strftime('%Y-%m-%d %H:%M:%S')
    return payload


def serialize_post(
    post: CommunityPost,
    *,
    include_comments: bool = True,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now()
    like_ids = [lk.user_id for lk in post.likes.all()]
    uid = getattr(current_user, 'id', None) if current_user else None
    data: Dict[str, Any] = {
        'id': post.id,
        'username': post.user.username if post.user else '익명',
        'user_id': post.user_id,
        'image': post.image or '',
        'media': post.media or [],
        'caption': post.caption or '',
        'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S') if post.created_at else '',
        'likes': like_ids,
        'like_count': len(like_ids),
        'liked': uid is not None and uid in like_ids,
        'time_ago': time_ago(post.created_at, now=now),
    }
    if include_comments:
        comments = (
            CommunityComment.query.filter_by(post_id=post.id)
            .order_by(CommunityComment.created_at.asc())
            .all()
        )
        data['comments'] = [serialize_comment(c, now=now) for c in comments]
    else:
        data['comments'] = []
        data['comment_count'] = post.comments.count()
    return data


def list_posts(page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], bool]:
    q = CommunityPost.query.order_by(CommunityPost.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    now = datetime.now()
    posts = []
    for model in items:
        p = serialize_post(model, include_comments=True, now=now)
        posts.append(p)
    has_more = page * per_page < total
    return posts, has_more


def get_post(post_id: int) -> Optional[CommunityPost]:
    return CommunityPost.query.get(post_id)


def import_from_json(posts: List[Dict[str, Any]]) -> int:
    """One-shot import from legacy sns_posts.json. Returns imported count."""
    if CommunityPost.query.count() > 0:
        return 0

    user_map: Dict[int, int] = {}

    def map_user(raw_uid: Optional[int], username: Optional[str] = None) -> Optional[int]:
        if raw_uid is None:
            return None
        if raw_uid in user_map:
            return user_map[raw_uid]
        # Prefer real existing user with that id
        existing = User.query.get(raw_uid)
        if existing:
            user_map[raw_uid] = existing.id
            return existing.id
        user = ensure_user(raw_uid, username)
        if not user:
            return None
        user_map[raw_uid] = user.id
        return user.id

    imported = 0
    for raw in sorted(posts, key=lambda p: p.get('id', 0)):
        uid = map_user(raw.get('user_id'), raw.get('username'))
        if uid is None:
            continue
        created = raw.get('created_at')
        try:
            created_at = datetime.strptime(created, '%Y-%m-%d %H:%M:%S') if created else datetime.utcnow()
        except ValueError:
            created_at = datetime.utcnow()
        post = CommunityPost(
            user_id=uid,
            caption=raw.get('caption') or '',
            image=raw.get('image') or '',
            media=raw.get('media') or [],
            created_at=created_at,
        )
        db.session.add(post)
        db.session.flush()

        for like_uid in raw.get('likes') or []:
            mapped = map_user(like_uid)
            if mapped:
                db.session.add(CommunityLike(user_id=mapped, post_id=post.id))

        id_map: Dict[int, int] = {}
        comments = raw.get('comments') or []
        for c in sorted(comments, key=lambda x: x.get('id', 0)):
            cu = map_user(c.get('user_id'), c.get('username'))
            if cu is None:
                continue
            try:
                c_created = datetime.strptime(c.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                c_created = created_at
            parent_old = c.get('parent_id')
            parent_new = id_map.get(parent_old) if parent_old else None
            comment = CommunityComment(
                post_id=post.id,
                user_id=cu,
                content=c.get('content') or '',
                parent_id=parent_new,
                created_at=c_created,
            )
            db.session.add(comment)
            db.session.flush()
            if c.get('id') is not None:
                id_map[c.get('id')] = comment.id
            for luid in c.get('likes') or []:
                mapped = map_user(luid)
                if mapped:
                    db.session.add(CommunityCommentLike(user_id=mapped, comment_id=comment.id))
        imported += 1

    db.session.commit()
    return imported
