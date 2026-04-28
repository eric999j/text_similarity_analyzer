---
name: code-review
description: Reviews code changes for bugs, style issues, and best practices specific to this MVVM Tkinter project. Use when reviewing PRs or checking code quality.
---

# Code Review Skill

專案特定的程式碼審查指南，確保遵循 MVVM 架構與執行緒安全慣例。

## 1. MVVM 架構檢查

### Models (`src/models/`)
- [ ] **無 UI 依賴**: 不得 import `tkinter`、`ttk` 或任何 View/ViewModel
- [ ] **純邏輯**: 只包含業務邏輯和資料處理
- [ ] **可測試性**: 方法應可獨立單元測試

### ViewModels (`src/viewmodels/`)
- [ ] **使用 Observable**: 狀態使用 `tk.StringVar`、`tk.BooleanVar`、`tk.IntVar`
- [ ] **不直接操作 Widget**: 透過回調通知 View 更新
- [ ] **執行緒安全**: 背景任務使用 `self.ui_callback(lambda: ...)` 更新 UI

### Views (`src/views/`)
- [ ] **僅 UI 邏輯**: 不包含業務邏輯計算
- [ ] **綁定 ViewModel**: 透過 `textvariable`、`command` 綁定
- [ ] **注入回調**: 初始化時設定 `viewmodel.ui_callback = lambda action: self.root.after(0, action)`

## 2. UI 慣例檢查

- [ ] **雙語標籤**: 格式為 `"中文 (English)"`
- [ ] **字型**: 使用 `"Microsoft JhengHei"` 支援中文
- [ ] **拖放容錯**: `tkinterdnd2` 功能需包裝在 try/except，不可用時優雅降級

## 3. 文字處理檢查

- [ ] **使用 jieba**: 中文分詞使用 `jieba.cut()`
- [ ] **停用詞參數**: 相關方法需接受 `remove_stopwords: bool` 參數
- [ ] **停用詞來源**: 使用 `SimilarityModel.STOPWORDS` 而非硬編碼

## 4. 音訊處理檢查

- [ ] **使用 librosa**: 音訊載入和特徵提取
- [ ] **取樣率**: 使用 `22050` Hz（`self.sample_rate`）
- [ ] **錯誤處理**: `load_audio()` 失敗時回傳 `(None, None)`

## 5. 執行緒安全檢查（關鍵）

```python
# ❌ 錯誤：從背景執行緒直接更新 UI
def background_task(self):
    result = heavy_computation()
    self.some_var.set(result)  # 會導致 Tcl 錯誤

# ✅ 正確：使用 ui_callback
def background_task(self):
    result = heavy_computation()
    self._run_on_ui(lambda: self.some_var.set(result))
```

## 6. 設定持久化檢查

新增設定選項時：
1. [ ] `ConfigModel` 新增欄位與預設值
2. [ ] 更新 `load_config()` 使用 `.get()` 提供預設值
3. [ ] 更新 `save_config()` 包含新欄位
4. [ ] `MainViewModel` 新增對應的 `tk.BooleanVar`/`tk.StringVar`

## 審查回饋格式

```markdown
### 🔴 必須修正
- [file:line] 問題描述 → 建議修正方式

### 🟡 建議改進
- [file:line] 改進建議

### ✅ 優點
- 符合架構的實作亮點
```