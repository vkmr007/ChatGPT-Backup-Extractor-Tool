# ChatGPT Backup Extractor Tool

A standalone Windows desktop app that extracts conversations from your **ChatGPT data export** — with a full chat browser, preview panel, and one-click story extraction to `.docx`.

![Dark Theme GUI with 3 tabs: Setup, Browse Chats, Extract](screenshot.png)

---

## Features

- 📦 **Loads your ChatGPT export** — supports `.zip` directly or an already-extracted folder
- 📋 **Browse all conversations** — searchable, filterable list with a rich preview panel
- ✅ **Selective extraction** — pick individual chats, stories only, or everything at once
- 📖 **Story detection** — automatically identifies narrative/fanfic conversations and saves them as formatted `.docx` files
- 📝 **Markdown export** — saves every conversation as a clean `.md` file
- 🖥️ **Standalone EXE** — no Python required on the target machine; just double-click and run

---

## Quick Start

### Option A — Run from Source

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. Install dependencies:
   ```bash
   pip install python-docx
   ```
3. Run the app:
   ```bash
   python chatgpt_extractor.py
   ```

### Option B — Build the EXE

1. Double-click **`build_exe.bat`**
2. Wait ~1 minute while PyInstaller packages everything
3. Find `ChatGPT_Extractor.exe` in the `dist\` folder
4. Double-click it — no Python needed!

---

## How to Get Your ChatGPT Export

1. Go to **ChatGPT → Settings → Data Controls**
2. Click **Export Data**
3. Wait for the email from OpenAI (usually a few minutes)
4. Download the `.zip` file — that's your backup

---

## How to Use the App

### Tab 1 — Setup
| Field | Description |
|-------|-------------|
| Source | Your ChatGPT export `.zip` file or extracted folder |
| Markdown output | Where to save `.md` files of all conversations |
| Stories output | Where to save `.docx` files of detected stories |

Click **Load Conversations** to parse the backup.

### Tab 2 — Browse Chats
- All conversations appear in the left panel
- Click any chat to preview its content on the right
- Use **Search** and **Filter** (All / Stories Only / Non-Stories)
- Select specific chats and click **Extract This Chat** for one-off extraction
- Use **Select Stories** to batch-select all detected narratives

### Tab 3 — Extract
- Choose extraction mode:
  - **All Conversations** — saves every chat as `.md`
  - **Stories Only** — saves detected stories as `.docx`
  - **Selected in Browse Tab** — only what you picked
- Hit **EXTRACT NOW** and watch the live progress log
- Click **Open Stories Folder** when done

---

## Story Detection Keywords

The app flags a conversation as a story if it contains any of these in the title or first 5 messages:

`chapter`, `prologue`, `epilogue`, `narrative`, `story`, `fanfic`, `novel`,  
`scene`, `dialogue`, `fiction`, `character`, `protagonist`, `transformers`,  
`autobot`, `decepticon`, `marcus cain`, `ghostrider`, `nest`, `sector seven`, ...

---

## File Structure

```
ChatGPT-Backup-Extractor-Tool/
├── chatgpt_extractor.py   # Main GUI app (tkinter, dark theme)
├── extractor_core.py      # Extraction logic (no GUI, callback-based)
├── build_exe.bat          # One-click PyInstaller EXE builder
└── README.md
```

---

## Requirements (source only)

- Python 3.10+
- `python-docx` — `pip install python-docx`
- `tkinter` — included with Python on Windows

---

## License

MIT — free to use, modify, and distribute.
