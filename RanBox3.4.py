import ttkbootstrap as ttk
import sqlite3
from ttkbootstrap.constants import *
import random
import tkinter.font as tkfont
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import sys


# 五十音图数据，按行划分
HIRAGANA_ROWS = [
    ["あ", "い", "う", "え", "お"],
    ["か", "き", "く", "け", "こ"],
    ["さ", "し", "す", "せ", "そ"],
    ["た", "ち", "つ", "て", "と"],
    ["な", "に", "ぬ", "ね", "の"],
    ["は", "ひ", "ふ", "へ", "ほ"],
    ["ま", "み", "む", "め", "も"],
    ["や", " ", "ゆ", " ", "よ"],
    ["ら", "り", "る", "れ", "ろ"],
    ["わ", " ", " ", " ", "を"],
    ["ん"]  # "ん" 单独一行
]

KATAKANA_ROWS = [
    ["ア", "イ", "ウ", "エ", "オ"],
    ["カ", "キ", "ク", "ケ", "コ"],
    ["サ", "シ", "ス", "セ", "ソ"],
    ["タ", "チ", "ツ", "テ", "ト"],
    ["ナ", "ニ", "ヌ", "ネ", "ノ"],
    ["ハ", "ヒ", "フ", "ヘ", "ホ"],
    ["マ", "ミ", "ム", "メ", "モ"],
    ["ヤ", " ", "ユ", " ", "ヨ"],
    ["ラ", "リ", "ル", "レ", "ロ"],
    ["ワ", " ", " ", " ", "ヲ"],
    ["ン"]  # "ン" 单独一行
]

ROMAJI_ROWS = [
    ["a", "i", "u", "e", "o"],
    ["ka", "ki", "ku", "ke", "ko"],
    ["sa", "shi", "su", "se", "so"],
    ["ta", "chi", "tsu", "te", "to"],
    ["na", "ni", "nu", "ne", "no"],
    ["ha", "hi", "fu", "he", "ho"],
    ["ma", "mi", "mu", "me", "mo"],
    ["ya", " ", "yu", " ", "yo"],
    ["ra", "ri", "ru", "re", "ro"],
    ["wa", " ", " ", " ", "wo"],
    ["n"]  # "n" 单独一行
]

# 合并行数据为一维列表
HIRAGANA = [char for row in HIRAGANA_ROWS for char in row if char != " "]
KATAKANA = [char for row in KATAKANA_ROWS for char in row if char != " "]
ROMAJI = [char for row in ROMAJI_ROWS for char in row if char != " "]

# 建立音对应关系
SOUND_MAP = {}
for i in range(len(HIRAGANA)):
    sound = ROMAJI[i]
    SOUND_MAP[sound] = [HIRAGANA[i], KATAKANA[i], ROMAJI[i]]


