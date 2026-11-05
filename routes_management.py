"""Gerenciamento administrativo de modelos e categorias, com validação no servidor."""
from flask import Blueprint, request, jsonify, abort, render_template
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Model3D, Category

management_bp = Blueprint("management", __name__, url_prefix="/admin")

def require_admin():
    if current_user.role != "admin":
        abort(403)

def as_model(model):
    return {"id": model.id, "title": model.title, "description": model.description,
            "price_cents": model.price_cents, "status": model.status,
            "category_id": model.category_id, "cover_path": model.cover_path}

def validated(data, model):
    title = str(data.get("title", model.title or "")).strip()
    description = str(data.get("description", model.description or "")).strip()
    if not 3 <= len(title) <= 180 or len(description) > 10000:
        abort(400, "Título ou descrição inválidos")
    raw_price = data.get("price_cents", model.price_cents)
    if isinstance(raw_price, bool) or not (isinstance(raw_price, int) or (isinstance(raw_price, str) and raw_price.isascii() and raw_price.isdecimal())):
        abort(400, "Preço deve ser um número inteiro de centavos")
    try:
        price = int(raw_price)
    except (ValueError, TypeError):
        abort(400, "Preço inválido")
    if price < 0 or price > 100000000:
        abort(400, "Preço fora do limite")
    status = str(data.get("status", model.status))
    if status not in ("draft", "published", "archived"):
        abort(400, "Status inválido")
    category_id = data.get("category_id", model.category_id)
    if category_id not in (None, ""):
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            abort(400, "Categoria inválida")
        if db.session.get(Category, category_id) is None:
            abort(400, "Categoria inexistente")
    else:
        category_id = None
    cover = str(data.get("cover_path", model.cover_path or "")).strip()
    if cover and (not cover.startswith("https://") or len(cover) > 500):
        abort(400, "A capa deve ser uma URL HTTPS")
    if status == "published" and not model.file_path:
        abort(409, "Envie o arquivo do modelo antes de publicar")
    if model.id is not None and status == "published" and price > 0:
        from pathlib import Path
        from flask import current_app
        path = Path(current_app.config["PRIVATE_MODELS_DIR"]).resolve()
        if not model.file_path or not (path / model.file_path).resolve().is_file():
            abort(409, "Arquivo do modelo indisponível")
    model.title, model.description = title, description
    model.price_cents, model.status = price, status
    model.category_id, model.cover_path = category_id, cover or None

@management_bp.get("")
@login_required
def panel():
    require_admin()
    return render_template("admin_panel.html")

@management_bp.get("/api/models")
@login_required
def list_models():
    require_admin()
    rows = Model3D.query.order_by(Model3D.id.desc()).limit(200).all()
    return jsonify([as_model(row) for row in rows])

@management_bp.post("/api/models")
@login_required
def create_model():
    require_admin()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    model = Model3D(seller_id=current_user.id, title="", description="",
                    price_cents=0, status="draft")
    validated(data, model)
    db.session.add(model)
    db.session.commit()
    return jsonify(as_model(model)), 201

@management_bp.patch("/api/models/<int:model_id>")
@login_required
def update_model(model_id):
    require_admin()
    model = db.session.get(Model3D, model_id)
    if model is None:
        abort(404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    validated(data, model)
    db.session.commit()
    return jsonify(as_model(model))

@management_bp.get("/api/categories")
@login_required
def list_categories():
    require_admin()
    return jsonify([{"id": c.id, "name": c.name, "slug": c.slug}
                    for c in Category.query.order_by(Category.name).all()])

@management_bp.post("/api/categories")
@login_required
def create_category():
    require_admin()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    slug = str(data.get("slug", "")).strip().lower()
    if not 2 <= len(name) <= 100 or not 2 <= len(slug) <= 120 or not all(
        ch.isascii() and (ch.islower() or ch.isdigit() or ch == "-") for ch in slug
    ):
        abort(400, "Nome ou slug inválido")
    category = Category(name=name, slug=slug)
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "Categoria já existe")
    return jsonify({"id": category.id, "name": name, "slug": slug}), 201

@management_bp.post("/api/models/<int:model_id>/upload")
@login_required
def upload_model_file(model_id):
    """Upload ZIP/BBMODEL para armazenamento fora da pasta static."""
    import os
    import secrets
    from pathlib import Path
    from flask import current_app
    require_admin()
    model = db.session.get(Model3D, model_id)
    if model is None:
        abort(404)
    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, "Selecione um arquivo")
    extension = Path(file.filename).suffix.lower()
    if extension not in {".zip", ".bbmodel"}:
        abort(400, "Apenas ZIP ou BBMODEL")
    max_bytes = 50 * 1024 * 1024
    # O servidor também limita o corpo HTTP para evitar uploads excessivos.
    if request.content_length is not None and request.content_length > max_bytes + 1024 * 1024:
        abort(413)
    root = Path(current_app.config["PRIVATE_MODELS_DIR"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    filename = secrets.token_hex(20) + extension
    destination = root / filename
    try:
        with destination.open("xb") as out:
            total = 0
            while True:
                chunk = file.stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    abort(413, "Arquivo muito grande")
                out.write(chunk)
        if total == 0:
            abort(400, "Arquivo vazio")
        model.file_path = filename
        db.session.commit()
    except Exception:
        db.session.rollback()
        destination.unlink(missing_ok=True)
        raise
    # Não excluir o arquivo anterior: pedidos históricos podem precisar de auditoria.
    return jsonify({"id": model.id, "file_ready": True, "size_bytes": total}), 201
