import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import customtkinter as ctk
import random
import string
import pyperclip
import os
import subprocess
import threading
import time
import json

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CPToolkit(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("算法竞赛调试助手V1.0")
        self.geometry("1300x900")

        # 状态变量
        self.is_stress_testing = False
        self.stop_signal = False
        self.template_file = "my_templates.json"

        # 布局初始化
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 侧边栏
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="欢迎使用算法竞赛调试助手V1.0",
                                       font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 导航按钮
        self.nav_buttons = []
        self.add_nav_btn("数据生成", "gen", 1)
        self.add_nav_btn("文本对比", "diff", 2)
        self.add_nav_btn("自动对拍", "stress", 3)
        self.add_nav_btn("算法模板", "template", 4)
        self.add_nav_btn("工具箱", "utils", 5)

        # 模式切换
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light"],
                                                      command=self.change_appearance_mode_event)
        self.appearance_mode_menu.grid(row=9, column=0, padx=20, pady=(10, 20))

        # 主内容容器
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # 数据模型初始化
        self.load_templates()

        # 各个功能面板
        self.frames = {}
        self.setup_gen_frame()
        self.setup_diff_frame()
        self.setup_stress_frame()
        self.setup_template_frame()
        self.setup_utils_frame()

        self.select_frame("gen")

    def add_nav_btn(self, text, frame_name, row):
        btn = ctk.CTkButton(self.sidebar_frame, text=text,
                            command=lambda: self.select_frame(frame_name))
        btn.grid(row=row, column=0, padx=20, pady=10)
        self.nav_buttons.append(btn)

    def change_appearance_mode_event(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)

    def select_frame(self, name):
        for f in self.frames.values():
            f.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nsew")

    # ========================== 数据生成模块 ==========================
    def setup_gen_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["gen"] = frame
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame, text="测试数据生成器", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0,
                                                                                                  sticky="w",
                                                                                                  pady=(0, 20))

        config_box = ctk.CTkFrame(frame)
        config_box.grid(row=1, column=0, sticky="ew", padx=0, pady=10)

        p1 = ctk.CTkFrame(config_box, fg_color="transparent")
        p1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(p1, text="组数 (T):").pack(side="left", padx=5)
        self.gen_t = ctk.CTkEntry(p1, width=60);
        self.gen_t.insert(0, "1");
        self.gen_t.pack(side="left", padx=5)

        ctk.CTkLabel(p1, text="范围 (N/Val):").pack(side="left", padx=15)
        self.gen_min = ctk.CTkEntry(p1, width=70);
        self.gen_min.insert(0, "1");
        self.gen_min.pack(side="left", padx=5)
        ctk.CTkLabel(p1, text="至").pack(side="left")
        self.gen_max = ctk.CTkEntry(p1, width=70);
        self.gen_max.insert(0, "100");
        self.gen_max.pack(side="left", padx=5)

        ctk.CTkLabel(p1, text="边权范围:").pack(side="left", padx=15)
        self.gen_w_min = ctk.CTkEntry(p1, width=60);
        self.gen_w_min.insert(0, "1");
        self.gen_w_min.pack(side="left", padx=5)
        ctk.CTkLabel(p1, text="至").pack(side="left")
        self.gen_w_max = ctk.CTkEntry(p1, width=60);
        self.gen_w_max.insert(0, "100");
        self.gen_w_max.pack(side="left", padx=5)

        p2 = ctk.CTkFrame(config_box, fg_color="transparent")
        p2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(p2, text="数据类型:").pack(side="left", padx=5)
        self.gen_type = ctk.CTkOptionMenu(p2,
                                          values=["整数数列", "随机排列", "矩阵/网格", "随机字符串", "简单图", "带权图",
                                                  "普通树", "二叉树"])
        self.gen_type.pack(side="left", padx=5)

        self.btn_do_gen = ctk.CTkButton(p2, text="生成数据", fg_color="#2ecc71", hover_color="#27ae60",
                                        command=self.generate_data)
        self.btn_do_gen.pack(side="right", padx=5)

        self.gen_output = ctk.CTkTextbox(frame, font=("Consolas", 14))
        self.gen_output.grid(row=2, column=0, sticky="nsew", pady=10)

        action_box = ctk.CTkFrame(frame, fg_color="transparent")
        action_box.grid(row=3, column=0, sticky="ew")
        ctk.CTkButton(action_box, text="复制到剪贴板", width=150, command=self.copy_to_clipboard).pack(side="left",
                                                                                                       padx=5)
        ctk.CTkButton(action_box, text="存为 data.in", width=120, command=self.export_to_txt).pack(side="left", padx=5)

    # ========================== 文本对比模块 (功能增强版) ==========================
    def setup_diff_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["diff"] = frame
        frame.grid_columnconfigure((0, 1), weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame, text="文本差异分析", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0,
                                                                                                columnspan=2,
                                                                                                sticky="w",
                                                                                                pady=(0, 20))

        # 控制栏
        ctrl_bar = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ctk.CTkButton(ctrl_bar, text="📂 载入 ANS", width=120, command=lambda: self.pick_file_diff(1)).pack(side="left",
                                                                                                           padx=5)
        ctk.CTkButton(ctrl_bar, text="📂 载入 OUT", width=120, command=lambda: self.pick_file_diff(2)).pack(side="left",
                                                                                                           padx=5)
        ctk.CTkButton(ctrl_bar, text="⚖️ 执行对比", fg_color="#3498db", width=150, command=self.compare_texts).pack(
            side="right", padx=5)
        ctk.CTkButton(ctrl_bar, text="🧹 清空", width=80, fg_color="#7f8c8d", command=self.clear_diff_boxes).pack(
            side="right", padx=5)

        # 左右对比区域（含行号）
        self.diff_main_area = ctk.CTkFrame(frame, fg_color="transparent")
        self.diff_main_area.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)
        self.diff_main_area.grid_columnconfigure((1, 3), weight=1)
        self.diff_main_area.grid_rowconfigure(0, weight=1)

        # 左侧面板 (行号 + 文本)
        self.left_nums = tk.Text(self.diff_main_area, width=4, padx=5, pady=5, font=("Consolas", 12),
                                 bg="#2b2b2b", fg="#858585", state="disabled", borderwidth=0)
        self.left_nums.grid(row=0, column=0, sticky="ns")
        self.diff_box1 = ctk.CTkTextbox(self.diff_main_area, font=("Consolas", 12), border_width=1)
        self.diff_box1.grid(row=0, column=1, sticky="nsew", padx=(0, 5))

        # 右侧面板 (行号 + 文本)
        self.right_nums = tk.Text(self.diff_main_area, width=4, padx=5, pady=5, font=("Consolas", 12),
                                  bg="#2b2b2b", fg="#858585", state="disabled", borderwidth=0)
        self.right_nums.grid(row=0, column=2, sticky="ns")
        self.diff_box2 = ctk.CTkTextbox(self.diff_main_area, font=("Consolas", 12), border_width=1)
        self.diff_box2.grid(row=0, column=3, sticky="nsew")

        # 状态栏
        self.diff_status = ctk.CTkLabel(frame, text="就绪：载入或粘贴文本进行比对", text_color="#7f8c8d")
        self.diff_status.grid(row=3, column=0, columnspan=2, pady=5)

        # 配置标红Tag
        self.diff_box1._textbox.tag_config("diff_line", background="#632121")
        self.diff_box2._textbox.tag_config("diff_line", background="#632121")

        # 绑定同步行号更新
        self.diff_box1.bind("<KeyRelease>", lambda e: self.update_line_numbers())
        self.diff_box2.bind("<KeyRelease>", lambda e: self.update_line_numbers())
        self.diff_box1._textbox.bind("<MouseWheel>", self.sync_scroll)
        self.diff_box2._textbox.bind("<MouseWheel>", self.sync_scroll)

    def sync_scroll(self, event):
        # 简单的滚动同步逻辑
        self.diff_box1._textbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.diff_box2._textbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.left_nums.yview_moveto(self.diff_box1._textbox.yview()[0])
        self.right_nums.yview_moveto(self.diff_box2._textbox.yview()[0])
        return "break"

    def update_line_numbers(self):
        # 更新左侧行号
        l_text = self.diff_box1.get("1.0", "end-1c")
        l_lines = l_text.count("\n") + (1 if l_text else 0)
        self.left_nums.configure(state="normal")
        self.left_nums.delete("1.0", "end")
        self.left_nums.insert("1.0", "\n".join(str(i + 1) for i in range(l_lines)))
        self.left_nums.configure(state="disabled")

        # 更新右侧行号
        r_text = self.diff_box2.get("1.0", "end-1c")
        r_lines = r_text.count("\n") + (1 if r_text else 0)
        self.right_nums.configure(state="normal")
        self.right_nums.delete("1.0", "end")
        self.right_nums.insert("1.0", "\n".join(str(i + 1) for i in range(r_lines)))
        self.right_nums.configure(state="disabled")

    def clear_diff_boxes(self):
        self.diff_box1.delete("1.0", "end")
        self.diff_box2.delete("1.0", "end")
        self.update_line_numbers()
        self.diff_status.configure(text="已清空", text_color="#7f8c8d")

    def compare_texts(self):
        # 移除之前的标记
        self.diff_box1._textbox.tag_remove("diff_line", "1.0", "end")
        self.diff_box2._textbox.tag_remove("diff_line", "1.0", "end")

        t1_lines = self.diff_box1.get("1.0", "end-1c").splitlines()
        t2_lines = self.diff_box2.get("1.0", "end-1c").splitlines()

        max_lines = max(len(t1_lines), len(t2_lines))
        diff_count = 0
        diff_line_indices = []

        for i in range(max_lines):
            l1 = t1_lines[i] if i < len(t1_lines) else None
            l2 = t2_lines[i] if i < len(t2_lines) else None

            if l1 != l2:
                diff_count += 1
                diff_line_indices.append(i + 1)
                # 标红整行
                if i < len(t1_lines):
                    self.diff_box1._textbox.tag_add("diff_line", f"{i + 1}.0", f"{i + 1}.end+1c")
                if i < len(t2_lines):
                    self.diff_box2._textbox.tag_add("diff_line", f"{i + 1}.0", f"{i + 1}.end+1c")

        if diff_count == 0:
            messagebox.showinfo("对比结果", "🎉 完全一致！未发现任何差异。")
            self.diff_status.configure(text="状态：内容完全匹配", text_color="#2ecc71")
        else:
            line_str = ", ".join(map(str, diff_line_indices[:10]))
            if len(diff_line_indices) > 10: line_str += " ..."

            summary = f"检测到 {diff_count} 处行差异。\n\n差异所在行号：\n{line_str}"
            messagebox.showwarning("对比结果", summary)
            self.diff_status.configure(text=f"状态：发现 {diff_count} 处差异", text_color="#e74c3c")

    # ========================== 算法模板模块 ==========================
    def setup_template_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["template"] = frame
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(top_bar, text="自定义模板库", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="+ 新建模板", width=100, command=self.add_new_template).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="💾 保存修改", width=100, fg_color="#3498db",
                      command=self.save_current_template).pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="🗑️ 删除", width=80, fg_color="#e74c3c", command=self.delete_template).pack(
            side="right", padx=5)

        self.tpl_list_frame = ctk.CTkScrollableFrame(frame, width=220)
        self.tpl_list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.tpl_edit_box = ctk.CTkFrame(frame)
        self.tpl_edit_box.grid(row=1, column=1, sticky="nsew")

        self.tpl_name_entry = ctk.CTkEntry(self.tpl_edit_box, placeholder_text="模板名称...",
                                           font=ctk.CTkFont(size=14, weight="bold"))
        self.tpl_name_entry.pack(fill="x", padx=10, pady=10)

        self.tpl_view = ctk.CTkTextbox(self.tpl_edit_box, font=("Consolas", 14))
        self.tpl_view.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.current_tpl_key = None
        self.refresh_template_list()

    # ========================== 自动对拍与工具 ==========================
    def setup_stress_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["stress"] = frame
        frame.grid_columnconfigure(0, weight=1);
        frame.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(frame, text="自动对拍引擎", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0,
                                                                                                sticky="w",
                                                                                                pady=(0, 10))
        self.stress_files = {"sol": tk.StringVar(), "std": tk.StringVar(), "gen": tk.StringVar()}
        config_box = ctk.CTkFrame(frame);
        config_box.grid(row=2, column=0, sticky="ew", pady=10)
        for i, (k, label) in enumerate(
                [("sol", "待测程序 (C++/Py)"), ("std", "标准程序 (C++/Py)"), ("gen", "数据生成 (C++/Py)")]):
            row_f = ctk.CTkFrame(config_box, fg_color="transparent");
            row_f.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(row_f, text=label, width=120).pack(side="left")
            ctk.CTkEntry(row_f, textvariable=self.stress_files[k]).pack(side="left", fill="x", expand=True, padx=10)
            ctk.CTkButton(row_f, text="浏览", width=60, command=lambda key=k: self.pick_stress_file(key)).pack(
                side="right")

        self.stress_log = ctk.CTkTextbox(frame, font=("Consolas", 12), fg_color="#1a1a1a");
        self.stress_log.grid(row=3, column=0, sticky="nsew", pady=10)

        ctl_f = ctk.CTkFrame(frame, fg_color="transparent");
        ctl_f.grid(row=4, column=0, sticky="ew")
        self.btn_start_stress = ctk.CTkButton(ctl_f, text="开始对拍", fg_color="#2ecc71", command=self.toggle_stress);
        self.btn_start_stress.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(ctl_f, text="清空日志", width=100, command=lambda: self.stress_log.delete("1.0", "end")).pack(
            side="right", padx=5)

    def setup_utils_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["utils"] = frame
        ctk.CTkLabel(frame, text="实用工具箱", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))
        calc_f = ctk.CTkFrame(frame);
        calc_f.pack(fill="x", pady=10)
        self.util_n = ctk.CTkEntry(calc_f, width=120);
        self.util_n.insert(0, "100000");
        self.util_n.grid(row=0, column=1, padx=10)
        ctk.CTkButton(calc_f, text="计算复杂度", command=self.calc_complexity).grid(row=0, column=2, padx=10)
        self.util_res = ctk.CTkLabel(calc_f, text="---");
        self.util_res.grid(row=1, column=0, columnspan=3)

    # 逻辑辅助方法 (通用)
    def load_templates(self):
        self.templates = {"示例模板": "// Hello World\n#include <iostream>\nint main() { return 0; }"}
        if os.path.exists(self.template_file):
            try:
                with open(self.template_file, "r", encoding="utf-8") as f:
                    self.templates = json.load(f)
            except:
                pass

    def refresh_template_list(self):
        for child in self.tpl_list_frame.winfo_children(): child.destroy()
        for name in sorted(self.templates.keys()):
            btn = ctk.CTkButton(self.tpl_list_frame, text=name, fg_color="transparent", anchor="w",
                                command=lambda n=name: self.select_template(n))
            btn.pack(fill="x", pady=2)

    def select_template(self, name):
        self.current_tpl_key = name
        self.tpl_name_entry.delete(0, "end");
        self.tpl_name_entry.insert(0, name)
        self.tpl_view.delete("1.0", "end");
        self.tpl_view.insert("1.0", self.templates[name])

    def save_current_template(self):
        new_name = self.tpl_name_entry.get().strip()
        if not new_name: return
        self.templates[new_name] = self.tpl_view.get("1.0", "end-1c")
        with open(self.template_file, "w", encoding="utf-8") as f: json.dump(self.templates, f, ensure_ascii=False,
                                                                             indent=4)
        self.refresh_template_list();
        messagebox.showinfo("成功", "保存成功")

    def add_new_template(self):
        self.current_tpl_key = f"新模板_{random.randint(100, 999)}"
        self.templates[self.current_tpl_key] = "// 新代码"
        self.refresh_template_list();
        self.select_template(self.current_tpl_key)

    def delete_template(self):
        if self.current_tpl_key in self.templates:
            del self.templates[self.current_tpl_key]
            self.save_current_template()

    def generate_data(self):
        try:
            T = int(self.gen_t.get());
            v_min, v_max = int(self.gen_min.get()), int(self.gen_max.get())
            w_min, w_max = int(self.gen_w_min.get()), int(self.gen_w_max.get())
            g_type = self.gen_type.get();
            res = []
            if T > 1: res.append(str(T))
            for _ in range(T):
                if g_type == "整数数列":
                    n = random.randint(v_min, v_max);
                    res.append(str(n))
                    res.append(" ".join(str(random.randint(w_min, w_max)) for _ in range(n)))
                elif g_type == "随机排列":
                    n = random.randint(v_min, v_max);
                    p = list(range(1, n + 1));
                    random.shuffle(p)
                    res.append(str(n));
                    res.append(" ".join(map(str, p)))
                elif g_type == "矩阵/网格":
                    r, c = random.randint(2, 10), random.randint(2, 10);
                    res.append(f"{r} {c}")
                    for _ in range(r): res.append(" ".join(str(random.randint(w_min, w_max)) for _ in range(c)))
                elif g_type == "随机字符串":
                    n = random.randint(v_min, v_max);
                    res.append(''.join(random.choices(string.ascii_lowercase, k=n)))
                elif g_type in ["简单图", "带权图", "普通树", "二叉树"]:
                    n = random.randint(v_min, v_max);
                    edges = []
                    if "树" in g_type:
                        for i in range(2, n + 1): edges.append(
                            (i // 2 if "二叉" in g_type else random.randint(1, i - 1), i))
                    else:
                        m = random.randint(n - 1, min(n * (n - 1) // 2, n + 5))
                        edge_set = set()
                        while len(edge_set) < m:
                            u, v = random.sample(range(1, n + 1), 2)
                            edge_set.add(tuple(sorted((u, v))))
                        edges = list(edge_set)
                    res.append(f"{n} {len(edges)}")
                    for u, v in edges:
                        w = f" {random.randint(w_min, w_max)}" if g_type == "带权图" else ""
                        res.append(f"{u} {v}{w}")
            self.gen_output.delete("1.0", "end");
            self.gen_output.insert("1.0", "\n".join(res))
        except:
            messagebox.showerror("错误", "参数有误")

    def pick_file_diff(self, target):
        path = filedialog.askopenfilename()
        if path:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if target == 1:
                    self.diff_box1.delete("1.0", "end");
                    self.diff_box1.insert("1.0", f.read())
                else:
                    self.diff_box2.delete("1.0", "end");
                    self.diff_box2.insert("1.0", f.read())
            self.update_line_numbers()

    def pick_stress_file(self, k):
        p = filedialog.askopenfilename();
        if p: self.stress_files[k].set(p)

    def toggle_stress(self):
        if self.is_stress_testing:
            self.stop_signal = True
            return

        sol, std, gen = self.stress_files["sol"].get(), self.stress_files["std"].get(), self.stress_files["gen"].get()
        if not (sol and std and gen):
            messagebox.showwarning("提示", "请先选择所有程序路径！")
            return

        self.is_stress_testing = True;
        self.stop_signal = False
        self.btn_start_stress.configure(text="停止对拍", fg_color="#e74c3c")
        self.stress_log.insert("end", f">>> 对拍开始时间: {time.strftime('%H:%M:%S')}\n")
        threading.Thread(target=self.run_stress_engine, args=(sol, std, gen), daemon=True).start()

    def _prepare_exec(self, path, name):
        """内部方法：如果是CPP则尝试编译并返回执行命令"""
        if path.endswith(".cpp"):
            exe_path = os.path.abspath(f"./temp_{name}.exe")
            self.stress_log.insert("end", f"正在编译 {name}...\n")
            try:
                # 编译命令，添加常用优化
                subprocess.check_call(f'g++ "{path}" -o "{exe_path}" -O2 -std=c++17', shell=True)
                return f'"{exe_path}"', exe_path
            except Exception as e:
                self.stress_log.insert("end", f"编译失败 {name}: {e}\n")
                return None, None
        elif path.endswith(".py"):
            return f'python "{path}"', None
        else:
            return f'"{path}"', None

    def run_stress_engine(self, sol_path, std_path, gen_path):
        # 1. 准备执行命令
        cmd_sol, exe_sol = self._prepare_exec(sol_path, "sol")
        cmd_std, exe_std = self._prepare_exec(std_path, "std")
        cmd_gen, exe_gen = self._prepare_exec(gen_path, "gen")

        if not (cmd_sol and cmd_std and cmd_gen):
            self.is_stress_testing = False
            self.btn_start_stress.configure(text="开始对拍", fg_color="#2ecc71")
            return

        count = 1
        self.stress_log.insert("end", "准备就绪，开始循环...\n")

        while not self.stop_signal:
            try:
                # 生成数据
                start_t = time.time()
                input_data = subprocess.check_output(cmd_gen, shell=True, text=True, timeout=10)

                # 运行标准程序
                out_std = subprocess.check_output(cmd_std, input=input_data, shell=True, text=True, timeout=10)

                # 运行待测程序
                out_sol = subprocess.check_output(cmd_sol, input=input_data, shell=True, text=True, timeout=10)

                duration = (time.time() - start_t) * 1000

                # 格式化比对（去除行末空格和文末空行）
                std_clean = "\n".join([line.rstrip() for line in out_std.strip().splitlines()])
                sol_clean = "\n".join([line.rstrip() for line in out_sol.strip().splitlines()])

                if std_clean == sol_clean:
                    self.stress_log.insert("end", f"#{count} PASS ({duration:.0f}ms)\n")
                    self.stress_log.see("end")
                else:
                    self.stress_log.insert("end", f"#{count} >>> ❌ WA (答案错误)!\n", "err")
                    self.stress_log.tag_config("err", foreground="#e74c3c")

                    # 保存错误现场
                    with open("error.in", "w", encoding="utf-8") as f:
                        f.write(input_data)
                    with open("std.out", "w", encoding="utf-8") as f:
                        f.write(out_std)
                    with open("sol.out", "w", encoding="utf-8") as f:
                        f.write(out_sol)

                    self.stress_log.insert("end", "数据已保存至 error.in / std.out / sol.out\n")
                    self.stress_log.see("end")
                    break

            except subprocess.TimeoutExpired:
                self.stress_log.insert("end", f"#{count} >>> ⚠️ TLE (运行超时)!\n")
                break
            except Exception as e:
                self.stress_log.insert("end", f"运行时错误: {e}\n")
                break
            count += 1

        # 清理临时文件
        self.stress_log.insert("end", f">>> 对拍停止。共运行 {count if self.stop_signal else count - 1} 组。\n")
        self.is_stress_testing = False
        self.btn_start_stress.configure(text="开始对拍", fg_color="#2ecc71")

    def calc_complexity(self):
        try:
            n = float(self.util_n.get());
            import math
            self.util_res.configure(text=f"N log N ≈ {n * math.log2(n):.1e} | N^2 ≈ {n * n:.1e}")
        except:
            pass

    def copy_to_clipboard(self):
        pyperclip.copy(self.gen_output.get("1.0", "end-1c"))

    def export_to_txt(self):
        with open("data.in", "w") as f: f.write(self.gen_output.get("1.0", "end-1c"))
        messagebox.showinfo("成功", "保存成功")


if __name__ == "__main__":
    app = CPToolkit()
    app.mainloop()
