import json
import uuid

import stripe
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.user import Plan
import backend.auth.router as router


@pytest.fixture
def client():
    return TestClient(app)


def register_user(client, email=None):
    email = email or f"test+{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    token = data["access_token"]
    user = data["user"]
    return token, user


def test_webhook_with_metadata_plan(client, monkeypatch):
    token, user = register_user(client)

    # Build event where session.metadata.plan is present
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"], "plan": "PRO"},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        },
    }

    # Mock stripe.Webhook.construct_event to return our event
    def fake_construct_event(payload, sig, secret):
        return event

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    resp = client.post(
        "/auth/stripe/webhook",
        data=json.dumps(event),
        headers={"stripe-signature": "t=1,v1=fake"},
    )
    assert resp.status_code == 200

    # Verify user's plan updated via /auth/me
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["plan"] == Plan.PRO.value


def test_webhook_without_metadata_uses_subscription(client, monkeypatch):
    token, user = register_user(client)

    # Ensure PRICE_TO_PLAN contains a known price id
    price_id = "price_test_123"
    router.PRICE_TO_PLAN[price_id] = Plan.PRO

    # Build event WITHOUT metadata.plan but with subscription
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"]},
                "customer": "cus_test",
                "subscription": "sub_no_meta",
            }
        },
    }

    # Mock construct_event
    def fake_construct_event(payload, sig, secret):
        return event

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    # Mock stripe.Subscription.retrieve to return an items->data->[0]->price->id
    def fake_subscription_retrieve(sub_id):
        return {"items": {"data": [{"price": {"id": price_id}}]}}

    monkeypatch.setattr(stripe.Subscription, "retrieve", fake_subscription_retrieve)

    resp = client.post(
        "/auth/stripe/webhook",
        data=json.dumps(event),
        headers={"stripe-signature": "t=1,v1=fake"},
    )
    assert resp.status_code == 200

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["plan"] == Plan.PRO.value


def test_customer_subscription_deleted_downgrades_user(client, monkeypatch):
    # create user and set subscription/customer ids
    token, user = register_user(client)

    # first, simulate that the user has a stripe_customer_id so lookup works
    # perform an upgrade via metadata to set a non-free plan
    event_upgrade = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"], "plan": "PRO"},
                "customer": "cus_delete_test",
                "subscription": "sub_delete_test",
            }
        },
    }

    def fake_construct_event_upgrade(payload, sig, secret):
        return event_upgrade

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event_upgrade)
    resp = client.post(
        "/auth/stripe/webhook",
        data=json.dumps(event_upgrade),
        headers={"stripe-signature": "t=1,v1=fake"},
    )
    assert resp.status_code == 200

    # sanity check user is PRO
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["plan"] == Plan.PRO.value

    # Now simulate subscription deletion event for that customer
    event_delete = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_delete_test"}},
    }

    def fake_construct_event_delete(payload, sig, secret):
        return event_delete

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event_delete)

    resp2 = client.post(
        "/auth/stripe/webhook",
        data=json.dumps(event_delete),
        headers={"stripe-signature": "t=1,v1=fake"},
    )
    assert resp2.status_code == 200

    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me2.json()["plan"] == Plan.FREE.value
