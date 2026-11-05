"""Consulta segura de cupons; desconto sempre recalculado no servidor."""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, abort
from models import db, Coupon

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
