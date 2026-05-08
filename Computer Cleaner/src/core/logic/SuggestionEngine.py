from __future__ import annotations

from dataclasses import dataclass

from logic.RulesEngine import RuleSuggestion, suggest_from_rules


@dataclass(frozen=True)
class Suggestion:
    label: str
    confidence: float
    reason: str


def suggest_label(*, size_bytes: int | None, modified_date, model_suggestion=None) -> Suggestion | None:
    rule = suggest_from_rules(size_bytes=size_bytes, modified_date=modified_date)
    if isinstance(rule, RuleSuggestion):
        return Suggestion(label=rule.label, confidence=0.6, reason=rule.reason)
    if model_suggestion is not None:
        return model_suggestion
    return None
