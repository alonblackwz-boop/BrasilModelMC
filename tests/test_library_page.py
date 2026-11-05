"""Testes de navegação e persistência de acesso após arquivamento."""
import io
import tempfile
import unittest
from app import create_app
from models import db, User, Model3D, Purchase

class LibraryPageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False, "PRIVATE_MODELS_DIR": self.temp.name})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        user = User(username="lib_user", email="lib_user@example.test", password_hash="x")
        db.session.add(user)
        db.session.flush()
        self.user_id = user.id
        model = Model3D(seller_id=user.id, title="Modelo arquivado", description="",
                        price_cents=900, status="archived", file_path="asset.bbmodel")
        db.session.add(model)
        db.session.commit()
        self.model_id = model.id
        with open(self.temp.name + "/asset.bbmodel", "wb") as f:
            f.write(b"test")
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.temp.cleanup()

    def login(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.user_id)
            session["_fresh"] = True

    def test_archived_paid_purchase_stays_downloadable(self):
        self.login()
        self.assertEqual(self.client.get("/api/library/" + str(self.model_id) + "/download").status_code, 403)
        db.session.add(Purchase(buyer_id=self.user_id, model_id=self.model_id,
                                amount_cents=900, status="paid"))
        db.session.commit()
        self.assertEqual(self.client.get("/api/library/" + str(self.model_id) + "/download").status_code, 200)
        response = self.client.get("/minha-biblioteca")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Modelo arquivado".encode(), response.data)

if __name__ == "__main__":
    unittest.main()
