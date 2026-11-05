"""Cadastro, entrada e saída com Flask-Login e senhas hash."""
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from models import db, User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/entrar", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(db.func.lower(User.email) == identifier).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=False)
            return redirect(url_for("index"))
        flash("E-mail ou senha inválidos.", "error")
    return render_template("auth.html", mode="login")

@auth_bp.route("/cadastrar", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not 3 <= len(username) <= 60 or not 5 <= len(email) <= 255 or "@" not in email or not 12 <= len(password) <= 128:
            flash("Confira seus dados. A senha precisa ter pelo menos 12 caracteres.", "error")
        else:
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Nome de usuário ou e-mail já cadastrado.", "error")
            else:
                login_user(user)
                return redirect(url_for("index"))
    return render_template("auth.html", mode="register")

@auth_bp.post("/sair")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
