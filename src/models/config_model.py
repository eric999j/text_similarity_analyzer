import json
import os
import sv_ttk

CONFIG_FILE = "config.json"

class ConfigModel:
    # Default constants
    DEFAULT_BINARY_EXTS = ['.exe', '.dll', '.bin', '.so', '.zip', '.rar', '.7z', '.pdf', '.jpg', '.png', '.mp3', '.wav']
    DEFAULT_TEXT_EXTS = ['.txt', '.py', '.md', '.json', '.xml', '.csv', '.log']
    DEFAULT_AUDIO_EXTS = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']

    def __init__(self):
        self.dark_mode = False
        self.highlight = True
        self.remove_stopwords = False
        
        # Extension lists
        self.binary_extensions = set(self.DEFAULT_BINARY_EXTS)
        self.text_extensions = set(self.DEFAULT_TEXT_EXTS)
        self.audio_extensions = set(self.DEFAULT_AUDIO_EXTS)
        
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.dark_mode = config.get("dark_mode", False)
                    self.highlight = config.get("highlight", True)
                    self.remove_stopwords = config.get("remove_stopwords", False)
                    
                    # Load extensions if present, otherwise keep defaults
                    if "binary_extensions" in config:
                        self.binary_extensions = set(config["binary_extensions"])
                    if "text_extensions" in config:
                        self.text_extensions = set(config["text_extensions"])
                    if "audio_extensions" in config:
                        self.audio_extensions = set(config["audio_extensions"])
            except Exception:
                pass
    
    def save_config(self):
        config = {
            "dark_mode": self.dark_mode,
            "highlight": self.highlight,
            "remove_stopwords": self.remove_stopwords,
            "binary_extensions": list(self.binary_extensions),
            "text_extensions": list(self.text_extensions),
            "audio_extensions": list(self.audio_extensions)
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
            
    def apply_theme(self):
        if self.dark_mode:
            sv_ttk.set_theme("dark")
        else:
            sv_ttk.set_theme("light")
