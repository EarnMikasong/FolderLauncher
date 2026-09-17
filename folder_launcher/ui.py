from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .config import ConfigStore, create_default_config, new_id
from .hierarchy import FolderNode, build_category_tree, normalized, suggest_category
from .launcher import FolderLauncher, LaunchError, command_label
from .models import AppConfig, Category, CommandProfile, FolderEntry


PAGE_SIZE = 7
COLORS = {
    "bg": "#EEF1F4",
    "surface": "#FFFFFF",
    "text": "#17202A",
    "muted": "#64707D",
    "line": "#D7DDE3",
    "accent": "#087568",
    "accent_soft": "#DDF0EC",
    "selected": "#E8F2F8",
    "blue": "#285F91",
    "danger": "#B43A45",
}


class FolderLauncherApp(tk.Tk):
    def __init__(self, store: ConfigStore | None = None) -> None:
        super().__init__()
        self.store = store or ConfigStore()
        self.runner = FolderLauncher()
        self.config_data = self._load_config()
        self.navigation: list[tuple[str, str | None]] = [("home", None)]
        self.page = 0
        self.selected_folder_id: str | None = None
        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self.selected_name_var = tk.StringVar(value="未选择目录")
        self.selected_path_var = tk.StringVar(value="-")
        self.selected_default_var = tk.StringVar(value="默认动作：-")
        self.open_with_command_var = tk.BooleanVar(value=False)
        self.default_action_var = tk.StringVar(value="仅打开文件夹")
        self.custom_command_var = tk.StringVar()
        self.default_actions: dict[str, tuple[str | None, bool]] = {}
        self.custom_commands: dict[str, str] = {}

        self.title("Folder Launcher")
        self.geometry("1040x760")
        self.minsize(900, 740)
        self.configure(bg=COLORS["bg"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._configure_styles()
        self._build_shell()
        self.bind_all("<Key>", self._handle_key, add="+")
        self.render()

    def _load_config(self) -> AppConfig:
        try:
            return self.store.load()
        except ValueError as exc:
            messagebox.showerror("配置错误", str(exc))
            return create_default_config()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        self.option_add("*Font", ("Segoe UI", 10))
        style.configure("TButton", padding=(12, 7), font=("Microsoft YaHei UI", 9))
        style.configure("Accent.TButton", padding=(14, 8), font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", COLORS["accent_soft"])])
        style.configure("Quick.TButton", padding=(8, 6), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Treeview", rowheight=30, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Microsoft YaHei UI", 9))

    def _build_shell(self) -> None:
        header = tk.Frame(self, bg=COLORS["surface"], highlightthickness=1, highlightbackground=COLORS["line"])
        header.pack(fill="x")
        header.columnconfigure(1, weight=1)

        self.back_button = ttk.Button(header, text="←", width=3, command=self.go_back)
        self.back_button.grid(row=0, column=0, rowspan=2, padx=(18, 10), pady=16)
        self.title_label = tk.Label(
            header,
            text="文件夹启动器",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 16, "bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=1, sticky="ew", pady=(14, 0))
        self.breadcrumb_label = tk.Label(
            header,
            text="",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.breadcrumb_label.grid(row=1, column=1, sticky="ew", pady=(1, 14))
        ttk.Button(header, text="配置管理", command=self.open_manager).grid(
            row=0, column=2, rowspan=2, padx=(8, 18), pady=16
        )

        add_bar = tk.Frame(self, bg=COLORS["bg"])
        add_bar.pack(fill="x", padx=20, pady=(18, 12))
        add_bar.columnconfigure(0, weight=1)
        self.path_entry = ttk.Entry(add_bar, textvariable=self.path_var, font=("Segoe UI", 10))
        self.path_entry.grid(row=0, column=0, sticky="ew", ipady=5)
        self.path_entry.bind("<Return>", lambda _event: self.add_typed_path())
        ttk.Button(add_bar, text="选择文件夹", command=self.choose_folder).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(add_bar, text="添加", style="Accent.TButton", command=self.add_typed_path).grid(
            row=0, column=2, padx=(8, 0)
        )

        action_bar = tk.Frame(self, bg=COLORS["bg"])
        action_bar.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(
            action_bar,
            text="数字键执行目录的默认动作",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left")
        self.page_label = tk.Label(action_bar, text="", bg=COLORS["bg"], fg=COLORS["muted"])
        self.page_label.pack(side="right", padx=8)
        self.next_button = ttk.Button(action_bar, text="下一页", command=lambda: self.change_page(1))
        self.next_button.pack(side="right")
        self.previous_button = ttk.Button(action_bar, text="上一页", command=lambda: self.change_page(-1))
        self.previous_button.pack(side="right", padx=(0, 6))

        workspace = tk.Frame(self, bg=COLORS["bg"])
        workspace.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, minsize=300)
        workspace.rowconfigure(0, weight=1)

        self.content = tk.Frame(workspace, bg=COLORS["bg"])
        self.content.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.action_panel = tk.Frame(
            workspace,
            bg=COLORS["surface"],
            highlightthickness=1,
            highlightbackground=COLORS["line"],
            padx=14,
            pady=12,
        )
        self.action_panel.grid(row=0, column=1, sticky="nsew")
        self._build_action_panel()

        footer = tk.Frame(self, bg=COLORS["surface"], highlightthickness=1, highlightbackground=COLORS["line"])
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            textvariable=self.status_var,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", padx=20, pady=9)

    def _build_action_panel(self) -> None:
        tk.Label(
            self.action_panel,
            text="快捷动作",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            self.action_panel,
            textvariable=self.selected_name_var,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(10, 2))
        tk.Label(
            self.action_panel,
            textvariable=self.selected_path_var,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=260,
        ).pack(fill="x")
        tk.Label(
            self.action_panel,
            textvariable=self.selected_default_var,
            bg=COLORS["surface"],
            fg=COLORS["accent"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 10))

        self.quick_buttons: list[ttk.Button] = []
        folder_button = ttk.Button(
            self.action_panel,
            text="打开文件夹",
            style="Accent.TButton",
            command=lambda: self._launch_quick(None, False, True),
        )
        folder_button.pack(fill="x")
        self.quick_buttons.append(folder_button)

        separator = ttk.Separator(self.action_panel, orient="horizontal")
        separator.pack(fill="x", pady=9)
        tk.Label(
            self.action_panel,
            text="在当前目录启动",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        ).pack(fill="x", pady=(0, 7))

        command_grid = ttk.Frame(self.action_panel)
        command_grid.pack(fill="x")
        command_grid.columnconfigure(0, weight=1)
        command_grid.columnconfigure(1, weight=1)
        for index, (label, command_id, use_continue) in enumerate((
            ("Claude", "claude", False),
            ("Claude 继续", "claude", True),
            ("Agy", "agy", False),
            ("Agy 继续", "agy", True),
        )):
            button = ttk.Button(
                command_grid,
                text=label,
                style="Quick.TButton",
                command=lambda cid=command_id, cont=use_continue: self._launch_quick(
                    cid, cont, self.open_with_command_var.get()
                ),
            )
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 4) if index % 2 == 0 else (4, 0), pady=3)
            self.quick_buttons.append(button)

        self.custom_row = ttk.Frame(self.action_panel)
        self.custom_row.pack(fill="x", pady=(7, 2))
        self.custom_row.columnconfigure(0, weight=1)
        self.custom_command_box = ttk.Combobox(
            self.custom_row,
            textvariable=self.custom_command_var,
            state="readonly",
            width=16,
        )
        self.custom_command_box.grid(row=0, column=0, sticky="ew")
        self.custom_run_button = ttk.Button(self.custom_row, text="运行", command=self._launch_custom)
        self.custom_run_button.grid(row=0, column=1, padx=(6, 0))
        self.quick_buttons.append(self.custom_run_button)
        self.command_explorer_check = ttk.Checkbutton(
            self.action_panel,
            text="运行命令时同时打开文件夹",
            variable=self.open_with_command_var,
        )
        self.command_explorer_check.pack(fill="x", pady=(5, 8))

        ttk.Separator(self.action_panel, orient="horizontal").pack(fill="x", pady=(0, 9))
        tk.Label(
            self.action_panel,
            text="数字键默认动作",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.default_action_box = ttk.Combobox(
            self.action_panel,
            textvariable=self.default_action_var,
            state="readonly",
        )
        self.default_action_box.pack(fill="x")
        settings_buttons = ttk.Frame(self.action_panel)
        settings_buttons.pack(fill="x", pady=(5, 0))
        settings_buttons.columnconfigure(0, weight=1)
        settings_buttons.columnconfigure(1, weight=1)
        self.save_default_button = ttk.Button(
            settings_buttons,
            text="保存默认动作",
            command=self._save_default_action,
        )
        self.save_default_button.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.quick_buttons.append(self.save_default_button)
        self.edit_selected_button = ttk.Button(
            settings_buttons,
            text="编辑此目录",
            command=self._edit_selected,
        )
        self.edit_selected_button.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        self.quick_buttons.append(self.edit_selected_button)

    def _current(self) -> tuple[str, str | None]:
        return self.navigation[-1]

    def _current_items(self) -> list[Category | FolderNode]:
        view, identifier = self._current()
        if view == "home":
            return list(self.config_data.categories)
        if view == "category" and identifier:
            return build_category_tree(self.config_data.folders, identifier)
        if view == "folder" and identifier:
            node = self._find_node(identifier)
            return list(node.children) if node else []
        return []

    def _find_node(self, folder_id: str) -> FolderNode | None:
        entry = self.config_data.folder(folder_id)
        if not entry:
            return None
        pending = build_category_tree(self.config_data.folders, entry.category_id)
        while pending:
            node = pending.pop()
            if node.entry.id == folder_id:
                return node
            pending.extend(node.children)
        return None

    def render(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

        view, identifier = self._current()
        title, breadcrumb = self._view_heading(view, identifier)
        self.title_label.configure(text=title)
        self.breadcrumb_label.configure(text=breadcrumb)
        self.back_button.configure(state="normal" if len(self.navigation) > 1 else "disabled")
        if view == "folder" and identifier:
            self.selected_folder_id = identifier
        elif self.selected_folder_id:
            selected = self.config_data.folder(self.selected_folder_id)
            if not selected or (view == "category" and selected.category_id != identifier):
                self.selected_folder_id = None

        items = self._current_items()
        max_page = max(0, (len(items) - 1) // PAGE_SIZE)
        self.page = min(self.page, max_page)
        visible = items[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]

        if not visible:
            tk.Label(
                self.content,
                text="暂无内容",
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 11),
            ).pack(pady=70)
        else:
            for index, item in enumerate(visible, start=1):
                self._render_row(index, item)

        pages = max_page + 1
        self.page_label.configure(text=f"{self.page + 1} / {pages}" if pages > 1 else "")
        self.previous_button.configure(state="normal" if self.page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.page < max_page else "disabled")
        self._update_action_panel()

    def _view_heading(self, view: str, identifier: str | None) -> tuple[str, str]:
        if view == "home":
            return "文件夹启动器", "全部分类"
        if view == "category" and identifier:
            category = self.config_data.category(identifier)
            return (category.name if category else "分类", "分类 / " + (category.name if category else ""))
        if view == "folder" and identifier:
            entry = self.config_data.folder(identifier)
            category = self.config_data.category(entry.category_id) if entry else None
            return (
                entry.name if entry else "文件夹",
                f"分类 / {category.name if category else ''} / {entry.name if entry else ''}",
            )
        return "快速打开", ""

    def _render_row(self, index: int, item: Category | FolderNode) -> None:
        row = tk.Frame(
            self.content,
            bg=COLORS["selected"] if self._item_is_selected(item) else COLORS["surface"],
            highlightthickness=1,
            highlightbackground=COLORS["accent"] if self._item_is_selected(item) else COLORS["line"],
            cursor="hand2",
        )
        row.pack(fill="x", pady=4)
        row.columnconfigure(1, weight=1)

        number = tk.Label(
            row,
            text=str(index),
            bg=COLORS["accent_soft"],
            fg=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
            width=3,
            height=2,
        )
        number.grid(row=0, column=0, rowspan=2, padx=10, pady=8)

        row_bg = COLORS["selected"] if self._item_is_selected(item) else COLORS["surface"]
        if isinstance(item, Category):
            name = item.name
            count = sum(1 for folder in self.config_data.folders if folder.category_id == item.id)
            detail = f"{count} 个文件夹"
            action = "进入"
        else:
            name = item.entry.name
            detail = item.entry.path
            action = f"进入 · {len(item.children)} 项" if item.children else "运行"

        name_label = tk.Label(
            row,
            text=name,
            bg=row_bg,
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        detail_label = tk.Label(
            row,
            text=detail,
            bg=row_bg,
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        )
        detail_label.grid(row=1, column=1, sticky="ew", pady=(0, 10))
        default_label = "" if isinstance(item, Category) else f"默认：{command_label(item.entry, self.config_data)}"
        default_action_label = tk.Label(
            row,
            text=default_label,
            bg=row_bg,
            fg=COLORS["accent"],
            font=("Microsoft YaHei UI", 8, "bold"),
            anchor="e",
        )
        default_action_label.grid(row=0, column=2, sticky="e", padx=(8, 10), pady=(10, 0))
        action_button = ttk.Button(row, text=action, width=11, command=lambda selected=item: self._run_row_action(selected))
        action_button.grid(row=1, column=2, sticky="e", padx=(8, 10), pady=(2, 9))

        for widget in (row, number, name_label, detail_label, default_action_label):
            widget.bind("<Button-1>", lambda _event, selected=item: self.activate_item(selected))
            if isinstance(item, FolderNode) and not item.children:
                widget.bind("<Double-1>", lambda _event, entry=item.entry: self._launch_entry(entry))

    def _item_is_selected(self, item: Category | FolderNode) -> bool:
        return isinstance(item, FolderNode) and item.entry.id == self.selected_folder_id

    def _run_row_action(self, item: Category | FolderNode) -> None:
        if isinstance(item, Category) or item.children:
            self.activate_item(item)
            return
        self.selected_folder_id = item.entry.id
        self._launch_entry(item.entry)

    def activate_item(self, item: Category | FolderNode) -> None:
        self.page = 0
        if isinstance(item, Category):
            self.navigation.append(("category", item.id))
            self.selected_folder_id = None
            self.render()
            return
        if item.children:
            self.navigation.append(("folder", item.entry.id))
            self.selected_folder_id = item.entry.id
            self.render()
            return
        self.selected_folder_id = item.entry.id
        self.render()

    def launch_current(self) -> None:
        entry = self._selected_entry()
        if entry:
            self._launch_entry(entry)

    def _selected_entry(self) -> FolderEntry | None:
        return self.config_data.folder(self.selected_folder_id) if self.selected_folder_id else None

    def _action_choices(self) -> dict[str, tuple[str | None, bool]]:
        choices: dict[str, tuple[str | None, bool]] = {"仅打开文件夹": (None, False)}
        for command in self.config_data.commands:
            choices[command.name] = (command.id, False)
            if command.supports_continue:
                choices[f"{command.name} --continue"] = (command.id, True)
        return choices

    def _update_action_panel(self) -> None:
        self.default_actions = self._action_choices()
        self.default_action_box.configure(values=list(self.default_actions))
        self.custom_commands = {
            command.name: command.id
            for command in self.config_data.commands
            if command.id not in {"claude", "agy"}
        }
        custom_names = list(self.custom_commands)
        self.custom_command_box.configure(values=custom_names)
        if self.custom_command_var.get() not in self.custom_commands:
            self.custom_command_var.set(custom_names[0] if custom_names else "")
        if custom_names:
            if not self.custom_row.winfo_manager():
                self.custom_row.pack(
                    fill="x",
                    pady=(7, 2),
                    before=self.command_explorer_check,
                )
        else:
            self.custom_row.pack_forget()
        self.custom_command_box.configure(state="readonly" if custom_names else "disabled")
        self.custom_run_button.configure(state="normal" if custom_names else "disabled")

        entry = self._selected_entry()
        state = "normal" if entry else "disabled"
        for button in self.quick_buttons:
            if button is self.custom_run_button and not custom_names:
                continue
            button.configure(state=state)
        self.default_action_box.configure(state="readonly" if entry else "disabled")
        self.custom_command_box.configure(state="readonly" if entry and custom_names else "disabled")

        if not entry:
            self.selected_name_var.set("未选择目录")
            self.selected_path_var.set("-")
            self.selected_default_var.set("默认动作：-")
            self.default_action_var.set("仅打开文件夹")
            self.open_with_command_var.set(False)
            return

        self.selected_name_var.set(entry.name)
        self.selected_path_var.set(entry.path)
        self.selected_default_var.set(f"默认动作：{command_label(entry, self.config_data)}")
        self.open_with_command_var.set(entry.open_explorer if entry.command_id else False)
        selected_action = "仅打开文件夹"
        for label, action in self.default_actions.items():
            if action == (entry.command_id, entry.continue_session):
                selected_action = label
                break
        self.default_action_var.set(selected_action)

    def _launch_quick(self, command_id: str | None, continue_session: bool, open_explorer: bool) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        try:
            self.status_var.set(
                self.runner.launch_action(
                    entry,
                    self.config_data,
                    command_id=command_id,
                    continue_session=continue_session,
                    open_explorer=open_explorer,
                )
            )
        except LaunchError as exc:
            self.status_var.set("启动失败")
            messagebox.showerror("无法启动", str(exc), parent=self)

    def _launch_custom(self) -> None:
        command_id = self.custom_commands.get(self.custom_command_var.get())
        if command_id:
            self._launch_quick(command_id, False, self.open_with_command_var.get())

    def _save_default_action(self) -> None:
        entry = self._selected_entry()
        action = self.default_actions.get(self.default_action_var.get())
        if not entry or action is None:
            return
        command_id, continue_session = action
        entry.command_id = command_id
        entry.continue_session = continue_session
        entry.open_explorer = True if command_id is None else self.open_with_command_var.get()
        self._save_and_refresh("默认动作已保存", reset_navigation=False)

    def _edit_selected(self) -> None:
        entry = self._selected_entry()
        if entry:
            self.edit_folder(entry)

    def _launch_entry(self, entry: FolderEntry) -> None:
        try:
            self.status_var.set(self.runner.launch(entry, self.config_data))
        except LaunchError as exc:
            self.status_var.set("启动失败")
            messagebox.showerror("无法启动", str(exc), parent=self)

    def go_back(self) -> None:
        if len(self.navigation) > 1:
            self.navigation.pop()
            self.page = 0
            view, identifier = self._current()
            self.selected_folder_id = identifier if view == "folder" else None
            self.render()

    def change_page(self, offset: int) -> None:
        self.page = max(0, self.page + offset)
        self.render()

    def _handle_key(self, event: tk.Event) -> None:
        widget_class = event.widget.winfo_class() if event.widget else ""
        if widget_class in {"Entry", "TEntry", "Text", "TCombobox", "Spinbox"}:
            return
        if event.char and event.char in "123456789":
            index = int(event.char) - 1
            items = self._current_items()[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]
            if index < len(items):
                item = items[index]
                if isinstance(item, FolderNode) and not item.children:
                    self.selected_folder_id = item.entry.id
                    self._launch_entry(item.entry)
                    self.render()
                else:
                    self.activate_item(item)
        elif event.keysym in {"Escape", "BackSpace"}:
            self.go_back()
        elif event.keysym == "Return":
            self.launch_current()
        elif event.keysym in {"Next", "Right"}:
            self.change_page(1)
        elif event.keysym in {"Prior", "Left"}:
            self.change_page(-1)

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="选择文件夹")
        if path:
            self.path_var.set(path)
            self.add_typed_path()

    def add_typed_path(self) -> None:
        path = self.path_var.get().strip().strip('"')
        if not path:
            self.path_entry.focus_set()
            return
        if not Path(path).is_dir():
            messagebox.showerror("路径无效", f"文件夹不存在：\n{path}", parent=self)
            return
        if any(normalized(item.path) == normalized(path) for item in self.config_data.folders):
            messagebox.showinfo("已存在", "这个文件夹已经在列表中。", parent=self)
            return
        suggested = suggest_category(path, self.config_data.categories)
        editor = FolderEditor(self, self.config_data, path=path, category_id=suggested)
        self.wait_window(editor)
        if editor.result:
            self.config_data.folders.append(editor.result)
            self._save_and_refresh("已添加文件夹")
            self.path_var.set("")

    def edit_folder(self, entry: FolderEntry, parent: tk.Misc | None = None) -> bool:
        editor = FolderEditor(parent or self, self.config_data, entry=entry)
        self.wait_window(editor)
        if not editor.result:
            return False
        position = self.config_data.folders.index(entry)
        self.config_data.folders[position] = editor.result
        self._save_and_refresh("已更新文件夹")
        return True

    def _save_and_refresh(self, message: str = "配置已保存", reset_navigation: bool = True) -> None:
        try:
            self.store.save(self.config_data)
        except (OSError, ValueError) as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)
            return
        self.status_var.set(message)
        if reset_navigation:
            self.navigation = [("home", None)]
            self.selected_folder_id = None
            self.page = 0
        self.render()

    def open_manager(self) -> None:
        dialog = ManagerDialog(self, self.config_data, self._save_and_refresh, self.edit_folder)
        self.wait_window(dialog)
        self.render()


class FolderEditor(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        config: AppConfig,
        entry: FolderEntry | None = None,
        path: str = "",
        category_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.config_data = config
        self.original = entry
        self.result: FolderEntry | None = None
        self.title("编辑文件夹" if entry else "添加文件夹")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        initial_path = entry.path if entry else path
        self.name_var = tk.StringVar(value=entry.name if entry else (Path(initial_path).name or initial_path))
        self.path_var = tk.StringVar(value=initial_path)
        selected_category = entry.category_id if entry else category_id
        self.category_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.continue_var = tk.BooleanVar(value=entry.continue_session if entry else False)
        self.explorer_var = tk.BooleanVar(value=entry.open_explorer if entry else True)
        self.category_names = {item.name: item.id for item in config.categories}
        self.command_names = {"不运行命令": None, **{item.name: item.id for item in config.commands}}

        for name, identifier in self.category_names.items():
            if identifier == selected_category:
                self.category_var.set(name)
        selected_command = entry.command_id if entry else None
        for name, identifier in self.command_names.items():
            if identifier == selected_command:
                self.command_var.set(name)

        body = ttk.Frame(self, padding=18)
        body.grid(sticky="nsew")
        body.columnconfigure(1, weight=1)
        self._field(body, 0, "名称", ttk.Entry(body, textvariable=self.name_var, width=48))

        path_frame = ttk.Frame(body)
        path_frame.columnconfigure(0, weight=1)
        ttk.Entry(path_frame, textvariable=self.path_var, width=40).grid(row=0, column=0, sticky="ew")
        ttk.Button(path_frame, text="浏览", command=self._browse).grid(row=0, column=1, padx=(6, 0))
        self._field(body, 1, "路径", path_frame)

        category_box = ttk.Combobox(
            body, textvariable=self.category_var, values=list(self.category_names), state="readonly", width=45
        )
        self._field(body, 2, "分类", category_box)
        command_box = ttk.Combobox(
            body, textvariable=self.command_var, values=list(self.command_names), state="readonly", width=45
        )
        command_box.bind("<<ComboboxSelected>>", lambda _event: self._sync_continue())
        self._field(body, 3, "命令", command_box)

        options = ttk.Frame(body)
        ttk.Checkbutton(options, text="使用 --continue", variable=self.continue_var).pack(side="left")
        ttk.Checkbutton(options, text="同时打开资源管理器", variable=self.explorer_var).pack(side="left", padx=(16, 0))
        self._field(body, 4, "启动", options)

        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side="left")
        ttk.Button(buttons, text="保存", style="Accent.TButton", command=self._save).pack(side="left", padx=(8, 0))
        self._sync_continue()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.wait_visibility()
        self.focus_set()

    @staticmethod
    def _field(parent: ttk.Frame, row: int, label: str, widget: tk.Widget) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=7)
        widget.grid(row=row, column=1, sticky="ew", pady=7)

    def _browse(self) -> None:
        path = filedialog.askdirectory(parent=self, initialdir=self.path_var.get() or None)
        if path:
            self.path_var.set(path)
            if not self.name_var.get().strip():
                self.name_var.set(Path(path).name)

    def _sync_continue(self) -> None:
        command_id = self.command_names.get(self.command_var.get())
        command = self.config_data.command(command_id)
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
            messagebox.showerror("启动方式无效", "至少需要打开资源管理器或运行一个命令。", parent=self)
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


class ManagerDialog(tk.Toplevel):
    def __init__(
        self,
        parent: FolderLauncherApp,
        config: AppConfig,
        save_callback: Callable[[str], None],
        edit_folder_callback: Callable[[FolderEntry, tk.Misc | None], bool],
    ) -> None:
        super().__init__(parent)
        self.parent_app = parent
        self.config_data = config
        self.save_callback = save_callback
        self.edit_folder_callback = edit_folder_callback
        self.title("管理")
        self.geometry("860x520")
        self.minsize(760, 440)
        self.transient(parent)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=14)
        self.folder_tab = ttk.Frame(notebook, padding=10)
        self.category_tab = ttk.Frame(notebook, padding=10)
        self.command_tab = ttk.Frame(notebook, padding=10)
        notebook.add(self.folder_tab, text="文件夹")
        notebook.add(self.category_tab, text="分类")
        notebook.add(self.command_tab, text="命令")
        self._build_folder_tab()
        self._build_category_tab()
        self._build_command_tab()
        self.refresh_all()
        self.bind("<Escape>", lambda _event: self.destroy())

    @staticmethod
    def _tree(parent: ttk.Frame, columns: tuple[str, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=140, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    @staticmethod
    def _buttons(parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(10, 0))
        return frame

    def _build_folder_tab(self) -> None:
        self.folder_tree = self._tree(self.folder_tab, ("名称", "分类", "启动方式", "路径"))
        self.folder_tree.column("名称", width=130)
        self.folder_tree.column("分类", width=120)
        self.folder_tree.column("启动方式", width=140)
        self.folder_tree.column("路径", width=360)
        self.folder_tree.bind("<Double-1>", lambda _event: self.edit_folder())
        buttons = self._buttons(self.folder_tab)
        ttk.Button(buttons, text="添加", command=self.add_folder).pack(side="left")
        ttk.Button(buttons, text="编辑", command=self.edit_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="删除", command=self.delete_folder).pack(side="left")

    def _build_category_tab(self) -> None:
        self.category_tree = self._tree(self.category_tab, ("名称", "路径前缀"))
        self.category_tree.column("名称", width=180)
        self.category_tree.column("路径前缀", width=560)
        self.category_tree.bind("<Double-1>", lambda _event: self.edit_category())
        buttons = self._buttons(self.category_tab)
        ttk.Button(buttons, text="添加", command=self.add_category).pack(side="left")
        ttk.Button(buttons, text="编辑", command=self.edit_category).pack(side="left", padx=6)
        ttk.Button(buttons, text="删除", command=self.delete_category).pack(side="left")

    def _build_command_tab(self) -> None:
        self.command_tree = self._tree(self.command_tab, ("名称", "程序", "默认参数", "继续会话"))
        self.command_tree.column("名称", width=160)
        self.command_tree.column("程序", width=240)
        self.command_tree.column("默认参数", width=260)
        self.command_tree.column("继续会话", width=100)
        self.command_tree.bind("<Double-1>", lambda _event: self.edit_command())
        buttons = self._buttons(self.command_tab)
        ttk.Button(buttons, text="添加", command=self.add_command).pack(side="left")
        ttk.Button(buttons, text="编辑", command=self.edit_command).pack(side="left", padx=6)
        ttk.Button(buttons, text="删除", command=self.delete_command).pack(side="left")

    def refresh_all(self) -> None:
        for tree in (self.folder_tree, self.category_tree, self.command_tree):
            tree.delete(*tree.get_children())
        for item in self.config_data.folders:
            category = self.config_data.category(item.category_id)
            self.folder_tree.insert(
                "",
                "end",
                iid=item.id,
                values=(item.name, category.name if category else "", command_label(item, self.config_data), item.path),
            )
        for item in self.config_data.categories:
            self.category_tree.insert("", "end", iid=item.id, values=(item.name, "；".join(item.prefixes)))
        for item in self.config_data.commands:
            self.command_tree.insert(
                "",
                "end",
                iid=item.id,
                values=(item.name, item.program, " ".join(item.arguments), "是" if item.supports_continue else "否"),
            )

    @staticmethod
    def _selected_id(tree: ttk.Treeview) -> str | None:
        selection = tree.selection()
        return selection[0] if selection else None

    def add_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="选择文件夹")
        if not path:
            return
        editor = FolderEditor(
            self,
            self.config_data,
            path=path,
            category_id=suggest_category(path, self.config_data.categories),
        )
        self.wait_window(editor)
        if editor.result:
            self.config_data.folders.append(editor.result)
            self.save_callback("已添加文件夹")
            self.refresh_all()

    def edit_folder(self) -> None:
        identifier = self._selected_id(self.folder_tree)
        entry = self.config_data.folder(identifier) if identifier else None
        if entry and self.edit_folder_callback(entry, self):
            self.refresh_all()

    def delete_folder(self) -> None:
        identifier = self._selected_id(self.folder_tree)
        entry = self.config_data.folder(identifier) if identifier else None
        if not entry:
            return
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

    def edit_category(self) -> None:
        identifier = self._selected_id(self.category_tree)
        category = self.config_data.category(identifier) if identifier else None
        if not category:
            return
        editor = CategoryEditor(self, category)
        self.wait_window(editor)
        if editor.result:
            position = self.config_data.categories.index(category)
            self.config_data.categories[position] = editor.result
            self.save_callback("已更新分类")
            self.refresh_all()

    def delete_category(self) -> None:
        identifier = self._selected_id(self.category_tree)
        category = self.config_data.category(identifier) if identifier else None
        if not category:
            return
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

    def edit_command(self) -> None:
        identifier = self._selected_id(self.command_tree)
        command = self.config_data.command(identifier)
        if not command:
            return
        editor = CommandEditor(self, command)
        self.wait_window(editor)
        if editor.result:
            position = self.config_data.commands.index(command)
            self.config_data.commands[position] = editor.result
            self.save_callback("已更新命令")
            self.refresh_all()

    def delete_command(self) -> None:
        identifier = self._selected_id(self.command_tree)
        command = self.config_data.command(identifier)
        if not command:
            return
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


class CategoryEditor(tk.Toplevel):
    def __init__(self, parent: tk.Misc, category: Category | None = None) -> None:
        super().__init__(parent)
        self.original = category
        self.result: Category | None = None
        self.title("编辑分类" if category else "添加分类")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        self.name_var = tk.StringVar(value=category.name if category else "")
        ttk.Label(body, text="名称").grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=6)
        ttk.Entry(body, textvariable=self.name_var, width=48).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="路径前缀").grid(row=1, column=0, sticky="nw", padx=(0, 12), pady=6)
        self.prefix_text = tk.Text(body, width=48, height=5, font=("Consolas", 9))
        self.prefix_text.grid(row=1, column=1, pady=6)
        if category:
            self.prefix_text.insert("1.0", "\n".join(category.prefixes))
        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side="left")
        ttk.Button(buttons, text="保存", command=self._save).pack(side="left", padx=(8, 0))

    def _save(self) -> None:
        name = self.name_var.get().strip()
        prefixes = [line.strip().strip('"') for line in self.prefix_text.get("1.0", "end").splitlines() if line.strip()]
        if not name:
            messagebox.showerror("信息不完整", "分类名称不能为空。", parent=self)
            return
        self.result = Category(self.original.id if self.original else new_id("category"), name, prefixes)
        self.destroy()


