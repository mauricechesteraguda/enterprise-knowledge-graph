# type-10052026-Maurice: Expose the bounded GraphRAG module without API wiring.
"""Safe, provider-neutral GraphRAG orchestration."""

from kg.graphrag.ask import Answer, UnsupportedQuestionError, answer

__all__ = ["Answer", "UnsupportedQuestionError", "answer"]
