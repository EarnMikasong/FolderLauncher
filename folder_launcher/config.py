from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from .models import AppConfig, Category, CommandProfile, FolderEntry


APP_NAME = "FolderLauncher"


def default_config_path() -> Path:
    override = os.environ.get("FOLDER_LAUNCHER_CONFIG")
    if override:
        return Path(override)
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / APP_NAME / "config.json"


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def create_default_config() -> AppConfig:
    categories = [
        Category("claude-projects", "Claude 项目", [r"D:\claude"]),
        Category("work-projects", "工作项目", [r"D:\实习\京西智谷"]),
        Category("java-learning", "Java / 学习", [r"D:\Java"]),
        Category("downloads", "下载目录", [r"D:\download-edge"]),
        Category("tools", "常用工具", [r"C:\Users\Earn\Tools"]),
        Category("uncategorized", "未分类", []),
    ]
    commands = [
        CommandProfile("claude", "Claude", "claude", supports_continue=True, builtin=True),
        CommandProfile("agy", "Agy", "agy", supports_continue=True, builtin=True),
    ]
    folders = [
        FolderEntry("folder-claude", "Claude", r"D:\claude", "claude-projects"),
        FolderEntry("folder-filter", "筛选", r"D:\claude\geektime\筛选", "claude-projects"),
        FolderEntry(
            "folder-mysql-45",
            "MySQL 实战 45 讲",
            r"D:\claude\geektime\筛选\MySQL实战45讲",
            "claude-projects",
        ),
        FolderEntry("folder-open-source", "开源", r"D:\claude\开源", "claude-projects"),
        FolderEntry("folder-java", "Java", r"D:\Java", "java-learning"),
        FolderEntry("folder-downloads", "Edge 下载", r"D:\download-edge", "downloads"),
        FolderEntry("folder-tools", "用户工具", r"C:\Users\Earn\Tools", "tools"),
        FolderEntry("folder-jingxi", "京西智谷", r"D:\实习\京西智谷", "work-projects"),
        FolderEntry(
            "folder-small-tools",
            "小工具",
            r"D:\实习\京西智谷\小工具",
            "work-projects",
        ),
    ]
    return AppConfig(categories=categories, commands=commands, folders=folders)


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = create_default_config()
            self.save(config)
            return config
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            config = AppConfig.from_dict(value)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"配置文件无法读取：{self.path}\n{exc}") from exc
        self._restore_builtin_commands(config)
        return config

    def save(self, config: AppConfig) -> None:
        config.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
        temporary.write_text(payload + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def _restore_builtin_commands(config: AppConfig) -> None:
        defaults = {item.id: item for item in create_default_config().commands}
        present = {item.id for item in config.commands}
        for command_id in ("claude", "agy"):
            if command_id not in present:
                config.commands.append(defaults[command_id])
