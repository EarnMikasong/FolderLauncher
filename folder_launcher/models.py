from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Category:
    id: str
    name: str
    prefixes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Category":
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            prefixes=[str(item) for item in value.get("prefixes", [])],
        )


@dataclass
class CommandProfile:
    id: str
    name: str
    program: str
    arguments: list[str] = field(default_factory=list)
    supports_continue: bool = False
    builtin: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CommandProfile":
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            program=str(value["program"]),
            arguments=[str(item) for item in value.get("arguments", [])],
            supports_continue=bool(value.get("supports_continue", False)),
            builtin=bool(value.get("builtin", False)),
        )


@dataclass
class FolderEntry:
    id: str
    name: str
    path: str
    category_id: str
    command_id: str | None = None
    continue_session: bool = False
    open_explorer: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FolderEntry":
        command_id = value.get("command_id")
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            path=str(value["path"]),
            category_id=str(value["category_id"]),
            command_id=str(command_id) if command_id else None,
            continue_session=bool(value.get("continue_session", False)),
            open_explorer=bool(value.get("open_explorer", True)),
        )


@dataclass
class AppConfig:
    version: int = 1
    categories: list[Category] = field(default_factory=list)
    commands: list[CommandProfile] = field(default_factory=list)
    folders: list[FolderEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AppConfig":
        config = cls(
            version=int(value.get("version", 1)),
            categories=[Category.from_dict(item) for item in value.get("categories", [])],
            commands=[CommandProfile.from_dict(item) for item in value.get("commands", [])],
            folders=[FolderEntry.from_dict(item) for item in value.get("folders", [])],
        )
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        self._require_unique("category", [item.id for item in self.categories])
        self._require_unique("command", [item.id for item in self.commands])
        self._require_unique("folder", [item.id for item in self.folders])

        category_ids = {item.id for item in self.categories}
        command_ids = {item.id for item in self.commands}
        for folder in self.folders:
            if folder.category_id not in category_ids:
                raise ValueError(f"Folder {folder.name!r} references an unknown category")
            if folder.command_id and folder.command_id not in command_ids:
                raise ValueError(f"Folder {folder.name!r} references an unknown command")

    @staticmethod
    def _require_unique(kind: str, values: list[str]) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {kind} id in configuration")

    def category(self, category_id: str) -> Category | None:
        return next((item for item in self.categories if item.id == category_id), None)

    def command(self, command_id: str | None) -> CommandProfile | None:
        if not command_id:
            return None
        return next((item for item in self.commands if item.id == command_id), None)

    def folder(self, folder_id: str) -> FolderEntry | None:
        return next((item for item in self.folders if item.id == folder_id), None)
