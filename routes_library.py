"""Biblioteca privada e downloads autorizados de modelos adquiridos."""
from pathlib import Path
from flask import Blueprint, current_app, abort, jsonify, send_file
from flask_login import current_user, login_required
from models import db, Model3D, Purchase

library_bp = Blueprint("library", __name__, url_prefix="/api/library")

def owned_models(user_id):
    paid_ids = db.session.query(Purchase.model_id).filter(
        Purchase.buyer_id == user_id, Purchase.status == "paid"
    )
    return Model3D.query.filter(
        Model3D.status == "published",
        (Model3D.price_cents == 0) | Model3D.id.in_(paid_ids)
    )

@library_bp.get("")
@login_required
def list_library():
    # Modelos gratuitos são acessíveis sem compra.
    models = owned_models(current_user.id).order_by(Model3D.id.desc()).limit(100).all()
    return jsonify([{"id": m.id, "title": m.title, "free": m.price_cents == 0,
                     "download_url": f"/api/library/{m.id}/download"} for m in models])

@library_bp.get("/<int:model_id>/download")
@login_required
def download(model_id):
    model = db.session.get(Model3D, model_id)
    if model is None or model.status != "published":
        abort(404)
    if model.price_cents > 0:
        paid = Purchase.query.filter_by(
            buyer_id=current_user.id, model_id=model_id, status="paid"
        ).first()
        if paid is None:
            abort(403)
    if not model.file_path:
        abort(404, "Arquivo indisponível")
    root = Path(current_app.config.get("PRIVATE_MODELS_DIR", "private_models")).resolve()
    candidate = (root / model.file_path).resolve()
    if candidate == root or root not in candidate.parents:
        abort(404)
    if not candidate.is_file():
        abort(404)
    return send_file(candidate, as_attachment=True, download_name=candidate.name,
                     max_age=0)
