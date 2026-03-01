from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from ..referee.Laws.models import LawEdition, Law, LawClause, LawChange, ParsingJob
from .services.parsing_orchestrator import ParsingOrchestrator
import json

@admin.register(LawEdition)
class LawEditionAdmin(admin.ModelAdmin):
    list_display = ['year', 'publication_date', 'is_current', 'pdf_status', 'parsing_actions']
    list_filter = ['is_current', 'publication_date']
    
    def pdf_status(self, obj):
        if obj.pdf_file:
            return format_html('<span style="color: green;">✓ Uploaded</span>')
        return format_html('<span style="color: red;">✗ Missing</span>')
    
    def parsing_actions(self, obj):
        jobs = obj.parsingjob_set.all()
        if jobs.exists():
            latest = jobs.first()
            return format_html(
                '<a class="button" href="{}">View Jobs</a> Status: {}',
                reverse('admin:laws_parsingjob_changelist') + f'?edition__id__exact={obj.id}',
                latest.status
            )
        return format_html(
            '<a class="button" href="{}">Start Parsing</a>',
            reverse('admin:start-parsing', args=[obj.id])
        )
    
    parsing_actions.short_description = 'Parsing'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:edition_id>/start-parsing/', self.admin_site.admin_view(self.start_parsing_view), name='start-parsing'),
        ]
        return custom_urls + urls
    
    def start_parsing_view(self, request, edition_id):
        orchestrator = ParsingOrchestrator()
        try:
            job = orchestrator.parse_edition(edition_id)
            messages.success(request, f'Parsing job created: {job.id}. Status: {job.status}')
            return redirect('admin:laws_parsingjob_change', job.id)
        except Exception as e:
            messages.error(request, f'Parsing failed: {str(e)}')
            return redirect('admin:laws_lawedition_change', edition_id)

@admin.register(ParsingJob)
class ParsingJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'edition', 'status', 'started_at', 'completed_at', 'review_action']
    list_filter = ['status', 'edition']
    readonly_fields = ['parsed_data_display', 'error_message']
    
    def parsed_data_display(self, obj):
        if obj.parsed_data:
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.parsed_data, indent=2)
            )
        return '-'
    
    parsed_data_display.short_description = 'Parsed Data (Review)'
    
    def review_action(self, obj):
        if obj.status == 'review':
            return format_html(
                '<a class="button" href="{}">Approve & Save</a>',
                reverse('admin:approve-parsing', args=[obj.id])
            )
        return obj.status
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:job_id>/approve/', self.admin_site.admin_view(self.approve_view), name='approve-parsing'),
        ]
        return custom_urls + urls
    
    def approve_view(self, request, job_id):
        orchestrator = ParsingOrchestrator()
        try:
            job = orchestrator.approve_and_save(job_id)
            messages.success(request, f'Parsing job approved. {job.edition.laws.count()} laws saved.')
            return redirect('admin:laws_lawedition_change', job.edition.id)
        except Exception as e:
            messages.error(request, f'Approval failed: {str(e)}')
            return redirect('admin:laws_parsingjob_change', job_id)

@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'edition', 'clause_count']
    list_filter = ['edition']
    search_fields = ['title', 'number']
    
    def clause_count(self, obj):
        return obj.clauses.count()

@admin.register(LawClause)
class LawClauseAdmin(admin.ModelAdmin):
    list_display = ['clause_id', 'heading', 'law', 'order']
    list_filter = ['law__edition', 'law__number']
    search_fields = ['clause_id', 'heading', 'content']

@admin.register(LawChange)
class LawChangeAdmin(admin.ModelAdmin):
    list_display = ['law_number', 'clause_id', 'change_type', 'edition']
    list_filter = ['change_type', 'edition', 'law_number']
    search_fields = ['description']