"""Rotas de sugestões compatíveis com a arquitetura Flask-SQLAlchemy v0.3."""
from datetime import timedelta, timezone, datetime
from flask import Blueprint, request, jsonify, abort
from flask_login import current_user, login_required
from models import db, Suggestion

suggestions_bp = Blueprint("suggestions", __name__, url_prefix="/api/suggestions")
MAX_TITLE = 120
MAX_DESCRIPTION = 2000

def serialize(s):
    created = s.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    deadline = created + timedelta(days=15)
    effective_status = "closed" if s.status == "open" and deadline <= datetime.now(timezone.utc) else s.status
    return {"id": s.id, "title": s.title, "description": s.description,
            "status": effective_status, "created_at": created.isoformat(),
            "deadline": deadline.isoformat()}

@suggestions_bp.get("")
def list_suggestions():
    items = Suggestion.query.order_by(Suggestion.id.desc()).limit(100).all()
    return jsonify([serialize(item) for item in items])

@suggestions_bp.post("")
@login_required
def submit_suggestion():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Envie um JSON válido.")
    title = data.get("title", "")
    description = data.get("description", "")
    if not isinstance(title, str) or not isinstance(description, str):
        abort(400, "Campos inválidos.")
    title, description = title.strip(), description.strip()
    if not 5 <= len(title) <= MAX_TITLE or not 10 <= len(description) <= MAX_DESCRIPTION:
        abort(400, "Título ou descrição fora dos limites.")
    suggestion = Suggestion(author_id=current_user.id, title=title, description=description)
    db.session.add(suggestion)
    db.session.commit()
    return jsonify(serialize(suggestion)), 201
