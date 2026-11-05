"""Avaliações de modelos: API compatível com Flask-Login e SQLAlchemy."""
from flask import Blueprint, request, jsonify, abort
from flask_login import current_user, login_required
from sqlalchemy import func
from models import db, Review, Purchase, Model3D

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/models")

@reviews_bp.get("/<int:model_id>/reviews")
def list_reviews(model_id):
    model = db.session.get(Model3D, model_id)
    if model is None or model.status != "published":
        abort(404)
    rows = (db.session.query(Review).filter_by(model_id=model_id)
            .order_by(Review.id.desc()).limit(100).all())
    average = db.session.query(func.avg(Review.rating)).filter_by(model_id=model_id).scalar()
    return jsonify({"average": round(float(average), 2) if average is not None else None,
                    "count": db.session.query(func.count(Review.id)).filter_by(model_id=model_id).scalar(),
                    "reviews": [{"id": r.id, "rating": r.rating, "comment": r.comment}
                                for r in rows]})

@reviews_bp.post("/<int:model_id>/reviews")
@login_required
def submit_review(model_id):
    model = db.session.get(Model3D, model_id)
    if model is None or model.status != "published":
        abort(404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    rating, comment = data.get("rating"), data.get("comment", "")
    if type(rating) is not int or not 1 <= rating <= 5:
        abort(400, "Nota deve ser de 1 a 5.")
    if not isinstance(comment, str) or len(comment.strip()) > 1500:
        abort(400, "Comentário inválido.")
    bought = Purchase.query.filter_by(buyer_id=current_user.id, model_id=model_id, status="paid").first()
    if bought is None:
        abort(403, "Somente compradores com pagamento confirmado podem avaliar.")
    review = Review.query.filter_by(buyer_id=current_user.id, model_id=model_id).first()
    if review is None:
        review = Review(buyer_id=current_user.id, model_id=model_id, rating=rating)
        db.session.add(review)
    review.rating = rating
    review.comment = comment.strip()
    db.session.commit()
    return jsonify({"ok": True, "rating": review.rating})
