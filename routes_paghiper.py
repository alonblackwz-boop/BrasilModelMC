"""Notificações Pix: só aceita pagamento verificado diretamente no PagHiper."""
import hmac
import os
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError
from models import db, Purchase, PixPayment
from paghiper import notification, PagHiperError

paghiper_bp = Blueprint("paghiper", __name__)

@paghiper_bp.post("/webhooks/paghiper/pix")
def callback():
    # Este endpoint público recebe apenas identificadores, nunca credenciais.
    key = request.form.get("apiKey", "")
    transaction_id = request.form.get("transaction_id", "")
    notification_id = request.form.get("notification_id", "")
    if not os.environ.get("PAGHIPER_API_KEY") or not hmac.compare_digest(key, os.environ["PAGHIPER_API_KEY"]):
        return "", 403
    if not (1 <= len(transaction_id) <= 80 and 1 <= len(notification_id) <= 128):
        return "", 400
    payment = PixPayment.query.filter_by(transaction_id=transaction_id).first()
    if payment is None:
        return "", 404
    try:
        result = notification(transaction_id, notification_id).get("status_request", {})
    except PagHiperError:
        return "", 503
    if result.get("result") != "success":
        return "", 400
    purchase = db.session.get(Purchase, payment.purchase_id)
    if purchase is None:
        return "", 404
    if (str(result.get("transaction_id")) != transaction_id
        or str(result.get("order_id")) != str(purchase.id)
        or str(result.get("value_cents")) != str(purchase.amount_cents)):
        return "", 409
    if result.get("status") in ("paid", "completed"):
        purchase.status = "paid"
        db.session.commit()
    return "", 200
