"""Consulta segura de cupons; desconto sempre recalculado no servidor."""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, abort, render_template_string
from flask_login import login_required, current_user
from models import db, Coupon, Setting

coupons_bp = Blueprint("coupons", __name__, url_prefix="/api/coupons")

def calculate_discount(coupon, subtotal_cents):
    if type(subtotal_cents) is not int or not 0 <= subtotal_cents <= 100_000_000:
        raise ValueError("Subtotal inválido")
    if coupon is None or coupon.discount_value <= 0:
        return 0
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        return 0
    if coupon.expires_at is not None:
        expiry = coupon.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            return 0
    if coupon.discount_type == "percent":
        if coupon.discount_value > 100:
            return 0
        return subtotal_cents * coupon.discount_value // 100
    if coupon.discount_type == "fixed":
        return min(subtotal_cents, coupon.discount_value)
    return 0

@coupons_bp.post("/quote")
def quote_coupon():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "JSON inválido")
    code = data.get("code", "")
    subtotal = data.get("subtotal_cents")
    if not isinstance(code, str) or not 1 <= len(code.strip()) <= 50:
        abort(400, "Cupom inválido")
    if type(subtotal) is not int or not 0 <= subtotal <= 100_000_000:
        abort(400, "Subtotal inválido")
    coupon = Coupon.query.filter(db.func.upper(Coupon.code) == code.strip().upper()).first()
    discount = calculate_discount(coupon, subtotal)
    return jsonify({"valid": bool(discount), "discount_cents": discount,
                    "total_cents": subtotal - discount})

def _admin():
    if current_user.role != "admin":
        abort(403)

def active_promotion():
    """Faixa exibida apenas para cupom válido e ativado."""
    settings = {s.key: s.value for s in Setting.query.filter(Setting.key.in_(
        ("promo_enabled", "promo_coupon_id", "promo_message"))).all()}
    if settings.get("promo_enabled") != "true":
        return None
    try:
        coupon_id = int(settings.get("promo_coupon_id", ""))
    except ValueError:
        return None
    coupon = db.session.get(Coupon, coupon_id)
    if not coupon or not calculate_discount(coupon, 100_000_000):
        return None
    message = settings.get("promo_message", "").strip()[:160]
    if not message:
        message = "Aproveite nosso cupom especial!"
    if coupon.discount_type == "percent":
        discount_label = f"{coupon.discount_value}% OFF"
    else:
        discount_label = f"R$ {coupon.discount_value / 100:.2f} OFF".replace(".", ",")
    return {"message": message, "code": coupon.code, "discount_label": discount_label}

@coupons_bp.get("/admin")
@login_required
def admin_coupons():
    _admin()
    coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    settings = {s.key: s.value for s in Setting.query.filter(Setting.key.in_(
        ("promo_enabled", "promo_coupon_id", "promo_message"))).all()}
    return jsonify({"coupons": [
        {"id": c.id, "code": c.code, "discount_type": c.discount_type,
         "discount_value": c.discount_value, "max_uses": c.max_uses,
         "used_count": c.used_count, "expires_at": c.expires_at.isoformat() if c.expires_at else None}
        for c in coupons], "promotion": {
        "enabled": settings.get("promo_enabled") == "true",
        "coupon_id": settings.get("promo_coupon_id", ""),
        "message": settings.get("promo_message", "")}})

@coupons_bp.post("/admin")
@login_required
def create_admin_coupon():
    _admin()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    code = data.get("code")
    kind = data.get("discount_type")
    value = data.get("discount_value")
    limit = data.get("max_uses")
    if not isinstance(code, str) or not 3 <= len(code.strip()) <= 50 or not all(
        ch.isascii() and (ch.isalnum() or ch in "-_") for ch in code.strip()):
        abort(400, "Código inválido")
    if kind not in ("percent", "fixed") or type(value) is not int or value <= 0:
        abort(400, "Desconto inválido")
    if (kind == "percent" and value > 100) or (kind == "fixed" and value > 100_000_000):
        abort(400, "Desconto fora do limite")
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 1000000):
        abort(400, "Limite inválido")
    from sqlalchemy.exc import IntegrityError
    if Coupon.query.filter(db.func.upper(Coupon.code) == code.strip().upper()).first():
        abort(409, "Cupom já existe")
    coupon = Coupon(code=code.strip().upper(), discount_type=kind,
                    discount_value=value, max_uses=limit)
    db.session.add(coupon)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "Cupom já existe")
    return jsonify({"id": coupon.id, "code": coupon.code}), 201

@coupons_bp.put("/admin/promotion")
@login_required
def configure_promotion():
    _admin()
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or type(data.get("enabled")) is not bool:
        abort(400)
    message = data.get("message", "")
    if not isinstance(message, str) or len(message.strip()) > 160:
        abort(400, "Mensagem inválida")
    coupon_id = data.get("coupon_id")
    if type(coupon_id) is not int and coupon_id not in (None, ""):
        abort(400, "Cupom inválido")
    coupon = db.session.get(Coupon, coupon_id) if type(coupon_id) is int else None
    if data["enabled"] and (not coupon or not calculate_discount(coupon, 100_000_000)):
        abort(409, "Escolha um cupom válido antes de ativar")
    for key, value in {
        "promo_enabled": "true" if data["enabled"] else "false",
        "promo_coupon_id": str(coupon.id) if coupon else "",
        "promo_message": message.strip()
    }.items():
        setting = db.session.get(Setting, key)
        if setting is None:
            db.session.add(Setting(key=key, value=value))
        else:
            setting.value = value
    db.session.commit()
    return jsonify({"saved": True})
