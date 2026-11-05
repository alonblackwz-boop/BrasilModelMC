import os
from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import or_
from models import db, User, Model3D, Category

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
    from routes_suggestions import suggestions_bp
    from routes_reviews import reviews_bp
    from routes_auth import auth_bp
    from routes_coupons import coupons_bp
    from routes_checkout import checkout_bp
    from routes_admin import admin_bp
    from routes_library import library_bp
    from routes_paghiper import paghiper_bp
    from routes_management import management_bp
    app.register_blueprint(suggestions_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(coupons_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(paghiper_bp)
    app.register_blueprint(management_bp)
    login_manager.login_view = "auth.login"
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    csrf.exempt(paghiper_bp)

    @app.get("/")
    def index():
        models = Model3D.query.filter_by(status="published").order_by(Model3D.created_at.desc()).limit(6).all()
        return render_template("index.html", models=models)

    @app.get("/modelos")
    def catalog():
        query = request.args.get("q", "").strip()[:100]
        price = request.args.get("price", "")
        selected_category = request.args.get("category", "")
        stmt = Model3D.query.filter_by(status="published")
        if query:
            stmt = stmt.filter(or_(Model3D.title.ilike(f"%{query}%"), Model3D.description.ilike(f"%{query}%")))
        if selected_category.isdigit():
            stmt = stmt.filter_by(category_id=int(selected_category))
        if price == "free":
            stmt = stmt.filter_by(price_cents=0)
        elif price == "paid":
            stmt = stmt.filter(Model3D.price_cents > 0)
        models = stmt.order_by(Model3D.created_at.desc()).limit(60).all()
        return render_template("catalog.html", models=models, categories=Category.query.order_by(Category.name).all(), query=query, price=price, selected_category=selected_category)

    @app.get("/modelo/<int:model_id>")
    def model_detail(model_id):
        model = Model3D.query.filter_by(id=model_id, status="published").first_or_404()
        return render_template("detail.html", model=model)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()
    return app

if __name__ == "__main__":
    create_app().run()
