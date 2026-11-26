from flask import Flask
from dotenv import load_dotenv
import os
from app.extensions import db, migrate, login_manager, socketio, csrf


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['WTF_CSRF_ENABLED'] = True
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
        return User.query.get(int(user_id))

    # auto-import community JSON once if empty
    with app.app_context():
        try:
            import json
            import os as _os
            from app.models import CommunityPost
            from app.services.community import import_from_json
            if CommunityPost.query.count() == 0:
                path = _os.path.join(app.root_path, '..', 'data', 'sns_posts.json')
                if _os.path.isfile(path):
                    with open(path, encoding='utf-8') as f:
                        import_from_json(json.load(f))
        except Exception as e:
            print('community import skipped:', e)
    return app
