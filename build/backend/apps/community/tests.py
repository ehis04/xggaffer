from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import BannedWord, ModerationStatus, Post, PostReport


class CommunityModerationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_user(
            email="author@example.com",
            password="password123",
            username="author",
        )
        self.reporter_one = User.objects.create_user(
            email="reporter1@example.com",
            password="password123",
            username="reporter1",
        )
        self.reporter_two = User.objects.create_user(
            email="reporter2@example.com",
            password="password123",
            username="reporter2",
        )
        self.client = APIClient()

    def test_banned_word_sends_new_post_to_review(self):
        BannedWord.objects.create(term="badword")
        self.client.force_authenticate(self.author)

        response = self.client.post(
            "/api/community/create/post/",
            {"text_body": "This contains badword.", "visibility": "PB"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(id=response.data["id"])
        self.assertEqual(post.moderation_status, ModerationStatus.UNDER_REVIEW)

    def test_second_unique_report_sends_post_to_review(self):
        post = Post.objects.create(author=self.author, text_body="normal post")

        self.client.force_authenticate(self.reporter_one)
        first_response = self.client.post(f"/api/community/posts/{post.id}/report/", {}, format="json")

        post.refresh_from_db()
        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(post.moderation_status, ModerationStatus.OK)

        self.client.force_authenticate(self.reporter_two)
        second_response = self.client.post(f"/api/community/posts/{post.id}/report/", {}, format="json")

        post.refresh_from_db()
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.data["report_count"], 2)
        self.assertEqual(post.moderation_status, ModerationStatus.UNDER_REVIEW)

    def test_duplicate_report_does_not_increase_report_count(self):
        post = Post.objects.create(author=self.author, text_body="normal post")
        self.client.force_authenticate(self.reporter_one)

        self.client.post(f"/api/community/posts/{post.id}/report/", {}, format="json")
        response = self.client.post(f"/api/community/posts/{post.id}/report/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostReport.objects.filter(post=post).count(), 1)
        self.assertEqual(response.data["report_count"], 1)

    def test_author_cannot_report_own_post(self):
        post = Post.objects.create(author=self.author, text_body="normal post")
        self.client.force_authenticate(self.author)

        response = self.client.post(f"/api/community/posts/{post.id}/report/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PostReport.objects.filter(post=post).exists())
