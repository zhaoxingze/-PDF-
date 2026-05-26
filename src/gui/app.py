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


class TranslatorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(GUI_CONFIG["window_title"])
        self.root.geometry(GUI_CONFIG["window_size"])
        self.root.resizable(True, True)

        # 状态变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")

        # 翻译方式
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
        self._setup_ui()
        self._check_queue()

    def _setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, text="PDF论文翻译工具", font=("Microsoft YaHei", 14, "bold")).pack(pady=(0, 10))

        # 创建带滚动条的画布
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 使用Notebook创建标签页
        notebook = ttk.Notebook(scrollable_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 翻译设置页面
        translate_frame = ttk.Frame(notebook, padding="10")
        notebook.add(translate_frame, text="翻译设置")
        self._setup_translate_tab(translate_frame)

        # OCR设置页面
        ocr_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ocr_frame, text="OCR设置")
        self._setup_ocr_tab(ocr_frame)

        # 进度和日志
        progress_frame = ttk.Frame(scrollable_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W, pady=(3, 0))

        # 日志区域
        log_frame = ttk.LabelFrame(scrollable_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X)
        self.start_button = ttk.Button(button_frame, text="开始翻译", command=self._start_translation)
        self.start_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

        # 布局画布和滚动条
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _setup_translate_tab(self, parent):
        # 翻译方式选择
        ttk.Label(parent, text="翻译方式", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W)

        type_frame = ttk.Frame(parent)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(type_frame, text="Google翻译（免费，无需注册）", variable=self.translator_type_var, value="google").pack(anchor=tk.W)
        ttk.Radiobutton(type_frame, text="百度翻译API（需要API密钥）", variable=self.translator_type_var, value="baidu").pack(anchor=tk.W)
        ttk.Radiobutton(type_frame, text="本地翻译（需下载模型约300MB）", variable=self.translator_type_var, value="local").pack(anchor=tk.W)

        # 本地模型选择
        local_frame = ttk.LabelFrame(parent, text="本地模型设置", padding="10")
        local_frame.pack(fill=tk.X, pady=5)

        frame1 = ttk.Frame(local_frame)
        frame1.pack(fill=tk.X, pady=3)
        ttk.Label(frame1, text="模型:").pack(side=tk.LEFT)
        model_combo = ttk.Combobox(frame1, textvariable=self.local_model_var, width=40, state="readonly")
        model_combo['values'] = [
            "Helsinki-NLP/opus-mt-en-zh",
        ]
        model_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(local_frame, text="说明: 首次使用会自动下载模型，需要网络连接", font=("Microsoft YaHei", 8)).pack(anchor=tk.W)
        ttk.Label(local_frame, text="提示: 如果有NVIDIA显卡，会自动使用GPU加速", font=("Microsoft YaHei", 8)).pack(anchor=tk.W)

        # 百度翻译API配置
        baidu_frame = ttk.LabelFrame(parent, text="百度翻译API设置", padding="10")
        baidu_frame.pack(fill=tk.X, pady=5)
        ttk.Label(baidu_frame, text="获取方式: https://fanyi-api.baidu.com/ (标准版免费)", font=("Microsoft YaHei", 8)).pack(anchor=tk.W)

        frame2 = ttk.Frame(baidu_frame)
        frame2.pack(fill=tk.X, pady=3)
        ttk.Label(frame2, text="APP ID:").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(frame2, textvariable=self.translate_app_id_var, width=40).grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(frame2, text="密钥:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(frame2, textvariable=self.translate_secret_var, width=40, show="*").grid(row=1, column=1, padx=5, pady=3)

        # 文件选择
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(parent, text="文件选择", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W)

        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_frame, text="输入PDF:").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(file_frame, textvariable=self.input_path, width=50).grid(row=0, column=1, padx=5, pady=3)
        ttk.Button(file_frame, text="浏览", command=self._browse_input).grid(row=0, column=2, pady=3)

        ttk.Label(file_frame, text="输出PDF:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(file_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, padx=5, pady=3)
        ttk.Button(file_frame, text="浏览", command=self._browse_output).grid(row=1, column=2, pady=3)

    def _setup_ocr_tab(self, parent):
        ttk.Label(parent, text="OCR设置（用于扫描版PDF）", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(parent, text="如果PDF无法提取文本，需要启用OCR识别", font=("Microsoft YaHei", 8)).pack(anchor=tk.W)

        ttk.Checkbutton(parent, text="启用OCR识别", variable=self.use_ocr_var).pack(anchor=tk.W, pady=5)

        type_frame = ttk.Frame(parent)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="OCR方式:").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="百度OCR API", variable=self.ocr_type_var, value="baidu").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="本地Tesseract", variable=self.ocr_type_var, value="local").pack(side=tk.LEFT, padx=10)

        ocr_frame = ttk.LabelFrame(parent, text="百度OCR配置", padding="10")
        ocr_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ocr_frame, text="获取方式: https://cloud.baidu.com/product/ocr", font=("Microsoft YaHei", 8)).pack(anchor=tk.W)

        frame = ttk.Frame(ocr_frame)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(frame, textvariable=self.ocr_api_key_var, width=40).grid(row=0, column=1, padx=5, pady=3)
        ttk.Label(frame, text="Secret Key:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(frame, textvariable=self.ocr_secret_var, width=40, show="*").grid(row=1, column=1, padx=5, pady=3)

        ttk.Button(parent, text="保存所有配置", command=self._save_config).pack(anchor=tk.W, pady=10)

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

    def _browse_input(self):
        path = filedialog.askopenfilename(title="选择PDF文件", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_path.set(path)
            base, ext = os.path.splitext(path)
            self.output_path.set(f"{base}_translated{ext}")

    def _browse_output(self):
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

        if translator_type == "baidu":
            app_id = self.translate_app_id_var.get().strip()
            secret_key = self.translate_secret_var.get().strip()
            if not app_id or not secret_key:
                messagebox.showerror("错误", "请先配置百度翻译API的APP ID和密钥")
                return

        if not self.input_path.get():
            messagebox.showerror("错误", "请选择输入PDF文件")
            return
        if not self.output_path.get():
            messagebox.showerror("错误", "请选择输出PDF文件")
            return
        if not os.path.exists(self.input_path.get()):
            messagebox.showerror("错误", "输入文件不存在")
            return

        self.start_button.config(state="disabled")
        self.progress_var.set(0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

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
                        for span in block.spans:
                            texts.append(span.text)
                    self.queue.put(("log", f"第{page_num + 1}页: 提取{len(texts)}段文本"))

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
