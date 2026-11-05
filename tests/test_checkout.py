"""Testes de checkout: valores do banco, autenticação e isolamento dos pedidos."""
import unittest
from app import create_app
from models import db, User, Model3D, Purchase

class CheckoutTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        seller = User(username="seller2", email="seller2@example.test", password_hash="x")
        buyer = User(username="buyer2", email="buyer2@example.test", password_hash="x")
        other = User(username="other2", email="other2@example.test", password_hash="x")
        db.session.add_all([seller, buyer, other])
        db.session.flush()
        self.buyer_id, self.other_id = buyer.id, other.id
        model = Model3D(seller_id=seller.id, title="Helicóptero",
                        description="Modelo", price_cents=2990, status="published", file_path="test.bbmodel")
        db.session.add(model)
        db.session.commit()
        self.model_id = model.id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, user_id):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    def test_checkout_requires_login(self):
        response = self.client.post(f"/api/checkout/model/{self.model_id}")
        self.assertNotEqual(response.status_code, 201)

    def test_checkout_creates_pending_order(self):
        self.login(self.buyer_id)
        response = self.client.post(f"/api/checkout/model/{self.model_id}",
                                    json={"amount_cents": 1, "status": "paid"})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["amount_cents"], 2990)
        self.assertEqual(data["status"], "pending")
        self.assertFalse(data["payment_available"])
        order = db.session.get(Purchase, data["order_id"])
        self.assertEqual(order.status, "pending")

    def test_other_customer_cannot_read_order(self):
        self.login(self.buyer_id)
        order_id = self.client.post(f"/api/checkout/model/{self.model_id}").get_json()["order_id"]
        self.login(self.other_id)
        response = self.client.get(f"/api/checkout/orders/{order_id}")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
