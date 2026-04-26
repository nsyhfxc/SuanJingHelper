from __future__ import annotations

import math
import os
from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import APP_NAME, APP_VERSION, PALETTE, WORKSPACE_DIR, ensure_app_dirs
from .contest_tools import (
    bit_summary,
    comb_mod_prime,
    combination_exact,
    divisor_summary,
    estimate_complexities,
    euler_phi,
    extended_gcd,
    factorize,
    format_factorization,
    human_number,
    is_prime,
    max_n_table,
    mod_inverse,
    permutation_exact,
    permutation_mod_prime,
)
from .data_generators import DATA_TYPES, GenerateOptions, generate_data
from .diff_utils import DiffOptions, compare_texts
from .stress_runner import StressConfig, StressRunner
from .templates import TemplateStore, unique_template_name

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CPToolkit(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ensure_app_dirs()

        self.store = TemplateStore()
        self.templates = self.store.load()
        self.current_tpl_key: str | None = None

        self.frames: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.active_frame_name: str | None = None
        self._frame_order = ("gen", "diff", "stress", "template", "utils")
        self._transition_jobs: list[str] = []
        self._button_feedback_jobs: dict[int, str] = {}
        self.stress_runner: StressRunner | None = None
        self.stress_thread: threading.Thread | None = None
        self.stress_events: Queue[tuple[str, str, str]] = Queue()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1320x860")
        self.minsize(1120, 720)
        self.configure(fg_color=PALETTE["background"])

        self._build_shell()
        self._setup_gen_frame()
        self._setup_diff_frame()
        self._setup_stress_frame()
        self._setup_template_frame()
        self._setup_utils_frame()
        self.select_frame("gen", animate=False)
        self._wire_button_feedback(self)
        self.after(100, self._drain_stress_events)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=PALETTE["sidebar"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(7, weight=1)
        self.sidebar = sidebar

        ctk.CTkLabel(
            sidebar,
            text=APP_NAME,
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=22, pady=(26, 4), sticky="ew")
        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION} 竞赛调试工作台",
            text_color=PALETTE["muted"],
            anchor="w",
        ).grid(row=1, column=0, padx=22, pady=(0, 22), sticky="ew")

        nav_items = [
            ("gen", "数据生成"),
            ("diff", "文本对比"),
            ("stress", "自动对拍"),
            ("template", "算法模板"),
            ("utils", "实用工具"),
        ]
        for index, (name, label) in enumerate(nav_items, start=2):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                height=42,
                corner_radius=8,
                anchor="w",
                command=lambda frame=name: self.select_frame(frame),
            )
            button.grid(row=index, column=0, padx=16, pady=5, sticky="ew")
            self.nav_buttons[name] = button

        ctk.CTkLabel(sidebar, text="外观", text_color=PALETTE["muted"], anchor="w").grid(
            row=8, column=0, padx=22, pady=(16, 6), sticky="ew"
        )
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode,
            height=36,
        )
        self.appearance_mode_menu.grid(row=9, column=0, padx=16, pady=(0, 10), sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="打开工作区",
            height=36,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["border"],
            command=self.open_workspace,
        ).grid(row=10, column=0, padx=16, pady=(0, 22), sticky="ew")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=22, pady=22)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

    def select_frame(self, name: str, animate: bool = True) -> None:
        if name not in self.frames:
            return

        self._cancel_transition()
        self._animate_nav_state(name)
        current_name = self.active_frame_name
        if current_name == name:
            return

        if not animate or current_name is None or current_name not in self.frames:
            self._finish_frame_switch(name)
            return

        self._slide_to_frame(current_name, name)

    def _finish_frame_switch(self, name: str) -> None:
        for frame in self.frames.values():
            frame.place_forget()
            frame.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nsew")
        self.active_frame_name = name

    def _slide_to_frame(self, current_name: str, target_name: str) -> None:
        self.main_container.update_idletasks()
        width = max(self.main_container.winfo_width(), 640)
        current_index = self._frame_order.index(current_name) if current_name in self._frame_order else 0
        target_index = self._frame_order.index(target_name) if target_name in self._frame_order else current_index + 1
        direction = 1 if target_index > current_index else -1
        self.active_frame_name = target_name

        current_frame = self.frames[current_name]
        target_frame = self.frames[target_name]
        current_frame.grid_forget()
        target_frame.grid_forget()
        current_frame.place(x=0, y=0, relwidth=1, relheight=1)
        target_frame.place(x=direction * width, y=0, relwidth=1, relheight=1)

        duration_ms = 260
        interval_ms = 16
        steps = max(1, duration_ms // interval_ms)

        def animate(step: int = 0) -> None:
            progress = self._ease_out_cubic(step / steps)
            current_x = int(-direction * width * progress)
            target_x = int(direction * width * (1 - progress))
            current_frame.place_configure(x=current_x)
            target_frame.place_configure(x=target_x)

            if step >= steps:
                current_frame.place_forget()
                target_frame.place_forget()
                target_frame.grid(row=0, column=0, sticky="nsew")
                self.active_frame_name = target_name
                self._transition_jobs.clear()
                return

            job = self.after(interval_ms, lambda: animate(step + 1))
            self._transition_jobs.append(job)

        animate()

    def _cancel_transition(self) -> None:
        for job in self._transition_jobs:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._transition_jobs.clear()

        for frame in self.frames.values():
            frame.place_forget()
        if self.active_frame_name in self.frames:
            self.frames[self.active_frame_name].grid(row=0, column=0, sticky="nsew")

    def _animate_nav_state(self, selected_name: str) -> None:
        for frame_name, button in self.nav_buttons.items():
            active = frame_name == selected_name
            button.configure(
                fg_color=PALETTE["accent"] if active else "transparent",
                hover_color=PALETTE["accent_hover"] if active else PALETTE["surface_alt"],
                text_color="#ffffff" if active else PALETTE["text"],
            )
            if active:
                self._pulse_button_border(button, "#93c5fd", PALETTE["accent"], width=2, restore_width=0)

    def _wire_button_feedback(self, widget) -> None:
        if isinstance(widget, ctk.CTkButton):
            self._bind_button_feedback(widget)
        for child in widget.winfo_children():
            self._wire_button_feedback(child)

    def _bind_button_feedback(self, button: ctk.CTkButton) -> None:
        if getattr(button, "_feedback_bound", False):
            return
        button._feedback_bound = True
        button.bind("<ButtonPress-1>", lambda _event, item=button: self._press_button(item), add="+")
        button.bind("<ButtonRelease-1>", lambda _event, item=button: self._release_button(item), add="+")
        button.bind("<Leave>", lambda _event, item=button: self._release_button(item), add="+")

    def _press_button(self, button: ctk.CTkButton) -> None:
        try:
            if button.cget("state") == "disabled":
                return
        except tk.TclError:
            return
        self._pulse_button_border(button, "#bfdbfe", "#60a5fa", width=2, restore_width=2)

    def _release_button(self, button: ctk.CTkButton) -> None:
        self._pulse_button_border(button, "#60a5fa", PALETTE["border"], width=2, restore_width=0)

    def _pulse_button_border(
        self,
        button: ctk.CTkButton,
        start_color: str,
        end_color: str,
        width: int,
        restore_width: int,
    ) -> None:
        widget_id = id(button)
        old_job = self._button_feedback_jobs.pop(widget_id, None)
        if old_job:
            try:
                self.after_cancel(old_job)
            except tk.TclError:
                pass

        steps = 7
        interval_ms = 14

        def animate(step: int = 0) -> None:
            try:
                progress = self._ease_out_cubic(step / steps)
                color = self._mix_color(start_color, end_color, progress)
                button.configure(border_width=width if step < steps else restore_width, border_color=color)
            except tk.TclError:
                self._button_feedback_jobs.pop(widget_id, None)
                return

            if step >= steps:
                self._button_feedback_jobs.pop(widget_id, None)
                return

            job = self.after(interval_ms, lambda: animate(step + 1))
            self._button_feedback_jobs[widget_id] = job

        animate()

    @staticmethod
    def _ease_out_cubic(value: float) -> float:
        value = min(1.0, max(0.0, value))
        return 1 - (1 - value) ** 3

    @staticmethod
    def _mix_color(start: str, end: str, progress: float) -> str:
        progress = min(1.0, max(0.0, progress))
        sr, sg, sb = CPToolkit._hex_to_rgb(start)
        er, eg, eb = CPToolkit._hex_to_rgb(end)
        r = round(sr + (er - sr) * progress)
        g = round(sg + (eg - sg) * progress)
        b = round(sb + (eb - sb) * progress)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.strip().lstrip("#")
        if len(value) != 6:
            return 0, 0, 0
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

    def _new_page(self, key: str, title: str, subtitle: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent", corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)
        self.frames[key] = frame

        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=28, weight="bold"), anchor="w").grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkLabel(frame, text=subtitle, text_color=PALETTE["muted"], anchor="w").grid(
            row=1, column=0, sticky="ew", pady=(2, 18)
        )
        return frame

    def _panel(self, parent, row: int, **grid_options) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(
            parent,
            fg_color=PALETTE["surface"],
            border_color=PALETTE["border"],
            border_width=1,
            corner_radius=8,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=grid_options.pop("pady", (0, 14)), **grid_options)
        return panel

    def _entry(self, parent, label: str, default: str, width: int = 92) -> ctk.CTkEntry:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side="left", padx=(0, 12), pady=10)
        ctk.CTkLabel(box, text=label, text_color=PALETTE["muted"], anchor="w").pack(anchor="w")
        entry = ctk.CTkEntry(box, width=width, height=34)
        entry.insert(0, default)
        entry.pack(anchor="w", pady=(4, 0))
        return entry

    def _setup_gen_frame(self) -> None:
        frame = self._new_page("gen", "测试数据生成", "快速构造数组、排列、矩阵、字符串、图与树，支持固定随机种子复现。")
        frame.grid_rowconfigure(3, weight=1)

        control = self._panel(frame, 2)
        control.grid_columnconfigure(0, weight=1)

        first_row = ctk.CTkFrame(control, fg_color="transparent")
        first_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(4, 0))
        self.gen_type = ctk.CTkOptionMenu(first_row, values=DATA_TYPES, width=150, height=34)
        self.gen_type.pack(side="left", padx=(0, 12), pady=10)
        self.gen_cases = self._entry(first_row, "组数 T", "1", 70)
        self.gen_min_size = self._entry(first_row, "规模下限", "1", 86)
        self.gen_max_size = self._entry(first_row, "规模上限", "10", 86)
        self.gen_seed = self._entry(first_row, "随机种子", "", 130)

        self.gen_include_t = ctk.IntVar(value=1)
        ctk.CTkCheckBox(first_row, text="输出 T", variable=self.gen_include_t, width=80).pack(
            side="left", padx=(0, 12), pady=26
        )
        ctk.CTkButton(
            first_row,
            text="生成",
            height=38,
            width=112,
            corner_radius=8,
            fg_color=PALETTE["success"],
            hover_color=PALETTE["success_hover"],
            command=self.generate_data,
        ).pack(side="right", padx=(10, 0), pady=18)

        second_row = ctk.CTkFrame(control, fg_color="transparent")
        second_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 4))
        self.gen_min_value = self._entry(second_row, "数值下限", "1", 86)
        self.gen_max_value = self._entry(second_row, "数值上限", "100", 86)
        self.gen_min_weight = self._entry(second_row, "边权下限", "1", 86)
        self.gen_max_weight = self._entry(second_row, "边权上限", "100", 86)
        self.gen_status = ctk.CTkLabel(second_row, text="就绪", text_color=PALETTE["muted"])
        self.gen_status.pack(side="right", padx=8, pady=26)

        self.gen_output = ctk.CTkTextbox(frame, font=("Consolas", 14), corner_radius=8, border_width=1)
        self.gen_output.grid(row=3, column=0, sticky="nsew", pady=(0, 12))

        action = ctk.CTkFrame(frame, fg_color="transparent")
        action.grid(row=4, column=0, sticky="ew")
        ctk.CTkButton(action, text="复制到剪贴板", width=132, command=self.copy_generated_data).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(action, text="保存为 data.in", width=132, command=self.export_generated_data).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkLabel(action, text=f"默认保存目录：{WORKSPACE_DIR}", text_color=PALETTE["muted"]).pack(
            side="right"
        )

    def _setup_diff_frame(self) -> None:
        frame = self._new_page("diff", "文本差异分析", "左右粘贴或载入输出文件，按行高亮差异并支持常见判题忽略规则。")
        frame.grid_columnconfigure((0, 1), weight=1)
        frame.grid_rowconfigure(3, weight=1)

        control = ctk.CTkFrame(frame, fg_color="transparent")
        control.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ctk.CTkButton(control, text="载入左侧", width=108, command=lambda: self.pick_file_diff(1)).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(control, text="载入右侧", width=108, command=lambda: self.pick_file_diff(2)).pack(
            side="left", padx=(0, 8)
        )

        self.diff_ignore_space = ctk.IntVar(value=1)
        self.diff_ignore_blank = ctk.IntVar(value=0)
        self.diff_ignore_case = ctk.IntVar(value=0)
        for text, var in [
            ("忽略行尾空格", self.diff_ignore_space),
            ("忽略空行", self.diff_ignore_blank),
            ("忽略大小写", self.diff_ignore_case),
        ]:
            ctk.CTkCheckBox(control, text=text, variable=var, width=110).pack(side="left", padx=6)

        ctk.CTkButton(
            control,
            text="执行对比",
            width=120,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.compare_texts,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(control, text="清空", width=82, fg_color=PALETTE["surface_alt"], command=self.clear_diff_boxes).pack(
            side="right"
        )

        area = ctk.CTkFrame(frame, fg_color="transparent")
        area.grid(row=3, column=0, columnspan=2, sticky="nsew")
        area.grid_columnconfigure((1, 3), weight=1)
        area.grid_rowconfigure(0, weight=1)

        self.left_nums = self._line_number_box(area)
        self.left_nums.grid(row=0, column=0, sticky="ns")
        self.diff_box1 = ctk.CTkTextbox(area, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.diff_box1.grid(row=0, column=1, sticky="nsew", padx=(0, 10))

        self.right_nums = self._line_number_box(area)
        self.right_nums.grid(row=0, column=2, sticky="ns")
        self.diff_box2 = ctk.CTkTextbox(area, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.diff_box2.grid(row=0, column=3, sticky="nsew")

        self.diff_status = ctk.CTkLabel(frame, text="就绪：载入或粘贴文本后执行对比", text_color=PALETTE["muted"])
        self.diff_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.diff_box1._textbox.tag_config("diff_line", background="#5b1f2a")
        self.diff_box2._textbox.tag_config("diff_line", background="#5b1f2a")
        self.diff_box1.bind("<KeyRelease>", lambda _event: self.update_line_numbers())
        self.diff_box2.bind("<KeyRelease>", lambda _event: self.update_line_numbers())
        self.diff_box1._textbox.bind("<MouseWheel>", self.sync_scroll)
        self.diff_box2._textbox.bind("<MouseWheel>", self.sync_scroll)
        self.update_line_numbers()

    def _line_number_box(self, parent) -> tk.Text:
        return tk.Text(
            parent,
            width=5,
            padx=6,
            pady=7,
            font=("Consolas", 13),
            bg="#111827",
            fg="#8ba0ba",
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )

    def _setup_stress_frame(self) -> None:
        frame = self._new_page("stress", "自动对拍", "运行数据生成器、标准程序与待测程序，自动保存第一组失败现场。")
        frame.grid_rowconfigure(4, weight=1)

        self.stress_files = {"sol": tk.StringVar(), "std": tk.StringVar(), "gen": tk.StringVar()}
        file_panel = self._panel(frame, 2)
        file_panel.grid_columnconfigure(1, weight=1)
        rows = [
            ("sol", "待测程序"),
            ("std", "标准程序"),
            ("gen", "数据生成器"),
        ]
        for row, (key, label) in enumerate(rows):
            ctk.CTkLabel(file_panel, text=label, width=90, anchor="w").grid(row=row, column=0, padx=(14, 8), pady=8)
            ctk.CTkEntry(file_panel, textvariable=self.stress_files[key], height=34).grid(
                row=row, column=1, sticky="ew", padx=8, pady=8
            )
            ctk.CTkButton(file_panel, text="浏览", width=74, command=lambda name=key: self.pick_stress_file(name)).grid(
                row=row, column=2, padx=(8, 14), pady=8
            )

        option_panel = self._panel(frame, 3)
        option_panel.grid_columnconfigure(6, weight=1)
        self.stress_max_cases = self._entry(option_panel, "最大组数", "1000", 92)
        self.stress_timeout = self._entry(option_panel, "单程序超时(s)", "3", 112)
        self.stress_normalize = ctk.IntVar(value=1)
        ctk.CTkCheckBox(option_panel, text="忽略行尾空白和末尾空行", variable=self.stress_normalize, width=180).pack(
            side="left", padx=(4, 12), pady=26
        )
        self.btn_start_stress = ctk.CTkButton(
            option_panel,
            text="开始对拍",
            width=116,
            height=38,
            fg_color=PALETTE["success"],
            hover_color=PALETTE["success_hover"],
            command=self.toggle_stress,
        )
        self.btn_start_stress.pack(side="right", padx=(8, 14), pady=18)
        ctk.CTkButton(
            option_panel,
            text="清空日志",
            width=96,
            fg_color=PALETTE["surface_alt"],
            command=lambda: self.stress_log.delete("1.0", "end"),
        ).pack(side="right", pady=18)

        self.stress_log = ctk.CTkTextbox(frame, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.stress_log.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        self.stress_log._textbox.tag_config("info", foreground="#d1d5db")
        self.stress_log._textbox.tag_config("success", foreground="#34d399")
        self.stress_log._textbox.tag_config("error", foreground="#fb7185")

    def _setup_template_frame(self) -> None:
        frame = self._new_page("template", "算法模板库", "集中管理常用代码片段，支持搜索、重命名、复制和持久化保存。")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.tpl_search = ctk.CTkEntry(toolbar, placeholder_text="搜索模板...", width=240, height=34)
        self.tpl_search.pack(side="left")
        self.tpl_search.bind("<KeyRelease>", lambda _event: self.refresh_template_list())
        ctk.CTkButton(toolbar, text="新建", width=82, command=self.add_new_template).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            toolbar,
            text="保存",
            width=82,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.save_current_template,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(toolbar, text="复制", width=82, command=self.copy_current_template).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            toolbar,
            text="删除",
            width=82,
            fg_color=PALETTE["danger"],
            hover_color=PALETTE["danger_hover"],
            command=self.delete_template,
        ).pack(side="right", padx=(8, 0))

        self.tpl_list_frame = ctk.CTkScrollableFrame(frame, width=260, corner_radius=8)
        self.tpl_list_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 12))

        editor = ctk.CTkFrame(frame, fg_color=PALETTE["surface"], corner_radius=8, border_width=1, border_color=PALETTE["border"])
        editor.grid(row=3, column=1, sticky="nsew")
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(1, weight=1)
        self.tpl_name_entry = ctk.CTkEntry(editor, placeholder_text="模板名称", height=38)
        self.tpl_name_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.tpl_view = ctk.CTkTextbox(editor, font=("Consolas", 14), corner_radius=8)
        self.tpl_view.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.refresh_template_list()
        if self.templates:
            self.select_template(sorted(self.templates)[0])

    def _setup_utils_frame(self) -> None:
        frame = self._new_page("utils", "实用工具", "围绕比赛高频场景整理：复杂度、数论、组合计数和位运算。")
        frame.grid_rowconfigure(2, weight=1)

        self.utils_tabs = ctk.CTkTabview(frame, corner_radius=8, border_width=1)
        self.utils_tabs.grid(row=2, column=0, sticky="nsew")
        self.tab_complexity = self.utils_tabs.add("复杂度")
        self.tab_number = self.utils_tabs.add("数论")
        self.tab_combinatorics = self.utils_tabs.add("组合")
        self.tab_bits = self.utils_tabs.add("位运算")

        self._setup_complexity_tool(self.tab_complexity)
        self._setup_number_tool(self.tab_number)
        self._setup_combinatorics_tool(self.tab_combinatorics)
        self._setup_bit_tool(self.tab_bits)
        self.calc_complexity()

    def _setup_complexity_tool(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.util_n = self._entry(form, "N", "100000", 120)
        self.util_cases = self._entry(form, "测试组数 T", "1", 92)
        self.util_time = self._entry(form, "时限(s)", "1", 86)
        self.util_ops = self._entry(form, "每秒操作数", "100000000", 132)
        ctk.CTkButton(
            form,
            text="评估",
            width=96,
            height=38,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.calc_complexity,
        ).pack(side="right", padx=(8, 0), pady=24)

        self.util_res = ctk.CTkTextbox(tab, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.util_res.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _setup_number_tool(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.num_a = self._entry(form, "A / n", "1000000007", 132)
        self.num_b = self._entry(form, "B / exp", "123456", 132)
        self.num_mod = self._entry(form, "mod", "998244353", 132)
        ctk.CTkButton(
            form,
            text="计算",
            width=96,
            height=38,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.calc_number_theory,
        ).pack(side="right", padx=(8, 0), pady=24)

        self.num_output = ctk.CTkTextbox(tab, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.num_output.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _setup_combinatorics_tool(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.comb_n = self._entry(form, "n", "10", 112)
        self.comb_r = self._entry(form, "r", "3", 112)
        self.comb_mod = self._entry(form, "mod(可空)", "1000000007", 132)
        ctk.CTkButton(
            form,
            text="计算",
            width=96,
            height=38,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.calc_combinatorics,
        ).pack(side="right", padx=(8, 0), pady=24)

        self.comb_output = ctk.CTkTextbox(tab, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.comb_output.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _setup_bit_tool(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.bit_x = self._entry(form, "x", "1024", 160)
        ctk.CTkButton(
            form,
            text="分析",
            width=96,
            height=38,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self.calc_bits,
        ).pack(side="right", padx=(8, 0), pady=24)

        self.bit_output = ctk.CTkTextbox(tab, font=("Consolas", 13), corner_radius=8, border_width=1)
        self.bit_output.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def generate_data(self) -> None:
        try:
            options = GenerateOptions(
                data_type=self.gen_type.get(),
                cases=int(self.gen_cases.get()),
                min_size=int(self.gen_min_size.get()),
                max_size=int(self.gen_max_size.get()),
                min_value=int(self.gen_min_value.get()),
                max_value=int(self.gen_max_value.get()),
                min_weight=int(self.gen_min_weight.get()),
                max_weight=int(self.gen_max_weight.get()),
                include_case_count=bool(self.gen_include_t.get()),
                seed=self.gen_seed.get().strip(),
            )
            content = generate_data(options)
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.gen_output.delete("1.0", "end")
        self.gen_output.insert("1.0", content)
        line_count = content.count("\n") + (1 if content else 0)
        self.gen_status.configure(text=f"已生成 {line_count} 行", text_color=PALETTE["success"])

    def copy_generated_data(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.gen_output.get("1.0", "end-1c"))
        self.gen_status.configure(text="已复制到剪贴板", text_color=PALETTE["success"])

    def export_generated_data(self) -> None:
        target = WORKSPACE_DIR / "data.in"
        target.write_text(self.gen_output.get("1.0", "end-1c"), encoding="utf-8")
        self.gen_status.configure(text=f"已保存：{target.name}", text_color=PALETTE["success"])

    def sync_scroll(self, event) -> str:
        step = int(-1 * (event.delta / 120))
        self.diff_box1._textbox.yview_scroll(step, "units")
        self.diff_box2._textbox.yview_scroll(step, "units")
        self.left_nums.yview_moveto(self.diff_box1._textbox.yview()[0])
        self.right_nums.yview_moveto(self.diff_box2._textbox.yview()[0])
        return "break"

    def update_line_numbers(self) -> None:
        self._update_line_number_box(self.left_nums, self.diff_box1.get("1.0", "end-1c"))
        self._update_line_number_box(self.right_nums, self.diff_box2.get("1.0", "end-1c"))

    def _update_line_number_box(self, target: tk.Text, content: str) -> None:
        count = content.count("\n") + (1 if content else 1)
        target.configure(state="normal")
        target.delete("1.0", "end")
        target.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
        target.configure(state="disabled")

    def clear_diff_boxes(self) -> None:
        self.diff_box1.delete("1.0", "end")
        self.diff_box2.delete("1.0", "end")
        self.diff_box1._textbox.tag_remove("diff_line", "1.0", "end")
        self.diff_box2._textbox.tag_remove("diff_line", "1.0", "end")
        self.update_line_numbers()
        self.diff_status.configure(text="已清空", text_color=PALETTE["muted"])

    def compare_texts(self) -> None:
        self.diff_box1._textbox.tag_remove("diff_line", "1.0", "end")
        self.diff_box2._textbox.tag_remove("diff_line", "1.0", "end")

        options = DiffOptions(
            ignore_trailing_space=bool(self.diff_ignore_space.get()),
            ignore_blank_lines=bool(self.diff_ignore_blank.get()),
            ignore_case=bool(self.diff_ignore_case.get()),
        )
        result = compare_texts(
            self.diff_box1.get("1.0", "end-1c"),
            self.diff_box2.get("1.0", "end-1c"),
            options,
        )

        for line in result.left_lines:
            self.diff_box1._textbox.tag_add("diff_line", f"{line}.0", f"{line}.end+1c")
        for line in result.right_lines:
            self.diff_box2._textbox.tag_add("diff_line", f"{line}.0", f"{line}.end+1c")

        if result.is_equal:
            self.diff_status.configure(text="内容一致", text_color=PALETTE["success"])
            return

        line_preview = ", ".join(map(str, (result.left_lines or result.right_lines)[:10]))
        if len(result.left_lines or result.right_lines) > 10:
            line_preview += " ..."
        self.diff_status.configure(
            text=f"发现 {result.diff_count} 处差异，首批差异行：{line_preview}",
            text_color="#fb7185",
        )
        target_line = result.first_left_line or result.first_right_line
        if target_line:
            self.diff_box1.see(f"{target_line}.0")
            self.diff_box2.see(f"{target_line}.0")

    def pick_file_diff(self, target: int) -> None:
        path = filedialog.askopenfilename(title="选择文本文件")
        if not path:
            return
        content = Path(path).read_text(encoding="utf-8", errors="ignore")
        box = self.diff_box1 if target == 1 else self.diff_box2
        box.delete("1.0", "end")
        box.insert("1.0", content)
        self.update_line_numbers()
        self.diff_status.configure(text=f"已载入：{Path(path).name}", text_color=PALETTE["muted"])

    def refresh_template_list(self) -> None:
        for child in self.tpl_list_frame.winfo_children():
            child.destroy()

        keyword = self.tpl_search.get().strip().lower() if hasattr(self, "tpl_search") else ""
        names = [name for name in sorted(self.templates) if keyword in name.lower()]
        if not names:
            ctk.CTkLabel(self.tpl_list_frame, text="没有匹配的模板", text_color=PALETTE["muted"]).pack(pady=16)
            return

        for name in names:
            active = name == self.current_tpl_key
            button = ctk.CTkButton(
                self.tpl_list_frame,
                text=name,
                height=36,
                corner_radius=8,
                anchor="w",
                fg_color=PALETTE["accent"] if active else "transparent",
                hover_color=PALETTE["surface_alt"],
                command=lambda item=name: self.select_template(item),
            )
            button.pack(fill="x", pady=3)
            self._bind_button_feedback(button)

    def select_template(self, name: str) -> None:
        self.current_tpl_key = name
        self.tpl_name_entry.delete(0, "end")
        self.tpl_name_entry.insert(0, name)
        self.tpl_view.delete("1.0", "end")
        self.tpl_view.insert("1.0", self.templates[name])
        self.refresh_template_list()

    def save_current_template(self) -> None:
        new_name = self.tpl_name_entry.get().strip()
        if not new_name:
            messagebox.showwarning("提示", "模板名称不能为空")
            return

        old_name = self.current_tpl_key
        if old_name and old_name != new_name and old_name in self.templates:
            del self.templates[old_name]
        self.templates[new_name] = self.tpl_view.get("1.0", "end-1c")
        self.current_tpl_key = new_name
        self.store.save(self.templates)
        self.refresh_template_list()
        messagebox.showinfo("成功", "模板已保存")

    def add_new_template(self) -> None:
        name = unique_template_name(self.templates)
        self.templates[name] = "# 在这里写下你的模板\n"
        self.current_tpl_key = name
        self.refresh_template_list()
        self.select_template(name)

    def delete_template(self) -> None:
        if not self.current_tpl_key:
            return
        if not messagebox.askyesno("确认删除", f"删除模板“{self.current_tpl_key}”？"):
            return

        del self.templates[self.current_tpl_key]
        self.current_tpl_key = None
        self.store.save(self.templates)
        self.tpl_name_entry.delete(0, "end")
        self.tpl_view.delete("1.0", "end")
        self.refresh_template_list()
        if self.templates:
            self.select_template(sorted(self.templates)[0])

    def copy_current_template(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.tpl_view.get("1.0", "end-1c"))

    def pick_stress_file(self, key: str) -> None:
        path = filedialog.askopenfilename(
            title="选择程序",
            filetypes=[("程序文件", "*.py *.cpp *.exe"), ("全部文件", "*.*")],
        )
        if path:
            self.stress_files[key].set(path)

    def toggle_stress(self) -> None:
        if self.stress_runner:
            self.stress_runner.stop()
            self._append_stress_log("info", ">>> 正在请求停止...")
            self.btn_start_stress.configure(state="disabled", text="停止中")
            return

        try:
            max_cases = int(self.stress_max_cases.get())
            timeout = float(self.stress_timeout.get())
            if timeout <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "最大组数必须是整数，超时必须是正数")
            return

        raw_paths = {key: var.get().strip() for key, var in self.stress_files.items()}
        missing = [
            label
            for key, label in [("sol", "待测程序"), ("std", "标准程序"), ("gen", "数据生成器")]
            if not raw_paths[key]
        ]
        if missing:
            messagebox.showwarning("提示", "请先选择：" + "、".join(missing))
            return
        paths = {key: Path(value) for key, value in raw_paths.items()}

        config = StressConfig(
            solution_path=paths["sol"],
            standard_path=paths["std"],
            generator_path=paths["gen"],
            output_dir=WORKSPACE_DIR,
            max_cases=max_cases,
            timeout_seconds=timeout,
            normalize_output=bool(self.stress_normalize.get()),
        )
        self.stress_runner = StressRunner(config, self._queue_stress_log)
        self.btn_start_stress.configure(text="停止对拍", fg_color=PALETTE["danger"], hover_color=PALETTE["danger_hover"])
        self.stress_thread = threading.Thread(target=self._run_stress_thread, daemon=True)
        self.stress_thread.start()

    def _run_stress_thread(self) -> None:
        try:
            if self.stress_runner:
                self.stress_runner.run()
        finally:
            self.stress_events.put(("finished", "", ""))

    def _queue_stress_log(self, level: str, message: str) -> None:
        self.stress_events.put(("log", level, message))

    def _drain_stress_events(self) -> None:
        try:
            while True:
                event, level, message = self.stress_events.get_nowait()
                if event == "log":
                    self._append_stress_log(level, message)
                elif event == "finished":
                    self._finish_stress_ui()
        except Empty:
            pass
        self.after(100, self._drain_stress_events)

    def _append_stress_log(self, level: str, message: str) -> None:
        tag = level if level in {"info", "success", "error"} else "info"
        self.stress_log.insert("end", message + "\n", tag)
        self.stress_log.see("end")

    def _finish_stress_ui(self) -> None:
        self.stress_runner = None
        self.btn_start_stress.configure(
            state="normal",
            text="开始对拍",
            fg_color=PALETTE["success"],
            hover_color=PALETTE["success_hover"],
        )

    def calc_complexity(self) -> None:
        try:
            n = float(self.util_n.get().replace(",", ""))
            cases = int(self.util_cases.get().replace(",", ""))
            time_limit = float(self.util_time.get())
            ops_per_second = float(self.util_ops.get().replace(",", ""))
            if n <= 0:
                raise ValueError
            if cases <= 0 or time_limit <= 0 or ops_per_second <= 0:
                raise ValueError
        except ValueError:
            self._set_textbox(self.util_res, "请输入合法参数：N、T、时限、每秒操作数都必须为正数。\n")
            return

        rows, budget = estimate_complexities(n, cases, time_limit, ops_per_second)
        lines = [
            f"操作预算：{human_number(budget)} ops  ({time_limit:g}s × {human_number(ops_per_second)} ops/s)",
            f"总规模：N={human_number(n)}，T={cases}",
            "",
            "当前 N 的复杂度粗估：",
            f"{'复杂度':<14}{'估算操作数':>18}    结论",
            "-" * 42,
        ]
        for row in rows:
            lines.append(f"{row.name:<14}{human_number(row.operations):>18}    {row.verdict}")

        lines.extend(["", "按当前预算反推每组数据可承受的最大 N：", "-" * 42])
        for name, value in max_n_table(cases, time_limit, ops_per_second):
            lines.append(f"{name:<14}{value:>18}")

        lines.extend(
            [
                "",
                "经验提示：Python 通常按 2e7~8e7 ops/s 估，C++ 通常按 1e8~3e8 ops/s 估。",
                "包含大常数、递归、哈希、IO 或多重测试时，建议给预算再打折。",
            ]
        )
        self._set_textbox(self.util_res, "\n".join(lines))

    def calc_number_theory(self) -> None:
        try:
            a = int(self.num_a.get().replace(",", ""))
            b = int(self.num_b.get().replace(",", ""))
            mod_text = self.num_mod.get().strip().replace(",", "")
            mod = int(mod_text) if mod_text else 0
        except ValueError:
            self._set_textbox(self.num_output, "请输入整数 A、B；mod 可为空或填写大于 1 的整数。\n")
            return

        g = math.gcd(a, b)
        lcm = abs(a // g * b) if g else 0
        eg, x, y = extended_gcd(a, b)
        factors = factorize(a)

        lines = [
            "基础数论：",
            f"gcd(A, B) = {g}",
            f"lcm(A, B) = {lcm}",
            f"exgcd: {a} * ({x}) + {b} * ({y}) = {eg}",
            "",
            "A 的性质：",
            f"is_prime(A) = {'是' if is_prime(a) else '否'}",
            f"factor(A) = {format_factorization(factors)}",
        ]

        if a > 0:
            try:
                div_count, div_sum = divisor_summary(a)
                lines.append(f"phi(A) = {euler_phi(a)}")
                lines.append(f"约数个数 d(A) = {div_count}")
                lines.append(f"约数和 sigma(A) = {div_sum}")
            except ValueError as exc:
                lines.append(str(exc))
        else:
            lines.append("phi / 约数统计需要 A 为正整数")

        if mod > 1:
            inv = mod_inverse(a, mod)
            lines.extend(
                [
                    "",
                    "取模工具：",
                    f"A mod mod = {a % mod}",
                    f"B mod mod = {b % mod}",
                    f"A^B mod mod = {pow(a, b, mod) if b >= 0 else '指数为负时不计算'}",
                    f"inv(A) mod mod = {inv if inv is not None else '不存在'}",
                    f"mod 是否为素数 = {'是' if is_prime(mod) else '否'}",
                ]
            )
        else:
            lines.extend(["", "填写 mod > 1 后可计算快速幂和模逆。"])

        self._set_textbox(self.num_output, "\n".join(lines))

    def calc_combinatorics(self) -> None:
        try:
            n = int(self.comb_n.get().replace(",", ""))
            r = int(self.comb_r.get().replace(",", ""))
            mod_text = self.comb_mod.get().strip().replace(",", "")
            mod = int(mod_text) if mod_text else 0
        except ValueError:
            self._set_textbox(self.comb_output, "请输入整数 n、r；mod 可为空。\n")
            return

        exact_c = combination_exact(n, r)
        exact_p = permutation_exact(n, r)
        lines = [
            f"n={n}, r={r}",
            "",
            "精确值：",
            f"C(n, r) = {exact_c if exact_c is not None else 'n 较大，跳过精确大整数'}",
            f"P(n, r) = {exact_p if exact_p is not None else 'n 较大，跳过精确大整数'}",
        ]

        if mod > 1:
            c_mod = comb_mod_prime(n, r, mod)
            p_mod = permutation_mod_prime(n, r, mod)
            prime_text = "是" if is_prime(mod) else "否"
            lines.extend(
                [
                    "",
                    "模意义结果：",
                    f"mod 是否为素数 = {prime_text}",
                    f"C(n, r) mod mod = {c_mod if c_mod is not None else '需要素数 mod，且单段计算量不能过大'}",
                    f"P(n, r) mod mod = {p_mod if p_mod is not None else '需要素数 mod，且 r 不能过大'}",
                ]
            )
            if exact_c is not None:
                lines.append(f"精确 C % mod = {exact_c % mod}")
        else:
            lines.extend(["", "填写素数 mod 后可计算 C/P 取模。"])

        lines.extend(
            [
                "",
                "常用提醒：",
                "C(n,r)=C(n,n-r)，组合数 DP 适合小 n，阶乘逆元适合大量查询。",
                "当 n 很大且 mod 为小素数时，可用 Lucas 定理拆位计算。",
            ]
        )
        self._set_textbox(self.comb_output, "\n".join(lines))

    def calc_bits(self) -> None:
        try:
            x = int(self.bit_x.get().replace(",", ""), 0)
        except ValueError:
            self._set_textbox(self.bit_output, "请输入整数 x；支持 10、0b1010、0xff 这类格式。\n")
            return

        rows = bit_summary(x)
        lines = ["位运算摘要：", "-" * 42]
        lines.extend(f"{name:<14}{value}" for name, value in rows)
        lines.extend(
            [
                "",
                "常用写法：",
                "lowbit(x) = x & -x",
                "去掉最低位 1：x &= x - 1",
                "枚举子集：for (s = mask; s; s = (s - 1) & mask)",
                "判断 2 的幂：x > 0 && (x & (x - 1)) == 0",
            ]
        )
        self._set_textbox(self.bit_output, "\n".join(lines))

    def _set_textbox(self, box: ctk.CTkTextbox, content: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", content)
        box.configure(state="disabled")

    def open_workspace(self) -> None:
        WORKSPACE_DIR.mkdir(exist_ok=True)
        os.startfile(str(WORKSPACE_DIR))
