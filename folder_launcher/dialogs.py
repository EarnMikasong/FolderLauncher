from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from .config import new_id
from .hierarchy import normalized, suggest_category
from .launcher import command_label
from .models import AppConfig, Category, CommandProfile, FolderEntry


SURFACE = "#FFFFFF"
SURFACE_ALT = "#F6F8F9"
APP_BG = "#F1F4F6"
LINE = "#DCE2E6"
TEXT = "#172126"
MUTED = "#66747C"
ACCENT = "#0B766B"
ACCENT_HOVER = "#095F57"
DANGER = "#B4434D"


def neutral_button(parent: tk.Misc, text: str, command, width: int = 78) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        width=width,
        height=36,
        corner_radius=6,
        fg_color="#E5EAED",
        hover_color="#D5DDE1",
        text_color=TEXT,
        command=command,
    )


class ModalDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Misc, title: str, geometry: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(geometry)
        self.configure(fg_color=APP_BG)
        self.transient(parent)
        self.after(80, self.grab_set)
        self.bind("<Escape>", lambda _event: self.destroy())

    @staticmethod
    def heading(parent: ctk.CTkFrame, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            text_color=TEXT,
            font=ctk.CTkFont("Microsoft YaHei UI", 19, "bold"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(20, 14))

    def buttons(self, parent: ctk.CTkFrame, save_command: Callable[[], None]) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(4, 18))
        ctk.CTkButton(
            row,
            text="保存",
            width=90,
            height=36,
            corner_radius=6,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=save_command,
        ).pack(side="right")
        neutral_button(row, "取消", self.destroy).pack(side="right", padx=(0, 8))


