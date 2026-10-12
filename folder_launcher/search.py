from __future__ import annotations

from .models import AppConfig, Category, FolderEntry


def _tokens(query: str) -> list[str]:
    return [token for token in query.split() if token]


def _folder_score(entry: FolderEntry, tokens: list[str]) -> int | None:
    name = entry.name.casefold()
    path = entry.path.casefold()
    total = 0
    for token in tokens:
        token = token.casefold()
        if name.startswith(token):
            score = 0
        elif token in name:
            score = 1
        elif token in path:
            score = 2
        else:
            return None
        total += score
    return total


def search_folders(config: AppConfig, query: str) -> list[FolderEntry]:
    tokens = _tokens(query)
    if not tokens:
        return []
    scored: list[tuple[int, str, str, FolderEntry]] = []
    for entry in config.folders:
        total = _folder_score(entry, tokens)
        if total is None:
            continue
        scored.append((total, entry.name.casefold(), entry.path.casefold(), entry))
    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in scored]


def search_categories(config: AppConfig, query: str) -> list[Category]:
    tokens = _tokens(query)
    if not tokens:
        return []
    hits: list[Category] = []
    for category in config.categories:
        haystacks = [category.name.casefold(), *(prefix.casefold() for prefix in category.prefixes)]
        if all(any(token in haystack for haystack in haystacks) for token in tokens):
            hits.append(category)
    hits.sort(key=lambda item: item.name.casefold())
    return hits
