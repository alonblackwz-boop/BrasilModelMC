"""Testes do upload privado e download condicionado a compra paga."""
import io
import tempfile
import unittest
from flask import g
from app import create_app
from models import db, User, Model3D, Purchase

class FilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False, "PRIVATE_MODELS_DIR": self.temp.name,
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(username="files_admin", email="files_admin@example.test",
                     password_hash="x", role="admin")
        buyer = User(username="files_buyer", email="files_buyer@example.test",
                     password_hash="x", role="customer")
        db.session.add_all([admin, buyer])
        db.session.flush()
        self.admin_id, self.buyer_id = admin.id, buyer.id
        model = Model3D(seller_id=admin.id, title="Teste 3D", description="Arquivo",
                        price_cents=1200, status="published")
        db.session.add(model)
        db.session.commit()
        self.model_id = model.id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.temp.cleanup()

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        g.pop("_login_user", None)

    def test_upload_and_paid_download(self):
        self.login(self.admin_id)
        upload = self.client.post(f"/admin/api/models/{self.model_id}/upload",
                                  data={"file": (io.BytesIO(b"model content"), "asset.bbmodel")})
        self.assertEqual(upload.status_code, 201)
        self.login(self.buyer_id)
        url = f"/api/library/{self.model_id}/download"
        self.assertEqual(self.client.get(url).status_code, 403)
        db.session.add(Purchase(buyer_id=self.buyer_id, model_id=self.model_id,
                                amount_cents=1200, status="paid"))
        db.session.commit()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"model content")

    def test_customer_cannot_upload(self):
        self.login(self.buyer_id)
        response = self.client.post(f"/admin/api/models/{self.model_id}/upload",
                                    data={"file": (io.BytesIO(b"data"), "asset.zip")})
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
