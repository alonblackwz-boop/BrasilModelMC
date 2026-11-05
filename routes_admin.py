"""Painel administrativo v0.3: visão geral protegida por perfil."""
from flask import Blueprint, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, User, Model3D, Purchase, Suggestion, Review

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

def require_admin():
    if current_user.role != "admin":
        abort(403)

@admin_bp.get("/overview")
@login_required
def overview():
    require_admin()
    return jsonify({
        "users": db.session.query(func.count(User.id)).scalar(),
        "models": db.session.query(func.count(Model3D.id)).scalar(),
        "published_models": db.session.query(func.count(Model3D.id)).filter(Model3D.status == "published").scalar(),
        "pending_orders": db.session.query(func.count(Purchase.id)).filter(Purchase.status == "pending").scalar(),
        "paid_orders": db.session.query(func.count(Purchase.id)).filter(Purchase.status == "paid").scalar(),
        "suggestions": db.session.query(func.count(Suggestion.id)).scalar(),
        "reviews": db.session.query(func.count(Review.id)).scalar(),
    })

@admin_bp.get("/orders")
@login_required
def orders():
    require_admin()
    rows = Purchase.query.order_by(Purchase.id.desc()).limit(100).all()
    return jsonify([{"id": row.id, "buyer_id": row.buyer_id, "model_id": row.model_id,
                     "amount_cents": row.amount_cents, "status": row.status}
                    for row in rows])

@admin_bp.get("/suggestions")
@login_required
def suggestions():
    require_admin()
    rows = Suggestion.query.order_by(Suggestion.id.desc()).limit(100).all()
    return jsonify([{"id": row.id, "author_id": row.author_id,
                     "title": row.title, "status": row.status} for row in rows])
