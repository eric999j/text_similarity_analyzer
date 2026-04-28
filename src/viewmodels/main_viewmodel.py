import tkinter as tk
import threading
import os
from ..models.similarity_model import SimilarityModel
from ..models.config_model import ConfigModel
from ..models.audio_similarity_model import AudioSimilarityModel

class MainViewModel:
    def __init__(self):
        self.similarity_model = SimilarityModel()
        self.config_model = ConfigModel()
        self.audio_model = AudioSimilarityModel()
        
        # UI Dispatcher (Injected by View)
        self.ui_callback = None
        
        # Observable properties (using Tkinter variables for binding)
        self.text_a = tk.StringVar()
        self.text_b = tk.StringVar()
        self.similarity_score = tk.StringVar(value="0.00%")
        self.method_index = tk.IntVar(value=0) # 0: Standard, 1: Rearrangement

        # Audio properties
        self.audio_path_a = tk.StringVar()
        self.audio_path_b = tk.StringVar()
        self.audio_similarity_score = tk.StringVar(value="等待比對 (Waiting)")
        self.audio_method_index = tk.IntVar(value=0) # 0: MFCC, 1: Chroma, 2: Spectral
        
        self.is_dark_mode = tk.BooleanVar(value=self.config_model.dark_mode)
        self.is_highlight_enabled = tk.BooleanVar(value=self.config_model.highlight)
        self.is_remove_stopwords = tk.BooleanVar(value=self.config_model.remove_stopwords)
        
        # Batch processing properties
        self.batch_base_file_path = tk.StringVar()
        self.batch_target_folder_path = tk.StringVar()
        self.batch_results = [] # List of (filename, score)
        self.batch_progress = tk.DoubleVar(value=0.0)
        self.batch_status = tk.StringVar(value="隨時準備就緒 (Ready)")
        self.is_processing = tk.BooleanVar(value=False)

        # Apply initial theme
        self.config_model.apply_theme()
        
        # Bind callbacks
        self.on_highlight_update = None # Callback to view for highlighting
        self.on_batch_results_update = None # Callback to view when batch results are ready
        self.on_processing_state_change = None # Callback for UI state (enable/disable buttons)
        self.on_show_frequency_plot = None # Callback to view for plotting

    def toggle_remove_stopwords(self):
        self.config_model.remove_stopwords = self.is_remove_stopwords.get()
        self.config_model.save_config()
        self.calculate()

    def toggle_theme(self): # Helper for the command
        self.config_model.dark_mode = self.is_dark_mode.get()
        self.config_model.apply_theme()
        self.config_model.save_config()

    def toggle_highlight(self): # Helper for the command
        self.config_model.highlight = self.is_highlight_enabled.get()
        self.config_model.save_config()
        self.calculate()

    def _run_on_ui(self, func):
        """Helper to run a function on the main UI thread"""
        if self.ui_callback:
            self.ui_callback(func)
        else:
            func()

    def _read_text_with_encodings(self, file_path, encodings):
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None

    def calculate(self, *args):
        t1 = self.text_a.get().strip()
        t2 = self.text_b.get().strip()
        
        if not t1 or not t2:
            self.similarity_score.set("0.00%")
            if self.on_highlight_update:
                self.on_highlight_update(set(), set(), set())
            return

        score = 0.0
        remove_stopwords = self.is_remove_stopwords.get()
        method = self.method_index.get()
        
        if method == 0: # Standard Cosine
            score = self.similarity_model.calculate_standard_cosine(t1, t2, remove_stopwords)
        elif method == 1: # Rearrangement Cosine
            score = self.similarity_model.calculate_sorted_cosine(t1, t2, remove_stopwords)
        elif method == 2: # Jaccard
            score = self.similarity_model.calculate_jaccard_similarity(t1, t2, remove_stopwords)
        elif method == 3: # Levenshtein
            score = self.similarity_model.calculate_levenshtein_similarity(t1, t2, remove_stopwords)
        elif method == 4: # TF-IDF
            score = self.similarity_model.calculate_tfidf_similarity(t1, t2, remove_stopwords)
            
        self.similarity_score.set(f"{score * 100:.2f}%")
        
        # Highlight logic (Keep existing logic for now, though Levenshtein is char-based, Highlighting is token-based)
        if self.is_highlight_enabled.get():
            common_words, unique_a, unique_b = self.similarity_model.get_common_and_unique_words(
                t1,
                t2,
                remove_stopwords
            )
            if self.on_highlight_update:
                self.on_highlight_update(common_words, unique_a, unique_b)
        else:
            if self.on_highlight_update:
                self.on_highlight_update(set(), set(), set())

    def show_frequency_plot(self):
        t1 = self.text_a.get().strip()
        t2 = self.text_b.get().strip()
        if not t1 or not t2: return
        
        freq_a = self.similarity_model.get_word_frequencies(t1, self.is_remove_stopwords.get())
        freq_b = self.similarity_model.get_word_frequencies(t2, self.is_remove_stopwords.get())
        
        # Sort desc
        sorted_a = sorted(freq_a.values(), reverse=True)
        sorted_b = sorted(freq_b.values(), reverse=True)
        
        if self.on_show_frequency_plot:
            self.on_show_frequency_plot(sorted_a, sorted_b)

    def _get_chinese_font_path(self):
        """
        Cross-platform Chinese font detection for WordCloud
        """
        import platform
        import os
        import matplotlib.font_manager as fm
        
        system = platform.system()
        
        # Priority 1: Check known system paths
        if system == "Windows":
            candidates = ["msjh.ttc", "msjh.ttf", "simhei.ttf", "arialuni.ttf"]
            # Typically C:\Windows\Fonts
            font_dirs = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")]
        elif system == "Darwin": # macOS
            candidates = ["PingFang.ttc", "Arial Unicode.ttf", "STHeiti Light.ttc"]
            font_dirs = ["/System/Library/Fonts", "/Library/Fonts"]
        else: # Linux and others
            candidates = ["WenQuanYiMicroHei.ttf", "NotoSansCJK-Regular.ttc", "DroidSansFallback.ttf"]
            font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

        for d in font_dirs:
            if not os.path.exists(d): continue
            for c in candidates:
                p = os.path.join(d, c)
                if os.path.exists(p):
                    return p
                    
        # Priority 2: Matplotlib Font Manager
        # Try to find a font by family name
        font_families = ["Microsoft JhengHei", "SimHei", "PingFang HK", "Heiti TC", "WenQuanYi Micro Hei", "Noto Sans CJK SC"]
        for family in font_families:
            try:
                found = fm.findfont(fm.FontProperties(family=family))
                # findfont returns a default (like DejaVu) if not found. We want to avoid that if possible for determining success, 
                # but if it returns a specific path that's not DejaVu, let's use it.
                if found and os.path.exists(found) and "DejaVu" not in found:
                     return found
            except:
                continue

        return None

    def show_word_cloud(self):
        t1 = self.text_a.get().strip()
        t2 = self.text_b.get().strip()
        if not t1 or not t2: return
        
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            
            freq_a = self.similarity_model.get_word_frequencies(t1, self.is_remove_stopwords.get())
            freq_b = self.similarity_model.get_word_frequencies(t2, self.is_remove_stopwords.get())
            
            if not freq_a or not freq_b: return

            # Detect Font
            font_path = self._get_chinese_font_path()
            if not font_path:
                print("Warning: No suitable Chinese font found. WordCloud may display squares.")
            
            wc_a = WordCloud(font_path=font_path, width=400, height=300, background_color='white').generate_from_frequencies(freq_a)
            wc_b = WordCloud(font_path=font_path, width=400, height=300, background_color='white').generate_from_frequencies(freq_b)
            
            fig, axes = plt.subplots(1, 2, figsize=(12, 6))
            axes[0].imshow(wc_a)
            axes[0].set_title("Text A Word Cloud")
            axes[0].axis('off')
            
            axes[1].imshow(wc_b)
            axes[1].set_title("Text B Word Cloud")
            axes[1].axis('off')
            
            plt.show()
        except ImportError:
            print("WordCloud library not installed.")
        except Exception as e:
            print(f"Error generating word cloud: {e}")

    def start_batch_processing(self):
        """Starts batch processing in a separate thread"""
        if self.is_processing.get(): return
        
        base_path = self.batch_base_file_path.get()
        folder_path = self.batch_target_folder_path.get()
        
        # Capture settings for thread
        method_idx = self.method_index.get()
        remove_sw = self.is_remove_stopwords.get()

        if not base_path or not folder_path:
            self.batch_status.set("請先選擇檔案與資料夾\nPlease select file and folder first.")
            return

        self.is_processing.set(True)
        self.batch_progress.set(0.0)
        self.batch_status.set("準備中... (Preparing...)")
        if self.on_processing_state_change:
            self.on_processing_state_change(True)

        # Start thread
        t = threading.Thread(target=self._run_batch_processing_thread, args=(base_path, folder_path, method_idx, remove_sw))
        t.daemon = True
        t.start()
        
    def _run_batch_processing_thread(self, base_path, folder_path, method_idx, remove_sw):
        # Helper for thread-safe UI updates
        def update_status(msg):
            self._run_on_ui(lambda: self.batch_status.set(msg))
            
        def update_progress(val):
            self._run_on_ui(lambda: self.batch_progress.set(val))

        encodings = ('utf-8', 'cp950', 'gbk')

        try:
            # 1. Read Base File
            update_status("讀取基準檔... (Reading base file...)")
            base_text = self._read_text_with_encodings(base_path, encodings)
            if base_text is None:
                update_status("錯誤: 無法讀取基準檔 (Unknown encoding)")
                return

            # 2. Scan Folder
            update_status("掃描資料夾... (Scanning folder...)")
            valid_entries = [entry for entry in os.scandir(folder_path) if entry.is_file()]
            total_files = len(valid_entries)
            
            if total_files == 0:
                update_status("資料夾為空 (Folder is empty)")
                return

            # 3. Process Files
            scorer = self.similarity_model.create_similarity_scorer(base_text, method_idx, remove_sw)
            results = []
            
            for i, entry in enumerate(valid_entries, start=1):
                # Update progress
                progress = ((i - 1) / total_files) * 100
                update_progress(progress)
                update_status(f"正在分析 ({i}/{total_files}): {entry.name}")
                
                try:
                    content = self._read_text_with_encodings(entry.path, encodings)
                except OSError as e:
                    print(f"Skipping {entry.name}: {e}")
                    continue

                if content is None:
                    continue

                results.append((entry.name, scorer(content)))
            
            # 4. Sort and Finish
            update_status("整理結果... (Finalizing...)")
            results.sort(key=lambda x: x[1], reverse=True)
            self.batch_results = results
            
            update_progress(100.0)
            update_status(f"完成! 共分析 {len(results)} 個檔案")
            
            if self.on_batch_results_update:
                self._run_on_ui(lambda: self.on_batch_results_update(self.batch_results))

        except Exception as e:
            update_status(f"發生未預期錯誤: {str(e)}")
            print(e)
        finally:
            self._run_on_ui(lambda: self.is_processing.set(False))
            if self.on_processing_state_change:
                self._run_on_ui(lambda: self.on_processing_state_change(False))
    
    # Old method kept for reference or deleted, here I replaced it completely with the threaded logic above
    # The previous `run_batch_processing` logic is now effectively split into `start_...` and `_run...`

    def save_batch_results_to_csv(self, file_path):
        import csv
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Filename", "Similarity Score", "Method", "Stopwords Filter"])
                
                methods = {
                    0: "Standard Cosine",
                    1: "Rearrangement Cosine",
                    2: "Jaccard Similarity",
                    3: "Levenshtein Distance"
                }
                method_name = methods.get(self.method_index.get(), "Unknown")
                stopwords_status = "On" if self.is_remove_stopwords.get() else "Off"
                
                for fname, score in self.batch_results:
                    writer.writerow([fname, f"{score:.4f}", method_name, stopwords_status])
            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False


    def toggle_theme(self):
        # Update model
        self.config_model.dark_mode = self.is_dark_mode.get()
        self.config_model.apply_theme()
        self.config_model.save_config()
        # Trigger recalculate to update highlight colors if needed (logic in view)
        self.calculate()

    def toggle_highlight(self):
        self.config_model.highlight = self.is_highlight_enabled.get()
        self.config_model.save_config()
        self.calculate()

    def calculate_audio_similarity(self):
        path_a = self.audio_path_a.get()
        path_b = self.audio_path_b.get()
        
        if not path_a or not path_b:
            self.audio_similarity_score.set("請選擇兩個音訊檔案 (Select 2 files)")
            return

        if not os.path.exists(path_a) or not os.path.exists(path_b):
            self.audio_similarity_score.set("檔案不存在 (File not found)")
            return

        self.audio_similarity_score.set("計算中... (Calculating...)")
        
        def run_calc():
            try:
                # Get raw values on thread (safe for get if not modified concurrently)
                # But better to pass them as args or use .get() before thread start.
                # However, for simple StringVars, reading in thread is usually ok, 
                # writing is the main issue. To be 100% safe we could pass args.
                # Here we already read variables in the main method, oh wait, 
                # method_idx is read inside. Let's assume reading is fine for now or fix it.
                # Actually, self.audio_method_index.get() accesses Tcl, better do it on main.
                
                # We'll use a local var passed in via closure or args.
                # But to avoid refactoring too much, let's just wrap updates.
                
                # NOTE: Accessing Tk vars from thread is also risky. 
                # Ideally, we should capture values before starting thread.
                
                method = method_idx_val # Use captured value
                
                score = 0.0
                if method == 0: # MFCC
                    score = self.audio_model.calculate_mfcc_similarity(path_a, path_b)
                elif method == 1: # Chroma
                    score = self.audio_model.calculate_chroma_similarity(path_a, path_b)
                elif method == 2: # Spectral
                    score = self.audio_model.calculate_spectral_similarity(path_a, path_b)
                
                if score is not None:
                    self._run_on_ui(lambda: self.audio_similarity_score.set(f"{score:.2%}"))
                else:
                    self._run_on_ui(lambda: self.audio_similarity_score.set("錯誤 (Error)"))
            except Exception as e:
                print(f"Audio Calc Error: {e}")
                self._run_on_ui(lambda: self.audio_similarity_score.set("錯誤 (Error)"))

        # Capture method index before thread start
        method_idx_val = self.audio_method_index.get()
        threading.Thread(target=run_calc, daemon=True).start()
