"""
chatgpt_extractor.py
---------------------
ChatGPT Export Extractor — Windows Desktop App
Dark-themed tkinter GUI with 3 tabs:
  1. Setup    — pick source & output folders
  2. Browse   — preview all chats, select specific ones
  3. Extract  — run extraction with live progress & log
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import extractor_core as core

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = "#13131f"
BG2     = "#1e1e30"
BG3     = "#2a2a40"
ACCENT  = "#7c3aed"
ACCENT2 = "#9d5cf6"
ACCENT3 = "#4f1d96"
TEXT    = "#e2e8f0"
TEXT2   = "#8892a4"
GREEN   = "#10b981"
AMBER   = "#f59e0b"
RED     = "#ef4444"
BLUE    = "#60a5fa"
TEAL    = "#34d399"
BORDER  = "#2f2f4a"


# ── Custom Widgets ─────────────────────────────────────────────────────────────

class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, accent=True, small=False, **kw):
        bg = ACCENT if accent else BG3
        fg = "white" if accent else TEXT2
        abg = ACCENT2 if accent else BORDER
        font_size = 9 if small else 11
        bold = "bold" if not small else ""
        super().__init__(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=abg, activeforeground="white",
            font=("Segoe UI", font_size, bold) if bold else ("Segoe UI", font_size),
            bd=0, relief="flat", cursor="hand2",
            padx=18 if not small else 10,
            pady=9 if not small else 5,
            **kw
        )
        self.bind("<Enter>", lambda e: self.configure(bg=abg))
        self.bind("<Leave>", lambda e: self.configure(bg=bg))


class PathRow(tk.Frame):
    """Label + Entry + Browse button row."""
    def __init__(self, parent, label, variable, on_browse, **kw):
        super().__init__(parent, bg=BG2, **kw)
        tk.Label(self, text=label, font=("Segoe UI", 9), bg=BG2, fg=TEXT2,
                 width=28, anchor="w").pack(side="left")
        entry = tk.Entry(self, textvariable=variable, font=("Consolas", 9),
                         bg=BG3, fg=TEXT, insertbackground=TEXT, bd=0, relief="flat",
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER)
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        StyledButton(self, "Browse", command=on_browse, accent=False, small=True
                     ).pack(side="left")


# ── Main App ───────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatGPT Export Extractor")
        self.geometry("1150x740")
        self.minsize(960, 620)
        self.configure(bg=BG)
        self.resizable(True, True)

        # Try to set window icon (bundled EXE or dev mode)
        try:
            icon_path = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # ── State ──────────────────────────────────────────────────────────────
        self.conversations = []          # list of parsed conv dicts
        self._filtered_indices = []      # listbox index -> conversations index
        self._current_preview_idx = None

        self.source_var      = tk.StringVar()
        self.md_output_var   = tk.StringVar(value=r"f:\workplace\important chats")
        self.story_output_var= tk.StringVar(value=r"f:\stories")
        self.search_var      = tk.StringVar()
        self.filter_var      = tk.StringVar(value="All")
        self.extract_mode    = tk.StringVar(value="all")

        self.search_var.trace_add("write", lambda *_: self._filter_list())

        self._build_ui()

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Header bar ─────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=ACCENT, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="  \U0001f4ac  ChatGPT Export Extractor",
                 font=("Segoe UI", 15, "bold"), bg=ACCENT, fg="white"
                 ).pack(side="left", padx=8, pady=10)

        tk.Label(header, text="v2.0   ",
                 font=("Segoe UI", 8), bg=ACCENT, fg="#c4b5fd"
                 ).pack(side="right", pady=18)

        # ── Notebook (tabs) ────────────────────────────────────────────────────
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG2, borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab",
                        background=BG2, foreground=TEXT2,
                        padding=[22, 9], font=("Segoe UI", 10),
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG3), ("active", BG3)],
                  foreground=[("selected", TEXT), ("active", TEXT)])

        style.configure("Purple.Horizontal.TProgressbar",
                        troughcolor=BG3, background=ACCENT,
                        darkcolor=ACCENT, lightcolor=ACCENT2,
                        bordercolor=BG3, thickness=14)

        style.configure("TCombobox",
                        fieldbackground=BG3, background=BG3,
                        foreground=TEXT, arrowcolor=TEXT2,
                        selectbackground=ACCENT)

        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.tab_setup   = tk.Frame(self.notebook, bg=BG)
        self.tab_browse  = tk.Frame(self.notebook, bg=BG)
        self.tab_extract = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_setup,   text="  \u2699  Setup  ")
        self.notebook.add(self.tab_browse,  text="  \U0001f4cb  Browse Chats  ")
        self.notebook.add(self.tab_extract, text="  \u25b6  Extract  ")

        self._build_setup_tab()
        self._build_browse_tab()
        self._build_extract_tab()

    # ───────────────────────────────────────────── SETUP TAB ──────────────────

    def _build_setup_tab(self):
        f = self.tab_setup

        # Centered card
        card = tk.Frame(f, bg=BG2, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.45, anchor="center", width=680, height=400)

        tk.Label(card, text="Configure Export Source & Destinations",
                 font=("Segoe UI", 14, "bold"), bg=BG2, fg=TEXT
                 ).pack(pady=(32, 6))

        tk.Label(card,
                 text="Point to your ChatGPT export ZIP (or the already-extracted folder),\n"
                      "then set where markdown and story files should be saved.",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT2,
                 justify="center").pack(pady=(0, 24))

        rows = tk.Frame(card, bg=BG2)
        rows.pack(fill="x", padx=50)

        PathRow(rows, "Source  (.zip or folder):", self.source_var,
                self._browse_source).pack(fill="x", pady=7)
        PathRow(rows, "Markdown output folder:", self.md_output_var,
                self._browse_md).pack(fill="x", pady=7)
        PathRow(rows, "Stories output folder:", self.story_output_var,
                self._browse_story).pack(fill="x", pady=7)

        self.load_btn = StyledButton(card, "\u25b6  Load Conversations",
                                     command=self._load_conversations)
        self.load_btn.pack(pady=(28, 8))

        self.load_status = tk.Label(card, text="",
                                    font=("Segoe UI", 9), bg=BG2, fg=TEXT2)
        self.load_status.pack()

    def _browse_source(self):
        # Try ZIP first, fall back to folder
        path = filedialog.askopenfilename(
            title="Select ChatGPT Export ZIP",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if not path:
            path = filedialog.askdirectory(title="Or select extracted folder")
        if path:
            self.source_var.set(path)

    def _browse_md(self):
        p = filedialog.askdirectory(title="Markdown Output Folder")
        if p:
            self.md_output_var.set(p)

    def _browse_story(self):
        p = filedialog.askdirectory(title="Stories Output Folder")
        if p:
            self.story_output_var.set(p)

    def _load_conversations(self):
        source = self.source_var.get().strip()
        if not source:
            messagebox.showwarning("No Source", "Please select a source ZIP or folder.")
            return
        if not os.path.exists(source):
            messagebox.showerror("Not Found", f"Path does not exist:\n{source}")
            return

        self.load_btn.configure(state="disabled", text="  Loading...  ")
        self.load_status.configure(text="Starting...", fg=TEXT2)

        def _do():
            try:
                raw = core.load_conversations(source, log=self._setup_log)
                parsed = [core.parse_conversation(c) for c in raw]
                self.conversations = parsed
                stories = sum(1 for c in parsed if c["is_story"])
                self.after(0, lambda: self._on_load_done(len(parsed), stories))
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_load_error(err))

        threading.Thread(target=_do, daemon=True).start()

    def _setup_log(self, msg):
        self.after(0, lambda m=msg: self.load_status.configure(text=m, fg=TEXT2))

    def _on_load_done(self, total, stories):
        self.load_btn.configure(state="normal", text="\u25b6  Load Conversations")
        self.load_status.configure(
            text=f"Loaded {total} conversations — {stories} stories detected", fg=GREEN)
        self._populate_browse_list()
        self.notebook.select(self.tab_browse)

    def _on_load_error(self, err):
        self.load_btn.configure(state="normal", text="\u25b6  Load Conversations")
        self.load_status.configure(text=f"Error: {err}", fg=RED)
        messagebox.showerror("Load Error", err)

    # ───────────────────────────────────────────── BROWSE TAB ─────────────────

    def _build_browse_tab(self):
        f = self.tab_browse

        # ── Toolbar ────────────────────────────────────────────────────────────
        tb = tk.Frame(f, bg=BG2, height=50)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        tk.Label(tb, text="  Search:", font=("Segoe UI", 9), bg=BG2, fg=TEXT2
                 ).pack(side="left", pady=14)

        search_entry = tk.Entry(tb, textvariable=self.search_var,
                                font=("Segoe UI", 10), bg=BG3, fg=TEXT,
                                insertbackground=TEXT, bd=0, relief="flat",
                                highlightthickness=1, highlightcolor=ACCENT,
                                highlightbackground=BORDER, width=28)
        search_entry.pack(side="left", ipady=6, padx=(4, 12), pady=10)

        # Filter combobox
        filter_cb = ttk.Combobox(tb, textvariable=self.filter_var,
                                  values=["All", "Stories Only", "Non-Stories"],
                                  width=14, state="readonly",
                                  font=("Segoe UI", 9))
        filter_cb.pack(side="left", padx=(0, 16))
        filter_cb.bind("<<ComboboxSelected>>", lambda _: self._filter_list())

        for text, cmd in [("Select All", self._select_all),
                           ("Stories Only", self._select_stories),
                           ("Deselect All", self._deselect_all)]:
            StyledButton(tb, text, command=cmd, accent=False, small=True
                         ).pack(side="left", padx=3, pady=10)

        self.sel_count_label = tk.Label(tb, text="0 selected",
                                        font=("Segoe UI", 9), bg=BG2, fg=TEXT2)
        self.sel_count_label.pack(side="right", padx=14)

        # ── Splitter: list | preview ────────────────────────────────────────────
        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True)

        # Left panel
        left = tk.Frame(body, bg=BG2, width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="  Conversations", font=("Segoe UI", 9, "bold"),
                 bg=BG2, fg=TEXT2, anchor="w").pack(fill="x", pady=(10, 4))

        lb_frame = tk.Frame(left, bg=BG2)
        lb_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        sb = tk.Scrollbar(lb_frame, orient="vertical", bg=BG2, troughcolor=BG3)
        self.chat_listbox = tk.Listbox(
            lb_frame, yscrollcommand=sb.set,
            font=("Segoe UI", 9),
            bg=BG2, fg=TEXT, bd=0, relief="flat",
            selectbackground=ACCENT, selectforeground="white",
            activestyle="none", highlightthickness=0,
            selectmode="extended"
        )
        sb.configure(command=self.chat_listbox.yview)
        sb.pack(side="right", fill="y")
        self.chat_listbox.pack(side="left", fill="both", expand=True)
        self.chat_listbox.bind("<<ListboxSelect>>", self._on_chat_select)

        # Divider
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel — preview
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Preview header bar
        ph = tk.Frame(right, bg=BG3, height=54)
        ph.pack(fill="x")
        ph.pack_propagate(False)

        self.preview_title_lbl = tk.Label(ph, text="Select a chat to preview",
                                          font=("Segoe UI", 11, "bold"),
                                          bg=BG3, fg=TEXT, anchor="w")
        self.preview_title_lbl.pack(side="left", padx=16, pady=14)

        self.preview_extract_btn = StyledButton(
            ph, "\u25b6  Extract This Chat", command=self._extract_current_chat,
            small=True)
        self.preview_extract_btn.pack(side="right", padx=12, pady=12)

        self.preview_meta_lbl = tk.Label(ph, text="", font=("Segoe UI", 8),
                                         bg=BG3, fg=TEXT2, anchor="e")
        self.preview_meta_lbl.pack(side="right", padx=8)

        # Preview text
        self.preview_text = scrolledtext.ScrolledText(
            right, font=("Segoe UI", 9), bg=BG, fg=TEXT2, bd=0, relief="flat",
            insertbackground=TEXT, wrap="word", highlightthickness=0,
            state="disabled"
        )
        self.preview_text.pack(fill="both", expand=True)

        # Text tags
        self.preview_text.tag_configure("title",
            font=("Segoe UI", 13, "bold"), foreground=TEXT)
        self.preview_text.tag_configure("meta",
            font=("Segoe UI", 8), foreground=TEXT2)
        self.preview_text.tag_configure("story_badge",
            font=("Segoe UI", 8, "bold"), foreground=AMBER,
            background="#422006", spacing1=2, spacing3=4)
        self.preview_text.tag_configure("role_you",
            font=("Segoe UI", 9, "bold"), foreground=BLUE)
        self.preview_text.tag_configure("role_gpt",
            font=("Segoe UI", 9, "bold"), foreground=TEAL)
        self.preview_text.tag_configure("sep",
            foreground=BORDER)
        self.preview_text.tag_configure("body",
            font=("Segoe UI", 9), foreground=TEXT,
            spacing1=2, spacing3=8)
        self.preview_text.tag_configure("truncated",
            font=("Segoe UI", 8, "italic"), foreground=TEXT2)

    def _populate_browse_list(self):
        self._filter_list()

    def _filter_list(self):
        search = self.search_var.get().lower().strip()
        mode = self.filter_var.get()

        self.chat_listbox.delete(0, "end")
        self._filtered_indices = []

        for i, conv in enumerate(self.conversations):
            if search and search not in conv["title"].lower():
                continue
            if mode == "Stories Only" and not conv["is_story"]:
                continue
            if mode == "Non-Stories" and conv["is_story"]:
                continue

            prefix = "\U0001f4d6 " if conv["is_story"] else "    "
            label = f"{prefix}{conv['title']}"
            self.chat_listbox.insert("end", label)
            self._filtered_indices.append(i)

        self._update_sel_label()

    def _on_chat_select(self, _event=None):
        sel = self.chat_listbox.curselection()
        self._update_sel_label()
        if not sel:
            return
        lb_idx = sel[-1]
        if lb_idx >= len(self._filtered_indices):
            return
        conv_idx = self._filtered_indices[lb_idx]
        self._current_preview_idx = conv_idx
        self._show_preview(conv_idx)

    def _show_preview(self, conv_idx):
        conv = self.conversations[conv_idx]
        self.preview_title_lbl.configure(text=conv["title"])
        self.preview_meta_lbl.configure(
            text=f"{conv['message_count']} messages  \u2022  {conv['created'][:10]}")

        pt = self.preview_text
        pt.configure(state="normal")
        pt.delete("1.0", "end")

        if conv["is_story"]:
            pt.insert("end", "  \U0001f4d6  STORY  ", "story_badge")
            pt.insert("end", "\n\n")

        pt.insert("end", conv["title"] + "\n", "title")
        pt.insert("end",
                  f"Created: {conv['created']}  \u2022  Updated: {conv['updated']}\n\n",
                  "meta")

        preview_limit = 60
        for msg in conv["messages"][:preview_limit]:
            role = core.get_role(msg)
            text = core.get_text(msg)
            char_limit = 1500
            truncated = len(text) > char_limit
            tag = "role_you" if role == "You" else "role_gpt"
            pt.insert("end", f"\n{role}\n", tag)
            pt.insert("end", "\u2500" * 48 + "\n", "sep")
            pt.insert("end", (text[:char_limit] + " \u2026" if truncated else text) + "\n",
                      "body")

        if len(conv["messages"]) > preview_limit:
            pt.insert("end",
                      f"\n  [ ... {len(conv['messages']) - preview_limit} more messages — "
                      f"extract to see full conversation ]\n", "truncated")

        pt.configure(state="disabled")
        pt.see("1.0")

    def _select_all(self):
        self.chat_listbox.select_set(0, "end")
        self._update_sel_label()

    def _select_stories(self):
        self.chat_listbox.selection_clear(0, "end")
        for lb_i, conv_i in enumerate(self._filtered_indices):
            if self.conversations[conv_i]["is_story"]:
                self.chat_listbox.selection_set(lb_i)
        self._update_sel_label()

    def _deselect_all(self):
        self.chat_listbox.selection_clear(0, "end")
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self.chat_listbox.curselection())
        self.sel_count_label.configure(text=f"{n} selected")

    def _extract_current_chat(self):
        if self._current_preview_idx is None:
            messagebox.showinfo("Nothing Selected", "Click a chat in the list first.")
            return
        conv = self.conversations[self._current_preview_idx]
        self._run_extraction([conv])
        self.notebook.select(self.tab_extract)

    # ───────────────────────────────────────────── EXTRACT TAB ────────────────

    def _build_extract_tab(self):
        f = self.tab_extract

        # Mode selector
        top = tk.Frame(f, bg=BG2)
        top.pack(fill="x")

        tk.Label(top, text="  Extraction Mode", font=("Segoe UI", 10, "bold"),
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=20, pady=(16, 6))

        rb_frame = tk.Frame(top, bg=BG2)
        rb_frame.pack(anchor="w", padx=32, pady=(0, 16))

        for val, label in [
            ("all",      "All Conversations"),
            ("stories",  "Stories Only"),
            ("selected", "Selected in Browse Tab"),
        ]:
            rb = tk.Radiobutton(
                rb_frame, text=label, variable=self.extract_mode, value=val,
                font=("Segoe UI", 10), bg=BG2, fg=TEXT,
                selectcolor=BG3, activebackground=BG2, activeforeground=TEXT,
                cursor="hand2"
            )
            rb.pack(side="left", padx=(0, 28))

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # Progress
        pf = tk.Frame(f, bg=BG)
        pf.pack(fill="x", padx=24, pady=(16, 0))

        tk.Label(pf, text="Progress", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=TEXT2).pack(anchor="w")

        self.progress_var = tk.DoubleVar(value=0)
        self.progressbar = ttk.Progressbar(
            pf, variable=self.progress_var, maximum=100,
            style="Purple.Horizontal.TProgressbar"
        )
        self.progressbar.pack(fill="x", pady=(4, 0))

        self.progress_label = tk.Label(pf, text="Ready",
                                       font=("Segoe UI", 8), bg=BG, fg=TEXT2)
        self.progress_label.pack(anchor="e", pady=(2, 0))

        # Log area
        lf = tk.Frame(f, bg=BG)
        lf.pack(fill="both", expand=True, padx=24, pady=(14, 0))

        tk.Label(lf, text="Live Log", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=TEXT2).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            lf, font=("Consolas", 9),
            bg=BG2, fg=TEXT2, bd=0, relief="flat",
            insertbackground=TEXT, wrap="word",
            highlightthickness=1, highlightcolor=BORDER,
            highlightbackground=BORDER, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, pady=(4, 0))
        self.log_text.tag_configure("story", foreground=AMBER, font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("done", foreground=GREEN, font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("err", foreground=RED)
        self.log_text.tag_configure("info", foreground=TEXT2)

        # Bottom action bar
        bar = tk.Frame(f, bg=BG2, height=68)
        bar.pack(fill="x", pady=(12, 0))
        bar.pack_propagate(False)

        self.extract_btn = StyledButton(
            bar, "  \u25b6  EXTRACT NOW  ",
            command=self._start_extraction
        )
        self.extract_btn.pack(side="left", padx=20, pady=14)

        open_btn = StyledButton(
            bar, "\U0001f4c2  Open Stories Folder",
            command=self._open_story_folder,
            accent=False, small=True
        )
        open_btn.pack(side="left", padx=4, pady=14)

        self.summary_label = tk.Label(bar, text="",
                                      font=("Segoe UI", 9), bg=BG2, fg=TEXT2)
        self.summary_label.pack(side="left", padx=14)

    def _open_story_folder(self):
        path = self.story_output_var.get()
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def _start_extraction(self):
        if not self.conversations:
            messagebox.showwarning("No Data", "Go to Setup and load your conversations first.")
            return

        mode = self.extract_mode.get()

        if mode == "all":
            convs = self.conversations

        elif mode == "stories":
            convs = [c for c in self.conversations if c["is_story"]]
            if not convs:
                messagebox.showinfo("No Stories Found",
                                    "No story conversations were detected.\n\n"
                                    "Check your source file and try reloading.")
                return

        elif mode == "selected":
            sel = self.chat_listbox.curselection()
            if not sel:
                messagebox.showwarning("Nothing Selected",
                                       "Go to Browse Chats and select conversations first.")
                return
            convs = [self.conversations[self._filtered_indices[i]] for i in sel]

        else:
            return

        self._run_extraction(convs)

    def _run_extraction(self, convs):
        self.extract_btn.configure(state="disabled", text="  Extracting...  ")
        self.summary_label.configure(text="")
        self.progress_var.set(0)
        self.progress_label.configure(text=f"0 / {len(convs)}")

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        md_out    = self.md_output_var.get()
        story_out = self.story_output_var.get()

        def _progress(cur, total):
            pct = (cur / total * 100) if total else 100
            self.after(0, lambda: self.progress_var.set(pct))
            self.after(0, lambda: self.progress_label.configure(text=f"{cur} / {total}"))

        def _log(msg):
            def _insert(m=msg):
                self.log_text.configure(state="normal")
                tag = ("story" if "Story ->" in m else
                       "done" if "Done!" in m else
                       "err" if "error" in m.lower() else "info")
                self.log_text.insert("end", m + "\n", tag)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            self.after(0, _insert)

        def _do():
            try:
                md_w, docx_w, skip = core.extract_conversations(
                    convs, md_out, story_out, log=_log, progress=_progress
                )
                self.after(0, lambda: self._on_extract_done(md_w, docx_w, skip, len(convs)))
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_extract_error(err))

        threading.Thread(target=_do, daemon=True).start()

    def _on_extract_done(self, md_w, docx_w, skip, total):
        self.extract_btn.configure(state="normal", text="  \u25b6  EXTRACT NOW  ")
        self.progress_var.set(100)
        self.summary_label.configure(
            text=f"Done!  Processed: {total}  |  Markdown: {md_w}  |  Stories: {docx_w}  |  Skipped: {skip}",
            fg=GREEN
        )
        messagebox.showinfo(
            "Extraction Complete!",
            f"All done!\n\n"
            f"  Conversations processed : {total}\n"
            f"  Markdown files saved    : {md_w}\n"
            f"  Story DOCX files saved  : {docx_w}\n"
            f"  Skipped (empty)         : {skip}\n\n"
            f"Stories saved to:\n  {self.story_output_var.get()}"
        )

    def _on_extract_error(self, err):
        self.extract_btn.configure(state="normal", text="  \u25b6  EXTRACT NOW  ")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"ERROR: {err}\n", "err")
        self.log_text.configure(state="disabled")
        messagebox.showerror("Extraction Error", err)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
