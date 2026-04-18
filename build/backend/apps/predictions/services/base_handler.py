from __future__ import annotations

import abc
import dataclasses
import logging

from apps.predictions.services.intent_types import IntentClass, ParsedQuery


@dataclasses.dataclass
class QueryPayload:
    intent: IntentClass
    engine_data: dict
    partial: bool
    error: str | None


class EngineHandler(abc.ABC):
    @abc.abstractmethod
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        ...