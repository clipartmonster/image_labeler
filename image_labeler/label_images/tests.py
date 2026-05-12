"""Tests for workforce management: permissions, accuracy, agreement/adjudication."""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from .models import (
    BatchAssignment, LabelingSession,
    GoldStandardLabel, AdjudicationDecision,
)


class _UserMixin:
    """Create admin and labeler users for test cases."""

    def _make_admin(self, username="admin1"):
        user = User.objects.create_user(username=username, password="pass1234")
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user

    def _make_labeler(self, username="labeler1", is_staff=True):
        user = User.objects.create_user(username=username, password="pass1234")
        user.is_staff = is_staff
        user.save()
        return user


# ======================================================================
# Permission enforcement
# ======================================================================

class PermissionTests(_UserMixin, TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = self._make_admin()
        self.labeler = self._make_labeler()

    # --- Admin pages reject labelers ---

    def test_admin_labeler_list_forbidden_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.get("/label_images/admin/labelers/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bulk_assign_forbidden_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.get("/label_images/admin/bulk_assign/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_performance_forbidden_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.get("/label_images/admin/performance/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_adjudication_forbidden_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.get("/label_images/admin/adjudication/")
        self.assertEqual(resp.status_code, 403)

    # --- Admin pages allow admins ---

    def test_admin_labeler_list_allowed_for_admin(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.get("/label_images/admin/labelers/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_performance_allowed_for_admin(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.get("/label_images/admin/performance/")
        self.assertEqual(resp.status_code, 200)

    # --- Labeler pages reject admins ---

    def test_labeler_earnings_forbidden_for_admin(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.get("/label_images/earnings/")
        self.assertEqual(resp.status_code, 403)

    # --- Labeler pages allow labelers ---

    def test_labeler_earnings_allowed_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.get("/label_images/earnings/")
        self.assertEqual(resp.status_code, 200)

    # --- Unauthenticated redirect ---

    def test_unauthenticated_redirects_to_login(self):
        for url in ["/label_images/admin/labelers/", "/label_images/earnings/"]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, msg=f"{url} should redirect")
            self.assertIn("/accounts/login/", resp.url)

    # --- AJAX endpoints enforce admin ---

    def test_toggle_staff_forbidden_for_labeler(self):
        self.client.login(username="labeler1", password="pass1234")
        resp = self.client.post(
            "/label_images/admin/labelers/toggle_staff/",
            data=json.dumps({"user_id": self.labeler.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_toggle_staff_works_for_admin(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.post(
            "/label_images/admin/labelers/toggle_staff/",
            data=json.dumps({"user_id": self.labeler.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_staff"])  # toggled from True → False


# ======================================================================
# Accuracy computation
# ======================================================================

class AccuracyComputationTests(_UserMixin, TestCase):
    """Test gold-standard accuracy logic used in admin_performance_data."""

    databases = {"default"}

    def setUp(self):
        self.admin = self._make_admin()
        self.labeler = self._make_labeler()
        self.client = Client()

        # Gold labels
        GoldStandardLabel.objects.create(
            asset_id=1001, task_type="asset_type", rule_index=1, correct_response="yes",
        )
        GoldStandardLabel.objects.create(
            asset_id=1002, task_type="asset_type", rule_index=1, correct_response="no",
        )
        GoldStandardLabel.objects.create(
            asset_id=1003, task_type="asset_type", rule_index=1, correct_response="yes",
        )

    def _compute_accuracy(self, responses):
        """Replicate the accuracy logic from admin_performance_data.

        `responses` is a list of (asset_id, task_type, rule_index, prompt_response).
        Returns (gold_total, gold_correct, accuracy_pct_or_none).
        """
        gold_labels = {
            (g.asset_id, g.task_type, g.rule_index): g.correct_response
            for g in GoldStandardLabel.objects.all()
        }
        gold_total = 0
        gold_correct = 0
        for asset_id, task_type, rule_index, response in responses:
            key = (asset_id, task_type, rule_index)
            if key in gold_labels:
                gold_total += 1
                if response == gold_labels[key]:
                    gold_correct += 1
        accuracy = round(gold_correct / gold_total * 100, 1) if gold_total > 0 else None
        return gold_total, gold_correct, accuracy

    def test_perfect_accuracy(self):
        responses = [
            (1001, "asset_type", 1, "yes"),
            (1002, "asset_type", 1, "no"),
            (1003, "asset_type", 1, "yes"),
        ]
        total, correct, pct = self._compute_accuracy(responses)
        self.assertEqual(total, 3)
        self.assertEqual(correct, 3)
        self.assertEqual(pct, 100.0)

    def test_partial_accuracy(self):
        responses = [
            (1001, "asset_type", 1, "yes"),   # correct
            (1002, "asset_type", 1, "yes"),   # wrong (gold=no)
            (1003, "asset_type", 1, "yes"),   # correct
        ]
        total, correct, pct = self._compute_accuracy(responses)
        self.assertEqual(total, 3)
        self.assertEqual(correct, 2)
        self.assertAlmostEqual(pct, 66.7, places=1)

    def test_no_gold_overlap(self):
        responses = [
            (9999, "other_type", 1, "yes"),
        ]
        total, correct, pct = self._compute_accuracy(responses)
        self.assertEqual(total, 0)
        self.assertIsNone(pct)

    def test_all_wrong(self):
        responses = [
            (1001, "asset_type", 1, "no"),   # wrong
            (1002, "asset_type", 1, "yes"),  # wrong
        ]
        total, correct, pct = self._compute_accuracy(responses)
        self.assertEqual(total, 2)
        self.assertEqual(correct, 0)
        self.assertEqual(pct, 0.0)


# ======================================================================
# Agreement / adjudication logic
# ======================================================================

class AgreementAdjudicationTests(_UserMixin, TestCase):
    """Test the disagreement detection logic and adjudication saves."""

    def setUp(self):
        self.admin = self._make_admin()
        self.client = Client()

    def _compute_agreement(self, responses_by_asset):
        """Replicate disagreement detection from admin_adjudication_list.

        `responses_by_asset` is a dict:
            {(asset_id, task_type, rule_index): [response1, response2, ...]}
        Returns list of disagreement dicts.
        """
        disagreements = []
        for (asset_id, task_type, rule_index), responses in responses_by_asset.items():
            total = len(responses)
            if total < 2:
                continue
            yes_count = sum(1 for r in responses if r == "yes")
            no_count = total - yes_count
            majority = max(yes_count, no_count)
            agreement = majority / total
            if agreement < 1.0:
                disagreements.append({
                    "asset_id": asset_id,
                    "task_type": task_type,
                    "rule_index": rule_index,
                    "yes_count": yes_count,
                    "no_count": no_count,
                    "agreement_pct": round(agreement * 100, 1),
                })
        return disagreements

    def test_full_agreement_no_disagreement(self):
        data = {
            (1, "asset_type", 1): ["yes", "yes"],
            (2, "asset_type", 1): ["no", "no"],
        }
        self.assertEqual(self._compute_agreement(data), [])

    def test_simple_disagreement(self):
        data = {
            (1, "asset_type", 1): ["yes", "no"],
        }
        result = self._compute_agreement(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["asset_id"], 1)
        self.assertEqual(result[0]["agreement_pct"], 50.0)

    def test_three_labelers_majority(self):
        data = {
            (1, "asset_type", 1): ["yes", "yes", "no"],
        }
        result = self._compute_agreement(data)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["agreement_pct"], 66.7, places=1)

    def test_single_response_ignored(self):
        data = {
            (1, "asset_type", 1): ["yes"],
        }
        self.assertEqual(self._compute_agreement(data), [])

    def test_adjudication_save_creates_decision(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.post(
            "/label_images/admin/adjudication/save/",
            data=json.dumps({
                "asset_id": 12345,
                "task_type": "asset_type",
                "rule_index": 1,
                "decision": "yes",
                "notes": "clearly a yes",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["created"])

        obj = AdjudicationDecision.objects.get(
            asset_id=12345, task_type="asset_type", rule_index=1,
        )
        self.assertEqual(obj.decision, "yes")
        self.assertEqual(obj.decided_by, self.admin)
        self.assertEqual(obj.notes, "clearly a yes")

    def test_adjudication_save_updates_existing(self):
        AdjudicationDecision.objects.create(
            asset_id=12345, task_type="asset_type", rule_index=1,
            decided_by=self.admin, decision="no",
        )
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.post(
            "/label_images/admin/adjudication/save/",
            data=json.dumps({
                "asset_id": 12345,
                "task_type": "asset_type",
                "rule_index": 1,
                "decision": "yes",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["created"])
        obj = AdjudicationDecision.objects.get(
            asset_id=12345, task_type="asset_type", rule_index=1,
        )
        self.assertEqual(obj.decision, "yes")


# ======================================================================
# is_staff filtering tests
# ======================================================================

class StaffFilterTests(_UserMixin, TestCase):

    def test_real_labelers_only(self):
        real = self._make_labeler("real_labeler", is_staff=True)
        test = self._make_labeler("test_labeler", is_staff=False)

        real_qs = User.objects.filter(
            is_staff=True, is_superuser=False,
        )

        self.assertIn(real, real_qs)
        self.assertNotIn(test, real_qs)

    def test_test_labelers_only(self):
        real = self._make_labeler("real_labeler", is_staff=True)
        test = self._make_labeler("test_labeler", is_staff=False)

        test_qs = User.objects.filter(
            is_staff=False, is_superuser=False,
        )

        self.assertIn(test, test_qs)
        self.assertNotIn(real, test_qs)
