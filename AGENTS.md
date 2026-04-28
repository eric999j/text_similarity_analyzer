# Agent Instructions

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Project Overview

A desktop text and audio similarity analyzer built with Python + Tkinter, featuring:
- Single file comparison, batch comparison, and audio comparison modes
- Multiple similarity algorithms (Cosine, Jaccard, Levenshtein, MFCC, Chroma, Spectral)
- Bilingual UI (Traditional Chinese / English)

## Architecture

**MVVM Pattern** - Follow this structure strictly:

```
main.py                    # Entry point
config.json                # Runtime configuration (theme, extensions)
src/
├── models/                # Business logic, no UI dependencies
│   ├── similarity_model.py    # Text similarity algorithms
│   ├── audio_similarity_model.py  # Audio comparison (librosa)
│   └── config_model.py        # Configuration persistence
├── viewmodels/            # Bridge between models and views
│   └── main_viewmodel.py      # Observable state (tk.StringVar, tk.BooleanVar)
└── views/                 # UI components only
    └── main_view.py           # Tkinter widgets
```

### Data Flow
1. **View** captures user input → updates **ViewModel** variables
2. **ViewModel** calls **Model** methods for computation
3. **ViewModel** updates its observable variables → **View** reflects changes

### Thread Safety
Background tasks must use `self.viewmodel.ui_callback(lambda: ...)` to update UI safely.

## Key Conventions

### Text Processing
- Use `jieba` for Chinese tokenization
- Stopwords defined in `SimilarityModel.STOPWORDS` (Chinese + English)
- All text methods accept `remove_stopwords: bool` parameter

### Audio Processing
- Use `librosa` for audio loading and feature extraction
- Sample rate: 22050 Hz
- Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`

### UI Guidelines
- Font: "Microsoft JhengHei" for Chinese support
- Theme: `sv_ttk` (Sun Valley theme) - supports dark/light modes
- Bilingual labels format: `"中文 (English)"`
- Optional drag-and-drop via `tkinterdnd2` (graceful fallback if unavailable)

## Adding New Features

### New Similarity Algorithm
1. Add method to `src/models/similarity_model.py` or `audio_similarity_model.py`
2. Add selection option to `method_combo` in `main_view.py`
3. Handle new index in `MainViewModel.calculate()` or `calculate_audio_similarity()`

### New Configuration Option
1. Add field to `ConfigModel` with default value
2. Update `load_config()` and `save_config()` methods
3. Add `tk.BooleanVar`/`tk.StringVar` in `MainViewModel`
4. Create UI control in `MainView`

## Dependencies

| Library | Purpose |
|---------|---------|
| `jieba` | Chinese text segmentation |
| `librosa` | Audio feature extraction |
| `scikit-learn` | Cosine similarity |
| `Levenshtein` | Edit distance calculation |
| `sv_ttk` | Modern Tkinter theme |
| `tkinterdnd2` | Drag-and-drop (optional) |
