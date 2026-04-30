"""Safe integer counter helpers using Django F() expressions.

Use these instead of in-place Python increments to avoid race conditions on
concurrent requests. Decrement never goes below zero.
"""
from __future__ import annotations

from django.db.models import Case, F, IntegerField, Value, When


def increment_count(model_class, pk: int, field: str) -> None:
    model_class.objects.filter(pk=pk).update(**{field: F(field) + 1})


def decrement_count(model_class, pk: int, field: str) -> None:
    model_class.objects.filter(pk=pk).update(
        **{
            field: Case(
                When(**{f'{field}__gt': 0}, then=F(field) - 1),
                default=Value(0),
                output_field=IntegerField(),
            )
        }
    )
