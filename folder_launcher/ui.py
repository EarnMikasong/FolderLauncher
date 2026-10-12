from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import ConfigStore, create_default_config
from .hierarchy import FolderNode, build_category_tree, normalized, suggest_category
from .launcher import FolderLauncher, LaunchError, command_label
from .dialogs import FolderEditor, ManagerDialog
from .models import AppConfig, Category, FolderEntry
from .search import search_folders


PAGE_SIZE = 7
COLORS = {
    "app": "#F1F4F6",
    "sidebar": "#17313B",
    "sidebar_hover": "#294B56",
    "sidebar_selected": "#E5F1EE",
    "sidebar_muted": "#87A0A9",
    "surface": "#FFFFFF",
    "surface_alt": "#F6F8F9",
    "line": "#DCE2E6",
    "text": "#172126",
    "muted": "#66747C",
    "accent": "#0B766B",
    "accent_hover": "#095F57",
    "accent_soft": "#E1F1EE",
    "accent_bright": "#4FB3A6",
    "blue": "#346B9B",
    "blue_hover": "#28587F",
    "claude": "#B85F3A",
    "claude_hover": "#994D2F",
}


class FolderLauncherApp(ctk.CTk):
    def __init__(self, store: ConfigStore | None = None) -> None:
        ctk.set_appearance_mode("light")
        super().__init__()
        self.store = store or ConfigStore()
        self.runner = FolderLauncher()
        self.config_data = self._load_config()
        self.navigation: list[tuple[str, str | None]] = [("home", None)]
        self.page = 0
        self.selected_folder_id: str | None = None
        self.search_query = ""
        self.row_widgets: dict[str, ctk.CTkFrame] = {}
        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self.open_with_command_var = tk.BooleanVar(value=False)
        self.default_action_var = tk.StringVar(value="仅打开文件夹")
        self.custom_command_var = tk.StringVar()
        self.default_actions: dict[str, tuple[str | None, bool]] = {}
        self.custom_commands: dict[str, str] = {}
        self.action_widgets: list[ctk.CTkButton] = []

        self.title("文件夹启动器")
        self.geometry("1160x760")
        self.minsize(1020, 700)
        self.configure(fg_color=COLORS["app"])
        self.grid_columnconfigure(0, minsize=224)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, minsize=304)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build_sidebar()
        self._build_main()
        self._build_actions()
        self.bind_all("<Key>", self._handle_key, add="+")
        self.bind_all("<Control-k>", lambda _event: self.search_entry.focus_set())
        self.bind_all("<Control-K>", lambda _event: self.search_entry.focus_set())
        self.render()

    def _load_config(self) -> AppConfig:
        try:
            return self.store.load()
        except ValueError as exc:
            messagebox.showerror("配置错误", str(exc))
            return create_default_config()

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=224, corner_radius=0, fg_color=COLORS["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="文件夹启动器",
            text_color="#FFFFFF",
            font=ctk.CTkFont("Microsoft YaHei UI", 19, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 2))
        ctk.CTkLabel(
            self.sidebar,
            text="WORKSPACE LAUNCHER",
            text_color=COLORS["sidebar_muted"],
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 22))
        self.home_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.home_row.grid(row=2, column=0, sticky="ew", padx=12)
        self.home_row.grid_columnconfigure(1, weight=1)
        self.home_indicator = ctk.CTkFrame(self.home_row, width=3, corner_radius=0, fg_color="transparent")
        self.home_indicator.grid(row=0, column=0, sticky="ns")
        self.home_button = ctk.CTkButton(
            self.home_row,
            text="全部分类",
            height=40,
            corner_radius=6,
            anchor="w",
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color="#E4EEF0",
            font=ctk.CTkFont("Microsoft YaHei UI", 12),
            command=self.go_home,
        )
        self.home_button.grid(row=0, column=1, sticky="ew")
        self.category_sidebar = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color="#31525D",
            scrollbar_button_hover_color="#466772",
        )
        self.category_sidebar.grid(row=3, column=0, sticky="nsew", padx=6, pady=(10, 8))
        self.category_sidebar.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            self.sidebar,
            text="配置管理",
            height=38,
            corner_radius=6,
            fg_color="#294954",
            hover_color="#355B67",
            text_color="#FFFFFF",
            font=ctk.CTkFont("Microsoft YaHei UI", 11, "bold"),
            command=self.open_manager,
        ).grid(row=4, column=0, sticky="ew", padx=14, pady=(8, 18))

    def _build_main(self) -> None:
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["app"])
        self.main.grid(row=0, column=1, sticky="nsew", padx=(22, 14), pady=20)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        self.back_button = ctk.CTkButton(
            header,
            text="←",
            width=38,
            height=38,
            corner_radius=6,
            fg_color=COLORS["surface"],
            hover_color=COLORS["line"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["line"],
            font=ctk.CTkFont(size=18),
            command=self.go_back,
        )
        self.back_button.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        self.title_label = ctk.CTkLabel(
            header,
            text="全部分类",
            text_color=COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 24, "bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=1, sticky="ew")
        self.breadcrumb_label = ctk.CTkLabel(
            header,
            text="工作区 / 全部分类",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 10),
            anchor="w",
        )
        self.breadcrumb_label.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search_change())
        self.search_entry = ctk.CTkEntry(
            header,
            textvariable=self.search_var,
            width=250,
            height=36,
            corner_radius=6,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["line"],
            placeholder_text="搜索文件夹  Ctrl+K",
            font=ctk.CTkFont("Segoe UI", 11),
        )
        self.search_entry.grid(row=0, column=2, rowspan=2, sticky="e")
        self.search_entry.bind("<Return>", self._on_search_return)
        self.search_entry.bind("<Escape>", self._on_search_escape)

        add_bar = ctk.CTkFrame(
            self.main,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["line"],
        )
        add_bar.grid(row=1, column=0, sticky="ew", pady=(20, 14))
        add_bar.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            add_bar,
            textvariable=self.path_var,
            height=40,
            corner_radius=6,
            border_width=0,
            fg_color=COLORS["surface_alt"],
            placeholder_text="粘贴文件夹路径",
            font=ctk.CTkFont("Segoe UI", 11),
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.path_entry.bind("<Return>", lambda _event: self.add_typed_path())
        self._small_button(add_bar, "浏览", self.choose_folder, 72).grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            add_bar,
            text="+ 添加",
            width=82,
            height=40,
            corner_radius=6,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont("Microsoft YaHei UI", 11, "bold"),
            command=self.add_typed_path,
        ).grid(row=0, column=2, padx=(0, 8), pady=8)

        list_header = ctk.CTkFrame(self.main, fg_color="transparent")
        list_header.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        list_header.grid_columnconfigure(0, weight=1)
        self.section_label = ctk.CTkLabel(
            list_header,
            text="分类",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        )
        self.section_label.grid(row=0, column=0, sticky="ew")
        self.content = ctk.CTkScrollableFrame(
            self.main,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#C7D0D5",
            scrollbar_button_hover_color="#AEBBC2",
        )
        self.content.grid(row=3, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self.main, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure(0, weight=1)
        status_row = ctk.CTkFrame(footer, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            status_row,
            textvariable=self.status_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            status_row,
            text="↑↓ 选择 · Enter 打开 · Esc 返回 · Ctrl+K 搜索",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 9),
        ).grid(row=0, column=1, sticky="e", padx=(12, 12))
        self.previous_button = self._pager_button(footer, "←", -1)
        self.previous_button.grid(row=0, column=1, padx=(8, 5))
        self.page_label = ctk.CTkLabel(footer, text="", width=44, text_color=COLORS["muted"])
        self.page_label.grid(row=0, column=2)
        self.next_button = self._pager_button(footer, "→", 1)
        self.next_button.grid(row=0, column=3, padx=(5, 0))

    def _build_actions(self) -> None:
        self.actions = ctk.CTkFrame(self, width=304, corner_radius=0, fg_color=COLORS["surface"])
        self.actions.grid(row=0, column=2, sticky="nsew")
        self.actions.grid_propagate(False)
        self.actions.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.actions,
            text="快捷动作",
            text_color=COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 14, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(25, 0))
        self.selected_card = ctk.CTkFrame(self.actions, fg_color="transparent", corner_radius=8)
        self.selected_card.grid(row=1, column=0, sticky="ew", padx=22, pady=(22, 4))
        self.selected_card.grid_columnconfigure(0, weight=1)
        self.selected_name_label = ctk.CTkLabel(
            self.selected_card,
            text="未选择目录",
            text_color=COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 15, "bold"),
            anchor="w",
        )
        self.selected_name_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(12, 2))
        path_row = ctk.CTkFrame(self.selected_card, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))
        path_row.grid_columnconfigure(0, weight=1)
        self.selected_path_label = ctk.CTkLabel(
            path_row,
            text="-",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=176,
        )
        self.selected_path_label.grid(row=0, column=0, sticky="ew")
        self.copy_path_button = self._small_button(path_row, "复制路径", self._copy_selected_path, 64)
        self.copy_path_button.configure(height=28)
        self.copy_path_button.grid(row=0, column=1, padx=(8, 0))
        self.selected_default_label = ctk.CTkLabel(
            self.selected_card,
            text="默认动作  -",
            text_color=COLORS["accent"],
            font=ctk.CTkFont("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        )
        self.selected_default_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(7, 12))

        self.open_folder_button = self._action_button(
            4, "打开文件夹", COLORS["accent"], COLORS["accent_hover"], lambda: self._launch_quick(None, False, True)
        )
        ctk.CTkLabel(
            self.actions,
            text="在当前目录启动",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", padx=22, pady=(20, 7))
        command_grid = ctk.CTkFrame(self.actions, fg_color="transparent")
        command_grid.grid(row=6, column=0, sticky="ew", padx=22)
        command_grid.grid_columnconfigure((0, 1), weight=1)
        command_specs = (
            ("Claude", "claude", False, COLORS["claude"], COLORS["claude_hover"], "#FFFFFF"),
            ("Claude 继续", "claude", True, "#F2E5DF", "#E8D2C8", COLORS["text"]),
            ("Agy", "agy", False, COLORS["blue"], COLORS["blue_hover"], "#FFFFFF"),
            ("Agy 继续", "agy", True, "#E4EDF5", "#D3E1EC", COLORS["text"]),
        )
        for index, (label, command_id, use_continue, color, hover, text_color) in enumerate(command_specs):
            button = ctk.CTkButton(
                command_grid,
                text=label,
                height=39,
                corner_radius=6,
                fg_color=color,
                hover_color=hover,
                text_color=text_color,
                font=ctk.CTkFont("Microsoft YaHei UI", 10, "bold"),
                command=lambda cid=command_id, cont=use_continue: self._launch_quick(
                    cid, cont, self.open_with_command_var.get()
                ),
            )
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 4) if index % 2 == 0 else (4, 0), pady=4)
            self.action_widgets.append(button)

        self.custom_row = ctk.CTkFrame(self.actions, fg_color="transparent")
        self.custom_row.grid(row=7, column=0, sticky="ew", padx=22, pady=(8, 0))
        self.custom_row.grid_columnconfigure(0, weight=1)
        self.custom_command_menu = ctk.CTkOptionMenu(
            self.custom_row,
            variable=self.custom_command_var,
            values=["无自定义命令"],
            height=35,
            corner_radius=6,
            fg_color=COLORS["surface_alt"],
            button_color="#D7E0E4",
            button_hover_color="#C3CED3",
            text_color=COLORS["text"],
        )
        self.custom_command_menu.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.custom_run_button = self._small_button(self.custom_row, "运行", self._launch_custom, 58)
        self.custom_run_button.grid(row=0, column=1)
        self.action_widgets.append(self.custom_run_button)

        self.open_with_switch = ctk.CTkSwitch(
            self.actions,
            text="命令同时打开文件夹",
            variable=self.open_with_command_var,
            progress_color=COLORS["accent"],
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 10),
        )
        self.open_with_switch.grid(row=8, column=0, sticky="w", padx=22, pady=(12, 0))
        ctk.CTkFrame(self.actions, height=1, fg_color=COLORS["line"]).grid(
            row=9, column=0, sticky="ew", padx=22, pady=(20, 14)
        )
        ctk.CTkLabel(
            self.actions,
            text="数字键默认动作",
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
        ).grid(row=10, column=0, sticky="ew", padx=22, pady=(0, 6))
        self.default_action_menu = ctk.CTkOptionMenu(
            self.actions,
            variable=self.default_action_var,
            values=["仅打开文件夹"],
            height=38,
            corner_radius=6,
            fg_color=COLORS["surface_alt"],
            button_color="#D7E0E4",
            button_hover_color="#C3CED3",
            text_color=COLORS["text"],
        )
        self.default_action_menu.grid(row=11, column=0, sticky="ew", padx=22)
        settings = ctk.CTkFrame(self.actions, fg_color="transparent")
        settings.grid(row=12, column=0, sticky="ew", padx=22, pady=(8, 0))
        settings.grid_columnconfigure((0, 1), weight=1)
        self.save_default_button = ctk.CTkButton(
            settings,
            text="保存默认",
            height=36,
            corner_radius=6,
            fg_color=COLORS["accent_soft"],
            hover_color="#CFE8E3",
            text_color=COLORS["accent"],
            font=ctk.CTkFont("Microsoft YaHei UI", 10, "bold"),
            command=self._save_default_action,
        )
        self.save_default_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.edit_selected_button = self._small_button(settings, "编辑目录", self._edit_selected)
        self.edit_selected_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.action_widgets.extend([self.open_folder_button, self.save_default_button, self.edit_selected_button, self.copy_path_button])

    @staticmethod
    def _small_button(parent: tk.Misc, text: str, command, width: int = 74) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=36,
            corner_radius=6,
            fg_color="#E5EAED",
            hover_color="#D5DDE1",
            text_color=COLORS["text"],
            command=command,
        )

    def _pager_button(self, parent: tk.Misc, text: str, offset: int) -> ctk.CTkButton:
        button = self._small_button(parent, text, lambda: self.change_page(offset), 34)
        button.configure(height=30)
        return button

    def _action_button(self, row: int, text: str, color: str, hover: str, command) -> ctk.CTkButton:
        button = ctk.CTkButton(
            self.actions,
            text=text,
            height=42,
            corner_radius=6,
            fg_color=color,
            hover_color=hover,
            font=ctk.CTkFont("Microsoft YaHei UI", 11, "bold"),
            command=command,
        )
        button.grid(row=row, column=0, sticky="ew", padx=22)
        return button

    def _current(self) -> tuple[str, str | None]:
        return self.navigation[-1]

    def _current_items(self) -> list[Category | FolderNode]:
        if self.search_query:
            return [FolderNode(entry=entry, children=[]) for entry in search_folders(self.config_data, self.search_query)]
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

    def _refresh_sidebar(self) -> None:
        for child in self.category_sidebar.winfo_children():
            child.destroy()
        view, identifier = self._current()
        home_active = view == "home"
        self.home_indicator.configure(fg_color=COLORS["accent_bright"] if home_active else "transparent")
        self.home_button.configure(
            fg_color=COLORS["sidebar_hover"] if home_active else "transparent",
            text_color="#FFFFFF" if home_active else "#E4EEF0",
            font=ctk.CTkFont("Microsoft YaHei UI", 12, "bold" if home_active else "normal"),
        )
        current_folder = self.config_data.folder(identifier or "") if view == "folder" else None
        for index, category in enumerate(self.config_data.categories, start=1):
            selected = identifier == category.id or (current_folder is not None and current_folder.category_id == category.id)
            count = sum(1 for folder in self.config_data.folders if folder.category_id == category.id)
            row = ctk.CTkFrame(self.category_sidebar, fg_color="transparent")
            row.grid(row=index - 1, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)
            indicator = ctk.CTkFrame(row, width=3, corner_radius=0, fg_color=COLORS["accent_bright"] if selected else "transparent")
            indicator.grid(row=0, column=0, sticky="ns")
            button = ctk.CTkButton(
                row,
                text=f"{index}   {category.name}",
                height=38,
                corner_radius=6,
                anchor="w",
                fg_color=COLORS["sidebar_selected"] if selected else "transparent",
                hover_color=COLORS["sidebar_hover"],
                text_color=COLORS["sidebar"] if selected else "#CFDDE1",
                font=ctk.CTkFont("Microsoft YaHei UI", 10, "bold" if selected else "normal"),
                command=lambda item=category: self.open_category(item),
            )
            button.grid(row=0, column=1, sticky="ew")
            count_label = ctk.CTkLabel(
                row,
                text=str(count),
                text_color=COLORS["sidebar_selected"] if selected else COLORS["sidebar_muted"],
                font=ctk.CTkFont("Segoe UI", 9),
            )
            count_label.grid(row=0, column=2, padx=(4, 8))
            count_label.bind("<Button-1>", lambda _event, item=category: self.open_category(item))

    def render(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.row_widgets.clear()
        view, identifier = self._current()
        searching = bool(self.search_query)
        if searching:
            title, breadcrumb = "搜索", f"工作区 / 搜索「{self.search_query}」"
        else:
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
        if searching:
            self.page = 0
            visible = items
            max_page = 0
        else:
            max_page = max(0, (len(items) - 1) // PAGE_SIZE)
            self.page = min(self.page, max_page)
            visible = items[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]
        if not visible:
            if searching:
                empty_text = f"没有匹配「{self.search_query}」的文件夹，按 Esc 返回"
            elif not self.config_data.folders:
                empty_text = "还没有添加文件夹——在上方粘贴路径后回车，或点击「浏览」"
            else:
                empty_text = "这个分类还没有文件夹——点击左上角返回，或在上方添加"
            ctk.CTkLabel(
                self.content,
                text=empty_text,
                text_color=COLORS["muted"],
                font=ctk.CTkFont("Microsoft YaHei UI", 12),
                wraplength=560,
                justify="center",
            ).grid(row=0, column=0, sticky="ew", pady=90)
        else:
            for index, item in enumerate(visible, start=1):
                self._render_row(index, item)

        if searching:
            self.section_label.configure(text=f"搜索结果 · {len(items)} 个文件夹")
            self.page_label.configure(text="")
            self.previous_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
        else:
            self.section_label.configure(text="分类" if view == "home" else "目录")
            pages = max_page + 1
            self.page_label.configure(text=f"{self.page + 1} / {pages}" if pages > 1 else "")
            self.previous_button.configure(state="normal" if self.page > 0 else "disabled")
            self.next_button.configure(state="normal" if self.page < max_page else "disabled")
        self._refresh_sidebar()
        self._update_actions()

    def _visible_items(self) -> list[Category | FolderNode]:
        items = self._current_items()
        if self.search_query:
            return items
        return items[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.search_query = ""

    def _on_search_change(self) -> None:
        self.search_query = self.search_var.get().strip()
        self.page = 0
        self.render()

    def _on_search_return(self, _event: tk.Event) -> None:
        nodes = [item for item in self._current_items() if isinstance(item, FolderNode)]
        entry = next((node.entry for node in nodes if node.entry.id == self.selected_folder_id), None)
        if entry is None and nodes:
            entry = nodes[0].entry
        if entry is None:
            self.status_var.set("无匹配结果")
            return
        self.selected_folder_id = entry.id
        self._launch_entry(entry)
        self.render()

    def _on_search_escape(self, _event: tk.Event) -> None:
        if self.search_var.get().strip():
            self._clear_search()
            self.focus_set()
        else:
            self.go_back()

    def _view_heading(self, view: str, identifier: str | None) -> tuple[str, str]:
        if view == "home":
            return "全部分类", "工作区 / 全部分类"
        if view == "category" and identifier:
            category = self.config_data.category(identifier)
            name = category.name if category else "分类"
            return name, f"工作区 / {name}"
        entry = self.config_data.folder(identifier or "")
        category = self.config_data.category(entry.category_id) if entry else None
        name = entry.name if entry else "文件夹"
        return name, f"工作区 / {category.name if category else ''} / {name}"

    def _render_row(self, index: int, item: Category | FolderNode) -> None:
        selected = isinstance(item, FolderNode) and item.entry.id == self.selected_folder_id
        row = ctk.CTkFrame(
            self.content,
            fg_color=COLORS["accent_soft"] if selected else COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["accent"] if selected else COLORS["line"],
            height=67,
        )
        row.grid(row=index - 1, column=0, sticky="ew", pady=4, padx=(0, 4))
        row.grid_columnconfigure(1, weight=1)
        row.grid_propagate(False)
        number = ctk.CTkLabel(
            row,
            text=str(index),
            width=38,
            height=38,
            corner_radius=6,
            fg_color=COLORS["accent"] if selected else "#E7ECEF",
            text_color="#FFFFFF" if selected else COLORS["text"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        )
        number.grid(row=0, column=0, rowspan=2, padx=12, pady=13)
        if isinstance(item, Category):
            name = item.name
            detail = f"{sum(1 for folder in self.config_data.folders if folder.category_id == item.id)} 个文件夹"
            badge = "分类"
            action = "进入"
        else:
            name = item.entry.name
            detail = item.entry.path
            if self.search_query:
                category = self.config_data.category(item.entry.category_id)
                badge = category.name if category else "文件夹"
                action = "运行"
            else:
                badge = f"默认 · {command_label(item.entry, self.config_data)}"
                action = "进入" if item.children else "运行"
        name_label = ctk.CTkLabel(
            row,
            text=name,
            text_color=COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="sew", pady=(9, 0))
        detail_label = ctk.CTkLabel(
            row,
            text=detail,
            text_color=COLORS["muted"],
            font=ctk.CTkFont("Segoe UI", 9),
            anchor="w",
        )
        detail_label.grid(row=1, column=1, sticky="new", pady=(0, 8))
        badge_label = ctk.CTkLabel(
            row,
            text=badge,
            text_color=COLORS["accent"] if not isinstance(item, Category) else COLORS["blue"],
            fg_color=COLORS["surface_alt"],
            corner_radius=5,
            height=25,
            font=ctk.CTkFont("Microsoft YaHei UI", 8, "bold"),
        )
        badge_label.grid(row=0, column=2, rowspan=2, padx=(12, 8), pady=20)
        action_button = ctk.CTkButton(
            row,
            text=action,
            width=58,
            height=31,
            corner_radius=6,
            fg_color=COLORS["accent"] if action == "运行" else "#E8EDF0",
            hover_color=COLORS["accent_hover"] if action == "运行" else "#D9E1E5",
            text_color="#FFFFFF" if action == "运行" else COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 9, "bold"),
            command=lambda selected_item=item: self._run_row_action(selected_item),
        )
        action_button.grid(row=0, column=3, rowspan=2, padx=(0, 12), pady=18)
        row.configure(cursor="hand2")
        if isinstance(item, FolderNode):
            self.row_widgets[item.entry.id] = row
        for widget in (row, number, name_label, detail_label, badge_label):
            widget.bind("<Button-1>", lambda _event, selected_item=item: self.activate_item(selected_item))
            if isinstance(item, FolderNode) and not item.children:
                widget.bind("<Double-1>", lambda _event, entry=item.entry: self._launch_entry(entry))
            if not selected:
                widget.bind("<Enter>", lambda _event, target=row: self._set_row_hover(target, True))
                widget.bind("<Leave>", lambda _event, target=row: self._set_row_hover(target, False))

    def _set_row_hover(self, row: ctk.CTkFrame, hover: bool) -> None:
        try:
            row.configure(
                fg_color=COLORS["surface_alt"] if hover else COLORS["surface"],
                border_color="#C3D3D8" if hover else COLORS["line"],
            )
        except tk.TclError:
            pass

    def _ensure_visible(self, key: str) -> None:
        try:
            row = self.row_widgets.get(key)
            if row is None:
                return
            self.content.update_idletasks()
            canvas = getattr(self.content, "_parent_canvas", None)
            if canvas is None:
                return
            bounds = canvas.bbox("all")
            if not bounds:
                return
            total_height = bounds[3]
            if total_height <= 0:
                return
            viewport = canvas.winfo_height()
            if viewport <= 0:
                return
            top = row.winfo_rooty() - canvas.winfo_rooty()
            bottom = top + row.winfo_height()
            if bottom > viewport:
                canvas.yview_moveto(max(0.0, min(1.0, (bottom - viewport + 8) / total_height)))
            elif top < 0:
                canvas.yview_moveto(max(0.0, min(1.0, (top - 8) / total_height)))
        except Exception:
            pass

    def _move_selection(self, keysym: str) -> None:
        nodes = [item for item in self._visible_items() if isinstance(item, FolderNode)]
        if not nodes:
            return
        current = next((index for index, node in enumerate(nodes) if node.entry.id == self.selected_folder_id), None)
        if keysym == "Home":
            target = 0
        elif keysym == "End":
            target = len(nodes) - 1
        elif keysym == "Up":
            target = 0 if current is None else max(0, current - 1)
        else:
            target = 0 if current is None else min(len(nodes) - 1, current + 1)
        self.selected_folder_id = nodes[target].entry.id
        self.render()
        self._ensure_visible(self.selected_folder_id)

    def _run_row_action(self, item: Category | FolderNode) -> None:
        if isinstance(item, Category) or item.children:
            self.activate_item(item)
            return
        self.selected_folder_id = item.entry.id
        self._launch_entry(item.entry)
        self.render()

    def activate_item(self, item: Category | FolderNode) -> None:
        if isinstance(item, Category) or item.children:
            self._clear_search()
        self.page = 0
        if isinstance(item, Category):
            self.open_category(item)
        elif item.children:
            self.navigation.append(("folder", item.entry.id))
            self.selected_folder_id = item.entry.id
            self.render()
        else:
            self.selected_folder_id = item.entry.id
            self.render()

    def open_category(self, category: Category) -> None:
        self._clear_search()
        self.navigation = [("home", None), ("category", category.id)]
        self.selected_folder_id = None
        self.page = 0
        self.render()

    def go_home(self) -> None:
        self._clear_search()
        self.navigation = [("home", None)]
        self.selected_folder_id = None
        self.page = 0
        self.render()

    def go_back(self) -> None:
        self._clear_search()
        if len(self.navigation) > 1:
            self.navigation.pop()
            view, identifier = self._current()
            self.selected_folder_id = identifier if view == "folder" else None
            self.page = 0
            self.render()

    def change_page(self, offset: int) -> None:
        self.page = max(0, self.page + offset)
        self.render()
        try:
            canvas = getattr(self.content, "_parent_canvas", None)
            if canvas is not None:
                canvas.yview_moveto(0)
        except Exception:
            pass

    def _selected_entry(self) -> FolderEntry | None:
        return self.config_data.folder(self.selected_folder_id) if self.selected_folder_id else None

    def _copy_selected_path(self) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        self.clipboard_clear()
        self.clipboard_append(entry.path)
        self.status_var.set("已复制路径")

    def _update_actions(self) -> None:
        self.default_actions = {"仅打开文件夹": (None, False)}
        for command in self.config_data.commands:
            self.default_actions[command.name] = (command.id, False)
            if command.supports_continue:
                self.default_actions[f"{command.name} --continue"] = (command.id, True)
        self.default_action_menu.configure(values=list(self.default_actions))
        self.custom_commands = {
            command.name: command.id for command in self.config_data.commands if command.id not in {"claude", "agy"}
        }
        custom_names = list(self.custom_commands)
        self.custom_command_menu.configure(values=custom_names or ["无自定义命令"])
        self.custom_command_var.set(custom_names[0] if custom_names else "无自定义命令")
        self.custom_row.grid() if custom_names else self.custom_row.grid_remove()

        entry = self._selected_entry()
        state = "normal" if entry else "disabled"
        for widget in self.action_widgets:
            widget.configure(state=state)
        self.custom_run_button.configure(state="normal" if entry and custom_names else "disabled")
        self.default_action_menu.configure(state=state)
        self.open_with_switch.configure(state=state)
        if not entry:
            self.selected_card.configure(fg_color="transparent")
            self.selected_name_label.configure(
                text="从左侧列表选择一个文件夹",
                text_color=COLORS["muted"],
                font=ctk.CTkFont("Microsoft YaHei UI", 13),
            )
            self.selected_path_label.configure(text="也可按 Ctrl+K 搜索")
            self.selected_default_label.grid_remove()
            self.copy_path_button.grid_remove()
            self.default_action_var.set("仅打开文件夹")
            self.open_with_command_var.set(False)
            return
        self.selected_card.configure(fg_color=COLORS["surface_alt"])
        self.selected_name_label.configure(
            text=entry.name,
            text_color=COLORS["text"],
            font=ctk.CTkFont("Microsoft YaHei UI", 15, "bold"),
        )
        self.selected_path_label.configure(text=entry.path)
        self.selected_default_label.grid()
        self.copy_path_button.grid()
        self.selected_default_label.configure(text=f"默认动作  {command_label(entry, self.config_data)}")
        self.open_with_command_var.set(entry.open_explorer if entry.command_id else False)
        self.default_action_var.set(
            next(
                (label for label, action in self.default_actions.items() if action == (entry.command_id, entry.continue_session)),
                "仅打开文件夹",
            )
        )

    def _launch_quick(self, command_id: str | None, continue_session: bool, open_explorer: bool) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        try:
            self.status_var.set(
                self.runner.launch_action(entry, self.config_data, command_id, continue_session, open_explorer)
            )
        except LaunchError as exc:
            self.status_var.set("启动失败")
            messagebox.showerror("无法启动", str(exc), parent=self)

    def _launch_custom(self) -> None:
        command_id = self.custom_commands.get(self.custom_command_var.get())
        if command_id:
            self._launch_quick(command_id, False, self.open_with_command_var.get())

    def _launch_entry(self, entry: FolderEntry) -> None:
        try:
            self.status_var.set(self.runner.launch(entry, self.config_data))
        except LaunchError as exc:
            self.status_var.set("启动失败")
            messagebox.showerror("无法启动", str(exc), parent=self)

    def _save_default_action(self) -> None:
        entry = self._selected_entry()
        action = self.default_actions.get(self.default_action_var.get())
        if not entry or action is None:
            return
        entry.command_id, entry.continue_session = action
        entry.open_explorer = True if entry.command_id is None else self.open_with_command_var.get()
        self._save_and_refresh("默认动作已保存", reset_navigation=False)

    def _edit_selected(self) -> None:
        entry = self._selected_entry()
        if entry:
            self.edit_folder(entry)

    def _handle_key(self, event: tk.Event) -> None:
        if self.grab_current() is not None:
            return
        if event.widget and event.widget.winfo_class() in {"Entry", "Text", "TEntry", "TCombobox", "Spinbox"}:
            return
        if event.char and event.char in "123456789":
            index = int(event.char) - 1
            items = self._current_items()[:9] if self.search_query else self._visible_items()
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
        elif event.keysym == "Return" and (entry := self._selected_entry()):
            self._launch_entry(entry)
        elif event.keysym in {"Next", "Right"}:
            self.change_page(1)
        elif event.keysym in {"Prior", "Left"}:
            self.change_page(-1)
        elif event.keysym in {"Up", "Down", "Home", "End"}:
            self._move_selection(event.keysym)

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
        editor = FolderEditor(
            self,
            self.config_data,
            path=path,
            category_id=suggest_category(path, self.config_data.categories),
        )
        self.wait_window(editor)
        if editor.result:
            self.config_data.folders.append(editor.result)
            self.path_var.set("")
            self._save_and_refresh("已添加文件夹")

    def edit_folder(self, entry: FolderEntry, parent: tk.Misc | None = None) -> bool:
        editor = FolderEditor(parent or self, self.config_data, entry=entry)
        self.wait_window(editor)
        if not editor.result:
            return False
        self.config_data.folders[self.config_data.folders.index(entry)] = editor.result
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