class FolderEditor(ModalDialog):
    def __init__(
        self,
        parent: tk.Misc,
        config: AppConfig,
        entry: FolderEntry | None = None,
        path: str = "",
        category_id: str | None = None,
    ) -> None:
        super().__init__(parent, "编辑文件夹" if entry else "添加文件夹", "620x535")
        self.resizable(False, False)
        self.config_data = config
        self.original = entry
        self.result: FolderEntry | None = None
        initial_path = entry.path if entry else path
        self.name_var = tk.StringVar(value=entry.name if entry else (Path(initial_path).name or initial_path))
        self.path_var = tk.StringVar(value=initial_path)
        self.category_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.continue_var = tk.BooleanVar(value=entry.continue_session if entry else False)
        self.explorer_var = tk.BooleanVar(value=entry.open_explorer if entry else True)
        self.category_names = {item.name: item.id for item in config.categories}
        self.command_names = {"不运行命令": None, **{item.name: item.id for item in config.commands}}
        selected_category = entry.category_id if entry else category_id
        self.category_var.set(next((name for name, value in self.category_names.items() if value == selected_category), ""))
        selected_command = entry.command_id if entry else None
        self.command_var.set(next((name for name, value in self.command_names.items() if value == selected_command), "不运行命令"))

        panel = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        panel.pack(fill="both", expand=True, padx=22, pady=22)
        self.heading(panel, "编辑目录信息" if entry else "添加到启动器")
        self._entry_field(panel, "名称", self.name_var)

        path_row = ctk.CTkFrame(panel, fg_color="transparent")
        path_row.pack(fill="x", padx=22, pady=7)
        path_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(path_row, text="路径", text_color=MUTED, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        ctk.CTkEntry(path_row, textvariable=self.path_var, height=38, corner_radius=6).grid(
            row=1, column=0, sticky="ew", padx=(0, 7)
        )
        neutral_button(path_row, "浏览", self._browse, 68).grid(row=1, column=1)

        options = ctk.CTkFrame(panel, fg_color="transparent")
        options.pack(fill="x", padx=22, pady=7)
        options.grid_columnconfigure((0, 1), weight=1)
        self.category_menu = self._option_field(options, 0, "分类", self.category_var, list(self.category_names))
        self.command_menu = self._option_field(options, 1, "默认命令", self.command_var, list(self.command_names))
        self.command_menu.configure(command=lambda _value: self._sync_continue())

        switches = ctk.CTkFrame(panel, fg_color=SURFACE_ALT, corner_radius=6)
        switches.pack(fill="x", padx=22, pady=(10, 14))
        ctk.CTkSwitch(
            switches,
            text="使用 --continue",
            variable=self.continue_var,
            progress_color=ACCENT,
        ).pack(side="left", padx=14, pady=12)
        ctk.CTkSwitch(
            switches,
            text="同时打开文件夹",
            variable=self.explorer_var,
            progress_color=ACCENT,
        ).pack(side="left", padx=14, pady=12)
        self.buttons(panel, self._save)

    @staticmethod
    def _entry_field(parent: ctk.CTkFrame, label: str, variable: tk.StringVar) -> None:
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(fill="x", padx=22, pady=7)
        ctk.CTkLabel(wrapper, text=label, text_color=MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkEntry(wrapper, textvariable=variable, height=38, corner_radius=6).pack(fill="x")

    @staticmethod
    def _option_field(
        parent: ctk.CTkFrame,
        column: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
    ) -> ctk.CTkOptionMenu:
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.grid(row=0, column=column, sticky="ew", padx=(0, 5) if column == 0 else (5, 0))
        ctk.CTkLabel(wrapper, text=label, text_color=MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        menu = ctk.CTkOptionMenu(
            wrapper,
            variable=variable,
            values=values or [""],
            height=38,
            corner_radius=6,
            fg_color=SURFACE_ALT,
            button_color="#D7E0E4",
            button_hover_color="#C3CED3",
            text_color=TEXT,
        )
        menu.pack(fill="x")
        return menu

    def _browse(self) -> None:
        path = filedialog.askdirectory(parent=self, initialdir=self.path_var.get() or None)
        if path:
            self.path_var.set(path)
            if not self.name_var.get().strip():
                self.name_var.set(Path(path).name)

    def _sync_continue(self) -> None:
        command = self.config_data.command(self.command_names.get(self.command_var.get()))
        if not command or not command.supports_continue:
            self.continue_var.set(False)

    def _save(self) -> None:
        name = self.name_var.get().strip()
        path = self.path_var.get().strip().strip('"')
        category_id = self.category_names.get(self.category_var.get())
        command_id = self.command_names.get(self.command_var.get())
        if not name or not path or not category_id:
            messagebox.showerror("信息不完整", "名称、路径和分类不能为空。", parent=self)
            return
        if not Path(path).is_dir():
            messagebox.showerror("路径无效", f"文件夹不存在：\n{path}", parent=self)
            return
        for item in self.config_data.folders:
            if self.original and item.id == self.original.id:
                continue
            if normalized(item.path) == normalized(path):
                messagebox.showerror("路径重复", "这个文件夹已经在列表中。", parent=self)
                return
        if not self.explorer_var.get() and not command_id:
            messagebox.showerror("启动方式无效", "至少需要打开文件夹或运行一个命令。", parent=self)
            return
        command = self.config_data.command(command_id)
        self.result = FolderEntry(
            id=self.original.id if self.original else new_id("folder"),
            name=name,
            path=str(Path(path)),
            category_id=category_id,
            command_id=command_id,
            continue_session=self.continue_var.get() if command and command.supports_continue else False,
            open_explorer=self.explorer_var.get(),
        )
        self.destroy()


class TextListEditor(ModalDialog):
    def __init__(self, parent: tk.Misc, title: str, heading: str, geometry: str) -> None:
        super().__init__(parent, title, geometry)
        self.resizable(False, False)
        self.panel = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self.panel.pack(fill="both", expand=True, padx=22, pady=22)
        self.heading(self.panel, heading)

    def field(self, label: str, variable: tk.StringVar) -> None:
        ctk.CTkLabel(self.panel, text=label, text_color=MUTED, anchor="w").pack(fill="x", padx=22)
        ctk.CTkEntry(self.panel, textvariable=variable, height=36, corner_radius=6).pack(
            fill="x", padx=22, pady=(4, 9)
        )

    def text_field(self, label: str, height: int) -> ctk.CTkTextbox:
        ctk.CTkLabel(self.panel, text=label, text_color=MUTED, anchor="w").pack(fill="x", padx=22)
        textbox = ctk.CTkTextbox(self.panel, height=height, corner_radius=6, font=("Consolas", 11))
        textbox.pack(fill="x", padx=22, pady=(4, 10))
        return textbox


class CategoryEditor(TextListEditor):
    def __init__(self, parent: tk.Misc, category: Category | None = None) -> None:
        super().__init__(parent, "编辑分类" if category else "添加分类", "分类设置", "560x420")
        self.original = category
        self.result: Category | None = None
        self.name_var = tk.StringVar(value=category.name if category else "")
        self.field("名称", self.name_var)
        self.prefix_text = self.text_field("路径前缀（每行一个）", 110)
        if category:
            self.prefix_text.insert("1.0", "\n".join(category.prefixes))
        self.buttons(self.panel, self._save)

    def _save(self) -> None:
        name = self.name_var.get().strip()
        prefixes = [line.strip().strip('"') for line in self.prefix_text.get("1.0", "end").splitlines() if line.strip()]
        if not name:
            messagebox.showerror("信息不完整", "分类名称不能为空。", parent=self)
            return
        self.result = Category(self.original.id if self.original else new_id("category"), name, prefixes)
        self.destroy()


class CommandEditor(TextListEditor):
    def __init__(self, parent: tk.Misc, command: CommandProfile | None = None) -> None:
        super().__init__(parent, "编辑命令" if command else "添加命令", "命令设置", "560x490")
        self.original = command
        self.result: CommandProfile | None = None
        self.name_var = tk.StringVar(value=command.name if command else "")
        self.program_var = tk.StringVar(value=command.program if command else "")
        self.continue_var = tk.BooleanVar(value=command.supports_continue if command else False)
        self.field("名称", self.name_var)
        self.field("程序", self.program_var)
        self.arguments_text = self.text_field("默认参数（每行一个）", 80)
        if command:
            self.arguments_text.insert("1.0", "\n".join(command.arguments))
        ctk.CTkSwitch(
            self.panel,
            text="支持 --continue",
            variable=self.continue_var,
            progress_color=ACCENT,
        ).pack(anchor="w", padx=22, pady=(0, 10))
        self.buttons(self.panel, self._save)

    def _save(self) -> None:
        name = self.name_var.get().strip()
        program = self.program_var.get().strip().strip('"')
        arguments = [line.strip() for line in self.arguments_text.get("1.0", "end").splitlines() if line.strip()]
        if not name or not program:
            messagebox.showerror("信息不完整", "命令名称和程序不能为空。", parent=self)
            return
        self.result = CommandProfile(
            id=self.original.id if self.original else new_id("command"),
            name=name,
            program=program,
            arguments=arguments,
            supports_continue=self.continue_var.get(),
            builtin=self.original.builtin if self.original else False,
        )
        self.destroy()


class ManagerDialog(ModalDialog):
    def __init__(
        self,
        parent: tk.Misc,
        config: AppConfig,
        save_callback: Callable[[str], None],
        edit_folder_callback: Callable[[FolderEntry, tk.Misc | None], bool],
    ) -> None:
        super().__init__(parent, "配置管理", "940x650")
        self.minsize(820, 560)
        self.config_data = config
        self.save_callback = save_callback
        self.edit_folder_callback = edit_folder_callback

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header,
            text="配置管理",
            text_color=TEXT,
            font=ctk.CTkFont("Microsoft YaHei UI", 22, "bold"),
        ).pack(side="left")
        neutral_button(header, "关闭", self.destroy, 72).pack(side="right")
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=SURFACE,
            corner_radius=8,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color="#E5EAED",
            segmented_button_unselected_hover_color="#D4DDE1",
            text_color=TEXT,
        )
        self.tabs.pack(fill="both", expand=True, padx=24, pady=(6, 24))
        self.folder_list = self._tab(self.tabs.add("文件夹"), self.add_folder)
        self.category_list = self._tab(self.tabs.add("分类"), self.add_category)
        self.command_list = self._tab(self.tabs.add("命令"), self.add_command)
        self.refresh_all()

    @staticmethod
    def _tab(tab: ctk.CTkFrame, add_command: Callable[[], None]) -> ctk.CTkScrollableFrame:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        ctk.CTkButton(
            toolbar,
            text="+ 添加",
            width=82,
            height=34,
            corner_radius=6,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=add_command,
        ).pack(side="right")
        listing = ctk.CTkScrollableFrame(tab, fg_color=SURFACE_ALT, corner_radius=6)
        listing.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        listing.grid_columnconfigure(0, weight=1)
        return listing

    def refresh_all(self) -> None:
        for listing in (self.folder_list, self.category_list, self.command_list):
            for child in listing.winfo_children():
                child.destroy()
        for index, entry in enumerate(self.config_data.folders):
            category = self.config_data.category(entry.category_id)
            self._row(
                self.folder_list,
                index,
                entry.name,
                entry.path,
                f"{category.name if category else ''} · {command_label(entry, self.config_data)}",
                lambda item=entry: self._edit_folder(item),
                lambda item=entry: self._delete_folder(item),
            )
        for index, category in enumerate(self.config_data.categories):
            self._row(
                self.category_list,
                index,
                category.name,
                "；".join(category.prefixes) or "无路径前缀",
                f"{sum(1 for item in self.config_data.folders if item.category_id == category.id)} 个文件夹",
                lambda item=category: self._edit_category(item),
                lambda item=category: self._delete_category(item),
            )
        for index, command in enumerate(self.config_data.commands):
            self._row(
                self.command_list,
                index,
                command.name,
                f"{command.program}  {' '.join(command.arguments) or '无默认参数'}",
                "支持 --continue" if command.supports_continue else "普通命令",
                lambda item=command: self._edit_command(item),
                lambda item=command: self._delete_command(item),
            )

    @staticmethod
    def _row(parent, index, title, detail, badge, edit_command, delete_command) -> None:
        row = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=7, border_width=1, border_color=LINE)
        row.grid(row=index, column=0, sticky="ew", padx=5, pady=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            row,
            text=title,
            text_color=TEXT,
            font=ctk.CTkFont("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(9, 0))
        ctk.CTkLabel(row, text=detail, text_color=MUTED, font=ctk.CTkFont("Segoe UI", 9), anchor="w").grid(
            row=1, column=0, sticky="ew", padx=14, pady=(0, 9)
        )
        ctk.CTkLabel(row, text=badge, text_color=ACCENT, font=ctk.CTkFont("Microsoft YaHei UI", 8, "bold")).grid(
            row=0, column=1, rowspan=2, padx=10
        )
        neutral_button(row, "编辑", edit_command, 58).grid(row=0, column=2, rowspan=2, padx=(0, 6))
        ctk.CTkButton(
            row,
            text="删除",
            width=58,
            height=36,
            corner_radius=6,
            fg_color="#F7E7E9",
            hover_color="#EED4D7",
            text_color=DANGER,
            command=delete_command,
        ).grid(row=0, column=3, rowspan=2, padx=(0, 12))

    def add_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="选择文件夹")
        if not path:
            return
        editor = FolderEditor(self, self.config_data, path=path, category_id=suggest_category(path, self.config_data.categories))
        self.wait_window(editor)
        if editor.result:
            self.config_data.folders.append(editor.result)
            self.save_callback("已添加文件夹")
            self.refresh_all()

    def _edit_folder(self, entry: FolderEntry) -> None:
        if self.edit_folder_callback(entry, self):
            self.refresh_all()

    def _delete_folder(self, entry: FolderEntry) -> None:
        if messagebox.askyesno("删除文件夹", f"从列表中删除“{entry.name}”？\n不会删除磁盘文件。", parent=self):
            self.config_data.folders.remove(entry)
            self.save_callback("已从列表删除")
            self.refresh_all()

    def add_category(self) -> None:
        editor = CategoryEditor(self)
        self.wait_window(editor)
        if editor.result:
            self.config_data.categories.append(editor.result)
            self.save_callback("已添加分类")
            self.refresh_all()

    def _edit_category(self, category: Category) -> None:
        editor = CategoryEditor(self, category)
        self.wait_window(editor)
        if editor.result:
            self.config_data.categories[self.config_data.categories.index(category)] = editor.result
            self.save_callback("已更新分类")
            self.refresh_all()

    def _delete_category(self, category: Category) -> None:
        if any(item.category_id == category.id for item in self.config_data.folders):
            messagebox.showwarning("无法删除", "请先移动或删除这个分类中的文件夹。", parent=self)
            return
        if messagebox.askyesno("删除分类", f"删除分类“{category.name}”？", parent=self):
            self.config_data.categories.remove(category)
            self.save_callback("已删除分类")
            self.refresh_all()

    def add_command(self) -> None:
        editor = CommandEditor(self)
        self.wait_window(editor)
        if editor.result:
            self.config_data.commands.append(editor.result)
            self.save_callback("已添加命令")
            self.refresh_all()

    def _edit_command(self, command: CommandProfile) -> None:
        editor = CommandEditor(self, command)
        self.wait_window(editor)
        if editor.result:
            self.config_data.commands[self.config_data.commands.index(command)] = editor.result
            self.save_callback("已更新命令")
            self.refresh_all()

    def _delete_command(self, command: CommandProfile) -> None:
        if command.builtin:
            messagebox.showwarning("内置命令", "Claude 和 Agy 是内置命令，不能删除。", parent=self)
            return
        if messagebox.askyesno("删除命令", f"删除命令“{command.name}”？使用它的文件夹将改为仅打开。", parent=self):
            for folder in self.config_data.folders:
                if folder.command_id == command.id:
                    folder.command_id = None
                    folder.continue_session = False
                    folder.open_explorer = True
            self.config_data.commands.remove(command)
            self.save_callback("已删除命令")
            self.refresh_all()
