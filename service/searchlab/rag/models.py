from dataclasses import dataclass, field


@dataclass
class RagResult:
    answer: str | None
    sources: list
    error: str | None
