"""Temporary analysis context. Nothing is persisted on the server."""
from dataclasses import dataclass, field
from .config import Settings
from .model import AnalyzeInput, Extraction, Result, Quality, Metrics

@dataclass
class Context:
    input: AnalyzeInput
    settings: Settings
    providers: object
    catalog: object
    image: str | None = None
    metrics: Metrics | None = None
    extraction: Extraction | None = None
    quality: Quality | None = None
    result: Result | None = None
    completed: set[str] = field(default_factory=set)
