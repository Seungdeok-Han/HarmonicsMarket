from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric
from datetime import datetime
from sqlalchemy.dialects.mysql import JSON

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # FK로 연결
    user = db.relationship('User', backref='posts')  # 관계 설정
    brand = db.relationship('BrandInfo')
    images = db.Column(JSON)  # 이미지 파일명
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='available')  # 거래 상태: available, reserved, sold

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    likes = db.relationship('Like', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('instrument_post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship('Comment',
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')

    user = db.relationship('User', backref='comments')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('instrument_post.id'), nullable=False)

    user = db.relationship('User', overlaps="likes")
    post = db.relationship('InstrumentPost', backref=db.backref('likes', cascade='all, delete-orphan'))

class MyInstrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    images = db.Column(JSON)  # 여러장
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='my_instruments')

class GenreTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    genres = db.Column(db.String(200), nullable=False)  # 쉼표로 구분된 장르 문자열
    __table_args__ = (db.UniqueConstraint('brand', 'model_name', name='uix_brand_model'),)


class Message(db.Model):
    """1:1 사용자 메시지 모델"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='dynamic'))

class Notification(db.Model):
    """알림 모델"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # comment_like, sns_like, message, follow, comment
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 액션을 취한 사용자
    post_id = db.Column(db.Integer, nullable=True)  # 중고글 또는 SNS글 ID (SNS는 음수로)
    comment_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic'))
    related_user = db.relationship('User', foreign_keys=[related_user_id])

class Follow(db.Model):
    """팔로우 관계 모델"""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 팔로우하는 사용자
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 팔로우당하는 사용자
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))
    following_user = db.relationship('User', foreign_keys=[following_id], backref=db.backref('followers', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='uix_follower_following'),)


# ===== 연습 기록 시스템 =====
class PracticeRecommendation(db.Model):
    """AI 추천 기록"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    guitar_type = db.Column(db.String(100))
    goals = db.Column(db.Text)
    specific_song = db.Column(db.String(200))
    tips = db.Column(JSON)  # 연습 팁 배열
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('practice_recommendations', lazy='dynamic'))
    songs = db.relationship('PracticeSong', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')
    techniques = db.relationship('PracticeTechnique', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')


class PracticeSong(db.Model):
    """추천된 곡 (진행도 포함)"""
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('practice_recommendation.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200))
    difficulty = db.Column(db.String(50))
    reason = db.Column(db.Text)
    videos = db.Column(JSON)  # YouTube 영상 링크 배열
    status = db.Column(db.String(20), default='not_started')  # not_started, practicing, completed, paused
    
    
class PracticeTechnique(db.Model):
    """추천된 주법 (진행도 포함)"""
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('practice_recommendation.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    practice_time = db.Column(db.String(100))
    videos = db.Column(JSON)
    status = db.Column(db.String(20), default='not_started')  # not_started, practicing, completed, paused


class PracticeLog(db.Model):
    """연습 일지"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer)  # 연습 시간 (분)
    songs_practiced = db.Column(db.Text)  # 연습한 곡들
    notes = db.Column(db.Text)  # 메모
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('practice_logs', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='uix_user_date'),)
