"""Módulo v0.3: avaliações de compras verificadas.

Integração no app.py:
    from v03_reviews import init_reviews
    init_reviews(app, db, login_required)
"""
import sqlite3
from flask import request, session, redirect, url_for, abort, flash, render_template_string

def init_reviews(app, db, login_required):
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)")

    @app.post("/product/<int:pid>/review")
    @login_required
    def submit_review(pid):
        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            abort(400)
        comment = request.form.get("comment", "").strip()
        if not 1 <= rating <= 5 or len(comment) > 1500:
            abort(400)
        uid = session["uid"]
        with db() as con:
            purchased = con.execute(
                "SELECT 1 FROM licenses WHERE user_id=? AND product_id=?",
                (uid, pid)
            ).fetchone()
            if not purchased:
                abort(403, "Somente compradores podem avaliar este modelo.")
            try:
                con.execute(
                    """INSERT INTO reviews(user_id,product_id,rating,comment)
                       VALUES(?,?,?,?)
                       ON CONFLICT(user_id,product_id) DO UPDATE SET
                       rating=excluded.rating, comment=excluded.comment""",
                    (uid, pid, rating, comment)
                )
            except sqlite3.IntegrityError:
                abort(400)
        flash("Avaliação salva.", "success")
        return redirect(url_for("product", pid=pid))

    @app.get("/api/products/<int:pid>/reviews")
    def list_reviews(pid):
        from flask import jsonify
        with db() as con:
            rows = con.execute(
                """SELECT u.username, r.rating, r.comment, r.created_at
                   FROM reviews r JOIN users u ON u.id=r.user_id
                   JOIN products p ON p.id=r.product_id
                   WHERE r.product_id=? AND p.status='published'
                   ORDER BY r.id DESC LIMIT 100""", (pid,)
            ).fetchall()
        return jsonify([dict(r) for r in rows])
