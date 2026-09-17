from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .models import AppConfig, CommandProfile, FolderEntry


class LaunchError(RuntimeError):
    pass


def command_line(profile: CommandProfile, continue_session: bool) -> str:
    arguments = list(profile.arguments)
    if continue_session and profile.supports_continue:
        arguments.append("--continue")
    return subprocess.list2cmdline([profile.program, *arguments])


def command_label(entry: FolderEntry, config: AppConfig) -> str:
    profile = config.command(entry.command_id)
    if not profile:
        return "仅打开文件夹"
    suffix = " --continue" if entry.continue_session and profile.supports_continue else ""
    return f"{profile.name}{suffix}"


class FolderLauncher:
    def __init__(
        self,
        startfile: Callable[[str], None] | None = None,
        popen: Callable[..., subprocess.Popen] | None = None,
    ) -> None:
        self._startfile = startfile or os.startfile
        self._popen = popen or subprocess.Popen

    def launch(self, entry: FolderEntry, config: AppConfig) -> str:
        path = Path(entry.path)
        if not path.is_dir():
            raise LaunchError(f"文件夹不存在：{entry.path}")

        profile = config.command(entry.command_id)
        if entry.open_explorer:
            self._startfile(str(path))

        if profile:
            command = command_line(profile, entry.continue_session)
            comspec = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            try:
                self._popen(
                    [comspec, "/d", "/k", command],
                    cwd=str(path),
                    creationflags=creation_flags,
                )
            except OSError as exc:
                raise LaunchError(f"命令启动失败：{profile.name}\n{exc}") from exc

        if profile and entry.open_explorer:
            return f"已打开文件夹并启动 {command_label(entry, config)}"
        if profile:
            return f"已启动 {command_label(entry, config)}"
        return "已打开文件夹"

    def launch_action(
        self,
        entry: FolderEntry,
        config: AppConfig,
        command_id: str | None,
        continue_session: bool = False,
        open_explorer: bool = False,
    ) -> str:
        action = replace(
            entry,
            command_id=command_id,
            continue_session=continue_session,
            open_explorer=open_explorer,
        )
        return self.launch(action, config)
