from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Numeric, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class BrandInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    origin_country = db.Column(db.String(100))
    famous_users = db.Column(db.Text)
    logo_url = db.Column(db.String(255))


class InstrumentPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    brand_id = db.Column(db.Integer, db.ForeignKey('brand_info.id'))
    model_name = db.Column(db.String(100))
    shape = db.Column(db.String(100))
    condition = db.Column(db.Integer)  # 0~100
    description = db.Column(db.Text)
    price = db.Column(Numeric(10, 2))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='posts')
    brand = db.relationship('BrandInfo')
    images = db.Column(JSON)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='available')  # available, reserved, sold

    STATUS_LABELS = {
        'available': '판매중',
        'reserved': '예약중',
        'sold': '판매완료',
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status or 'available', self.status)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(280))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('Like', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def listing_count(self):
        return InstrumentPost.query.filter_by(user_id=self.id).count()

    @property
    def active_listing_count(self):
        return InstrumentPost.query.filter_by(user_id=self.id, status='available').count()

    @property
    def sold_count(self):
        return InstrumentPost.query.filter_by(user_id=self.id, status='sold').count()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('instrument_post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic',
    )
    user = db.relationship('User', backref='comments')


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('instrument_post.id'), nullable=False)

    user = db.relationship('User', overlaps='likes')
    post = db.relationship(
        'InstrumentPost',
        backref=db.backref('likes', cascade='all, delete-orphan'),
    )

    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='uix_like_user_post'),)


class MyInstrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    images = db.Column(JSON)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='my_instruments')


class GenreTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    genres = db.Column(db.String(200), nullable=False)
    __table_args__ = (UniqueConstraint('brand', 'model_name', name='uix_brand_model'),)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    related_post_id = db.Column(db.Integer, db.ForeignKey('instrument_post.id'), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship(
        'User',
        foreign_keys=[recipient_id],
        backref=db.backref('received_messages', lazy='dynamic'),
    )
    related_post = db.relationship('InstrumentPost')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    post_id = db.Column(db.Integer, nullable=True)
    community_post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=True)
    comment_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic'))
    related_user = db.relationship('User', foreign_keys=[related_user_id])


class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))
    following_user = db.relationship(
        'User',
        foreign_keys=[following_id],
        backref=db.backref('followers', lazy='dynamic'),
    )

    __table_args__ = (UniqueConstraint('follower_id', 'following_id', name='uix_follower_following'),)


# ===== Community (SNS) =====
class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    caption = db.Column(db.Text, default='')
    image = db.Column(db.String(255), default='')
    media = db.Column(JSON)  # [{type, filename}, ...]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('community_posts', lazy='dynamic'))
    likes = db.relationship(
        'CommunityLike',
        backref='post',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    comments = db.relationship(
        'CommunityComment',
        backref='post',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class CommunityLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='uix_community_like'),)


class CommunityComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('community_comment.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User')
    replies = db.relationship(
        'CommunityComment',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic',
    )
    likes = db.relationship(
        'CommunityCommentLike',
        backref='comment',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class CommunityCommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('community_comment.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'comment_id', name='uix_community_comment_like'),)


# ===== Practice =====
class PracticeRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    guitar_type = db.Column(db.String(100))
    goals = db.Column(db.Text)
    specific_song = db.Column(db.String(200))
    tips = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('practice_recommendations', lazy='dynamic'))
    songs = db.relationship(
        'PracticeSong',
        backref='recommendation',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    techniques = db.relationship(
        'PracticeTechnique',
        backref='recommendation',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class PracticeSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('practice_recommendation.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200))
    difficulty = db.Column(db.String(50))
    reason = db.Column(db.Text)
    videos = db.Column(JSON)
    status = db.Column(db.String(20), default='not_started')


class PracticeTechnique(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('practice_recommendation.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    practice_time = db.Column(db.String(100))
    videos = db.Column(JSON)
    status = db.Column(db.String(20), default='not_started')


class PracticeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer)
    songs_practiced = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('practice_logs', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('user_id', 'date', name='uix_user_date'),)
