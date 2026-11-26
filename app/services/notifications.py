from app.extensions import db
from app.models import Notification


def create_notification(
    user_id,
    notification_type,
    related_user_id=None,
    post_id=None,
    comment_id=None,
    community_post_id=None,
):
    if user_id is None:
        return None
    n = Notification(
        user_id=user_id,
        type=notification_type,
        related_user_id=related_user_id,
        post_id=post_id,
        comment_id=comment_id,
        community_post_id=community_post_id,
    )
    db.session.add(n)
    db.session.commit()
    return n
