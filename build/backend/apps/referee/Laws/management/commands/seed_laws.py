import json
import os
import re
import time
from decouple import config

import pdfplumber
from dotenv import load_dotenv
from google import genai
from google.genai import types

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referee.Laws.models import Law, CourseSection, CourseItem

GEMINI_API_KEY=config("GEMINI_API_KEY")

LAW_TITLES = {
    1:  'The Field of Play',
    2:  'The Ball',
    3:  'The Players',
    4:  "The Players' Equipment",
    5:  'The Referee',
    6:  'The Other Match Officials',
    7:  'The Duration of the Match',
    8:  'The Start and Restart of Play',
    9:  'The Ball In and Out of Play',
    10: 'Determining the Outcome of a Match',
    11: 'Offside',
    12: 'Fouls and Misconduct',
    13: 'Free Kicks',
    14: 'The Penalty Kick',
    15: 'The Throw-In',
    16: 'The Goal Kick',
    17: 'The Corner Kick',
}

GEMINI_DELAY_SECONDS = 5

CLAUSES_PER_SECTION_TARGET = 3

class Command(BaseCommand):
    help = 'Seeds the database with FIFA Laws of the Game from a PDF using Gemini AI.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf',
            required=True,
            type=str,
            help='Path to the Laws of the Game PDF file.',
        )
        parser.add_argument(
            '--law',
            type=int,
            default=None,
            help='Seed only this law number (1-17). Omit to seed all laws.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Extract and print text only — do not call Gemini or save to DB.',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Delete existing DB rows for a law before re-seeding it.',
        )

    def handle(self, *args, **options):
        pdf_path  = options['pdf']
        law_filter = options['law']
        dry_run   = options['dry_run']
        overwrite = options['overwrite']

        if not os.path.exists(pdf_path):
            raise CommandError(f'PDF not found: {pdf_path}')

        if not dry_run:
            api_key = GEMINI_API_KEY
            if not api_key:
                raise CommandError(
                    'GEMINI_API_KEY environment variable is not set.\n'
                )
            client = genai.Client(api_key=api_key)
        else:
            client = None

        self.stdout.write('\n Extracting text from PDF...')
        law_texts = extract_law_texts(pdf_path)
        self.stdout.write(
            f'Found text for {len(law_texts)} laws.'
        )

        if law_filter:
            if law_filter not in law_texts:
                raise CommandError(
                    f'Law {law_filter} not found in PDF. '
                    f'Available: {sorted(law_texts.keys())}'
                )
            law_texts = {law_filter: law_texts[law_filter]}

        if dry_run:
            for num, text in sorted(law_texts.items()):
                self.stdout.write(f'\n{"="*60}')
                self.stdout.write(f'LAW {num}: {LAW_TITLES.get(num, "Unknown")}')
                self.stdout.write(f'{"="*60}')
                self.stdout.write(text[:2000])
                self.stdout.write('... [truncated]' if len(text) > 2000 else '')
            return

        success_count = 0
        fail_count    = 0

        for law_number in sorted(law_texts.keys()):
            raw_text = law_texts[law_number]
            title    = LAW_TITLES.get(law_number, f'Law {law_number}')

            self.stdout.write(f'\n Generating Course for Law {law_number}: {title}')

            if Law.objects.filter(law_number=law_number).exists() and not overwrite:
                self.stdout.write(
                        f' Skipping, already in DB.'
                )
                continue

            try:
                structured = call_gemini(client, law_number, title, raw_text)
                save_law(law_number, title, structured, overwrite, self.stdout)
                success_count += 1

                time.sleep(GEMINI_DELAY_SECONDS)

            except Exception as exc:
                self.stdout.write(
                    f'    ✗  Failed: {exc}'
                )
                fail_count += 1

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(
            f'Seeded: {success_count} laws'
        )
        if fail_count:
            self.stdout.write(
                f'Failed: {fail_count} laws'
            )

def extract_law_texts(pdf_path: str) -> dict[int, str]:
    full_text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + '\n'

    law_pattern = re.compile(
        r'(?:^|\n)\s*(?:LAW|Law)\s+(\d{1,2})\b',
        re.MULTILINE,
    )

    matches = list(law_pattern.finditer(full_text))
    law_texts: dict[int, str] = {}

    for i, match in enumerate(matches):
        law_number = int(match.group(1))
        if law_number < 1 or law_number > 17:
            continue

        start = match.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text  = full_text[start:end].strip()

        if law_number not in law_texts:
            law_texts[law_number] = text
        else:
            law_texts[law_number] += '\n' + text

    return law_texts


