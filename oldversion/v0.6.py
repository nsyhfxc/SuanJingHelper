import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import random
import string
import pyperclip
import os
import threading

# 设置主题
ctk.set_appearance_mode("dark")  # 默认深色
ctk.set_default_color_theme("blue")


class CPToolkit(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CP Master - 算法竞赛辅助工具")
        self.geometry("1100, 800")

        # 布局初始化
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 侧边栏
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CP Master", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_gen = ctk.CTkButton(self.sidebar_frame, text="数据生成", command=lambda: self.select_frame("gen"))
        self.btn_gen.grid(row=1, column=0, padx=20, pady=10)

        self.btn_diff = ctk.CTkButton(self.sidebar_frame, text="对拍/对比", command=lambda: self.select_frame("diff"))
        self.btn_diff.grid(row=2, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="显示模式:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))

        # 数据生成面板
        self.gen_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_gen_ui()

        # 对拍面板
        self.diff_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_diff_ui()

        # 默认显示生成器
        self.select_frame("gen")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def select_frame(self, name):
        self.gen_frame.grid_forget()
        self.diff_frame.grid_forget()
        if name == "gen":
            self.gen_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        elif name == "diff":
            self.diff_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    # --- 数据生成模块 UI ---
    def setup_gen_ui(self):
        self.gen_frame.grid_columnconfigure(0, weight=1)
        self.gen_frame.grid_rowconfigure(2, weight=1)

        header = ctk.CTkLabel(self.gen_frame, text="测试数据生成器", font=ctk.CTkFont(size=20, weight="bold"))
        header.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # 参数配置区域
        config_frame = ctk.CTkFrame(self.gen_frame)
        config_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        # 组数
        ctk.CTkLabel(config_frame, text="组数 (T):").grid(row=0, column=0, padx=10, pady=10)
        self.gen_t = ctk.CTkEntry(config_frame, width=60)
        self.gen_t.insert(0, "1")
        self.gen_t.grid(row=0, column=1, padx=10, pady=10)

        # 范围
        ctk.CTkLabel(config_frame, text="数值范围 (Min-Max):").grid(row=0, column=2, padx=10, pady=10)
        self.gen_min = ctk.CTkEntry(config_frame, width=80)
        self.gen_min.insert(0, "1")
        self.gen_min.grid(row=0, column=3, padx=5, pady=10)
        self.gen_max = ctk.CTkEntry(config_frame, width=80)
        self.gen_max.insert(0, "100")
        self.gen_max.grid(row=0, column=4, padx=5, pady=10)

        # 类型选择
        ctk.CTkLabel(config_frame, text="数据类型:").grid(row=1, column=0, padx=10, pady=10)
        self.gen_type = ctk.CTkOptionMenu(config_frame,
                                          values=["整数数列", "随机字符串", "简单图", "连通图", "普通树", "二叉树"])
        self.gen_type.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="w")

        self.btn_run_gen = ctk.CTkButton(config_frame, text="生成数据", fg_color="green", hover_color="#006400",
                                         command=self.generate_data)
        self.btn_run_gen.grid(row=1, column=3, columnspan=2, padx=10, pady=10, sticky="ew")

        # 结果展示区
        self.gen_output = ctk.CTkTextbox(self.gen_frame, font=("Consolas", 14))
        self.gen_output.grid(row=2, column=0, sticky="nsew", pady=(20, 10))

        # 操作区
        op_frame = ctk.CTkFrame(self.gen_frame, fg_color="transparent")
        op_frame.grid(row=3, column=0, sticky="ew")

        self.btn_copy = ctk.CTkButton(op_frame, text="复制到剪贴板", width=150, command=self.copy_to_clipboard)
        self.btn_copy.pack(side="left", padx=10)

        self.btn_export = ctk.CTkButton(op_frame, text="导出为 TXT", width=150, command=self.export_to_txt)
        self.btn_export.pack(side="left", padx=10)

    # --- 对拍模块 UI ---
    def setup_diff_ui(self):
        self.diff_frame.grid_columnconfigure((0, 1), weight=1)
        self.diff_frame.grid_rowconfigure(2, weight=1)

        header = ctk.CTkLabel(self.diff_frame, text="文本对比 (对拍辅助)", font=ctk.CTkFont(size=20, weight="bold"))
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        # 文件选择
        self.file1_path = tk.StringVar(value="未选择文件 1 (标准答案)")
        self.file2_path = tk.StringVar(value="未选择文件 2 (待测程序)")

        f1_btn = ctk.CTkButton(self.diff_frame, text="选择文件 1", command=lambda: self.pick_file(1))
        f1_btn.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        f2_btn = ctk.CTkButton(self.diff_frame, text="选择文件 2", command=lambda: self.pick_file(2))
        f2_btn.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # 文本框展示
        self.diff_box1 = ctk.CTkTextbox(self.diff_frame, font=("Consolas", 12))
        self.diff_box1.grid(row=2, column=0, padx=5, pady=10, sticky="nsew")

        self.diff_box2 = ctk.CTkTextbox(self.diff_frame, font=("Consolas", 12))
        self.diff_box2.grid(row=2, column=1, padx=5, pady=10, sticky="nsew")

        # 状态栏
        self.diff_status = ctk.CTkLabel(self.diff_frame, text="等待对比...", text_color="gray")
        self.diff_status.grid(row=3, column=0, columnspan=2, pady=5)

        self.btn_compare = ctk.CTkButton(self.diff_frame, text="开始对比", font=ctk.CTkFont(weight="bold"),
                                         command=self.compare_files)
        self.btn_compare.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # --- 功能逻辑：数据生成 ---
    def generate_data(self):
        try:
            T = int(self.gen_t.get())
            v_min = int(self.gen_min.get())
            v_max = int(self.gen_max.get())
            g_type = self.gen_type.get()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
            return

        result = []
        if T > 1: result.append(str(T))

        for _ in range(T):
            if g_type == "整数数列":
                n = random.randint(v_min, v_max)
                arr = [str(random.randint(v_min, v_max)) for _ in range(n)]
                result.append(str(n))
                result.append(" ".join(arr))

            elif g_type == "随机字符串":
                n = random.randint(v_min, v_max)
                s = ''.join(random.choices(string.ascii_lowercase, k=n))
                result.append(str(n))
                result.append(s)

            elif g_type == "简单图":
                n = random.randint(max(2, v_min // 10), v_max // 10)
                m = random.randint(n - 1, min(n * (n - 1) // 2, v_max))
                edges = set()
                while len(edges) < m:
                    u, v = random.randint(1, n), random.randint(1, n)
                    if u != v:
                        edge = tuple(sorted((u, v)))
                        edges.add(edge)
                result.append(f"{n} {m}")
                for u, v in edges:
                    result.append(f"{u} {v}")

            elif g_type == "连通图":
                # 先生成一棵树保证连通，再补齐边
                n = random.randint(max(2, v_min // 10), v_max // 10)
                m = random.randint(n - 1, min(n * (n - 1) // 2, v_max))
                edges = []
                # 树部分
                nodes = list(range(1, n + 1))
                random.shuffle(nodes)
                connected = [nodes[0]]
                remaining = nodes[1:]
                while remaining:
                    u = random.choice(connected)
                    v = remaining.pop()
                    edges.append(tuple(sorted((u, v))))
                    connected.append(v)
                # 额外边
                all_edges = set(edges)
                while len(all_edges) < m:
                    u, v = random.randint(1, n), random.randint(1, n)
                    if u != v:
                        all_edges.add(tuple(sorted((u, v))))
                result.append(f"{n} {len(all_edges)}")
                for u, v in all_edges:
                    result.append(f"{u} {v}")

            elif g_type == "普通树":
                n = random.randint(max(2, v_min), v_max)
                result.append(str(n))
                for i in range(2, n + 1):
                    fa = random.randint(1, i - 1)
                    result.append(f"{fa} {i}")

            elif g_type == "二叉树":
                n = random.randint(max(2, v_min), v_max)
                result.append(str(n))
                nodes = list(range(1, n + 1))
                # 模拟随机二叉树生成：每个点随机分左右子节点
                for i in range(1, n + 1):
                    # 此处为简化逻辑，实际竞赛中树通常输出边集
                    pass
                # 采用 Prüfer 类似逻辑简化
                for i in range(2, n + 1):
                    fa = random.randint(1, i - 1)
                    result.append(f"{fa} {i}")

        self.gen_output.delete("1.0", "end")
        self.gen_output.insert("1.0", "\n".join(result))

    def copy_to_clipboard(self):
        data = self.gen_output.get("1.0", "end-1c")
        if data.strip():
            pyperclip.copy(data)
            messagebox.showinfo("成功", "数据已复制到剪贴板")

    def export_to_txt(self):
        data = self.gen_output.get("1.0", "end-1c")
        if not data.strip(): return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, "w") as f:
                f.write(data)
            messagebox.showinfo("成功", f"数据已导出至: {file_path}")

    # --- 功能逻辑：文件对比 ---
    def pick_file(self, idx):
        path = filedialog.askopenfilename()
        if path:
            if idx == 1:
                self.file1_path.set(path)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.diff_box1.delete("1.0", "end")
                    self.diff_box1.insert("1.0", f.read())
            else:
                self.file2_path.set(path)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.diff_box2.delete("1.0", "end")
                    self.diff_box2.insert("1.0", f.read())

    def compare_files(self):
        # 获取文本并清除之前的高亮
        text1 = self.diff_box1.get("1.0", "end-1c").splitlines()
        text2 = self.diff_box2.get("1.0", "end-1c").splitlines()

        self.diff_box1.tag_remove("diff", "1.0", "end")
        self.diff_box2.tag_remove("diff", "1.0", "end")

        # 定义高亮样式
        self.diff_box1.tag_config("diff", background="#FFB6C1", foreground="black")  # 淡红色
        self.diff_box2.tag_config("diff", background="#FFB6C1", foreground="black")

        max_len = max(len(text1), len(text2))
        diff_count = 0
        first_diff_line = -1

        for i in range(max_len):
            l1 = text1[i].rstrip() if i < len(text1) else None
            l2 = text2[i].rstrip() if i < len(text2) else None

            if l1 != l2:
                diff_count += 1
                if first_diff_line == -1: first_diff_line = i + 1

                # 在 GUI 中高亮显示该行
                self.diff_box1.tag_add("diff", f"{i + 1}.0", f"{i + 1}.end")
                self.diff_box2.tag_add("diff", f"{i + 1}.0", f"{i + 1}.end")

        if diff_count == 0:
            self.diff_status.configure(text="Accepted (完全一致!)", text_color="green")
            messagebox.showinfo("结果", "两个文件内容完全一致 (忽略行尾空格)")
        else:
            self.diff_status.configure(text=f"Wrong Answer (发现 {diff_count} 处不同)", text_color="red")
            if first_diff_line != -1:
                # 自动滚动到第一个不同点
                self.diff_box1.see(f"{first_diff_line}.0")
                self.diff_box2.see(f"{first_diff_line}.0")


if __name__ == "__main__":
    app = CPToolkit()
    app.mainloop()