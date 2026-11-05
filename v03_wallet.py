"""Carteira v0.3: livro-razão de créditos internos, sem pagamentos reais.

Os saldos são calculados a partir de lançamentos imutáveis em centavos.
Créditos administrativos e débitos precisam de uma transação autenticada.
Não é uma integração Pix nem autoriza saques.
"""
import sqlite3

def install_wallet(db):
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS wallet_entries(
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id),
          amount_cents INTEGER NOT NULL CHECK(amount_cents != 0),
          reason TEXT NOT NULL CHECK(length(reason) BETWEEN 3 AND 200),
          reference TEXT UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_wallet_user ON wallet_entries(user_id,id)")

def balance(db, user_id):
    with db() as con:
        row=con.execute("SELECT COALESCE(SUM(amount_cents),0) AS cents FROM wallet_entries WHERE user_id=?",(user_id,)).fetchone()
        return int(row["cents"])

def debit(db, user_id, amount_cents, reason, reference):
    """Debita de forma atômica, rejeitando saldo insuficiente.

    A referência idempotente deve ser única por operação. Chamadores devem
    associá-la ao pedido real, nunca a dados arbitrários do navegador.
    """
    if not isinstance(amount_cents,int) or amount_cents<=0 or not reference:
        raise ValueError("Débito inválido")
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        old=con.execute("SELECT amount_cents FROM wallet_entries WHERE reference=?",(reference,)).fetchone()
        if old:
            if old["amount_cents"] != -amount_cents:
                raise ValueError("Referência reutilizada com valor diferente")
            return False
        current=con.execute("SELECT COALESCE(SUM(amount_cents),0) FROM wallet_entries WHERE user_id=?",(user_id,)).fetchone()[0]
        if current<amount_cents:
            raise ValueError("Saldo insuficiente")
        con.execute("INSERT INTO wallet_entries(user_id,amount_cents,reason,reference) VALUES(?,?,?,?)",
                    (user_id,-amount_cents,reason,reference))
    return True

def credit(db, user_id, amount_cents, reason, reference):
    """Uso exclusivo por rotinas internas autorizadas após validação externa."""
    if not isinstance(amount_cents,int) or amount_cents<=0 or not reference:
        raise ValueError("Crédito inválido")
    with db() as con:
        con.execute("INSERT OR IGNORE INTO wallet_entries(user_id,amount_cents,reason,reference) VALUES(?,?,?,?)",
                    (user_id,amount_cents,reason,reference))
        return con.execute("SELECT changes()").fetchone()[0] == 1