class KanaPracticeApp:
    def __init__(self, root):  # 初始化
        self.root = root
        self.root.title("日语五十音练习")
        # 设置窗口尺寸
        self.root.geometry("1000x1000")

        # 添加正确率文件路径
        import os
        self.stats_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kana_stats.json")

        # 数据库路径
        self.conn = sqlite3.connect('kana_practice.db')
        self.create_tables()
        self.load_stats_from_db()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 选择合适的字体，将 ming_font 变成类属性
        font_names = tkfont.families()
        self.ming_font = next((font for font in font_names if "明" in font), "Microsoft YaHei")
        self.current_font = self.ming_font
        self.is_ming_font = True

        # 初始化主题
        self.style = ttk.Style(theme='litera')
        # 初始化时添加用于存储 grid 布局参数的字典
        self.grid_params = {}
        # 全局字体设置，浅色模式下字体黑色
        self.update_font_style()

        # 自定义按钮样式，浅色模式下按键背景白色，字体黑色
        self.style.configure("Custom.TButton",
                             relief="flat",
                             borderwidth=1,  # 设置边框宽度，增加区分度
                             background="white",
                             foreground="black",  # 字体颜色为黑色
                             activebackground="#219d54",
                             font=(self.current_font, 12, "bold"),
                             borderradius=5)  # 适当减小圆角
        self.style.map("Custom.TButton",
                       background=[('active', '#219d54'), ('pressed', '#219d54')])

        # 深色模式切换按钮，设置固定宽度
        self.dark_mode = False
        self.theme_btn = ttk.Button(
            root,
            text="切换深色模式",
            style="Custom.TButton",
            command=self.toggle_dark_mode,
            width=12  # 设置固定宽度
        )
        self.theme_btn.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        # 字体切换按钮
        self.font_btn = ttk.Button(
            root,
            text="黑",
            style="Custom.TButton",
            command=self.toggle_font,
            width=3  # 设置固定宽度
        )
        self.font_btn.grid(row=0, column=1, padx=10, pady=10, sticky="nw")

        # 设置浅色模式背景颜色为淡淡的灰色
        if not self.dark_mode:
            self.root.configure(background="#f5f5f5")

        # 模式选择区域
        self.mode_frame = ttk.Frame(root)
        self.mode_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.mode_var = ttk.StringVar()
        self.mode_var.set("片-平")
        mode_options = ["片-平", "平-片", "平-罗", "罗-平", "片-罗", "罗-片"]
        mode_label = ttk.Label(self.mode_frame, text="选择练习模式:", style="Title.TLabel")
        mode_label.pack(side=ttk.LEFT, padx=5)
        mode_menu = ttk.Combobox(self.mode_frame, textvariable=self.mode_var, values=mode_options,
                                 style="Custom.TCombobox")
        mode_menu.pack(side=ttk.LEFT, padx=5)
        mode_menu.bind("<<ComboboxSelected>>", self.new_question)

        # 交换模式
        swap_button = ttk.Button(self.mode_frame, text="♻", style="Custom.TButton", command=self.swap_mode)
        swap_button.pack(side=ttk.LEFT, padx=5)

        # 添加随机模式按钮
        random_button = ttk.Button(
            self.mode_frame,
            text="🎲",
            style="Custom.TButton",
            command=self.random_mode,
            width=3,
            padding=(0, 0, 0, 8)
        )
        random_button.pack(side=ttk.LEFT, padx=5)

        # 添加打乱/恢复键盘按钮
        self.normal_button_width = 3  # 记录正常模式下按钮宽度
        self.shuffle_keyboard_btn = ttk.Button(
            self.mode_frame,
            text="🎁",
            style="Custom.TButton",
            command=self.toggle_keyboard_shuffle,
            width=self.normal_button_width,
            padding=(0, 0, 0, 8)
        )
        self.shuffle_keyboard_btn.pack(side=ttk.LEFT, padx=5)
        self.is_keyboard_shuffled = False
        self.original_char_rows = None
        # 添加奖励模式状态变量，normal 表示正常模式，triple 表示三倍奖励模式
        self.is_triple_mode = False

        # 初始化时创建新样式
        self.style.configure("Triple.Custom.TButton",
                             font=("Microsoft YaHei", 12, "bold"))

        # 添加重置数据按钮
        self.reset_data_btn = ttk.Button(
            self.mode_frame,
            text="🚮",
            style="Custom.TButton",
            command=self.reset_data,
            width=3,
            padding=(0, 0, 0, 8)
        )
        self.reset_data_btn.pack(side=ttk.LEFT, padx=5)

        # 连胜统计与最高纪录
        self.streak = 0
        self.high_score = 0
        self.streak_label = ttk.Label(root, text=f"连胜: {self.streak}", style="TLabel")
        self.streak_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.high_score_label = ttk.Label(root, text=f"最高纪录: {self.high_score}", style="TLabel")
        self.high_score_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        # 题目显示，让文字在格子内居中，格子相对于窗口宽度居中
        self.root.columnconfigure(0, weight=1)
        self.question_label = ttk.Label(root, text="", style="Title.TLabel", anchor="center")
        self.question_label.grid(row=4, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

        # 键盘区域
        self.keyboard_frame = ttk.Frame(root)
        self.keyboard_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(5, weight=1)

        # 答案反馈
        self.feedback_label = ttk.Label(root, text="", style="TLabel")
        self.feedback_label.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # 添加正确率统计字典
        self.correct_counts = {char: {'correct': 0, 'total': 0} for char in HIRAGANA + KATAKANA + ROMAJI}

        # 加载已有统计数据
        self.load_stats()

        # 熟练度地图按钮
        self.proficiency_btn = ttk.Button(
            root,
            text="熟练度地图",
            style="Custom.TButton",
            command=self.show_proficiency_map,
            width=10
        )
        self.proficiency_btn.grid(row=0, column=1, padx=8, pady=10, sticky="nw")

        # 调整字体切换按钮位置
        self.font_btn.grid(row=0, column=2, padx=10, pady=10, sticky="nw")

        # 熟练度地图页面
        self.proficiency_frame = ttk.Frame(root)
        self.proficiency_label = ttk.Label(self.proficiency_frame, text="熟练度地图", style="Title.TLabel")
        self.back_btn = ttk.Button(
            self.proficiency_frame,
            text="返回练习",
            style="Custom.TButton",
            command=self.hide_proficiency_map
        )

        # 添加加强训练按钮
        self.intensive_training_btn = ttk.Button(
            self.proficiency_frame,
            text="加强训练",
            style="Custom.TButton",
            command=self.start_intensive_training
        )

        # 使用 grid 布局放置标签、返回按钮和加强训练按钮
        self.proficiency_label.grid(row=0, column=0, columnspan=5, pady=10, sticky="n")
        self.back_btn.grid(row=len(HIRAGANA_ROWS) + 1, column=0, columnspan=5, pady=10, sticky="s")
        self.intensive_training_btn.grid(row=0, column=5, rowspan=len(HIRAGANA_ROWS) + 2, padx=10, sticky="ns")

        # 初始化
        self.buttons = []
        self.current_answer = None
        self.question_label.config(foreground="black")  # 初始时设置为黑色
        self.new_question()

    def random_mode(self):  # 随机模式
        """随机选择一种练习模式"""
        modes = ["片-平", "平-片", "平-罗", "罗-平", "片-罗", "罗-片"]
        random_mode = random.choice(modes)
        self.mode_var.set(random_mode)
        self.new_question()

    def on_close(self):  # 窗口关闭时执行的操作
        try:
            # 保存统计数据到数据库
            self.save_stats_to_db()
            # 保存统计数据到 JSON 文件
            self.save_stats()
            print("数据保存成功")
        except Exception as e:
            print(f"保存数据时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 关闭数据库连接
            self.conn.close()
            # 销毁窗口
            self.root.destroy()

    def load_stats(self):  # 加载统计数据
        """从文件加载统计数据，如果不存在则初始化空数据"""
        import json
        import os

        # 先检查文件是否存在
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print("从文件加载的数据:", data)  # 调试输出

                    # 只初始化文件中存在的字符数据
                    self.correct_counts = {}
                    if 'correct_counts' in data:
                        for char, stats in data['correct_counts'].items():
                            self.correct_counts[char] = {
                                'correct': stats.get('correct', 0),
                                'total': stats.get('total', 0)
                            }
            except Exception as e:
                print(f"加载数据时出错: {e}")
                # 出错时才初始化为全0
                self.correct_counts = {char: {'correct': 0, 'total': 0}
                                       for char in HIRAGANA + KATAKANA + ROMAJI}
        else:
            # 文件不存在时才初始化为全0
            self.correct_counts = {char: {'correct': 0, 'total': 0}
                                   for char in HIRAGANA + KATAKANA + ROMAJI}

    def save_stats(self):  # 保存统计数据
        """保存统计数据到文件"""
        import json
        import os

        print("准备保存的数据:", self.correct_counts)  # 调试输出
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'correct_counts': self.correct_counts
                }, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到: {os.path.abspath(self.stats_file)}")  # 打印完整路径
        except Exception as e:
            print(f"保存数据时出错: {e}")
            raise

    def update_font_style(self):  # 更新字体
        self.style.configure("TLabel", font=(self.current_font, 12))
        self.style.configure("Title.TLabel", font=(self.current_font, 16, "bold"))
        self.style.configure("Custom.TButton", font=(self.current_font, 12, "bold"))

    def toggle_font(self):  # 切换字体
        if self.is_ming_font:
            self.current_font = "Microsoft YaHei"
            self.font_btn.config(text="明")
        else:
            self.current_font = self.ming_font
            self.font_btn.config(text="黑")
        self.is_ming_font = not self.is_ming_font
        self.update_font_style()
        self.root.update_idletasks()

    def toggle_dark_mode(self):  # 切换深色模式
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.root.style.theme_use('darkly')
            self.theme_btn.config(text="切换浅色模式")
            # 获取深色模式下的背景颜色并设置
            dark_bg = self.style.lookup("TFrame", "background")
            self.root.configure(background=dark_bg)
            self.style.configure("TLabel", font=(self.current_font, 12), foreground="#7f8c8d")
            self.style.configure("Title.TLabel", font=(self.current_font, 16, "bold"), foreground="#34495e")
            self.style.configure("Custom.TButton",
                                 background=self.style.lookup("TButton", "background"),
                                 foreground=self.style.lookup("TButton", "foreground"))
            self.question_label.config(foreground="white")
        else:
            self.root.style.theme_use('litera')
            self.theme_btn.config(text="切换深色模式")
            self.root.configure(background="#f5f5f5")
            self.style.configure("TLabel", font=(self.current_font, 12), foreground="black")
            self.style.configure("Title.TLabel", font=(self.current_font, 16, "bold"), foreground="black")
            self.style.configure("Custom.TButton",
                                 background="white",
                                 foreground="black")
            self.question_label.config(foreground="black")
        # 刷新布局
        self.root.update_idletasks()

    def swap_mode(self):  # 交换模式
        mode = self.mode_var.get()
        if "-" in mode:
            left, right = mode.split("-")
            new_mode = f"{right}-{left}"
            self.mode_var.set(new_mode)
            self.new_question()

    def new_question(self, event=None):  # 生成新题目
        self.feedback_label.config(text="")
        mode = self.mode_var.get()
        index = random.randint(0, len(HIRAGANA) - 1)

        if mode == "片-平":
            self.question_label.config(text=KATAKANA[index])
            self.current_answer = HIRAGANA[index]
        elif mode == "平-片":
            self.question_label.config(text=HIRAGANA[index])
            self.current_answer = KATAKANA[index]
        elif mode == "平-罗":
            self.question_label.config(text=HIRAGANA[index])
            self.current_answer = ROMAJI[index]
        elif mode == "罗-平":
            self.question_label.config(text=ROMAJI[index])
            self.current_answer = HIRAGANA[index]
        elif mode == "片-罗":
            self.question_label.config(text=KATAKANA[index])
            self.current_answer = ROMAJI[index]
        elif mode == "罗-片":
            self.question_label.config(text=ROMAJI[index])
            self.current_answer = KATAKANA[index]

        # 只有不在三倍模式时，才重新创建键盘
        if not self.is_triple_mode:
            # 清除旧按钮
            for button in self.buttons:
                button.destroy()
            self.buttons = []

            if mode == "片-平":
                self.create_keyboard(HIRAGANA_ROWS)
            elif mode == "平-片":
                self.create_keyboard(KATAKANA_ROWS)
            elif mode == "平-罗":
                self.create_keyboard(ROMAJI_ROWS)
            elif mode == "罗-平":
                self.create_keyboard(HIRAGANA_ROWS)
            elif mode == "片-罗":
                self.create_keyboard(ROMAJI_ROWS)
            elif mode == "罗-片":
                self.create_keyboard(KATAKANA_ROWS)

    def toggle_keyboard_shuffle(self):  # 打乱键盘
        self.is_triple_mode = not self.is_triple_mode
        self.is_keyboard_shuffled = self.is_triple_mode  # 乱序键盘与三倍状态绑定
        mode = self.mode_var.get()

        if self.is_triple_mode:
            self.shuffle_keyboard_btn.config(
                text="🎁x3",
                width=5,  # 扩展按钮宽度
                style="Triple.Custom.TButton"  # 使用新样式
            )
            # 每次进入三倍状态，重新生成乱序键盘
            if mode in ["罗-片", "平-片"]:
                original_rows = KATAKANA_ROWS.copy()
                char_list = KATAKANA.copy()
            elif mode in ["片-平", "罗-平"]:
                original_rows = HIRAGANA_ROWS.copy()
                char_list = HIRAGANA.copy()
            else:  # mode in ["片-罗", "平-罗"]:
                original_rows = ROMAJI_ROWS.copy()
                char_list = ROMAJI.copy()

            random.shuffle(char_list)
            shuffled_rows = []
            index = 0
            for row in original_rows:
                new_row = []
                for char in row:
                    if char != " ":
                        new_row.append(char_list[index])
                        index += 1
                    else:
                        new_row.append(" ")
                shuffled_rows.append(new_row)
            self.create_keyboard(shuffled_rows)
            self.original_char_rows = original_rows
        else:
            self.shuffle_keyboard_btn.config(
                text="🎁",
                width=self.normal_button_width,  # 恢复正常宽度
                style="Custom.TButton"  # 恢复原样式
            )
            if self.original_char_rows:
                self.create_keyboard(self.original_char_rows)
                # 退出三倍模式后重置原始字符行
                self.original_char_rows = None

    def reset_data(self):  # 重置 SQLite3 数据库和 JSON 文件
        try:
            # 重置数据库中的连胜和最高纪录
            cursor = self.conn.cursor()
            cursor.execute('UPDATE streak_stats SET streak = 0, high_score = 0 WHERE id = (SELECT MAX(id) FROM streak_stats)')
            # 重置数据库中的正确率统计
            all_chars = HIRAGANA + KATAKANA + ROMAJI
            for char in all_chars:
                cursor.execute('''
                    INSERT OR REPLACE INTO proficiency_stats (char, correct, total)
                    VALUES (?, 0, 0)
                ''', (char,))
            self.conn.commit()

            # 重置内存中的统计数据
            self.streak = 0
            self.high_score = 0
            self.streak_label.config(text=f"连胜: {self.streak}")
            self.high_score_label.config(text=f"最高纪录: {self.high_score}")
            self.correct_counts = {char: {'correct': 0, 'total': 0} for char in all_chars}

            # 重置 JSON 文件中的统计数据
            import json
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'correct_counts': self.correct_counts
                }, f, ensure_ascii=False, indent=2)
            print("数据已重置")
        except Exception as e:
            print(f"重置数据时出错: {e}")

    def make_square(self, event):  # 使按钮为正方形
        size = min(event.width, event.height)
        event.widget.config(width=size // 10)

    def check_answer(self, user_answer):  # 检查答案
        # 根据模式确定要更新的字符
        mode = self.mode_var.get()

        try:
            if mode == "片-平":
                index = KATAKANA.index(self.question_label.cget("text"))
                target_char = KATAKANA[index]  # 统计片假名
            elif mode == "平-片":
                index = HIRAGANA.index(self.question_label.cget("text"))
                target_char = HIRAGANA[index]  # 统计平假名
            elif mode == "平-罗":
                index = HIRAGANA.index(self.question_label.cget("text"))
                target_char = HIRAGANA[index]  # 统计平假名
            elif mode == "罗-平":
                index = ROMAJI.index(self.question_label.cget("text"))
                target_char = HIRAGANA[index]  # 统计平假名
            elif mode == "片-罗":
                index = KATAKANA.index(self.question_label.cget("text"))
                target_char = KATAKANA[index]  # 统计片假名
            elif mode == "罗-片":
                index = ROMAJI.index(self.question_label.cget("text"))
                target_char = KATAKANA[index]  # 统计片假名
        except ValueError as e:
            print(f"查找字符时出错: {e}")
            print(f"当前模式: {mode}, 当前问题: {self.question_label.cget('text')}")
            return

        # 获取旧统计数据
        old_correct = self.correct_counts[target_char]['correct']
        old_total = self.correct_counts[target_char]['total']
        old_percentage = (old_correct / old_total * 100) if old_total > 0 else 0

        # 根据奖励模式更新统计
        increment = 3 if self.is_triple_mode else 1
        self.correct_counts[target_char]['total'] += increment
        is_correct = user_answer == self.current_answer
        if is_correct:
            self.correct_counts[target_char]['correct'] += increment

        # 反馈处理
        if is_correct:
            self.feedback_label.config(text="√", foreground="green")
            self.streak += 1
            if self.streak > self.high_score:
                self.high_score = self.streak
            self.streak_label.config(text=f"连胜: {self.streak}")
            self.high_score_label.config(text=f"最高纪录: {self.high_score}")
            # 答对时，正确按键变色
            for button in self.buttons.copy():  # 使用 copy 避免遍历过程中修改列表
                if button.winfo_exists():  # 检查按钮是否存在
                    if button.cget("text") == self.current_answer:
                        button.config(bootstyle="success")
                        break
        else:
            self.feedback_label.config(text="×", foreground="red")
            self.streak = 0
            self.streak_label.config(text=f"连胜: {self.streak}")
            # 高亮正确答案和错误答案
            for button in self.buttons.copy():  # 使用 copy 避免遍历过程中修改列表
                if button.winfo_exists():  # 检查按钮是否存在
                    if button.cget("text") == self.current_answer:
                        button.config(bootstyle="success")
                    if button.cget("text") == user_answer:
                        button.config(bootstyle="danger")

        # 计算新正确率
        new_correct = self.correct_counts[target_char]['correct']
        new_total = self.correct_counts[target_char]['total']
        new_percentage = (new_correct / new_total * 100) if new_total > 0 else 0

        # 输出正确率变化
        print(f"目标字符[{target_char}]：{old_percentage:.0f}%→{new_percentage:.0f}%")

        # 如果当前显示的是熟练度地图，则刷新它
        if self.proficiency_frame.winfo_ismapped():
            self.show_proficiency_map()
        self.root.after(2000, self.new_question)

    def get_combined_proficiency(self, char):  # 获取综合熟练度
        """汇总不同模式下对应假名的熟练度统计"""
        combined_correct = 0
        combined_total = 0
        # 假设所有相关字符都在 HIRAGANA + KATAKANA + ROMAJI 中
        all_chars = HIRAGANA + KATAKANA + ROMAJI
        for c in all_chars:
            stats = self.correct_counts[c]
            combined_correct += stats['correct']
            combined_total += stats['total']
        return combined_correct, combined_total

    def create_keyboard(self, char_rows):    # 创建键盘按钮布局
        self.char_rows = char_rows  # 保存字符行数据，供后续使用

        # 清除旧的键盘按钮
        for widget in self.keyboard_frame.winfo_children():
            widget.destroy()

        # 创建新的键盘按钮
        for row_num, row in enumerate(char_rows):
            for col_num, char in enumerate(row):
                if char != " ":
                    button = ttk.Button(
                        self.keyboard_frame,
                        text=char,
                        style="Custom.TButton",
                        command=lambda c=char: self.check_answer(c)
                    )
                    button.grid(row=row_num, column=col_num, padx=3, pady=3, sticky="nsew")
                    self.keyboard_frame.columnconfigure(col_num, weight=1)
                    self.keyboard_frame.rowconfigure(row_num, weight=1)
                    self.buttons.append(button)
                    # 绑定事件使按钮为正方形
                    button.bind("<Configure>", self.make_square)
                    # 绑定按钮点击动画
                    #button.bind("<ButtonPress-1>", lambda e, btn=button: self.animate_click(btn))

    def create_proficiency_button(self, char, row, col):  # 创建 proficiency 按钮
        # 计算正确率
        stats = self.correct_counts[char]
        total = stats['total']
        correct = stats['correct']
        percentage = (correct / total * 100) if total > 0 else 0

        # 创建自定义画布
        canvas = ttk.Canvas(self.proficiency_frame, width=100, height=30, highlightthickness=0)
        canvas.grid(row=row, column=col, padx=5, pady=5)

        # 设置画布背景颜色
        if self.dark_mode:
            bg_color = self.style.lookup("TFrame", "background")
        else:
            bg_color = "#f5f5f5"
        canvas.configure(background=bg_color)

        # 绘制电池外框
        canvas.create_rectangle(5, 5, 95, 35, outline="black", width=2)

        # 绘制电量背景（灰色）
        if not self.dark_mode:
            canvas.create_rectangle(7, 7, 93, 35, fill="lightgray", stipple="gray12", outline="")

        # 根据正确率绘制电量（覆盖灰色背景）
        fill_width = int(86 * (percentage / 100))  # 86 = 93-7
        fill_color = "green" if percentage >= 70 else "orange" if percentage >= 30 else "red"
        canvas.create_rectangle(7, 7, 7 + fill_width, 35, fill=fill_color, outline="")

        # 显示假名，使用白色字体
        text_color = "white" if self.dark_mode else "black"
        canvas.create_text(50, 15, text=char, font=(self.current_font, 12), fill=text_color)

    def show_proficiency_map(self):  # 显示熟练度地图
        # 仅隐藏练习相关组件
        components = [
            self.mode_frame, self.streak_label, self.high_score_label,
            self.question_label, self.keyboard_frame, self.feedback_label
        ]
        for component in components:
            # 记录 grid 布局参数
            self.grid_params[component] = component.grid_info()
            component.grid_remove()

        # 显示熟练度地图
        self.proficiency_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # 设置主窗口的行和列权重，确保熟练度框架能扩展
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)

        # 清除旧组件
        for widget in self.proficiency_frame.winfo_children():
            if isinstance(widget, ttk.Canvas) or (
                    isinstance(widget, ttk.Button) and widget != self.back_btn and widget != self.intensive_training_btn):
                widget.destroy()

        # 设置熟练度地图的布局
        max_columns = max(len(row) for row in HIRAGANA_ROWS)
        for i in range(max_columns):
            self.proficiency_frame.columnconfigure(i, weight=1, uniform="group1")
        for j in range(len(HIRAGANA_ROWS) + 2):
            self.proficiency_frame.rowconfigure(j, weight=1)

        # 根据当前模式确定要显示的字符行
        mode = self.mode_var.get()
        if mode in ["片-平", "片-罗", "罗-片"]:
            char_rows = KATAKANA_ROWS
        else:  # mode in ["平-罗", "平-片", "罗-平"]:
            char_rows = HIRAGANA_ROWS

        # 创建假名按键，行号从1开始，为标签留出第0行
        for row_num, row in enumerate(char_rows):
            for col_num, char in enumerate(row):
                if char != " ":
                    self.create_proficiency_button(char, row_num + 1, col_num)

        # 显示返回按钮
        self.back_btn.grid(row=len(HIRAGANA_ROWS) + 1, column=0, columnspan=max_columns, pady=10, sticky="s")

    def hide_proficiency_map(self):  # 隐藏熟练度地图
        self.proficiency_frame.grid_remove()

        # 恢复练习相关组件
        for component in self.grid_params:
            params = self.grid_params[component]
            component.grid(**params)

        # 重置布局权重
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)  # 恢复默认权重
        self.root.columnconfigure(2, weight=0)  # 恢复默认权重

    def create_tables(self):
        cursor = self.conn.cursor()
        # 创建连胜和最高纪录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streak_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                streak INTEGER DEFAULT 0,
                high_score INTEGER DEFAULT 0
            )
        ''')
        # 创建正确率统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proficiency_stats (
                char TEXT PRIMARY KEY,
                correct INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def load_stats_from_db(self):   # 从数据库加载统计数据
        cursor = self.conn.cursor()
        # 加载连胜和最高纪录
        cursor.execute('SELECT streak, high_score FROM streak_stats ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        if result:
            self.streak, self.high_score = result
        else:
            self.streak = 0
            self.high_score = 0
            cursor.execute('INSERT INTO streak_stats (streak, high_score) VALUES (?, ?)',
                           (self.streak, self.high_score))
            self.conn.commit()

        # 加载正确率统计
        cursor.execute('SELECT char, correct, total FROM proficiency_stats')
        rows = cursor.fetchall()
        self.correct_counts = {}
        for row in rows:
            char, correct, total = row
            self.correct_counts[char] = {'correct': correct, 'total': total}

    def save_stats_to_db(self):  # 保存统计数据到数据库
        cursor = self.conn.cursor()
        # 保存连胜和最高纪录
        cursor.execute('UPDATE streak_stats SET streak = ?, high_score = ? WHERE id = (SELECT MAX(id) FROM streak_stats)',
                       (self.streak, self.high_score))
        # 保存正确率统计
        for char, stats in self.correct_counts.items():
            cursor.execute('''
                INSERT OR REPLACE INTO proficiency_stats (char, correct, total)
                VALUES (?, ?, ?)
            ''', (char, stats['correct'], stats['total']))
        self.conn.commit()

    def get_font_path(self, font_name):  # 查找字体文件路径
        """
        根据字体名称查找字体文件路径。
        :param font_name: 字体名称。
        :return: 找到字体文件路径则返回该路径，否则返回 None。
        """
        import tkinter.font as tkfont
        import os

        # 定义常见字体目录
        font_dirs = [
            "C:\\Windows\\Fonts",  # Windows 字体目录
            os.path.expanduser("~/.fonts"),  # Linux 用户字体目录
            "/usr/share/fonts",  # Linux 系统字体目录
            "/usr/local/share/fonts"  # Linux 本地字体目录
        ]

        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for _, _, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf')):
                            font_file_path = os.path.join(os.path.dirname(font_dir), file)
                            try:
                                # 尝试使用字体文件创建字体对象
                                font = tkfont.Font(family=font_name, file=font_file_path)
                                if font.actual('family') == font_name:
                                    return font_file_path
                            except Exception:
                                continue
        return None

    def start_intensive_training(self): # 开始加强训练
        # 创建新窗口
        intensive_window = ttk.Toplevel(self.root)
        intensive_window.title("加强训练")
        intensive_window.geometry("1400x800")

        # 配置窗口的行列权重，使用 grid 布局
        intensive_window.columnconfigure(0, weight=2)
        intensive_window.rowconfigure(0, weight=2)
        intensive_window.rowconfigure(1, weight=6)

        # 获取熟练度最低且统计次数大于 1 次的前 10 个字符
        proficiency_scores = []
        for _, chars in SOUND_MAP.items():
            for char in chars:
                stats = self.correct_counts[char]
                total = stats['total']
                if total > 1:  # 统计次数大于 1 次
                    correct = stats['correct']
                    percentage = correct / total
                    proficiency_scores.append((char, percentage))

        proficiency_scores.sort(key=lambda x: x[1])
        top_10_chars = [char for char, _ in proficiency_scores[:10]]

        # 生成连连看字符列表
        char_list = []
        for char in top_10_chars:
            for _, chars in SOUND_MAP.items():
                if char in chars:
                    # 添加平假名、片假名、罗马字以及其中任意一个符号
                    char_list.extend(chars)
                    char_list.append(random.choice(chars))
                    break

        # 确保每个字符出现偶数次
        char_list *= 2
        random.shuffle(char_list)

        # 自动查找字体文件路径
        font_path = self.get_font_path(self.current_font)
        if font_path is None:
            font_path = 'simhei.ttf'  # 修正字体文件扩展名

        # 生成词云
        wordcloud_dict = {char: 1 / (i + 1) for i, char in enumerate(top_10_chars)}
        if not wordcloud_dict:
            print("没有足够的数据来生成词云，请进行更多练习。")
            return

        wc = WordCloud(font_path=font_path, background_color='white' if not self.dark_mode else self.style.lookup("TFrame", "background"), prefer_horizontal=1)
        wc.generate_from_frequencies(wordcloud_dict)

        # 显示词云
        fig = plt.Figure(figsize=(6, 2), dpi=100)

        # 设置图形背景颜色
        if self.dark_mode:
            fig.set_facecolor(self.style.lookup("TFrame", "background"))
        else:
            fig.set_facecolor("white")        

        ax = fig.add_subplot(111)
        ax.imshow(wc, interpolation='bilinear')
        ax.axis("off")
        canvas = FigureCanvasTkAgg(fig, master=intensive_window)
        canvas.draw()
        # 获取当前全局背景颜色
        if self.dark_mode:
            bg_color = self.style.lookup("TFrame", "background")
        else:
            bg_color = "#f5f5f5"
        # 设置画布对应 tkinter 组件的背景颜色
        canvas.get_tk_widget().config(background=bg_color)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="ew")



        # 生成连连看游戏布局
        game_frame = ttk.Frame(intensive_window)
        game_frame.grid(row=1, column=0, sticky="nsew")

        # 计算合适的行数和列数
        n = len(char_list)
        rows = int(np.sqrt(n))
        while n % rows != 0:
            rows -= 1
        cols = n // rows

        board = np.array(char_list).reshape(rows, cols)

        selected_button = [None, None]
        original_bg = intensive_window.cget("background")

        # 定义微软雅黑字体
        msyh_font = tkfont.Font(family="微软雅黑", size=12)

        # 创建一个新的样式
        style = ttk.Style()
        style.configure("CustomMSYH.TButton", font=msyh_font)

        def on_button_click(btn, char):
            nonlocal original_bg, selected_button
            if selected_button[0] is None:
                selected_button[0] = (btn, char)
                if btn.winfo_exists():
                    btn.config(bootstyle="info")
            elif selected_button[1] is None:
                # 禁止自己连自己
                if btn == selected_button[0][0]:
                    return
                selected_button[1] = (btn, char)
                if btn.winfo_exists():
                    btn.config(bootstyle="info")
                match_success = False
                for _, chars in SOUND_MAP.items():
                    if selected_button[0][1] in chars and selected_button[1][1] in chars:
                        if selected_button[0][0].winfo_exists():
                            selected_button[0][0].destroy()
                        if selected_button[1][0].winfo_exists():
                            selected_button[1][0].destroy()
                        # 匹配成功，窗口变绿一秒
                        intensive_window.configure(background="green")
                        intensive_window.after(1000, lambda: intensive_window.configure(background=original_bg))
                        match_success = True
                        break
                if not match_success:
                    # 匹配失败，窗口变红一秒
                    intensive_window.configure(background="red")
                    intensive_window.after(1000, lambda: intensive_window.configure(background=original_bg))
                    if selected_button[0][0].winfo_exists():
                        selected_button[0][0].config(bootstyle="Custom.TButton")
                    if selected_button[1][0].winfo_exists():
                        selected_button[1][0].config(bootstyle="Custom.TButton")
                selected_button = [None, None]

        for i in range(rows):
            game_frame.rowconfigure(i, weight=1)
            for j in range(cols):
                game_frame.columnconfigure(j, weight=1)
                char = board[i][j]
                btn = ttk.Button(
                    game_frame,
                    text=char,
                    style="CustomMSYH.TButton"
                )
                btn.config(command=lambda b=btn, c=char: on_button_click(b, c))
                btn.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")


if __name__ == "__main__":
    root = ttk.Window()
    app = KanaPracticeApp(root)
    root.mainloop()