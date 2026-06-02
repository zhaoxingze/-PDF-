import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from queue import Queue
import os
import sys
import traceback
import time
import fitz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import GUI_CONFIG, FONT_CONFIG, API_CONFIG, save_api_config, get_translate_config, get_ocr_config
from src.core.pdf_reader import PDFReader
from src.core.translator import create_translator
from src.core.pdf_writer import PDFWriter
from src.core.ocr import OCRFactory
from src.core.docx_reader import DocxReader
from src.core.docx_writer import DocxWriter


class TranslatorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(GUI_CONFIG["window_title"])
        self.root.geometry(GUI_CONFIG["window_size"])
        self.root.minsize(820, 700)
        self.root.resizable(True, True)
        self.colors = {
            "bg": "#f5f7fb",
            "panel": "#ffffff",
            "panel_soft": "#eef4ff",
            "text": "#172033",
            "muted": "#667085",
            "accent": "#2563eb",
            "accent_dark": "#1d4ed8",
            "border": "#d7deea",
            "success": "#16803c",
        }
        self.root.configure(bg=self.colors["bg"])

        # 状态变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")

        # 翻译方式
        self.file_type_var = tk.StringVar(value="pdf")
        self.translator_type_var = tk.StringVar(value=API_CONFIG.get("translator_type", "local"))
        self.local_model_var = tk.StringVar(value=API_CONFIG.get("local_model", "Helsinki-NLP/opus-mt-en-zh"))

        # 百度翻译API配置
        self.translate_app_id_var = tk.StringVar(value=API_CONFIG.get("baidu_translate_app_id", ""))
        self.translate_secret_var = tk.StringVar(value=API_CONFIG.get("baidu_translate_secret_key", ""))

        # OCR配置
        self.use_ocr_var = tk.BooleanVar(value=API_CONFIG.get("use_ocr", False))
        self.ocr_type_var = tk.StringVar(value=API_CONFIG.get("ocr_type", "baidu"))
        self.ocr_api_key_var = tk.StringVar(value=API_CONFIG.get("baidu_ocr_api_key", ""))
        self.ocr_secret_var = tk.StringVar(value=API_CONFIG.get("baidu_ocr_secret_key", ""))

        self.queue = Queue()
        self._setup_style()
        self._setup_ui()
        self._check_queue()

    def _setup_style(self):
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        default_font = ("Microsoft YaHei", 10)
        self.root.option_add("*Font", default_font)

        self.style.configure("App.TFrame", background=self.colors["bg"])
        self.style.configure("Panel.TFrame", background=self.colors["panel"])
        self.style.configure("Soft.TFrame", background=self.colors["panel_soft"])
        self.style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        self.style.configure("App.TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Microsoft YaHei", 18, "bold"))
        self.style.configure("Subtitle.TLabel", background=self.colors["bg"], foreground=self.colors["muted"], font=("Microsoft YaHei", 9))
        self.style.configure("Section.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Microsoft YaHei", 11, "bold"))
        self.style.configure("Muted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Microsoft YaHei", 9))
        self.style.configure("Status.TLabel", background=self.colors["panel_soft"], foreground=self.colors["accent_dark"], font=("Microsoft YaHei", 9, "bold"))
        self.style.configure("Card.TLabelframe", background=self.colors["panel"], bordercolor=self.colors["border"], relief=tk.SOLID)
        self.style.configure("Card.TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["text"], font=("Microsoft YaHei", 11, "bold"))
        self.style.configure("TRadiobutton", background=self.colors["panel"], foreground=self.colors["text"])
        self.style.configure("TCheckbutton", background=self.colors["panel"], foreground=self.colors["text"])
        self.style.configure("TEntry", fieldbackground="#ffffff", bordercolor=self.colors["border"], lightcolor=self.colors["border"])
        self.style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=self.colors["border"])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(18, 8), font=("Microsoft YaHei", 10))
        self.style.map("TNotebook.Tab", background=[("selected", self.colors["panel"])])
        self.style.configure("TButton", padding=(12, 7), font=("Microsoft YaHei", 10))
        self.style.configure("Primary.TButton", padding=(18, 9), font=("Microsoft YaHei", 10, "bold"), foreground="#ffffff", background=self.colors["accent"])
        self.style.map("Primary.TButton", background=[("active", self.colors["accent_dark"]), ("disabled", "#9db8f9")])
        self.style.configure("Horizontal.TProgressbar", troughcolor="#e8edf6", background=self.colors["accent"], bordercolor="#e8edf6", lightcolor=self.colors["accent"], darkcolor=self.colors["accent"])

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=(18, 16), style="App.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main_frame, style="App.TFrame")
        header.pack(fill=tk.X, pady=(0, 14))

        title_area = ttk.Frame(header, style="App.TFrame")
        title_area.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_area, text="PDF / Word 翻译工具", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_area,
            text="保持文档顺序与排版，减少乱码和重复翻译",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(3, 0))

        status_box = ttk.Frame(header, padding=(14, 8), style="Soft.TFrame")
        status_box.pack(side=tk.RIGHT, padx=(12, 0))
        ttk.Label(status_box, textvariable=self.status_var, style="Status.TLabel").pack()

        # 创建带滚动条的画布
        canvas = tk.Canvas(main_frame, bg=self.colors["bg"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="App.TFrame")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 使用Notebook创建标签页
        self.notebook = ttk.Notebook(scrollable_frame)
        notebook = self.notebook
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        # 翻译设置页面
        translate_frame = ttk.Frame(notebook, padding=(16, 14), style="Panel.TFrame")
        notebook.add(translate_frame, text="翻译设置")
        self._setup_translate_tab(translate_frame)

        # OCR设置页面
        self.ocr_frame = ttk.Frame(notebook, padding=(16, 14), style="Panel.TFrame")
        notebook.add(self.ocr_frame, text="OCR设置")
        self._setup_ocr_tab(self.ocr_frame)
        self._on_file_type_change()

        # 进度和日志
        progress_frame = ttk.LabelFrame(scrollable_frame, text="运行状态", padding=(14, 10), style="Card.TLabelframe")
        progress_frame.pack(fill=tk.X, pady=(0, 12))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(anchor=tk.W)

        # 日志区域
        log_frame = ttk.LabelFrame(scrollable_frame, text="日志", padding=(10, 8), style="Card.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        self.log_text = tk.Text(
            log_frame,
            height=8,
            state=tk.DISABLED,
            bg="#101828",
            fg="#e6edf8",
            insertbackground="#e6edf8",
            relief=tk.FLAT,
            padx=10,
            pady=8,
            font=("Consolas", 9),
            wrap=tk.WORD,
        )
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 按钮
        button_frame = ttk.Frame(scrollable_frame, style="App.TFrame")
        button_frame.pack(fill=tk.X)
        self.start_button = ttk.Button(button_frame, text="开始翻译", style="Primary.TButton", command=self._start_translation)
        self.start_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

        # 布局画布和滚动条
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _setup_translate_tab(self, parent):
        type_card = ttk.LabelFrame(parent, text="文档类型", padding=(14, 10), style="Card.TLabelframe")
        type_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Radiobutton(type_card, text="PDF 翻译", variable=self.file_type_var, value="pdf", command=self._on_file_type_change).pack(side=tk.LEFT, padx=(0, 24))
        ttk.Radiobutton(type_card, text="Word 翻译", variable=self.file_type_var, value="docx", command=self._on_file_type_change).pack(side=tk.LEFT)

        translator_card = ttk.LabelFrame(parent, text="翻译方式", padding=(14, 10), style="Card.TLabelframe")
        translator_card.pack(fill=tk.X, pady=(0, 12))
        translator_card.columnconfigure(0, weight=1)
        translator_card.columnconfigure(1, weight=1)
        translator_card.columnconfigure(2, weight=1)
        ttk.Radiobutton(translator_card, text="Google 翻译", variable=self.translator_type_var, value="google").grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=3)
        ttk.Radiobutton(translator_card, text="百度翻译 API", variable=self.translator_type_var, value="baidu").grid(row=0, column=1, sticky=tk.W, padx=(0, 12), pady=3)
        ttk.Radiobutton(translator_card, text="本地翻译模型", variable=self.translator_type_var, value="local").grid(row=0, column=2, sticky=tk.W, pady=3)

        model_card = ttk.LabelFrame(parent, text="模型与 API", padding=(14, 10), style="Card.TLabelframe")
        model_card.pack(fill=tk.X, pady=(0, 12))
        model_card.columnconfigure(1, weight=1)

        ttk.Label(model_card, text="本地模型", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 10))
        model_combo = ttk.Combobox(model_card, textvariable=self.local_model_var, state="readonly")
        model_combo["values"] = ["Helsinki-NLP/opus-mt-en-zh"]
        model_combo.grid(row=0, column=1, sticky=tk.EW, pady=(0, 8))

        ttk.Label(model_card, text="APP ID", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 10))
        ttk.Entry(model_card, textvariable=self.translate_app_id_var).grid(row=1, column=1, sticky=tk.EW, pady=(0, 8))

        ttk.Label(model_card, text="密钥", style="Muted.TLabel").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(model_card, textvariable=self.translate_secret_var, show="*").grid(row=2, column=1, sticky=tk.EW)

        ttk.Label(
            model_card,
            text="Google 可直接使用；百度需填写 API；本地模型首次运行会下载模型。",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        file_card = ttk.LabelFrame(parent, text="文件路径", padding=(14, 10), style="Card.TLabelframe")
        file_card.pack(fill=tk.X)
        file_card.columnconfigure(1, weight=1)

        self.input_file_label = ttk.Label(file_card, text="输入 PDF", style="Muted.TLabel")
        self.input_file_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 8))
        ttk.Entry(file_card, textvariable=self.input_path).grid(row=0, column=1, sticky=tk.EW, pady=(0, 8))
        ttk.Button(file_card, text="浏览", command=self._browse_input).grid(row=0, column=2, padx=(10, 0), pady=(0, 8))

        self.output_file_label = ttk.Label(file_card, text="输出 PDF", style="Muted.TLabel")
        self.output_file_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(file_card, textvariable=self.output_path).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(file_card, text="浏览", command=self._browse_output).grid(row=1, column=2, padx=(10, 0))

    def _setup_ocr_tab(self, parent):
        intro_card = ttk.LabelFrame(parent, text="扫描版 PDF", padding=(14, 10), style="Card.TLabelframe")
        intro_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Checkbutton(intro_card, text="启用 OCR 识别", variable=self.use_ocr_var).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(intro_card, text="当 PDF 没有可提取文本时，OCR 会先识别图片文字再翻译。", style="Muted.TLabel").pack(anchor=tk.W)

        type_card = ttk.LabelFrame(parent, text="OCR 方式", padding=(14, 10), style="Card.TLabelframe")
        type_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Radiobutton(type_card, text="百度 OCR API", variable=self.ocr_type_var, value="baidu").pack(side=tk.LEFT, padx=(0, 24))
        ttk.Radiobutton(type_card, text="本地 Tesseract", variable=self.ocr_type_var, value="local").pack(side=tk.LEFT)

        api_card = ttk.LabelFrame(parent, text="百度 OCR 配置", padding=(14, 10), style="Card.TLabelframe")
        api_card.pack(fill=tk.X, pady=(0, 12))
        api_card.columnconfigure(1, weight=1)
        ttk.Label(api_card, text="API Key", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 8))
        ttk.Entry(api_card, textvariable=self.ocr_api_key_var).grid(row=0, column=1, sticky=tk.EW, pady=(0, 8))
        ttk.Label(api_card, text="Secret Key", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(api_card, textvariable=self.ocr_secret_var, show="*").grid(row=1, column=1, sticky=tk.EW)
        ttk.Label(api_card, text="百度 OCR 获取地址: https://cloud.baidu.com/product/ocr", style="Muted.TLabel").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        ttk.Button(parent, text="保存配置", command=self._save_config).pack(anchor=tk.W)

    def _log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _save_config(self):
        config = {
            "translator_type": self.translator_type_var.get(),
            "local_model": self.local_model_var.get(),
            "baidu_translate_app_id": self.translate_app_id_var.get().strip(),
            "baidu_translate_secret_key": self.translate_secret_var.get().strip(),
            "baidu_ocr_api_key": self.ocr_api_key_var.get().strip(),
            "baidu_ocr_secret_key": self.ocr_secret_var.get().strip(),
            "use_ocr": self.use_ocr_var.get(),
            "ocr_type": self.ocr_type_var.get(),
        }
        save_api_config(config)
        messagebox.showinfo("成功", "配置已保存")

    def _on_file_type_change(self):
        """切换文件类型时更新UI"""
        file_type = self.file_type_var.get()
        file_label = "Word" if file_type == "docx" else "PDF"
        if hasattr(self, "input_file_label"):
            self.input_file_label.configure(text=f"输入 {file_label}")
        if hasattr(self, "output_file_label"):
            self.output_file_label.configure(text=f"输出 {file_label}")

        if file_type == "docx":
            if hasattr(self, "ocr_frame"):
                self.notebook.hide(self.ocr_frame)
        else:
            if hasattr(self, "ocr_frame") and str(self.ocr_frame) not in self.notebook.tabs():
                self.notebook.add(self.ocr_frame, text="OCR设置")

    def _browse_input(self):
        file_type = self.file_type_var.get()
        if file_type == "docx":
            path = filedialog.askopenfilename(title="选择Word文件", filetypes=[("Word files", "*.docx")])
        else:
            path = filedialog.askopenfilename(title="选择PDF文件", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_path.set(path)
            base, ext = os.path.splitext(path)
            self.output_path.set(f"{base}_translated{ext}")

    def _browse_output(self):
        file_type = self.file_type_var.get()
        if file_type == "docx":
            path = filedialog.asksaveasfilename(
                title="保存翻译后的Word",
                defaultextension=".docx",
                filetypes=[("Word files", "*.docx")],
                initialfile=os.path.basename(self.output_path.get()) if self.output_path.get() else "translated.docx"
            )
        else:
            path = filedialog.asksaveasfilename(
                title="保存翻译后的PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=os.path.basename(self.output_path.get()) if self.output_path.get() else "translated.pdf"
            )
        if path:
            self.output_path.set(path)

    def _start_translation(self):
        self._save_config()

        translator_type = self.translator_type_var.get()
        file_type = self.file_type_var.get()

        if translator_type == "baidu":
            app_id = self.translate_app_id_var.get().strip()
            secret_key = self.translate_secret_var.get().strip()
            if not app_id or not secret_key:
                messagebox.showerror("错误", "请先配置百度翻译API的APP ID和密钥")
                return

        file_label = "Word" if file_type == "docx" else "PDF"
        if not self.input_path.get():
            messagebox.showerror("错误", f"请选择输入{file_label}文件")
            return
        if not self.output_path.get():
            messagebox.showerror("错误", f"请选择输出{file_label}文件")
            return
        if not os.path.exists(self.input_path.get()):
            messagebox.showerror("错误", "输入文件不存在")
            return

        self.start_button.config(state="disabled")
        self.progress_var.set(0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        if file_type == "docx":
            thread = threading.Thread(target=self._translate_docx_worker, daemon=True)
        else:
            thread = threading.Thread(target=self._translate_worker, daemon=True)
        thread.start()

    def _translate_worker(self):
        try:
            input_path = self.input_path.get()
            output_path = self.output_path.get()
            translator_type = self.translator_type_var.get()

            self.queue.put(("log", f"输入: {input_path}"))
            self.queue.put(("log", f"输出: {output_path}"))
            self.queue.put(("log", f"翻译方式: {translator_type}"))

            # 加载PDF
            self.queue.put(("status", "正在加载PDF..."))
            reader = PDFReader(input_path)
            total_pages = reader.get_page_count()
            self.queue.put(("log", f"PDF共 {total_pages} 页"))

            # 检测是否需要OCR
            use_ocr = self.use_ocr_var.get()
            is_scanned = reader.is_scanned_pdf()
            self.queue.put(("log", f"扫描版PDF: {'是' if is_scanned else '否'}"))

            if is_scanned and not use_ocr:
                self.queue.put(("log", "警告: 检测到扫描版PDF，但未启用OCR"))
                self.queue.put(("error", "检测到扫描版PDF\n请在OCR设置中启用OCR识别"))
                return

            # 初始化翻译器
            self.queue.put(("status", "正在初始化翻译..."))

            if translator_type == "baidu":
                app_id = self.translate_app_id_var.get().strip()
                secret_key = self.translate_secret_var.get().strip()
                translator = create_translator("baidu", app_id=app_id, secret_key=secret_key)
            elif translator_type == "local":
                model_name = self.local_model_var.get()
                translator = create_translator("local", model_name=model_name)
                self.queue.put(("log", f"本地模型: {model_name}"))
                self.queue.put(("log", "首次使用需要下载模型，请稍候..."))
            else:  # google
                translator = create_translator("google")
                self.queue.put(("log", "使用Google翻译"))

            # 测试翻译
            self.queue.put(("log", "测试翻译..."))
            test_result = translator.test_connection()
            self.queue.put(("log", f"测试结果: {test_result}"))
            if test_result.startswith("["):
                error_msg = (
                    f"翻译测试失败: {test_result}\n\n"
                    "解决方案：\n"
                    "1. 检查网络连接\n"
                    "2. 尝试使用VPN/代理\n"
                    "3. 切换到其他翻译方式"
                )
                self.queue.put(("error", error_msg))
                return
            self.queue.put(("log", f"翻译正常: Hello -> {test_result}"))

            # 初始化OCR（如果需要）
            ocr = None
            if use_ocr and is_scanned:
                self.queue.put(("status", "正在初始化OCR..."))
                ocr_config = get_ocr_config()
                ocr_type = ocr_config.pop("ocr_type")
                ocr = OCRFactory.create(ocr_type, **ocr_config)
                self.queue.put(("log", f"OCR方式: {ocr_type}"))

            # 初始化写入器
            writer = PDFWriter(reader.doc, FONT_CONFIG["default_font"])

            total_texts = 0
            failed_texts = 0
            start_time = time.time()

            # 逐页处理
            for page_num in range(total_pages):
                progress = (page_num / total_pages) * 100
                self.queue.put(("progress", progress))

                texts = []
                blocks = []

                if use_ocr and is_scanned:
                    self.queue.put(("status", f"OCR识别第{page_num + 1}页..."))
                    image_bytes = reader.get_page_image(page_num)
                    ocr_text = ocr.recognize(image_bytes)
                    if ocr_text and not ocr_text.startswith("["):
                        texts = [line.strip() for line in ocr_text.split("\n") if line.strip()]
                        self.queue.put(("log", f"第{page_num + 1}页OCR: {len(texts)}行"))
                    else:
                        self.queue.put(("log", f"第{page_num + 1}页OCR失败: {ocr_text}"))
                else:
                    blocks = reader.extract_page_blocks(page_num)
                    for block in blocks:
                        texts.append(block.merged_text)
                    self.queue.put(("log", f"第{page_num + 1}页: 提取{len(blocks)}个文本块"))

                if not texts:
                    self.queue.put(("log", f"第{page_num + 1}页: 无文本，跳过"))
                    continue

                # 显示前3段原文
                for i, t in enumerate(texts[:3]):
                    self.queue.put(("log", f"  原文{i+1}: {t[:50]}..."))

                total_texts += len(texts)
                elapsed = time.time() - start_time
                speed = total_texts / elapsed if elapsed > 0 else 0
                self.queue.put(("status", f"翻译第{page_num + 1}/{total_pages}页 | {total_texts}段 | {speed:.1f}段/秒"))

                # 翻译
                translated = translator.translate_batch(texts)

                # 显示前3段译文
                for i, t in enumerate(translated[:3]):
                    if t and not t.startswith("["):
                        self.queue.put(("log", f"  译文{i+1}: {t[:50]}..."))

                for t in translated:
                    if t.startswith("["):
                        failed_texts += 1

                # 写入
                if use_ocr and is_scanned:
                    self._write_ocr_page(writer, page_num, texts, translated)
                    self.queue.put(("log", f"第{page_num + 1}页: OCR模式写入完成"))
                else:
                    writer.replace_text_on_page(page_num, blocks, translated)
                    self.queue.put(("log", f"第{page_num + 1}页: 文本替换完成"))

            # 保存
            self.queue.put(("status", "正在保存..."))
            writer.save(output_path)
            self.queue.put(("log", f"文件已保存: {output_path}"))

            elapsed = time.time() - start_time
            self.queue.put(("progress", 100))
            self.queue.put(("log", f"\n翻译完成! {total_texts}段, 失败{failed_texts}, 耗时{elapsed:.1f}秒"))
            self.queue.put(("complete", f"翻译完成！\n\n翻译: {total_texts}段\n失败: {failed_texts}\n耗时: {elapsed:.1f}秒\n\n输出: {output_path}"))

        except Exception as e:
            error_detail = traceback.format_exc()
            self.queue.put(("log", f"错误: {str(e)}"))
            self.queue.put(("log", error_detail))
            self.queue.put(("error", f"翻译失败: {str(e)}"))

    def _translate_docx_worker(self):
        """Word文档翻译工作线程"""
        try:
            input_path = self.input_path.get()
            output_path = self.output_path.get()
            translator_type = self.translator_type_var.get()

            self.queue.put(("log", f"输入: {input_path}"))
            self.queue.put(("log", f"输出: {output_path}"))
            self.queue.put(("log", f"翻译方式: {translator_type}"))

            # 加载Word文档
            self.queue.put(("status", "正在加载Word文档..."))
            reader = DocxReader(input_path)
            paragraphs = reader.extract_paragraphs()
            total_paragraphs = len(paragraphs)
            self.queue.put(("log", f"Word文档共 {total_paragraphs} 个段落"))

            if total_paragraphs == 0:
                self.queue.put(("error", "文档中没有可翻译的文本"))
                return

            # 初始化翻译器
            self.queue.put(("status", "正在初始化翻译..."))
            if translator_type == "baidu":
                app_id = self.translate_app_id_var.get().strip()
                secret_key = self.translate_secret_var.get().strip()
                translator = create_translator("baidu", app_id=app_id, secret_key=secret_key)
            elif translator_type == "local":
                model_name = self.local_model_var.get()
                translator = create_translator("local", model_name=model_name)
                self.queue.put(("log", f"本地模型: {model_name}"))
                self.queue.put(("log", "首次使用需要下载模型，请稍候..."))
            else:
                translator = create_translator("google")
                self.queue.put(("log", "使用Google翻译"))

            # 测试翻译
            self.queue.put(("log", "测试翻译..."))
            test_result = translator.test_connection()
            self.queue.put(("log", f"测试结果: {test_result}"))
            if test_result.startswith("["):
                error_msg = (
                    f"翻译测试失败: {test_result}\n\n"
                    "解决方案：\n"
                    "1. 检查网络连接\n"
                    "2. 尝试使用VPN/代理\n"
                    "3. 切换到其他翻译方式"
                )
                self.queue.put(("error", error_msg))
                return
            self.queue.put(("log", f"翻译正常: Hello -> {test_result}"))

            # 提取文本
            texts = [p.text for p in paragraphs]
            start_time = time.time()

            # 显示前3段原文
            for i, t in enumerate(texts[:3]):
                self.queue.put(("log", f"  原文{i+1}: {t[:50]}..."))

            # 分批翻译
            self.queue.put(("status", f"翻译中... 共{total_paragraphs}段"))
            translated = translator.translate_batch(texts)

            # 统计失败
            failed = sum(1 for t in translated if t.startswith("["))

            # 显示前3段译文
            for i, t in enumerate(translated[:3]):
                if t and not t.startswith("["):
                    self.queue.put(("log", f"  译文{i+1}: {t[:50]}..."))

            # 写入
            self.queue.put(("status", "正在写入Word文档..."))
            writer = DocxWriter(input_path)
            writer.replace_paragraphs(paragraphs, translated)
            writer.save(output_path)
            self.queue.put(("log", f"文件已保存: {output_path}"))

            elapsed = time.time() - start_time
            self.queue.put(("progress", 100))
            self.queue.put(("log", f"\n翻译完成! {total_paragraphs}段, 失败{failed}, 耗时{elapsed:.1f}秒"))
            self.queue.put(("complete", f"翻译完成！\n\n翻译: {total_paragraphs}段\n失败: {failed}\n耗时: {elapsed:.1f}秒\n\n输出: {output_path}"))

        except Exception as e:
            error_detail = traceback.format_exc()
            self.queue.put(("log", f"错误: {str(e)}"))
            self.queue.put(("log", error_detail))
            self.queue.put(("error", f"翻译失败: {str(e)}"))

    def _write_ocr_page(self, writer, page_num, original_texts, translated_texts):
        """OCR模式写入：在页面底部添加翻译文本"""
        page = writer.doc[page_num]
        rect = page.rect

        translated_lines = []
        for orig, trans in zip(original_texts, translated_texts):
            if trans and not trans.startswith("["):
                translated_lines.append(trans)

        if not translated_lines:
            return

        margin = 40
        text_area_height = min(len(translated_lines) * 15 + 20, rect.height * 0.4)
        bg_rect = fitz.Rect(
            margin,
            rect.height - text_area_height - margin,
            rect.width - margin,
            rect.height - margin
        )

        shape = page.new_shape()
        shape.draw_rect(bg_rect)
        shape.finish(color=(1, 1, 1), fill=(1, 1, 1))
        shape.commit()

        text_rect = fitz.Rect(
            margin + 10,
            rect.height - text_area_height - margin + 10,
            rect.width - margin - 10,
            rect.height - margin - 10
        )

        full_text = "\n".join(translated_lines)

        page.insert_textbox(
            text_rect,
            full_text,
            fontname="china-s",
            fontsize=9,
            color=(0, 0, 0),
            align=fitz.TEXT_ALIGN_LEFT,
        )

    def _check_queue(self):
        while not self.queue.empty():
            msg_type, msg_data = self.queue.get()

            if msg_type == "progress":
                self.progress_var.set(msg_data)
            elif msg_type == "status":
                self.status_var.set(msg_data)
            elif msg_type == "log":
                self._log(msg_data)
            elif msg_type == "complete":
                messagebox.showinfo("完成", msg_data)
                self.start_button.config(state="normal")
                self.progress_var.set(100)
            elif msg_type == "error":
                messagebox.showerror("错误", msg_data)
                self.start_button.config(state="normal")

        self.root.after(100, self._check_queue)

    def run(self):
        self.root.mainloop()
