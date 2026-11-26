import json
import os

from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import inspect

from app.extensions import csrf, db, login_manager, migrate, socketio


def create_app(config_overrides=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'dev-secret-key'))
    app.config['WTF_CSRF_ENABLED'] = True
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, async_mode='threading')

    from app.routes import main
    from app.routes_auth import auth

    app.register_blueprint(main)
    app.register_blueprint(auth)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Seed community from legacy JSON only for the real on-disk DB.
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not app.config.get('TESTING') and uri.startswith('sqlite:///'):
        with app.app_context():
            try:
                from app.models import CommunityPost
                from app.services.community import import_from_json

                insp = inspect(db.engine)
                if insp.has_table('community_post') and CommunityPost.query.count() == 0:
                    path = os.path.join(app.root_path, '..', 'data', 'sns_posts.json')
                    if os.path.isfile(path):
                        with open(path, encoding='utf-8') as f:
                            n = import_from_json(json.load(f))
                            if n:
                                print(f'community import: {n} posts')
            except Exception as e:
                db.session.rollback()
                print('community import skipped:', e)

    return app
