from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from apps.articles.models import *
import random
import datetime
import uuid

class Command(BaseCommand):
    help = "Seed initial articles, authors, sites and topics"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        topics_data = [
            ('VAR', 'Opinions and analysis on VAR performance and effect on matches'),
            ('Referee Appointments', 'Weekly updates on referee assignments for upcoming matches'),
            ('Controversy', 'News and opinions on controversial decisions and incidents, sometimes involving referees'),
            ('Fitness', 'Learn about what it takes to be as fit as a top referee or player'),
            ('Laws of the Game', 'Rule changes and interpretations'),
            ('Team News', 'Team news for upcoming games'),
            ('Player Performance', 'Analysis of player performances in recent matches'),
            ('Match Analysis', 'Analysis and breakdowns of recent games'),
            ('Training', 'Coaching tips and info for managers and trainers'),
            ('Youth Development', 'News on youth academies and upcoming talent'),
        ]

        topics = {}
        for name, description in topics_data:
            topic, created = Topic.objects.get_or_create(
                name=name,
                defaults={'description': description, 'slug': slugify(name)}
            )
            topics[name] = topic
            if created:
                self.stdout.write(f'  ✓ Created topic: {name}')

        sites_data = [
            {
                'name': 'Premier League',
                'domain': 'https://www.premierleague.com/en/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'Sky Sports',
                'domain': 'https://www.skysports.com/football',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'ESPN',
                'domain': 'https://www.espn.com/soccer/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'BBC',
                'domain': 'https://www.bbc.com/sport/football',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'Sports Illustrated',
                'domain': 'https://www.si.com/soccer/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'The Athletic',
                'domain': 'https://theatheletic.com',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'The Guardian',
                'domain': 'https://www.theguardian.com/football',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'talkSport',
                'domain': 'https://talksport.com/football/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'RTE',
                'domain': 'https://www.rte.ie/sport/soccer/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'The Irish Times',
                'domain': 'https://www.irishtimes.com/sport/soccer/',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
            {
                'name': 'The Irish Independent',
                'domain': 'https://www.independent.ie/sport/soccer',
                'reputation_score': 85.0,
                'trust_score': 90.0
            },
        ]

        sites = {}
        for s in sites_data:
            site, created = Site.objects.get_or_create(
                name=s['name'],
                defaults={
                    'domain': s.get('domain', ''),
                    'reputation_score': s.get('reputation_score', 0.0),
                    'trust_score': s.get('trust_score', 0.0),
                }
            )
            sites[s['name']] = site
            if created:
                self.stdout.write(f'  ✓ Created site: {s["name"]}')

        def get_site_by_name(name):
            if name in sites:
                return sites[name]
            unique_domain = f"https://{slugify(name)}-{uuid.uuid4().hex[:8]}.local"
            site, created = Site.objects.get_or_create(
                name=name,
                defaults={'domain': unique_domain, 'reputation_score': 50.0, 'trust_score': 50.0}
            )
            sites[name] = site
            if created:
                self.stdout.write(f'  ✓ Created site (missing ref): {name}')
            return site

        existing_sites = set(sites.keys())

        authors_data = [
            {
                'name': 'Michael Cox',
                'bio': 'Tactical analyst and founder of Zonal Marking',
                'expertise_score': 90.0,
                'credibility_score': 92.0,
                'sites': ['The Athletic', 'ESPN FC'],
            },
            {
                'name': 'Jonathan Wilson',
                'bio': 'Football historian and tactical expert',
                'expertise_score': 88.0,
                'credibility_score': 90.0,
                'sites': ['The Guardian Football', 'ESPN FC'],
            },
            {
                'name': 'Raphael Honigstein',
                'bio': 'German football expert',
                'expertise_score': 85.0,
                'credibility_score': 87.0,
                'sites': ['The Athletic'],
            },
            {
                'name': 'Amy Lawrence',
                'bio': 'Arsenal correspondent and columnist',
                'expertise_score': 82.0,
                'credibility_score': 85.0,
                'sites': ['The Guardian Football', 'The Athletic'],
            },
            {
                'name': 'James Pearce',
                'bio': 'Liverpool correspondent',
                'expertise_score': 80.0,
                'credibility_score': 83.0,
                'sites': ['The Athletic'],
            },
        ]

        authors = {}
        for author_data in authors_data:
            site_names = author_data.pop('sites', [])
            author, created = Author.objects.get_or_create(
                name=author_data['name'],
                defaults=author_data
            )

            for site_name in site_names:
                site_obj = get_site_by_name(site_name)
                author.sites.add(site_obj)

            authors[author_data['name']] = author
            if created:
                self.stdout.write(f'  ✓ Created author: {author_data["name"]}')

        articles_data = [
            {
                'title': 'Tactical Analysis: How Manchester City Dominates Possession',
                'summary': 'A deep dive into Pep Guardiola\'s system and how City controls games through intelligent positioning.',
                'site': 'The Athletic',
                'authors': ['Michael Cox'],
                'topics': ['Football Tactics', 'Match Analysis'],
                'quality_score': 88.0,
                'word_count': 1500,
                'read_time_minutes': 7,
            },
            {
                'title': 'Understanding the Offside Trap: A Tactical Guide',
                'summary': 'Breaking down one of football\'s most effective defensive strategies.',
                'site': 'The Guardian Football',
                'authors': ['Jonathan Wilson'],
                'topics': ['Football Tactics', 'Laws of the Game'],
                'quality_score': 85.0,
                'word_count': 1200,
                'read_time_minutes': 6,
            },
            {
                'title': 'VAR Controversies: What Needs to Change',
                'summary': 'Examining the most contentious VAR decisions and proposing improvements.',
                'site': 'BBC Sport',
                'authors': ['Amy Lawrence'],
                'topics': ['Refereeing', 'Laws of the Game'],
                'quality_score': 82.0,
                'word_count': 1800,
                'read_time_minutes': 8,
            },
            {
                'title': 'Bundesliga Tactics: Why German Football Leads in Pressing',
                'summary': 'How German clubs perfected the high-press system.',
                'site': 'The Athletic',
                'authors': ['Raphael Honigstein'],
                'topics': ['Football Tactics', 'Training Methods'],
                'quality_score': 87.0,
                'word_count': 2000,
                'read_time_minutes': 9,
            },
            {
                'title': 'Liverpool\'s Youth Development: Building the Next Generation',
                'summary': 'Inside Liverpool\'s academy and their pathway to first team.',
                'site': 'The Athletic',
                'authors': ['James Pearce'],
                'topics': ['Youth Development', 'Team News'],
                'quality_score': 80.0,
                'word_count': 1400,
                'read_time_minutes': 7,
            },
            {
                'title': 'The Evolution of the False 9 Position',
                'summary': 'From Messi to modern football: how the false 9 changed the game.',
                'site': 'ESPN FC',
                'authors': ['Michael Cox', 'Jonathan Wilson'],
                'topics': ['Football Tactics', 'Player Performance'],
                'quality_score': 90.0,
                'word_count': 2200,
                'read_time_minutes': 10,
            },
            {
                'title': 'IFAB Law Changes 2025: What Referees Need to Know',
                'summary': 'Summary of the latest changes to the Laws of the Game.',
                'site': 'Sky Sports',
                'authors': ['Amy Lawrence'],
                'topics': ['Laws of the Game', 'Refereeing'],
                'quality_score': 83.0,
                'word_count': 1100,
                'read_time_minutes': 5,
            },
            {
                'title': 'Coaching the Counter-Attack: Tactical Masterclass',
                'summary': 'How top managers set up their teams for devastating counter-attacks.',
                'site': 'The Guardian Football',
                'authors': ['Jonathan Wilson'],
                'topics': ['Football Tactics', 'Training Methods'],
                'quality_score': 86.0,
                'word_count': 1600,
                'read_time_minutes': 8,
            },
        ]

        for i, article_data in enumerate(articles_data):
            site_name = article_data.pop('site')
            author_names = article_data.pop('authors')
            topic_names = article_data.pop('topics')

            slug = slugify(article_data['title'])
            site_obj = get_site_by_name(site_name)
            url = f"{site_obj.domain.rstrip('/')}/article/{slug}" if site_obj.domain else f"/article/{slug}"

            publication_date = timezone.now() - datetime.timedelta(days=random.randint(0, 30))

            article, created = Article.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    'slug': slug,
                    'url': url,
                    'content': article_data.get('content', ''),
                    'site': site_obj,
                    'publication_date': publication_date,
                    'readability_score': article_data.get('readability_score', 50.0),
                    'engagement_score': article_data.get('engagement_score', 50.0),
                    'quality_score': article_data.get('quality_score', 50.0),
                }
            )

            if author_names:
                author_objs = [authors[name] for name in author_names if name in authors]
                if author_objs:
                    article.authors.set(author_objs)

            for topic_name in topic_names:
                topic_obj, _ = Topic.objects.get_or_create(
                    name=topic_name,
                    defaults={'slug': slugify(topic_name), 'description': ''}
                )
                article.topics.add(topic_obj)

            self.stdout.write(f'  ✓ Created article: {article.title[:60]}...')

        self.stdout.write(self.style.SUCCESS('\n✓ Seeding complete!'))
        self.stdout.write(f'  Topics: {Topic.objects.count()}')
        self.stdout.write(f'  Sites: {Site.objects.count()}')
        self.stdout.write(f'  Authors: {Author.objects.count()}')
        self.stdout.write(f'  Articles: {Article.objects.count()}')