GEMINI_PROMPT_TEMPLATE = """
You are a football referee education expert. You will be given the raw text of
FIFA Law {law_number} ({law_title}) extracted from a PDF.

Your task is to structure this law into a course with sections and learning items.

Return ONLY valid JSON matching this exact schema — no markdown, no explanation:

{{
  "description": "One sentence describing what this law covers.",
  "sections": [
    {{
      "title": "Section title (e.g. 'Types of Free Kicks')",
      "items": [
        {{
          "type": "clause",
          "title": "Short clause title",
          "mins": 3,
          "clause_number": 1,
          "clause_text": "Full clause text, preserving bullet points with \\n\\n between paragraphs and • for bullet items."
        }},
        {{
          "type": "scenario",
          "title": "Scenario title (e.g. 'Direct or Indirect?')",
          "mins": 3,
          "situation": "Describe a specific match situation that tests understanding of the clauses in this section.",
          "options": [
            {{"id": "a", "t": "First option"}},
            {{"id": "b", "t": "Second option"}},
            {{"id": "c", "t": "Third option"}},
            {{"id": "d", "t": "Fourth option"}}
          ],
          "correct_id": "b",
          "explanation": "Explain why the correct answer is right, referencing the law."
        }},
        {{
          "type": "drill",
          "title": "Drill title (e.g. 'Card Decisions Drill')",
          "mins": 4,
          "description": "True or false — decide for each statement.",
          "items": [
            {{"s": "A true/false statement about this law.", "a": "true"}},
            {{"s": "Another statement.", "a": "false"}},
            {{"s": "Another statement.", "a": "true"}},
            {{"s": "Another statement.", "a": "false"}}
          ]
        }}
      ]
    }}
  ]
}}

Rules:
- Group clauses into {sections_target} to 5 logical sections based on topic.
- Each section must have: 2-4 clause items, then 1 scenario item, then 1 drill item.
- Clause text must be accurate to the law — do not invent or change rules.
- Scenarios must be realistic match situations with exactly 4 options (a/b/c/d).
- Only one correct answer per scenario.
- Drills must have exactly 4 true/false statements, alternating true and false where possible.
- clause_number starts at 1 and increments across the whole law (not per section).
- mins should reflect reading time: short clause=2, medium=3, long=4, scenario=3, drill=4.
- Return ONLY the JSON object. No markdown fences. No explanation text.

Raw law text:
{raw_text}
"""


def call_gemini(client, law_number: int, law_title: str, raw_text: str) -> dict:
    prompt = GEMINI_PROMPT_TEMPLATE.format(
        law_number=law_number,
        law_title=law_title,
        sections_target=CLAUSES_PER_SECTION_TARGET,
        raw_text=raw_text[:12000],
    )

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.2,
                ),
            )
            text     = response.text.strip()

            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

            return json.loads(text)

        except json.JSONDecodeError as exc:
            if attempt == 0:
                time.sleep(3)
                continue
            raise ValueError(
                f'Gemini returned invalid JSON after 2 attempts: {exc}\n'
                f'Raw response: {text[:500]}'
            )
        except Exception as exc:
            if attempt == 0:
                time.sleep(3)
                continue
            raise

@transaction.atomic
def save_law(
    law_number: int,
    title: str,
    structured: dict,
    overwrite: bool,
    stdout,
) -> None:
    if overwrite:
        Law.objects.filter(law_number=law_number).delete()
        stdout.write(f'    Deleted existing Law {law_number} rows.')

    law = Law.objects.create(
        law_number  = law_number,
        title       = title,
        description = structured.get('description', ''),
        order       = law_number,
    )

    sections_data = structured.get('sections', [])
    total_items   = 0

    for section_order, section_data in enumerate(sections_data):
        section = CourseSection.objects.create(
            law   = law,
            title = section_data.get('title', f'Section {section_order + 1}'),
            order = section_order,
        )

        for item_order, item_data in enumerate(section_data.get('items', [])):
            item_type = item_data.get('type', 'clause')
            _save_item(section, item_type, item_data, item_order)
            total_items += 1

    stdout.write(
            f' Saved: {len(sections_data)} sections, {total_items} items.'
    )


def _save_item(
    section: CourseSection,
    item_type: str,
    data: dict,
    order: int,
) -> CourseItem:

    kwargs = dict(
        section   = section,
        item_type = item_type,
        title     = data.get('title', ''),
        order     = order,
        mins      = int(data.get('mins', 3)),
    )

    if item_type == 'clause':
        kwargs.update(
            clause_number = int(data.get('clause_number', 0)) or None,
            clause_text   = data.get('clause_text', ''),
        )

    elif item_type == 'scenario':
        kwargs.update(
            scenario_situation   = data.get('situation', ''),
            scenario_options     = data.get('options', []),
            scenario_correct_id  = data.get('correct_id', ''),
            scenario_explanation = data.get('explanation', ''),
        )

    elif item_type == 'drill':
        kwargs.update(
            drill_description = data.get('description', ''),
            drill_items       = data.get('items', []),
        )

    return CourseItem.objects.create(**kwargs)