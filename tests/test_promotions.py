"""Testes de permissões e exibição da faixa promocional."""
import unittest
from flask import g
from app import create_app
from models import db, User, Coupon, Setting

class PromotionTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        db.session.add_all([
            User(username="promo_admin", email="promo_admin@example.test", password_hash="x", role="admin"),
            User(username="promo_customer", email="promo_customer@example.test", password_hash="x", role="customer")
        ])
        db.session.commit()
        self.admin_id = User.query.filter_by(username="promo_admin").first().id
        self.customer_id = User.query.filter_by(username="promo_customer").first().id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        g.pop("_login_user", None)

    def test_only_admin_can_manage_promotions(self):
        self.login(self.customer_id)
        self.assertEqual(self.client.get("/api/coupons/admin").status_code, 403)
        self.assertEqual(self.client.post("/api/coupons/admin", json={
            "code": "BMC20", "discount_type": "percent", "discount_value": 20}).status_code, 403)
        self.assertEqual(self.client.put("/api/coupons/admin/promotion", json={
            "enabled": False, "coupon_id": None, "message": ""}).status_code, 403)

    def test_create_show_and_hide_when_exhausted(self):
        self.login(self.admin_id)
        response = self.client.post("/api/coupons/admin", json={
            "code": "BMC20", "discount_type": "percent", "discount_value": 20,
            "max_uses": 1})
        self.assertEqual(response.status_code, 201)
        coupon_id = response.get_json()["id"]
        response = self.client.put("/api/coupons/admin/promotion", json={
            "enabled": True, "coupon_id": coupon_id, "message": "Oferta especial!"})
        self.assertEqual(response.status_code, 200)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Oferta especial!", html)
        self.assertIn("BMC20", html)
        coupon = db.session.get(Coupon, coupon_id)
        coupon.used_count = 1
        db.session.commit()
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("Oferta especial!", html)

    def test_invalid_coupon_cannot_be_promoted(self):
        self.login(self.admin_id)
        response = self.client.put("/api/coupons/admin/promotion", json={
            "enabled": True, "coupon_id": 9999, "message": "Cupom falso"})
        self.assertEqual(response.status_code, 409)

if __name__ == "__main__":
    unittest.main()
