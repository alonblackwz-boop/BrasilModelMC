"""Estrutura de pedidos Pix para integração PagHiper.

Não cria cobranças reais sem configuração e integração validada com o provedor.
Valores sempre são calculados no servidor a partir do modelo publicado.
"""
from datetime import datetime, timezone
from flask import Blueprint, abort, jsonify
from flask_login import current_user, login_required
from models import db, Model3D, Purchase

checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/checkout")

@checkout_bp.post("/model/<int:model_id>")
@login_required
def create_checkout(model_id):
    model = db.session.get(Model3D, model_id)
    if model is None or model.status != "published":
        abort(404)
    if model.price_cents < 0:
        abort(409, "Preço inválido")
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
