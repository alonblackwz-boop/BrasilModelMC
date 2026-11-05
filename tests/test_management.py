"""Testes do painel de administração e publicação."""
import unittest
from app import create_app
from models import db, User, Model3D

class ManagementTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        db.session.add_all([
            User(username="admin_m", email="admin_m@example.test", password_hash="x", role="admin"),
            User(username="buyer_m", email="buyer_m@example.test", password_hash="x", role="customer"),
        ])
        db.session.commit()
        self.admin_id = User.query.filter_by(username="admin_m").first().id
        self.buyer_id = User.query.filter_by(username="buyer_m").first().id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    def test_customer_cannot_create_model(self):
        self.login(self.buyer_id)
        response = self.client.post("/admin/api/models", json={"title":"Teste", "price_cents": 1000})
        self.assertEqual(response.status_code, 403)

    def test_admin_create_and_publish(self):
        self.login(self.admin_id)
        response = self.client.post("/admin/api/models", json={
            "title": "Helicóptero", "description": "Modelo 3D",
            "price_cents": 2990, "status": "draft"})
        self.assertEqual(response.status_code, 201)
        model_id = response.get_json()["id"]
        response = self.client.patch(f"/admin/api/models/{model_id}", json={"status": "published"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(db.session.get(Model3D, model_id).status, "published")

    def test_invalid_price_rejected(self):
        self.login(self.admin_id)
        response = self.client.post("/admin/api/models", json={"title": "Teste", "price_cents": -1})
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()
