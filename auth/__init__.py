from .admin_routes import admin_bp
from .routes import auth_bp


def register_auth(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
