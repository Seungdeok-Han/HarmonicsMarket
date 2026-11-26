from flask import Blueprint

main = Blueprint('main', __name__)

# Import submodules so their @main.route / @socketio.on handlers register.
from app.routes import youtube  # noqa: E402, F401
from app.routes import sns  # noqa: E402, F401
from app.routes import sockets  # noqa: E402, F401
from app.routes import core  # noqa: E402, F401
