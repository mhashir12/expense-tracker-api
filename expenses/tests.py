from decimal import Decimal

# Create your tests here.
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Expense

LIST_URL = "/api/expenses/"


def detail_url(pk):
    return f"/api/expenses/{pk}/"


def rows(response):
    """Works whether or not pagination is switched on."""
    data = response.data
    return data["results"] if isinstance(data, dict) and "results" in data else data


def make_expense(user, **overrides):
    data = {
        "user": user,
        "amount": Decimal("100.00"),
        "category": "food",
        "date": "2026-10-31",
        "place": "Canteen",
    }
    data.update(overrides)
    return Expense.objects.create(**data)


class AuthRequiredTests(APITestCase):
    def test_list_requires_login(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_login(self):
        payload = {"amount": "50.00", "category": "food", "date": "2026-10-31", "place": "X"}
        response = self.client.post(LIST_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IsolationTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="StrongPass123")
        self.bob = User.objects.create_user("bob", password="StrongPass123")
        self.alice_expense = make_expense(self.alice, place="Alice place")
        self.bob_expense = make_expense(self.bob, place="Bob place")

    def test_user_sees_only_own_expenses(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in rows(response)]
        self.assertEqual(ids, [self.alice_expense.id])

    def test_cannot_retrieve_another_users_expense(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get(detail_url(self.bob_expense.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_another_users_expense(self):
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            detail_url(self.bob_expense.id), {"place": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.bob_expense.refresh_from_db()
        self.assertEqual(self.bob_expense.place, "Bob place")

    def test_cannot_delete_another_users_expense(self):
        self.client.force_authenticate(self.alice)
        response = self.client.delete(detail_url(self.bob_expense.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Expense.objects.filter(id=self.bob_expense.id).exists())


class CreateAndValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="StrongPass123")
        self.other = User.objects.create_user("bob", password="StrongPass123")
        self.client.force_authenticate(self.user)
        self.valid = {
            "amount": "200.00",
            "category": "transport",
            "description": "Auto fare",
            "date": "2026-10-31",
            "place": "Mathura",
        }

    def test_create_expense_sets_logged_in_user(self):
        response = self.client.post(LIST_URL, self.valid, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Expense.objects.get(id=response.data["id"]).user, self.user)

    def test_user_field_in_payload_is_ignored(self):
        payload = {**self.valid, "user": self.other.id}
        response = self.client.post(LIST_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Expense.objects.get(id=response.data["id"]).user, self.user)

    def test_negative_amount_rejected(self):
        response = self.client.post(LIST_URL, {**self.valid, "amount": "-5.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_zero_amount_rejected(self):
        response = self.client.post(LIST_URL, {**self.valid, "amount": "0"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_category_rejected(self):
        response = self.client.post(LIST_URL, {**self.valid, "category": "Food"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_missing_required_fields_rejected(self):
        response = self.client.post(LIST_URL, {"description": "only this"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ("amount", "date", "place"):
            self.assertIn(field, response.data)


class RegistrationAndLoginTests(APITestCase):
    def test_register_creates_user_with_hashed_password(self):
        payload = {"username": "newuser", "email": "n@example.com", "password": "StrongPass123"}
        response = self.client.post("/api/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, "StrongPass123")
        self.assertTrue(user.check_password("StrongPass123"))
        self.assertNotIn("password", response.data)

    def test_register_rejects_short_password(self):
        payload = {"username": "newuser", "email": "n@example.com", "password": "abc"}
        response = self.client.post("/api/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens(self):
        User.objects.create_user("alice", password="StrongPass123")
        response = self.client.post(
            "/api/token/", {"username": "alice", "password": "StrongPass123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_fails(self):
        User.objects.create_user("alice", password="StrongPass123")
        response = self.client.post(
            "/api/token/", {"username": "alice", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_works_in_bearer_header(self):
        User.objects.create_user("alice", password="StrongPass123")
        token = self.client.post(
            "/api/token/", {"username": "alice", "password": "StrongPass123"}, format="json"
        ).data["access"]
        response = self.client.get(LIST_URL, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class SummaryTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="StrongPass123")
        self.bob = User.objects.create_user("bob", password="StrongPass123")
        make_expense(self.alice, amount=Decimal("100.00"), category="food")
        make_expense(self.alice, amount=Decimal("50.50"), category="food")
        make_expense(self.alice, amount=Decimal("200.00"), category="transport")
        make_expense(self.bob, amount=Decimal("999.00"), category="bills")

    def test_summary_requires_login(self):
        response = self.client.get("/api/expenses/summary/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summary_totals_are_correct(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get("/api/expenses/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["total"]), Decimal("350.50"))
        by_cat = {r["category"]: Decimal(r["total"]) for r in response.data["by_category"]}
        self.assertEqual(by_cat, {"food": Decimal("150.50"), "transport": Decimal("200.00")})

    def test_summary_excludes_other_users_data(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get("/api/expenses/summary/")
        categories = [r["category"] for r in response.data["by_category"]]
        self.assertNotIn("bills", categories)  