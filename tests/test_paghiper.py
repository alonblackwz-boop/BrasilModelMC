"""Webhook PagHiper não pode liberar compra sem conferência remota."""
import os
import unittest
from unittest.mock import patch
from app import create_app
from models import db, User, Model3D, Purchase, PixPayment

class PagHiperWebhookTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        user = User(username="pixbuyer", email="pixbuyer@example.test", password_hash="x")
        db.session.add(user)
        db.session.flush()
        model = Model3D(seller_id=user.id, title="Modelo", description="Arquivo",
                        price_cents=2990, status="published", file_path="model.zip")
        db.session.add(model)
        db.session.flush()
        purchase = Purchase(buyer_id=user.id, model_id=model.id, amount_cents=2990)
        db.session.add(purchase)
        db.session.flush()
        self.purchase_id = purchase.id
        db.session.add(PixPayment(purchase_id=purchase.id, transaction_id="tx-001"))
        db.session.commit()
        self.client = self.app.test_client()
        self.environment = patch.dict(os.environ, {"PAGHIPER_API_KEY": "test-api-key",
                                                    "PAGHIPER_TOKEN": "test-token"})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def send(self, key="test-api-key"):
        return self.client.post("/webhooks/paghiper/pix", data={
            "apiKey": key, "transaction_id": "tx-001", "notification_id": "notification-001"})

    def status(self):
        db.session.expire_all()
        return db.session.get(Purchase, self.purchase_id).status

    def test_wrong_key_rejected(self):
        self.assertEqual(self.send(key="wrong").status_code, 403)
        self.assertEqual(self.status(), "pending")

    @patch("routes_paghiper.notification")
    def test_wrong_amount_never_marks_paid(self, mock_notification):
        mock_notification.return_value = {"status_request": {
            "result": "success", "transaction_id": "tx-001",
            "order_id": str(self.purchase_id), "value_cents": "1", "status": "paid"}}
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(self.status(), "pending")

    @patch("routes_paghiper.notification")
    def test_confirmed_payment_is_idempotent(self, mock_notification):
        mock_notification.return_value = {"status_request": {
            "result": "success", "transaction_id": "tx-001",
            "order_id": str(self.purchase_id), "value_cents": "2990", "status": "paid"}}
        self.assertEqual(self.send().status_code, 200)
        self.assertEqual(self.send().status_code, 200)
        self.assertEqual(self.status(), "paid")

if __name__ == "__main__":
    unittest.main()
