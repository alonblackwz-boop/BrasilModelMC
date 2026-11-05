"""Cliente Pix PagHiper. Nunca registrar credenciais nem dados do pagador em logs."""
import os
import requests

BASE = "https://pix.paghiper.com/invoice/"
class PagHiperError(Exception):
    pass

def configured():
    return bool(os.environ.get("PAGHIPER_API_KEY") and os.environ.get("PAGHIPER_TOKEN"))

def request_api(action, payload):
    if action not in {"create", "status", "notification"}:
        raise ValueError("Ação não permitida")
    if not configured():
        raise PagHiperError("Credenciais PagHiper não configuradas")
    try:
        response = requests.post(
            BASE + action + "/",
            json=payload,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Resposta inesperada")
        return result
    except (requests.RequestException, ValueError) as exc:
        raise PagHiperError("Não foi possível validar a resposta do PagHiper") from exc

def create_pix(order_id, title, amount_cents, email, name, document, callback_url):
    return request_api("create", {
        "apiKey": os.environ["PAGHIPER_API_KEY"],
        "order_id": str(order_id),
        "payer_email": email,
        "payer_name": name,
        "payer_cpf_cnpj": document,
        "days_due_date": "1",
        "notification_url": callback_url,
        "items": [{
            "item_id": str(order_id),
            "description": title[:180],
            "quantity": "1",
            "price_cents": str(amount_cents),
        }],
    })

def notification(transaction_id, notification_id):
    return request_api("notification", {
        "apiKey": os.environ["PAGHIPER_API_KEY"],
        "token": os.environ["PAGHIPER_TOKEN"],
        "transaction_id": transaction_id,
        "notification_id": notification_id,
    })

def status(transaction_id):
    return request_api("status", {
        "apiKey": os.environ["PAGHIPER_API_KEY"],
        "token": os.environ["PAGHIPER_TOKEN"],
        "transaction_id": transaction_id,
    })
