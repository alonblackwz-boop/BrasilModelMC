"""Testes de autorização para endpoints administrativos."""
import unittest
from app import create_app
from models import db, User

class AdminTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        regular = User(username="regular", email="regular@example.test", password_hash="x", role="customer")
        admin = User(username="admin", email="admin@example.test", password_hash="x", role="admin")
        db.session.add_all([regular, admin])
        db.session.commit()
        self.regular_id, self.admin_id = regular.id, admin.id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, uid):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(uid)
            session["_fresh"] = True

    def test_anonymous_denied(self):
        self.assertNotEqual(self.client.get("/api/admin/overview").status_code, 200)

    def test_regular_user_forbidden(self):
        self.login(self.regular_id)
        self.assertEqual(self.client.get("/api/admin/overview").status_code, 403)

    def test_admin_allowed(self):
        self.login(self.admin_id)
        response = self.client.get("/api/admin/overview")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["users"], 2)

if __name__ == "__main__":
    unittest.main()
