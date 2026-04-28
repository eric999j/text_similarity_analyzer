import tkinter as tk
from src.viewmodels.main_viewmodel import MainViewModel
from src.views.main_view import MainView

# Try to import TkinterDnD, fallback to standard Tk if not available
try:
    from tkinterdnd2 import TkinterDnD
    USE_DND = True
except ImportError:
    USE_DND = False

def main():
    try:
        if USE_DND:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
            print("Warning: tkinterdnd2 not found. Drag and drop will be disabled.")
            
        root.title("相似度分析器 (Text Similarity Analyzer)")
        root.geometry("800x800")
        
        # Initialize MVVM components
        viewmodel = MainViewModel()
        view = MainView(root, viewmodel)
        
        root.mainloop()
    except KeyboardInterrupt:
        print("\n程式已由使用者強制終止 (Application terminated by user).")
        try:
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()
