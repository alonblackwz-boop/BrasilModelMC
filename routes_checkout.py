"""Estrutura de pedidos Pix para integração PagHiper.

Não cria cobranças reais sem configuração e integração validada com o provedor.
Valores sempre são calculados no servidor a partir do modelo publicado.
"""
from flask import Blueprint, abort, jsonify, render_template, current_app
from pathlib import Path
from flask_login import current_user, login_required
from models import db, Model3D, Purchase

checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/checkout")

def deliverable(model):
    if not model or not model.file_path:
        return False
    root = Path(current_app.config["PRIVATE_MODELS_DIR"]).resolve()
    path = (root / model.file_path).resolve()
    return path != root and root in path.parents and path.is_file()


@checkout_bp.post("/model/<int:model_id>")
@login_required
def create_checkout(model_id):
    model = db.session.get(Model3D, model_id)
    if model is None or model.status != "published":
        abort(404)
    if model.price_cents < 0:
        abort(409, "Preço inválido")
    if not deliverable(model):
        return jsonify({"error": "Este modelo ainda não possui arquivo disponível."}), 409
    if model.price_cents == 0:
        return jsonify({"error": "Modelo gratuito: use o fluxo de aquisição gratuita."}), 409
    if model.price_cents < 300:
        return jsonify({"error": "Valor abaixo do mínimo para Pix."}), 409
    # Não é seguro marcar pedidos como pagos antes da confirmação do provedor.
    # Uma integração real deve salvar a referência externa e validar valor/status
    # pela API autenticada do PagHiper antes de conceder acesso ao arquivo.
    order = Purchase(
        buyer_id=current_user.id,
        model_id=model.id,
        amount_cents=model.price_cents,
        status="pending",
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({
        "order_id": order.id,
        "status": "pending",
        "amount_cents": order.amount_cents,
        "payment_available": False,
        "message": "Pedido registrado. A emissão Pix aguarda ativação segura do PagHiper.",
    }), 201

@checkout_bp.get("/orders/<int:order_id>")
@login_required
def order_status(order_id):
    order = db.session.get(Purchase, order_id)
    if order is None or order.buyer_id != current_user.id:
        abort(404)
    return jsonify({"order_id": order.id, "status": order.status,
                    "amount_cents": order.amount_cents, "model_id": order.model_id})

@checkout_bp.post("/orders/<int:order_id>/pix")
@login_required
def issue_pix(order_id):
    import os
    from flask import request
    from models import PixPayment
    from paghiper import create_pix, PagHiperError, configured
    order = db.session.get(Purchase, order_id)
    if order is None or order.buyer_id != current_user.id:
        abort(404)
    existing = PixPayment.query.filter_by(purchase_id=order.id).first()
    if existing:
        return jsonify({"order_id": order.id, "status": order.status,
                        "pix_code": existing.pix_emv, "qr_image_url": existing.qr_image_url})
    if order.status != "pending":
        return jsonify({"error": "Pedido não está pendente"}), 409
    if not configured() or os.environ.get("PAGHIPER_PIX_ENABLED") != "true":
        return jsonify({"error": "Pix não está habilitado nesta loja"}), 503
    data = request.get_json(silent=True) or {}
    name = str(data.get("payer_name", "")).strip()
    document = "".join(c for c in str(data.get("payer_cpf_cnpj", "")) if c.isdigit())
    if not 3 <= len(name) <= 120 or len(document) not in (11, 14):
        return jsonify({"error": "Dados do pagador inválidos"}), 400
    model = db.session.get(Model3D, order.model_id)
    if not deliverable(model):
        return jsonify({"error": "Modelo sem arquivo para entrega."}), 409
    callback_url = os.environ.get("PAGHIPER_NOTIFICATION_URL", "")
    if not callback_url.startswith("https://"):
        return jsonify({"error": "Configure uma URL HTTPS para notificações"}), 503
    try:
        result = create_pix(order.id, model.title, order.amount_cents,
                            current_user.email, name, document, callback_url)
    except PagHiperError:
        return jsonify({"error": "PagHiper indisponível"}), 503
    response = result.get("create_request", {})
    pix = response.get("bank_slip") or {}
    transaction = str(response.get("transaction_id", ""))
    if response.get("result") != "success" or not transaction or not pix.get("digitable_line"):
        return jsonify({"error": "PagHiper não retornou uma cobrança válida"}), 502
    payment = PixPayment(purchase_id=order.id, transaction_id=transaction,
                         pix_emv=pix.get("emv"), qr_image_url=pix.get("url_slip"))
    db.session.add(payment)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Falha ao registrar cobrança; contate o suporte antes de tentar novamente"}), 409
    return jsonify({"order_id": order.id, "status": "pending",
                    "pix_code": payment.pix_emv, "qr_image_url": payment.qr_image_url}), 201

@checkout_bp.get("/orders/<int:order_id>/page")
@login_required
def checkout_page(order_id):
    order = db.session.get(Purchase, order_id)
    if order is None or order.buyer_id != current_user.id:
        abort(404)
    model = db.session.get(Model3D, order.model_id)
    return render_template("checkout.html", order=order, model=model)
