"""Sugestões de modelos para o BrasilModelMC v0.3.

Apenas usuários autenticados podem sugerir. Sugestões públicas não revelam e-mail.
O prazo de 15 dias é calculado no servidor e não depende do navegador.
"""
from datetime import datetime, timedelta, timezone
from flask import request, session, abort, redirect, url_for, flash, render_template_string

PAGE = """{% extends 'base.html' %}{% block title %}Sugestões — BrasilModelMC{% endblock %}
{% block content %}<section class="container"><h1>Sugestões de modelos</h1>
<p>Peça um modelo para Minecraft. As solicitações ficam abertas por 15 dias.</p>
{% if current_user %}<form method="post" action="{{url_for('create_suggestion')}}">
<input type="hidden" name="_csrf" value="{{csrf_token()}}">
<label>Título <input name="title" required maxlength="120"></label>
<label>Descrição <textarea name="description" required maxlength="2000"></textarea></label>
<button class="btn" type="submit">Enviar sugestão</button></form>
{% else %}<p><a href="{{url_for('login')}}">Entre na sua conta</a> para sugerir.</p>{% endif %}
{% for item in items %}<article class="card"><h2>{{item.title}}</h2>
<p>{{item.description}}</p><small>Por {{item.username}} · {{item.status}} · até {{item.deadline[:10]}}</small>
</article>{% else %}<p>Nenhuma sugestão cadastrada.</p>{% endfor %}
</section>{% endblock %}"""

def install(app, db, login_required):
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS suggestions (
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id),
          title TEXT NOT NULL CHECK(length(title) BETWEEN 5 AND 120),
          description TEXT NOT NULL CHECK(length(description) BETWEEN 10 AND 2000),
          created_at TEXT NOT NULL,
          deadline TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open'
          CHECK(status IN ('open','completed','closed'))
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_created ON suggestions(created_at)")

    @app.get('/suggestions')
    def suggestions():
        now=datetime.now(timezone.utc).isoformat()
        with db() as con:
            rows=con.execute("""SELECT s.id,s.title,s.description,s.deadline,
                CASE WHEN s.status='open' AND s.deadline<=? THEN 'closed'
                ELSE s.status END AS status, u.username
                FROM suggestions s JOIN users u ON u.id=s.user_id
                ORDER BY s.id DESC LIMIT 100""",(now,)).fetchall()
        return render_template_string(PAGE,items=rows)

    @app.post('/suggestions')
    @login_required
    def create_suggestion():
        title=request.form.get('title','').strip()
        description=request.form.get('description','').strip()
        if not (5<=len(title)<=120 and 10<=len(description)<=2000):
            abort(400, 'Título ou descrição inválidos.')
        now=datetime.now(timezone.utc)
        with db() as con:
            con.execute("""INSERT INTO suggestions
                (user_id,title,description,created_at,deadline)
                VALUES(?,?,?,?,?)""",(session['uid'],title,description,
                    now.isoformat(),(now+timedelta(days=15)).isoformat()))
        flash('Sugestão enviada com sucesso.','success')
        return redirect(url_for('suggestions'))
