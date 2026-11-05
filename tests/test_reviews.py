"""Testes de integração da API de avaliações.

Execute: python -m unittest discover -s tests -v
"""
import unittest
from app import create_app
from models import db, User, Category, Model3D, Purchase

class ReviewsTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        seller = User(username="seller", email="seller@example.test", password_hash="test")
        buyer = User(username="buyer", email="buyer@example.test", password_hash="test")
        db.session.add_all([seller, buyer])
        db.session.flush()
        self.seller_id = seller.id
        self.buyer_id = buyer.id
        model = Model3D(seller_id=seller.id, title="Modelo teste",
                        description="Teste", status="published", price_cents=100)
        db.session.add(model)
        db.session.commit()
        self.model_id = model.id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(self.buyer_id)
            sess["_fresh"] = True

    def test_anonymous_cannot_review(self):
        res = self.client.post(f"/api/models/{self.model_id}/reviews", json={"rating":5})
        self.assertNotEqual(res.status_code, 200)

    def test_unpaid_cannot_review(self):
        self.login()
        res = self.client.post(f"/api/models/{self.model_id}/reviews", json={"rating":5})
        self.assertEqual(res.status_code, 403)

    def test_paid_review_and_update(self):
        db.session.add(Purchase(buyer_id=self.buyer_id, model_id=self.model_id,
                                amount_cents=100, status="paid"))
        db.session.commit()
        self.login()
        endpoint = f"/api/models/{self.model_id}/reviews"
        self.assertEqual(self.client.post(endpoint, json={"rating":5,"comment":"Ótimo"}).status_code, 200)
        self.assertEqual(self.client.post(endpoint, json={"rating":4}).status_code, 200)
        result = self.client.get(endpoint).get_json()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["average"], 4.0)

    def test_rating_validation(self):
        self.login()
        endpoint = f"/api/models/{self.model_id}/reviews"
        for value in [0, 6, True, "5"]:
            self.assertEqual(self.client.post(endpoint, json={"rating":value}).status_code, 400)

if __name__ == "__main__":
    unittest.main()
