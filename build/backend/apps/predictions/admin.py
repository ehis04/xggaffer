from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import ScrapedMatch, ScrapeLog, TeamStats
from .tasks import scrape_specific_league

@admin.register(ScrapedMatch)
class ScrapedMatchAdmin(admin.ModelAdmin):
    list_display = [
        'match_summary',
        'match_date',
        'league',
        'season',
        'xg_display',
        'result_display',
        'scraped_at',
        'view_raw_data'
    ]
    
    list_filter = [
        'league',
        'season',
        'match_date',
        'scraped_at',
    ]
    
    search_fields = [
        'home_team',
        'away_team',
        'external_id',
    ]
    
    readonly_fields = [
        'external_id',
        'scraped_at',
        'last_updated',
        'formatted_raw_data',
    ]
    
    date_hierarchy = 'match_date'
    
    ordering = ['-match_date']
    
    def match_summary(self, obj):
        return f"{obj.home_team} vs {obj.away_team}"
    match_summary.short_description = 'Match'
    
    def xg_display(self, obj):
        home_color = 'green' if obj.home_xg > obj.away_xg else 'red'
        away_color = 'green' if obj.away_xg > obj.home_xg else 'red'
        
        return format_html(
            '<span style="color: {};">{:.2f}</span> - <span style="color: {};">{:.2f}</span>',
            home_color, obj.home_xg, away_color, obj.away_xg
        )
    xg_display.short_description = 'xG (H-A)'
    
    def result_display(self, obj):
        return f"{obj.home_goals} - {obj.away_goals}"
    result_display.short_description = 'Result'
    
    def view_raw_data(self, obj):
        if obj.raw_data:
            return format_html(
                '<a href="#" onclick="alert(JSON.stringify({}, null, 2)); return false;">View JSON</a>',
                obj.raw_data
            )
        return '-'
    view_raw_data.short_description = 'Raw Data'
    
    def formatted_raw_data(self, obj):
        import json
        if obj.raw_data:
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.raw_data, indent=2)
            )
        return '-'
    formatted_raw_data.short_description = 'Raw Data (JSON)'
    
    actions = ['delete_selected', 'rescrape_matches']
    
    def rescrape_matches(self, request, queryset):
        for match in queryset:
            scrape_specific_league.delay(match.league, match.season)
        
        self.message_user(
            request,
            f"Queued re-scraping for {queryset.count()} matches"
        )
    rescrape_matches.short_description = "Re-scrape selected matches"


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'scraper_name',
        'target',
        'status_display',
        'success_rate',
        'started_at',
        'duration_display',
        'view_details',
    ]
    
    list_filter = [
        'status',
        'scraper_name',
        'started_at',
    ]
    
    search_fields = [
        'target',
        'error_message',
    ]
    
    readonly_fields = [
        'scraper_name',
        'target',
        'status',
        'matches_found',
        'matches_created',
        'matches_updated',
        'matches_failed',
        'started_at',
        'completed_at',
        'duration_seconds',
        'formatted_error',
        'formatted_metadata',
    ]
    
    date_hierarchy = 'started_at'
    
    ordering = ['-started_at']
    
    def status_display(self, obj):
        colors = {
            'success': 'green',
            'partial': 'orange',
            'failed': 'red',
            'running': 'blue',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def success_rate(self, obj):
        if obj.matches_found == 0:
            return '-'
        
        success = obj.matches_created + obj.matches_updated
        rate = (success / obj.matches_found) * 100
        
        color = 'green' if rate > 90 else 'orange' if rate > 50 else 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span> ({}/{})',
            color, rate, success, obj.matches_found
        )
    success_rate.short_description = 'Success Rate'
    
    def duration_display(self, obj):
        if obj.duration_seconds is None:
            return '-'
        
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    duration_display.short_description = 'Duration'
    
    def view_details(self, obj):
        url = reverse('admin:predictions_scrapelog_change', args=[obj.id])
        return format_html('<a href="{}">View Details</a>', url)
    view_details.short_description = 'Details'
    
    def formatted_error(self, obj):
        if obj.error_traceback:
            return format_html('<pre style="color: red;">{}</pre>', obj.error_traceback)
        elif obj.error_message:
            return format_html('<p style="color: red;">{}</p>', obj.error_message)
        return '-'
    formatted_error.short_description = 'Error Details'
    
    def formatted_metadata(self, obj):
        import json
        if obj.metadata:
            return format_html('<pre>{}</pre>', json.dumps(obj.metadata, indent=2))
        return '-'
    formatted_metadata.short_description = 'Metadata'
    
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        week_ago = timezone.now() - timedelta(days=7)
        recent_logs = ScrapeLog.objects.filter(started_at__gte=week_ago)
        
        extra_context['stats'] = {
            'total_scrapes': recent_logs.count(),
            'successful_scrapes': recent_logs.filter(status='success').count(),
            'failed_scrapes': recent_logs.filter(status='failed').count(),
            'avg_duration': recent_logs.aggregate(Avg('duration_seconds'))['duration_seconds__avg'],
            'total_matches': recent_logs.aggregate(
                total=Count('matches_created')
            )['total'] or 0,
        }
        
        return super().changelist_view(request, extra_context)


@admin.register(TeamStats)
class TeamStatsAdmin(admin.ModelAdmin):
    list_display = [
        'team_name',
        'league',
        'season',
        'matches_played',
        'avg_xg_display',
        'form_display',
        'calculated_at',
    ]
    
    list_filter = [
        'league',
        'season',
        'calculated_at',
    ]
    
    search_fields = [
        'team_name',
    ]
    
    readonly_fields = [
        'calculated_at',
    ]
    
    ordering = ['-avg_xg_for']
    
    def avg_xg_display(self, obj):
        return f"{obj.avg_xg_for:.2f} / {obj.avg_xg_against:.2f}"
    avg_xg_display.short_description = 'Avg xG (For/Against)'
    
    def form_display(self, obj):
        return f"{obj.last_5_xg_for:.2f} xGF (L5)"
    form_display.short_description = 'Recent Form'
