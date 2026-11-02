"""Automated unit and integration test suite for AI Semantic Matching Engine (Phase 3)."""
import math
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.items.models import CampusLocation, Category, Item
from apps.matching.models import ItemEmbedding, PotentialMatch, MatchStatus
from apps.matching.services import (
    MODEL_NAME,
    EMBEDDING_DIMENSIONS,
    serialize_item_text,
    generate_embedding_vector,
    get_or_create_item_embedding,
    compute_vector_cosine_similarity,
    compute_title_similarity,
    compute_category_score,
    compute_location_score,
    compute_date_score,
    compute_hybrid_match_score,
    generate_match_explanation,
    find_candidate_items,
    find_and_generate_matches_for_item,
    run_system_wide_matching,
)

User = get_user_model()


class MatchingEngineServiceTests(TestCase):
    """Unit tests for embedding generation, text serialization, and heuristic scoring algorithms."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1@university.edu",
            email="student1@university.edu",
            password="SecurePassword123!",
            role=User.Role.STUDENT,
        )
        self.category_electronics = Category.objects.create(name="Electronics")
        self.category_books = Category.objects.create(name="Books & Notes")
        self.location_library = CampusLocation.objects.create(name="Central Library 2nd Floor")
        self.location_library_annex = CampusLocation.objects.create(name="Central Library Study Carrel")
        self.location_cafeteria = CampusLocation.objects.create(name="Main Dining Hall")

        self.lost_item = Item.objects.create(
            title="Black Samsung Wireless Earbuds",
            description="Left on a study desk with black charging case.",
            item_type=Item.ItemType.LOST,
            category=self.category_electronics,
            location=self.location_library,
            date_lost_or_found=date.today(),
            reported_by=self.user,
            status=Item.ItemStatus.OPEN,
        )

        self.found_item = Item.objects.create(
            title="Black Bluetooth Earbuds in Case",
            description="Found outside central library study room on 2nd floor.",
            item_type=Item.ItemType.FOUND,
            category=self.category_electronics,
            location=self.location_library_annex,
            date_lost_or_found=date.today(),
            reported_by=self.user,
            status=Item.ItemStatus.OPEN,
        )

    def test_text_serialization(self):
        """Item attributes are composed into a structured canonical narrative."""
        text, text_hash = serialize_item_text(self.lost_item)
        self.assertIn("Title: Black Samsung Wireless Earbuds", text)
        self.assertIn("Category: Electronics", text)
        self.assertIn("Central Library 2nd Floor", text)
        self.assertEqual(len(text_hash), 64)  # Valid SHA-256 length

    def test_embedding_vector_dimensions_and_norm(self):
        """Generated embedding vector must have 384 dimensions and unit L2 norm."""
        text, _ = serialize_item_text(self.lost_item)
        vector = generate_embedding_vector(text)
        self.assertEqual(len(vector), EMBEDDING_DIMENSIONS)
        norm = math.sqrt(sum(x * x for x in vector))
        self.assertAlmostEqual(norm, 1.0, places=3)

    def test_get_or_create_item_embedding(self):
        """ItemEmbedding record is created and linked to the item."""
        embedding_obj = get_or_create_item_embedding(self.lost_item)
        self.assertIsNotNone(embedding_obj)
        self.assertEqual(embedding_obj.item, self.lost_item)
        self.assertEqual(len(embedding_obj.embedding), 384)

        # Caching check: repeated call does not recreate if hash matches
        embedding_obj2 = get_or_create_item_embedding(self.lost_item)
        self.assertEqual(embedding_obj.id, embedding_obj2.id)

    def test_cosine_similarity(self):
        """Cosine similarity produces 1.0 for identical vectors and 0.0 for orthogonal."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(compute_vector_cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(compute_vector_cosine_similarity(v1, v3), 0.0)

    def test_title_similarity_word_reordering(self):
        """Title similarity handles exact match, substring, and token reordering."""
        # Exact match
        self.assertEqual(compute_title_similarity("AirPods Pro", "AirPods Pro"), 1.0)
        # Word reordering: "Black Samsung Earbuds" vs "Samsung Earbuds Black"
        reordered = compute_title_similarity("Black Samsung Earbuds", "Samsung Earbuds Black")
        self.assertGreater(reordered, 0.75)
        # Completely different
        diff = compute_title_similarity("HydroFlask Bottle", "Calculus Textbook")
        self.assertLess(diff, 0.20)

    def test_category_score(self):
        """Category score is 1.0 for match, 0.0 for mismatch."""
        self.assertEqual(compute_category_score(1, 1), 1.0)
        self.assertEqual(compute_category_score(1, 2), 0.0)
        self.assertEqual(compute_category_score(None, 1), 0.0)

    def test_location_score(self):
        """Location score awards 1.0 for same ID and 0.6 for related campus buildings."""
        # Same location
        self.assertEqual(compute_location_score(self.location_library, self.location_library), 1.0)
        # Related building keyword: both contain 'Library'
        self.assertEqual(compute_location_score(self.location_library, self.location_library_annex), 0.6)
        # Unrelated
        self.assertEqual(compute_location_score(self.location_library, self.location_cafeteria), 0.0)

    def test_date_proximity_decay(self):
        """Date score decays gracefully as temporal distance increases."""
        today = date.today()
        self.assertEqual(compute_date_score(today, today), 1.0)
        self.assertEqual(compute_date_score(today, today - timedelta(days=1)), 0.95)
        self.assertEqual(compute_date_score(today, today - timedelta(days=3)), 0.85)
        self.assertEqual(compute_date_score(today, today - timedelta(days=7)), 0.70)
        self.assertEqual(compute_date_score(today, today - timedelta(days=14)), 0.50)
        self.assertLess(compute_date_score(today, today - timedelta(days=25)), 0.50)
        self.assertEqual(compute_date_score(today, today - timedelta(days=35)), 0.0)

    def test_hybrid_matching_formula(self):
        """Weighted hybrid composite score calculates expected linear combination."""
        # Weights: Desc 0.45, Title 0.20, Cat 0.15, Loc 0.10, Date 0.10
        score = compute_hybrid_match_score(
            desc_sim=1.0,
            title_sim=1.0,
            cat_score=1.0,
            loc_score=1.0,
            date_score=1.0,
        )
        self.assertAlmostEqual(score, 1.0)

        partial = compute_hybrid_match_score(
            desc_sim=0.80,  # 0.36
            title_sim=0.70, # 0.14
            cat_score=1.00, # 0.15
            loc_score=0.60, # 0.06
            date_score=0.95,# 0.095
        ) # sum = 0.805
        self.assertAlmostEqual(partial, 0.805, places=2)

    def test_match_explanation_generation(self):
        """Explanation articulates key reasons based on actual scoring attributes."""
        explanation = generate_match_explanation(
            lost_item=self.lost_item,
            found_item=self.found_item,
            desc_sim=0.85,
            title_sim=0.75,
            cat_score=1.0,
            loc_score=0.6,
            date_score=1.0,
            final_score=0.84,
        )
        self.assertIn("Strong potential match (84%)", explanation)
        self.assertIn("Electronics", explanation)
        self.assertIn("does not constitute proof of ownership", explanation)


