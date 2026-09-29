import hashlib
import re

_WHITESPACE = re.compile(r"\s+")


def normalize_prompt(prompt: str) -> str:
    return _WHITESPACE.sub(" ", prompt.strip().lower())


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(normalize_prompt(prompt).encode("utf-8")).hexdigest()


def to_pgvector(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"
