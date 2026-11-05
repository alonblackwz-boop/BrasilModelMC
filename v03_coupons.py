"""Cupons v0.3: cálculo seguro de desconto em centavos.

Integração: from v03_coupons import init_coupons, quote_coupon
           init_coupons(db)
           quote_coupon(db, code, subtotal_cents)
O consumo deve ocorrer na MESMA transação da confirmação do pagamento.
"""
from datetime import datetime, timezone

def init_coupons(db):
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            kind TEXT NOT NULL CHECK(kind IN ('percent','fixed')),
            amount INTEGER NOT NULL CHECK(amount > 0),
            max_uses INTEGER,
            uses INTEGER NOT NULL DEFAULT 0,
            expires_at TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            CHECK(max_uses IS NULL OR max_uses > 0)
        )""")

def quote_coupon(db, code, subtotal_cents):
    """Retorna desconto e total, sem resgatar o cupom."""
    if not isinstance(subtotal_cents, int) or subtotal_cents < 0:
        raise ValueError("Subtotal inválido")
    code = (code or "").strip()
    if not code or len(code) > 64:
        return None
    with db() as con:
        row = con.execute(
            "SELECT * FROM coupons WHERE code=? COLLATE NOCASE AND active=1",
            (code,)
        ).fetchone()
    if not row or (row["max_uses"] is not None and row["uses"] >= row["max_uses"]):
        return None
    if row["expires_at"]:
        try:
            expiration = datetime.fromisoformat(row["expires_at"].replace("Z","+00:00"))
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            if expiration <= datetime.now(timezone.utc):
                return None
        except ValueError:
            return None
    if row["kind"] == "percent":
        if row["amount"] > 100:
            return None
        discount = subtotal_cents * row["amount"] // 100
    else:
        discount = min(subtotal_cents, row["amount"])
    return {"coupon_id": row["id"], "discount_cents": discount,
            "total_cents": subtotal_cents - discount}