class PotentialMatchModelTests(TestCase):
    """Tests for PotentialMatch model constraints and validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student2@university.edu",
            email="student2@university.edu",
            password="SecurePassword123!",
        )
        self.category = Category.objects.create(name="Clothing")
        self.location = CampusLocation.objects.create(name="Gymnasium")

        self.lost = Item.objects.create(
            title="Navy Blue Hoodie",
            description="Nike navy hoodie size L.",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
        )
        self.found = Item.objects.create(
            title="Dark Blue Nike Sweatshirt",
            description="Found on gym bleachers.",
            item_type=Item.ItemType.FOUND,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
        )

    def test_unique_pair_constraint(self):
        """A lost item and found item pair cannot be duplicated."""
        PotentialMatch.objects.get_or_create(
            lost_item=self.lost,
            found_item=self.found,
            defaults={"final_score": 0.85},
        )
        with self.assertRaises(Exception):
            PotentialMatch.objects.create(
                lost_item=self.lost,
                found_item=self.found,
                final_score=0.90,
            )

    def test_item_type_enforcement(self):
        """lost_item must be LOST and found_item must be FOUND."""
        with self.assertRaises(ValidationError):
            # Inverted types: found item passed as lost_item
            match = PotentialMatch(
                lost_item=self.found,
                found_item=self.lost,
                final_score=0.50,
            )
            match.clean()

    def test_match_percentage_and_helpers(self):
        """Helper properties return expected boolean and integer values."""
        match, _ = PotentialMatch.objects.get_or_create(
            lost_item=self.lost,
            found_item=self.found,
            defaults={"final_score": 0.78, "status": MatchStatus.SUGGESTED},
        )
        match.final_score = 0.78
        match.save()
        self.assertEqual(match.match_percentage, 78)
        self.assertTrue(match.is_strong_match)
        self.assertFalse(match.is_moderate_match)


class MatchingWorkflowAndViewsTests(TestCase):
    """Integration tests for candidate matching workflow and view endpoints."""

    def setUp(self):
        self.student_a = User.objects.create_user(
            username="alice@university.edu",
            email="alice@university.edu",
            password="SecurePassword123!",
            role=User.Role.STUDENT,
        )
        self.student_b = User.objects.create_user(
            username="bob@university.edu",
            email="bob@university.edu",
            password="SecurePassword123!",
            role=User.Role.STUDENT,
        )
        self.admin = User.objects.create_user(
            username="admin@university.edu",
            email="admin@university.edu",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
        )

        self.category = Category.objects.create(name="Accessories")
        self.location = CampusLocation.objects.create(name="Science Center")

        # Alice's lost item
        self.alice_lost = Item.objects.create(
            title="Silver Water Flask",
            description="HydroFlask 32oz bottle with university logo sticker.",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.student_a,
            status=Item.ItemStatus.OPEN,
        )

        # Bob's found item
        self.bob_found = Item.objects.create(
            title="Silver HydroFlask Water Bottle",
            description="Discovered in science center lecture hall 101 with sticker.",
            item_type=Item.ItemType.FOUND,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.student_b,
            status=Item.ItemStatus.OPEN,
        )

    def test_find_candidates_opposite_types_only(self):
        """Candidates include only opposite item types and exclude resolved reports."""
        candidates = find_candidate_items(self.alice_lost)
        self.assertIn(self.bob_found, candidates)
        self.assertTrue(all(c.item_type == Item.ItemType.FOUND for c in candidates))

    def test_exclude_resolved_and_closed_items(self):
        """Resolved reports are excluded from candidate matching."""
        self.bob_found.status = Item.ItemStatus.RESOLVED
        self.bob_found.save()
        candidates = find_candidate_items(self.alice_lost)
        self.assertNotIn(self.bob_found, candidates)

    def test_find_and_generate_matches_workflow(self):
        """End-to-end matching produces ranked PotentialMatch record."""
        matches = find_and_generate_matches_for_item(self.alice_lost, min_score=0.30)
        self.assertGreaterEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.lost_item, self.alice_lost)
        self.assertEqual(match.found_item, self.bob_found)
        self.assertGreater(match.final_score, 0.60)
        self.assertTrue(match.explanation)

    def test_matching_hub_view_access_and_privacy(self):
        """Students only see matches involving their own reports; admins see all."""
        # Retrieve or create match between Alice and Bob
        match, _ = PotentialMatch.objects.get_or_create(
            lost_item=self.alice_lost,
            found_item=self.bob_found,
            defaults={"final_score": 0.80, "status": MatchStatus.SUGGESTED},
        )
        match.final_score = 0.80
        match.status = MatchStatus.SUGGESTED
        match.save()

        # Create Stranger user with unrelated report
        stranger = User.objects.create_user(
            username="stranger@university.edu",
            email="stranger@university.edu",
            password="SecurePassword123!",
            role=User.Role.STUDENT,
        )

        # Alice sees the match
        self.client.login(username="alice@university.edu", password="SecurePassword123!")
        response = self.client.get(reverse("matching:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Silver Water Flask")
        self.client.logout()

        # Stranger does NOT see Alice and Bob's match
        self.client.login(username="stranger@university.edu", password="SecurePassword123!")
        response = self.client.get(reverse("matching:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Silver Water Flask")
        self.client.logout()

        # Admin sees all matches
        self.client.login(username="admin@university.edu", password="SecurePassword123!")
        response = self.client.get(reverse("matching:hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Silver Water Flask")

    def test_match_action_express_interest_and_dismiss(self):
        """Match actions update match status correctly."""
        match, _ = PotentialMatch.objects.get_or_create(
            lost_item=self.alice_lost,
            found_item=self.bob_found,
            defaults={"final_score": 0.82, "status": MatchStatus.SUGGESTED},
        )
        match.status = MatchStatus.SUGGESTED
        match.save()

        self.client.login(username="alice@university.edu", password="SecurePassword123!")

        # Express Interest
        response = self.client.post(
            reverse("matching:match_action", kwargs={"match_id": match.id}),
            {"action": "interested"},
        )
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, MatchStatus.INTERESTED)

        # Dismiss
        response = self.client.post(
            reverse("matching:match_action", kwargs={"match_id": match.id}),
            {"action": "dismiss"},
        )
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, MatchStatus.DISMISSED)

    def test_trigger_matching_view(self):
        """Trigger matching endpoint generates matches and redirects."""
        self.client.login(username="alice@university.edu", password="SecurePassword123!")
        response = self.client.post(
            reverse("matching:trigger_item", kwargs={"item_id": self.alice_lost.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PotentialMatch.objects.filter(lost_item=self.alice_lost).exists())
