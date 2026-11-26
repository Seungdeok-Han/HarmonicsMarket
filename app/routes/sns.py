"""Community (SNS) routes — DB-backed via app.services.community."""
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import CommunityComment, CommunityCommentLike, CommunityLike, CommunityPost
from app.routes import main
from app.services.community import get_post, list_posts, serialize_comment, serialize_post
from app.services.notifications import create_notification
from app.utils.uploads import delete_upload, media_type_for, save_upload


@main.route('/sns')
def sns_feed():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    posts, has_more = list_posts(page=page, per_page=per_page)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'posts': posts,
            'has_more': has_more,
            'next_page': page + 1,
        })

    return render_template('sns.html', posts=posts, has_more=has_more)


@main.route('/sns/create', methods=['GET', 'POST'])
@login_required
def sns_create():
    if request.method == 'POST':
        caption = request.form.get('caption', '').strip()
        files_images = request.files.getlist('images') or []
        files_videos = request.files.getlist('videos') or []
        fallback_media = request.files.getlist('media') or []
        files = []
        files.extend(files_images)
        files.extend(files_videos)
        if not files:
            files = fallback_media

        media_list = []
        for f in files:
            stored = save_upload(f)
            if not stored:
                continue
            media_list.append({'type': media_type_for(stored), 'filename': stored})

        first_image = next((m['filename'] for m in media_list if m.get('type') == 'image'), '')
        post = CommunityPost(
            user_id=current_user.id,
            caption=caption,
            image=first_image,
            media=media_list,
            created_at=datetime.now(),
        )
        db.session.add(post)
        db.session.commit()
        flash('게시물이 업로드되었습니다.', 'success')
        return redirect(url_for('main.sns_feed'))
    return render_template('sns_create.html')


@main.route('/sns/like/<int:post_id>', methods=['POST'])
@login_required
def sns_like(post_id):
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'not found'}), 404

    uid = current_user.id
    existing = CommunityLike.query.filter_by(user_id=uid, post_id=post.id).first()
    if existing:
        db.session.delete(existing)
        liked = False
    else:
        db.session.add(CommunityLike(user_id=uid, post_id=post.id))
        liked = True
        if post.user_id and post.user_id != uid:
            create_notification(
                post.user_id,
                'sns_like',
                related_user_id=uid,
                community_post_id=post.id,
            )
    db.session.commit()
    like_count = post.likes.count()
    return jsonify({'like_count': like_count, 'liked': liked})


@main.route('/sns/<int:post_id>')
def sns_post_detail(post_id):
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'not found'}), 404
    return jsonify(serialize_post(post, include_comments=True))


@main.route('/sns/<int:post_id>/comment', methods=['POST'])
@login_required
def sns_add_comment(post_id):
    """Add a comment or reply. Accepts JSON: {content: str, parent_id: optional int}"""
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')
    if not content:
        return jsonify({'error': 'no content'}), 400

    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'not found'}), 404

    if parent_id is not None:
        parent = CommunityComment.query.filter_by(id=parent_id, post_id=post.id).first()
        if not parent:
            return jsonify({'error': 'parent not found'}), 404

    comment = CommunityComment(
        post_id=post.id,
        user_id=current_user.id,
        content=content,
        parent_id=parent_id,
        created_at=datetime.now(),
    )
    db.session.add(comment)
    db.session.commit()

    if post.user_id and post.user_id != current_user.id:
        create_notification(
            post.user_id,
            'comment',
            related_user_id=current_user.id,
            community_post_id=post.id,
            comment_id=comment.id,
        )

    payload = serialize_comment(comment)
    return jsonify(payload), 201


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/edit', methods=['POST'])
@login_required
def sns_edit_comment(post_id, comment_id):
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'no content'}), 400

    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'post not found'}), 404

    comment = CommunityComment.query.filter_by(id=comment_id, post_id=post.id).first()
    if not comment:
        return jsonify({'error': 'comment not found'}), 404
    if comment.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    comment.content = content
    comment.edited_at = datetime.now()
    db.session.commit()
    return jsonify(serialize_comment(comment))


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def sns_delete_comment(post_id, comment_id):
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'post not found'}), 404

    comment = CommunityComment.query.filter_by(id=comment_id, post_id=post.id).first()
    if not comment:
        return jsonify({'error': 'comment not found'}), 404
    if comment.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    def delete_recursive(cid):
        replies = CommunityComment.query.filter_by(post_id=post.id, parent_id=cid).all()
        for r in replies:
            delete_recursive(r.id)
        target = CommunityComment.query.get(cid)
        if target:
            CommunityCommentLike.query.filter_by(comment_id=cid).delete()
            db.session.delete(target)

    delete_recursive(comment_id)
    db.session.commit()
    return jsonify({'success': True})


@main.route('/sns/<int:post_id>/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def sns_like_comment(post_id, comment_id):
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'post not found'}), 404

    comment = CommunityComment.query.filter_by(id=comment_id, post_id=post.id).first()
    if not comment:
        return jsonify({'error': 'comment not found'}), 404

    uid = current_user.id
    existing = CommunityCommentLike.query.filter_by(user_id=uid, comment_id=comment.id).first()
    if existing:
        db.session.delete(existing)
        liked = False
    else:
        db.session.add(CommunityCommentLike(user_id=uid, comment_id=comment.id))
        liked = True
        if comment.user_id and comment.user_id != uid:
            create_notification(
                comment.user_id,
                'comment_like',
                related_user_id=uid,
                community_post_id=post.id,
                comment_id=comment.id,
            )
    db.session.commit()
    like_count = comment.likes.count()
    return jsonify({'like_count': like_count, 'liked': liked})


@main.route('/sns/<int:post_id>/delete', methods=['POST'])
@login_required
def sns_delete_post(post_id):
    """SNS 게시물을 삭제합니다. 작성자만 삭제 가능하며, 업로드된 미디어 파일도 함께 제거합니다."""
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'not found'}), 404
    if post.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    media = post.media or []
    for m in media:
        fn = m.get('filename') if isinstance(m, dict) else None
        if fn:
            delete_upload(fn)
    if post.image:
        delete_upload(post.image)

    CommunityCommentLike.query.filter(
        CommunityCommentLike.comment_id.in_(
            db.session.query(CommunityComment.id).filter_by(post_id=post.id)
        )
    ).delete(synchronize_session=False)
    CommunityComment.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    CommunityLike.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True})