class CommandEditor(tk.Toplevel):
    def __init__(self, parent: tk.Misc, command: CommandProfile | None = None) -> None:
        super().__init__(parent)
        self.original = command
        self.result: CommandProfile | None = None
        self.title("编辑命令" if command else "添加命令")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        self.name_var = tk.StringVar(value=command.name if command else "")
        self.program_var = tk.StringVar(value=command.program if command else "")
        self.continue_var = tk.BooleanVar(value=command.supports_continue if command else False)
        ttk.Label(body, text="名称").grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=6)
        ttk.Entry(body, textvariable=self.name_var, width=48).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="程序").grid(row=1, column=0, sticky="nw", padx=(0, 12), pady=6)
        ttk.Entry(body, textvariable=self.program_var, width=48).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Label(body, text="默认参数").grid(row=2, column=0, sticky="nw", padx=(0, 12), pady=6)
        self.arguments_text = tk.Text(body, width=48, height=5, font=("Consolas", 9))
        self.arguments_text.grid(row=2, column=1, pady=6)
        if command:
            self.arguments_text.insert("1.0", "\n".join(command.arguments))
        ttk.Checkbutton(body, text="支持 --continue", variable=self.continue_var).grid(
            row=3, column=1, sticky="w", pady=6
        )
        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side="left")
        ttk.Button(buttons, text="保存", command=self._save).pack(side="left", padx=(8, 0))

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
