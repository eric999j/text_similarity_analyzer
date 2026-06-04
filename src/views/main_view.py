import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ..viewmodels.main_viewmodel import MainViewModel

# Handle DnD import gracefully
try:
    from tkinterdnd2 import DND_FILES
except ImportError:
    DND_FILES = None

class MainView(ttk.Frame):
    def __init__(self, root, viewmodel):
        super().__init__(root, padding="10")
        self.root = root
        self.viewmodel = viewmodel
        
        # Inject thread-safe UI dispatcher
        # This ensures background threads in ViewModel can update UI safely
        self.viewmodel.ui_callback = lambda action: self.root.after(0, action)
        
        # Bind plot callback
        self.viewmodel.on_show_frequency_plot = self.show_frequency_plot_window
        self._text_change_after_id = None
        
        self.pack(fill=tk.BOTH, expand=True)
        
        # Font settings
        self.font_style = ("Microsoft JhengHei", 10)
        
        self.create_widgets()
        self.setup_bindings()

    def _setup_dnd(self, widget, callback):
        if DND_FILES is None:
            return
            
        try:
            # Check if root supports DND (it might be a standard Tk root)
            if not hasattr(self.root, 'drop_target_register'):
                return

            widget.drop_target_register(DND_FILES)
            widget.dnd_bind('<<Drop>>', callback)
        except Exception as e:
            # Just ignore if DND fails setup, don't crash the UI
            print(f"Debug: DnD setup skipped or failed: {e}")

    def _handle_drop_text(self, event, text_widget, view_model_var):
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if not os.path.isfile(file_path):
                return
            
            # Basic content check
            _, ext = os.path.splitext(file_path)
            binary_exts = self.viewmodel.config_model.binary_extensions
            if ext.lower() in binary_exts:
                messagebox.showerror("格式錯誤 (Format Error)", "此檔案似乎不是純文字檔，無法載入。\nThis file appears to be binary.")
                return

            try:
                # Basic text file reading
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                    # Heuristic check for binary content (null bytes)
                    if '\0' in content:
                        messagebox.showerror("格式錯誤 (Format Error)", "檢測到二進位內容，無法載入為文字。\nBinary content detected.")
                        return

                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", content)
                    # Sync to VM
                    view_model_var.set(content.strip())
                    self.viewmodel.calculate()
            except Exception as e:
                print(f"Error reading dropped file: {e}")
                messagebox.showerror("讀取錯誤 (Read Error)", f"無法讀取檔案:\n{e}")

    def _handle_drop_path(self, event, variable, valid_extensions=None, is_folder=False):
        files = self.root.tk.splitlist(event.data)
        if files:
            path = files[0]
            
            if is_folder:
                if not os.path.isdir(path):
                    messagebox.showerror("格式錯誤 (Format Error)", "請拖曳資料夾 (Please drop a folder).")
                    return
            else:
                if not os.path.isfile(path):
                    return
                
                if valid_extensions:
                    _, ext = os.path.splitext(path)
                    if ext.lower() not in valid_extensions:
                        messagebox.showerror("格式錯誤 (Format Error)", f"不支援的檔案格式。\n僅支援: {', '.join(valid_extensions)}")
                        return

            variable.set(path)

    def create_widgets(self):
        # --- Top Controls (Global Settings) ---
        control_frame = ttk.LabelFrame(self, text="全域設定 (Global Settings)", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(control_frame, text="相似度方法:", font=self.font_style).pack(side=tk.LEFT, padx=5)
        
        self.method_combo = ttk.Combobox(control_frame, state="readonly", width=40)
        self.method_combo['values'] = (
            "Standard Cosine (cos) - 語意與詞彙重疊", 
            "Rearrangement Cosine (recos) - 詞頻分佈形狀",
            "Jaccard Similarity - 集合重疊度 (Set Overlap)",
            "Levenshtein Distance - 編輯距離 (Edit Distance)",
            "TF-IDF Cosine - 詞頻逆文檔頻率 (Term Frequency-Inverse Document Frequency)"
        )
        self.method_combo.current(0)
        self.method_combo.pack(side=tk.LEFT, padx=5)

        # Stopwords Checkbox
        self.stopwords_chk = ttk.Checkbutton(
            control_frame,
            text="過濾停用詞 (Filter Stopwords)",
            variable=self.viewmodel.is_remove_stopwords,
            command=self.viewmodel.toggle_remove_stopwords
        )
        self.stopwords_chk.pack(side=tk.LEFT, padx=15)

        # --- Main Tabs ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab 1: Single Compare
        self.tab_single = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_single, text="單檔比對 (Single Mode)")
        self.create_single_compare_ui(self.tab_single)

        # Tab 2: Batch Compare
        self.tab_batch = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_batch, text="批次比對 (Batch Mode)")
        self.create_batch_compare_ui(self.tab_batch)

        # Tab 3: Audio Compare
        self.tab_audio = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_audio, text="音訊比對 (Audio Mode)")
        self.create_audio_compare_ui(self.tab_audio)

        # --- Bottom Status & Options ---
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

        # Dark Mode Switch
        self.theme_switch = ttk.Checkbutton(
            bottom_frame, 
            text="深色模式 (Dark Mode)", 
            variable=self.viewmodel.is_dark_mode, 
            command=self.viewmodel.toggle_theme,
            style="Switch.TCheckbutton"
        )
        self.theme_switch.pack(side=tk.RIGHT, padx=10)

        # Highlight Switch (Only relevant for single mode, but kept global for simplicity)
        self.highlight_chk = ttk.Checkbutton(
            bottom_frame,
            text="高亮共同詞彙 (Highlight Common Words)",
            variable=self.viewmodel.is_highlight_enabled,
            command=self.viewmodel.toggle_highlight,
            style="Switch.TCheckbutton"
        )
        self.highlight_chk.pack(side=tk.RIGHT, padx=10)

    def create_single_compare_ui(self, parent):
        # --- Visualization Tools ---
        vis_frame = ttk.Frame(parent)
        vis_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(vis_frame, text="詞頻分佈圖 (Frequency Plot)", command=self.viewmodel.show_frequency_plot).pack(side=tk.LEFT, padx=5)
        ttk.Button(vis_frame, text="文字雲 (Word Cloud)", command=self.viewmodel.show_word_cloud).pack(side=tk.LEFT, padx=5)

        # --- Input Area ---
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Text A
        frame_a = ttk.LabelFrame(input_frame, text="文本 A (Text A) - 可拖曳檔案 (Drag & Drop)", padding="5")
        frame_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.text_widget_a = tk.Text(frame_a, height=15, width=30, font=self.font_style)
        self.text_widget_a.pack(fill=tk.BOTH, expand=True)
        self._setup_dnd(self.text_widget_a, lambda e: self._handle_drop_text(e, self.text_widget_a, self.viewmodel.text_a))

        # Text B
        frame_b = ttk.LabelFrame(input_frame, text="文本 B (Text B) - 可拖曳檔案 (Drag & Drop)", padding="5")
        frame_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        self.text_widget_b = tk.Text(frame_b, height=15, width=30, font=self.font_style)
        self.text_widget_b.pack(fill=tk.BOTH, expand=True)
        self._setup_dnd(self.text_widget_b, lambda e: self._handle_drop_text(e, self.text_widget_b, self.viewmodel.text_b))

        # --- Result Area ---
        result_frame = ttk.Frame(parent, padding="20")
        result_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(result_frame, text="相似度結果:", font=("Microsoft JhengHei", 14, "bold")).pack(side=tk.LEFT)
        
        self.result_label = ttk.Label(result_frame, font=("Arial", 24, "bold"), foreground="blue")
        self.result_label.pack(side=tk.RIGHT, padx=20)

    def create_batch_compare_ui(self, parent):
        # Base File Selection
        base_frame = ttk.LabelFrame(parent, text="1. 選擇基準檔 (Select Base File) - 可拖曳", padding=10)
        base_frame.pack(fill=tk.X, pady=5)
        
        entry_base = ttk.Entry(base_frame, textvariable=self.viewmodel.batch_base_file_path)
        entry_base.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Allow common text formats for base file
        text_exts = self.viewmodel.config_model.text_extensions
        self._setup_dnd(entry_base, lambda e: self._handle_drop_path(e, self.viewmodel.batch_base_file_path, valid_extensions=text_exts))
        
        ttk.Button(base_frame, text="瀏覽 (Browse)", command=self.browse_base_file).pack(side=tk.RIGHT)

        # Target Folder Selection
        target_frame = ttk.LabelFrame(parent, text="2. 選擇比對資料夾 (Select Target Folder) - 可拖曳", padding=10)
        target_frame.pack(fill=tk.X, pady=5)
        
        entry_target = ttk.Entry(target_frame, textvariable=self.viewmodel.batch_target_folder_path)
        entry_target.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._setup_dnd(entry_target, lambda e: self._handle_drop_path(e, self.viewmodel.batch_target_folder_path, is_folder=True))
        
        ttk.Button(target_frame, text="瀏覽 (Browse)", command=self.browse_target_folder).pack(side=tk.RIGHT)

        # Actions Frame
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(action_frame, text="開始批次比對 (Start Batch Comparison)", command=self.viewmodel.start_batch_processing, style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
        self.export_btn = ttk.Button(action_frame, text="匯出 CSV (Export CSV)", command=self.export_csv)
        self.export_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Progress Section
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, textvariable=self.viewmodel.batch_status, font=("Microsoft JhengHei", 9)).pack(anchor="w")
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', variable=self.viewmodel.batch_progress)
        self.progress_bar.pack(fill=tk.X, pady=2)

        # Results Table
        result_frame = ttk.LabelFrame(parent, text="比對結果 (Results)", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("filename", "score")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        self.tree.heading("filename", text="檔案名稱 (Filename)")
        self.tree.heading("score", text="相似度 (Score)")
        self.tree.column("filename", width=400)
        self.tree.column("score", width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def browse_base_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt *.py *.md *.json"), ("All Files", "*.*")])
        if filename:
            self.viewmodel.batch_base_file_path.set(filename)
            
    def export_csv(self):
        if not self.viewmodel.batch_results:
            from tkinter import messagebox
            messagebox.showwarning("無法匯出 (Cannot Export)", "沒有比對結果可供匯出，請先執行比對。\nNo results to export. Please run comparison first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="similarity_results.csv"
        )
        
        if file_path:
            success = self.viewmodel.save_batch_results_to_csv(file_path)
            if success:
                from tkinter import messagebox
                messagebox.showinfo("匯出成功 (Success)", f"已成功儲存至:\n{file_path}")
            else:
                from tkinter import messagebox
                messagebox.showerror("匯出失敗 (Error)", "儲存檔案時發生錯誤。")

    def browse_target_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.viewmodel.batch_target_folder_path.set(folder)

    def setup_bindings(self):
        # Two-way binding for method selection
        self.method_combo.bind("<<ComboboxSelected>>", self.on_method_changed)
        
        # Binding Text widgets to ViewModel variables is tricky in Tkinter.
        # We act on KeyRelease events to update VM and trigger calculation.
        self.text_widget_a.bind("<KeyRelease>", self.on_text_changed)
        self.text_widget_b.bind("<KeyRelease>", self.on_text_changed)
        
        # Bind ViewModel output to View
        self.result_label.config(textvariable=self.viewmodel.similarity_score)
        
        # Set initial values from VM to View
        self.method_combo.current(self.viewmodel.method_index.get())
        
        # Callbacks
        self.viewmodel.on_highlight_update = self.update_highlights
        self.viewmodel.on_batch_results_update = self.update_batch_results
        self.viewmodel.on_processing_state_change = self.set_processing_state

    def set_processing_state(self, is_processing):
        """Enable/Disable buttons during processing to prevent re-entry"""
        state = "disabled" if is_processing else "normal"
        self.start_btn.configure(state=state)
        # We might want to keep allow export if previous results exist, but safer to disable
        # self.export_btn.configure(state=state) 

    def on_method_changed(self, event):
        self.viewmodel.method_index.set(self.method_combo.current())
        self.viewmodel.calculate()

    def on_text_changed(self, event):
        if self._text_change_after_id is not None:
            self.root.after_cancel(self._text_change_after_id)
        self._text_change_after_id = self.root.after(180, self._flush_text_changes)

    def _flush_text_changes(self):
        self._text_change_after_id = None
        self.viewmodel.text_a.set(self.text_widget_a.get("1.0", tk.END).strip())
        self.viewmodel.text_b.set(self.text_widget_b.get("1.0", tk.END).strip())
        self.viewmodel.calculate()
        
    def update_batch_results(self, results):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for fname, score in results:
            self.tree.insert("", tk.END, values=(fname, f"{score * 100:.2f}%"))

    def update_highlights(self, common_words, unique_a=set(), unique_b=set()):
        """Called by ViewModel when highlights need to be updated"""
        
        # Determine colors based on theme
        is_dark = self.viewmodel.is_dark_mode.get()
        # Common words: Greenish
        bg_common = "#2a6e2a" if is_dark else "#d0f0c0" # Dark Green / Tea Green
        fg_common = "white" if is_dark else "black"
        
        # Unique words: Reddish
        bg_unique = "#8b0000" if is_dark else "#ffcccb" # Dark Red / Light Red
        fg_unique = "white" if is_dark else "black"
        
        # Configure tags
        self.text_widget_a.tag_config("common", background=bg_common, foreground=fg_common)
        self.text_widget_b.tag_config("common", background=bg_common, foreground=fg_common)
        
        self.text_widget_a.tag_config("unique", background=bg_unique, foreground=fg_unique)
        self.text_widget_b.tag_config("unique", background=bg_unique, foreground=fg_unique)
        
        # Apply Common
        self.apply_highlight(self.text_widget_a, common_words, "common")
        self.apply_highlight(self.text_widget_b, common_words, "common")
        
        # Apply Unique
        self.apply_highlight(self.text_widget_a, unique_a, "unique")
        self.apply_highlight(self.text_widget_b, unique_b, "unique")

    def apply_highlight(self, text_widget, target_words, tag_name):
        text_widget.tag_remove(tag_name, "1.0", tk.END)
        if not target_words:
            return

        for word in target_words:
            if not word.strip():
                continue
                
            start_pos = "1.0"
            while True:
                start_pos = text_widget.search(word, start_pos, stopindex=tk.END)
                if not start_pos:
                    break
                
                line, col = start_pos.split('.')
                end_pos = f"{line}.{int(col) + len(word)}"
                
                text_widget.tag_add(tag_name, start_pos, end_pos)
                start_pos = end_pos

    def create_audio_compare_ui(self, parent):
        # --- Audio A Selection ---
        frame_a = ttk.LabelFrame(parent, text="音訊 A (Audio A) - 可拖曳檔案", padding=10)
        frame_a.pack(fill=tk.X, pady=5)
        
        entry_a = ttk.Entry(frame_a, textvariable=self.viewmodel.audio_path_a)
        entry_a.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        audio_exts = self.viewmodel.config_model.audio_extensions
        self._setup_dnd(entry_a, lambda e: self._handle_drop_path(e, self.viewmodel.audio_path_a, valid_extensions=audio_exts))
        
        ttk.Button(frame_a, text="瀏覽 (Browse)", command=lambda: self.browse_audio(self.viewmodel.audio_path_a)).pack(side=tk.RIGHT)

        # --- Audio B Selection ---
        frame_b = ttk.LabelFrame(parent, text="音訊 B (Audio B) - 可拖曳檔案", padding=10)
        frame_b.pack(fill=tk.X, pady=5)
        
        entry_b = ttk.Entry(frame_b, textvariable=self.viewmodel.audio_path_b)
        entry_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._setup_dnd(entry_b, lambda e: self._handle_drop_path(e, self.viewmodel.audio_path_b, valid_extensions=audio_exts))
        
        ttk.Button(frame_b, text="瀏覽 (Browse)", command=lambda: self.browse_audio(self.viewmodel.audio_path_b)).pack(side=tk.RIGHT)

        # --- Method Selection ---
        method_frame = ttk.LabelFrame(parent, text="音訊演算法 (Audio Algorithm)", padding=10)
        method_frame.pack(fill=tk.X, pady=5)
        
        audio_methods = (
            "MFCC Similarity (Timbre) - 語音/音色",
            "Chroma Similarity (Harmonic) - 音樂/和弦",
            "Spectral Contrast (Texture) - 光譜對比/紋理"
        )
        audio_combo = ttk.Combobox(method_frame, state="readonly", values=audio_methods)
        audio_combo.current(0)
        audio_combo.bind("<<ComboboxSelected>>", lambda e: self.viewmodel.audio_method_index.set(audio_combo.current()))
        audio_combo.pack(fill=tk.X)

        # --- Action ---
        action_frame = ttk.Frame(parent, padding=10)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="開始音訊比對 (Start Audio Compare)", command=self.viewmodel.calculate_audio_similarity, style="Accent.TButton").pack(fill=tk.X)
        
        # --- Result ---
        result_frame = ttk.Frame(parent, padding="20")
        result_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(result_frame, text="相似度結果:", font=("Microsoft JhengHei", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(result_frame, textvariable=self.viewmodel.audio_similarity_score, font=("Arial", 24, "bold"), foreground="green").pack(side=tk.RIGHT, padx=20)

        detail_label = ttk.Label(
            parent,
            textvariable=self.viewmodel.audio_analysis_detail,
            font=("Microsoft JhengHei", 10),
            justify=tk.LEFT,
            wraplength=720,
            foreground="#555555"
        )
        detail_label.pack(fill=tk.X, padx=10, pady=(0, 10))

    def browse_audio(self, string_var):
        filename = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("All Files", "*.*")]
        )
        if filename:
            string_var.set(filename)

    def show_frequency_plot_window(self, sorted_a, sorted_b):
        top = tk.Toplevel(self.root)
        top.title("詞頻分佈比較 (Frequency Plot)")
        top.geometry("800x600")

        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Set Chinese font support
        from matplotlib import rcParams
        rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False

        ax.plot(sorted_a, label='Text A Frequency', color='blue', alpha=0.7)
        ax.plot(sorted_b, label='Text B Frequency', color='red', alpha=0.7)
        ax.set_title('詞頻分佈比較 (Zipfian Curve Comparison)')
        ax.set_xlabel('Rank (詞彙排名)')
        ax.set_ylabel('Frequency (頻率)')
        ax.legend()
        ax.grid(True)

        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
