"""
Tests article serializer text cleanup behaviour

Covers summary fallback logic, duplicate content removal, HTML cleanup, paragraph formatting, and source noise filtering
"""

from django.test import TestCase
from django.utils import timezone

from .models import Article, Site, Topic
from .serializers import ArticleDetailSerializer, ArticleListSerializer


# Tests article list and detail serializer text cleanup behaviour
class ArticleSerializerTextCleanupTests(TestCase):

	# Set up shared site and topic records for serializer tests
	def setUp(self):
		self.site = Site.objects.create(name='Test Site', domain='https://example.com')
		self.topic = Topic.objects.create(name='Test Topic', slug='test-topic')

	# Create an article with sensible defaults for serializer tests
	def _make_article(self, **kwargs) -> Article:
		defaults = {
			'title': 'Test Article',
			'slug': 'test-article',
			'url': 'https://example.com/articles/test-article',
			'summary': '',
			'content': '',
			'site': self.site,
			'publication_date': timezone.now(),
			'word_count': 100,
			'read_time_minutes': 1,
			'quality_score': 70.0,
		}
		defaults.update(kwargs)
		article = Article.objects.create(**defaults)
		article.topics.add(self.topic)
		return article

	# Confirms duplicate detail content is hidden when it matches the summary
	def test_detail_serializer_omits_duplicate_content_matching_summary(self):
		article = self._make_article(
			summary='Same text appears once.',
			content='Same text appears once.',
		)

		data = ArticleDetailSerializer(article).data

		self.assertEqual(data['summary'], 'Same text appears once.')
		self.assertEqual(data['content'], '')

	# Confirms HTML cleanup and repeated paragraph removal in article detail output
	def test_detail_serializer_cleans_html_and_removes_repeated_paragraphs(self):
		article = self._make_article(
			summary='Lead paragraph',
			content='<p>Lead paragraph</p><p>Lead paragraph</p>\n\nSecond&nbsp;paragraph\n\nSecond paragraph',
		)

		data = ArticleDetailSerializer(article).data

		self.assertEqual(data['summary'], 'Lead paragraph')
		self.assertEqual(data['content'], 'Second paragraph')

	# Confirms list serializer summaries can fall back to cleaned content
	def test_list_serializer_uses_clean_content_for_summary_fallback(self):
		article = self._make_article(
			summary='',
			content='<p>Line one</p>\n\nLine one\n\nLine two',
		)

		data = ArticleListSerializer(article).data

		self.assertEqual(data['summary'], 'Line one\n\nLine two')

	# Confirms noisy source text is stripped while useful article content remains
	def test_detail_serializer_strips_source_noise_and_formats_paragraphs(self):
		noisy = (
			'⚽ Premier League updates from the 5.30pm BST kick-off'
			'⚽ Live scores | Table | Top scorers | Follow us on Bluesky'
			'Mikel Arteta\'s pre-match thoughts'
			'[On making only one change from the City game] We did a lot of great things.'
			'[On how long Bukayo Saka might be able to play from the bench] We will see how the game goes.'
			' Continue reading...'
		)
		article = self._make_article(summary='', content=noisy)

		data = ArticleDetailSerializer(article).data
		content = data['content']

		self.assertIn('Premier League updates from the 5.30pm BST kick-off', content)
		self.assertIn("Mikel Arteta's pre-match thoughts", content)
		self.assertIn('[On making only one change from the City game]', content)
		self.assertIn('[On how long Bukayo Saka might be able to play from the bench]', content)
		self.assertNotIn('Live scores', content)
		self.assertNotIn('Top scorers', content)
		self.assertNotIn('Follow us on Bluesky', content)
		self.assertNotIn('Continue reading', content)