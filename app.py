import os
from pathlib import Path
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from models import db, User

login_manager = LoginManager()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///brasilmodelmc.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        if not app.config.get("TESTING"):
            raise RuntimeError("Configure SECRET_KEY no ambiente antes de iniciar.")
        app.config["SECRET_KEY"] = "testing-only-not-for-production"
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.get("/")
    def index():
        return jsonify(name="BrasilModelMC", version="0.3.0-dev", status="em desenvolvimento")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    with app.app_context():
        db.create_all()
    return app

app = create_app()
