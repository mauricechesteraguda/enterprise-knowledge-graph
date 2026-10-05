# type-10052026-Maurice: Expose the bounded catalog seam without broad query access.
"""Safe, documented SPARQL query catalog."""

from kg.query.catalog import CatalogExecution, CatalogIntent, CatalogResult, all_intents, execute

__all__ = ["CatalogExecution", "CatalogIntent", "CatalogResult", "all_intents", "execute"]
