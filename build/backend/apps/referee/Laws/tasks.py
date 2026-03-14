"""
apps/referee/Laws/tasks.py

PDF parsing pipeline for the Laws of the Game.
Triggered via admin UI or API, runs as a background job.

Requires: pip install pdfplumber
"""
import re
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Public entry point (called by django_rq)
# ─────────────────────────────────────────────

def run_parsing_job(job_id: int):
    """
    Entry point enqueued by the API view.
    Fetches the ParsingJob, downloads/reads the PDF,
    and populates Law + LawClause records.
    """
    from .models import ParsingJob, LawEdition

    job = ParsingJob.objects.select_related('edition').get(pk=job_id)
    job.status = 'processing'
    job.started_at = timezone.now()
    job.save()

    try:
        edition = job.edition

        if edition.pdf_file:
            pdf_source = edition.pdf_file.path
        elif edition.pdf_url:
            pdf_source = _download_pdf(edition.pdf_url)
        else:
            raise ValueError("Edition has no PDF file or URL.")

        parsed = parse_laws_pdf(pdf_source)
        _save_parsed_laws(parsed, edition)

        job.status = 'completed'
        job.completed_at = timezone.now()
        job.parsed_data = {'laws_parsed': len(parsed)}
        job.save()
        logger.info(f"Parsing job {job_id} completed: {len(parsed)} laws parsed.")

    except Exception as exc:
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_message = str(exc)
        job.save()
        logger.error(f"Parsing job {job_id} failed: {exc}", exc_info=True)
        raise


# ─────────────────────────────────────────────
# PDF Parsing Logic
# ─────────────────────────────────────────────

LAW_HEADER_RE = re.compile(r'^law\s+(\d+)\s*[:\-–—]?\s*(.+)$', re.IGNORECASE)
CLAUSE_RE = re.compile(r'^(\d+(?:\.\d+)?)\s+(.+)$')
BULLET_RE = re.compile(r'^[\-•*]\s+(.+)$')
HASHTAG_RE = re.compile(r'#\s*(.+)')


def parse_laws_pdf(pdf_path: str) -> list[dict]:
    """
    Parse a FIFA Laws of the Game PDF into a structured list.

    Returns a list of law dicts:
    [
        {
            "number": 1,
            "title": "The Field of Play",
            "clauses": [
                {
                    "clause_id": "1",
                    "heading": "Field surface",
                    "content": "...",
                    "bullet_points": [...],
                    "examples": [],
                    "notes": [],
                    "order": 0,
                }
            ]
        },
        ...
    ]
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required. Run: pip install pdfplumber")

    laws = []
    current_law = None
    current_clause = None
    clause_order = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                # ── Detect a new Law heading ──
                law_match = LAW_HEADER_RE.match(line)
                if law_match:
                    if current_law:
                        if current_clause:
                            current_law['clauses'].append(current_clause)
                            current_clause = None
                        laws.append(current_law)

                    law_number = int(law_match.group(1))
                    law_title = law_match.group(2).strip().title()
                    current_law = {
                        'number': law_number,
                        'title': law_title,
                        'clauses': [],
                    }
                    clause_order = 0
                    continue

                if current_law is None:
                    continue

                # ── Detect a clause heading ──
                clause_match = CLAUSE_RE.match(line)
                if clause_match:
                    if current_clause:
                        current_law['clauses'].append(current_clause)

                    clause_id = clause_match.group(1)
                    heading = clause_match.group(2).strip()
                    current_clause = {
                        'clause_id': clause_id,
                        'heading': heading,
                        'content': '',
                        'bullet_points': [],
                        'examples': [],
                        'notes': [],
                        'order': clause_order,
                    }
                    clause_order += 1
                    continue

                if current_clause is None:
                    # Free-floating text before first clause belongs to the law
                    if current_law and not current_law.get('description'):
                        current_law['description'] = line
                    continue

                # ── Bullet points ──
                bullet_match = BULLET_RE.match(line)
                if bullet_match:
                    current_clause['bullet_points'].append(bullet_match.group(1))
                    continue

                # ── Examples (lines starting with "Example:" or "e.g.") ──
                if re.match(r'^(example|e\.g\.)', line, re.IGNORECASE):
                    current_clause['examples'].append(line)
                    continue

                # ── Notes ──
                if re.match(r'^note:', line, re.IGNORECASE):
                    current_clause['notes'].append(line)
                    continue

                # ── Regular content ──
                if current_clause['content']:
                    current_clause['content'] += ' ' + line
                else:
                    current_clause['content'] = line

    # Flush last law/clause
    if current_law:
        if current_clause:
            current_law['clauses'].append(current_clause)
        laws.append(current_law)

    # Only keep laws 1-17
    laws = [l for l in laws if 1 <= l['number'] <= 17]
    return laws


# ─────────────────────────────────────────────
# Database Save
# ─────────────────────────────────────────────

def _save_parsed_laws(parsed_laws: list[dict], edition):
    from .models import Law, LawClause

    DIFFICULTY_MAP = {
        range(1, 6): 'beginner',
        range(6, 13): 'intermediate',
        range(13, 18): 'advanced',
    }

    def get_difficulty(number):
        for r, level in DIFFICULTY_MAP.items():
            if number in r:
                return level
        return 'intermediate'

    for law_data in parsed_laws:
        law, _ = Law.objects.update_or_create(
            edition=edition,
            number=law_data['number'],
            defaults={
                'title': law_data['title'],
                'description': law_data.get('description', ''),
                'difficulty_level': get_difficulty(law_data['number']),
                'full_content': law_data,
            }
        )

        # Sync clauses
        existing_ids = set(
            law.clauses.values_list('clause_id', flat=True)
        )
        incoming_ids = {c['clause_id'] for c in law_data.get('clauses', [])}

        # Remove clauses that no longer exist
        law.clauses.filter(clause_id__in=existing_ids - incoming_ids).delete()

        for clause_data in law_data.get('clauses', []):
            LawClause.objects.update_or_create(
                law=law,
                clause_id=clause_data['clause_id'],
                defaults={
                    'heading': clause_data['heading'],
                    'content': clause_data['content'],
                    'bullet_points': clause_data['bullet_points'],
                    'examples': clause_data['examples'],
                    'notes': clause_data['notes'],
                    'order': clause_data['order'],
                }
            )

    logger.info(f"Saved {len(parsed_laws)} laws for edition {edition.year}")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _download_pdf(url: str) -> str:
    """Download a PDF from a URL to a temp file and return the path."""
    import tempfile
    import urllib.request

    suffix = '.pdf'
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    urllib.request.urlretrieve(url, tmp.name)
    return tmp.name