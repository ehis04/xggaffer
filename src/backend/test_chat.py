import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.predictions.services.chat_service import handle_chat_query

queries = [
    'Arsenal recent form this season',
    'Arsenal vs Chelsea head to head history',
    'how has Salah performed this season',
    'who is top of the Premier League',
    'how congested is Arsenal fixture schedule',
]
for q in queries:
    result = handle_chat_query(q)
    print(f'Q: {q}')
    print(f'  intent: {result["intent"]}')
    print(f'  used_fallback: {result["used_fallback"]}')
    print(f'  prose: {result["prose"][:120]}')
    print()
