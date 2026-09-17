from __future__ import annotations

import ntpath
from dataclasses import dataclass, field

from .models import Category, FolderEntry


def normalized(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(path.strip().strip('"')))


def is_same_or_descendant(path: str, parent: str) -> bool:
    child_value = normalized(path)
    parent_value = normalized(parent)
    try:
        return ntpath.commonpath([child_value, parent_value]) == parent_value
    except ValueError:
        return False


def suggest_category(path: str, categories: list[Category]) -> str | None:
    winner: tuple[int, str] | None = None
    for category in categories:
        for prefix in category.prefixes:
            if is_same_or_descendant(path, prefix):
                score = len(normalized(prefix))
                if winner is None or score > winner[0]:
                    winner = (score, category.id)
    if winner:
        return winner[1]
    fallback = next((item.id for item in categories if not item.prefixes), None)
    return fallback or (categories[0].id if categories else None)


@dataclass
class FolderNode:
    entry: FolderEntry
    children: list["FolderNode"] = field(default_factory=list)


def build_category_tree(entries: list[FolderEntry], category_id: str) -> list[FolderNode]:
    selected = [entry for entry in entries if entry.category_id == category_id]
    nodes = {entry.id: FolderNode(entry=entry) for entry in selected}
    roots: list[FolderNode] = []

    for entry in selected:
        parents = [
            candidate
            for candidate in selected
            if candidate.id != entry.id
            and normalized(candidate.path) != normalized(entry.path)
            and is_same_or_descendant(entry.path, candidate.path)
        ]
        if not parents:
            roots.append(nodes[entry.id])
            continue
        parent = max(parents, key=lambda item: len(normalized(item.path)))
        nodes[parent.id].children.append(nodes[entry.id])

    def sort_nodes(items: list[FolderNode]) -> None:
        items.sort(key=lambda node: (node.entry.name.casefold(), normalized(node.entry.path)))
        for node in items:
            sort_nodes(node.children)

    sort_nodes(roots)
    return roots
