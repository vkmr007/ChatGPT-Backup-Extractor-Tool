"""
extractor_core.py
-----------------
Pure extraction logic for the ChatGPT Export Extractor.
No print() calls — uses log_callback and progress_callback for GUI integration.
"""

import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone

# ── python-docx ───────────────────────────────────────────────────────────────
try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# ── Story detection keywords ──────────────────────────────────────────────────
STORY_KEYWORDS = [
    "chapter", "prologue", "epilogue", "marcus cain", "ghostrider",
    "narrative", "story", "fanfic", "fanfiction", "novel", "write a story",
    "continue the story", "scene", "dialogue", "fiction", "transformers",
    "autobot", "decepticon", "nest", "sector seven", "mission city",
    "character", "protagonist", "antagonist", "plot",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize(name, max_len=100):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().strip(".")
    return name[:max_len] if name else "Untitled"


def fmt_ts(ts):
    if ts:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass
    return "Unknown"


def get_text(message):
    if not message:
        return ""
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        parts = content.get("parts", [])
        texts = []
        for part in parts:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, dict):
                ct = part.get("content_type", "")
                if ct == "text":
                    texts.append(part.get("text", ""))
                else:
                    texts.append(f"[{ct}]")
        return "\n".join(texts).strip()
    return ""


def get_role(message):
    role = message.get("author", {}).get("role", "unknown")
    if role == "user":
        return "You"
    elif role == "assistant":
        return "ChatGPT"
    return role.capitalize()


def is_story(title, messages):
    combined = title.lower()
    for msg in messages[:5]:
        combined += " " + get_text(msg).lower()
    return any(kw in combined for kw in STORY_KEYWORDS)


def ordered_messages(mapping):
    """
    Walk the message tree and return an ordered list of messages.
    Builds children relationships from parent references because
    the ChatGPT export format does NOT include a 'children' field.
    Uses an iterative approach to avoid Python recursion limits on deep trees.
    """
    node_map = dict(mapping)

    # Build children lookup by inverting parent references
    children_map = {nid: [] for nid in node_map}
    root_id = None

    for node_id, node in node_map.items():
        parent = node.get("parent")
        if parent is None:
            root_id = node_id
        elif parent in children_map:
            children_map[parent].append(node_id)

    if not root_id:
        return []

    # Iterative DFS to avoid recursion limit on very long conversations
    result = []
    stack = [root_id]
    while stack:
        nid = stack.pop(0)
        node = node_map.get(nid)
        if not node:
            continue
        msg = node.get("message")
        if msg:
            result.append(msg)
        # Add children in order (reversed because we use insert-at-front logic)
        for child in children_map.get(nid, []):
            stack.append(child)

    return result


def filter_messages(messages):
    """Keep only user/assistant messages with actual text content."""
    out = []
    for msg in messages:
        role = msg.get("author", {}).get("role", "")
        if role not in ("user", "assistant"):
            continue
        if not get_text(msg):
            continue
        out.append(msg)
    return out


def unique_path(path):
    """Return a unique file path by appending (1), (2), etc. if needed."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base} ({counter}){ext}"):
        counter += 1
    return f"{base} ({counter}){ext}"


# ── DOCX writer ───────────────────────────────────────────────────────────────

def write_docx(title, created_str, updated_str, messages, out_path):
    doc = Document()

    heading = doc.add_heading(title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.add_run(
        f"Created: {created_str}    |    Last Updated: {updated_str}    |    Messages: {len(messages)}"
    )
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.runs[0].font.size = Pt(9)
    meta.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.add_paragraph()  # spacer

    for msg in messages:
        role = get_role(msg)
        text = get_text(msg)
        ts = fmt_ts(msg.get("create_time")) if msg.get("create_time") else ""

        sep = doc.add_paragraph()
        sep_run = sep.add_run("─" * 60)
        sep_run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        sep_run.font.size = Pt(8)

        role_line = doc.add_paragraph()
        role_run = role_line.add_run(role)
        role_run.bold = True
        role_run.font.size = Pt(10)
        if role == "ChatGPT":
            role_run.font.color.rgb = RGBColor(0x10, 0xA3, 0x7F)
        else:
            role_run.font.color.rgb = RGBColor(0x20, 0x60, 0xD0)
        if ts:
            ts_run = role_line.add_run(f"  {ts}")
            ts_run.font.size = Pt(8)
            ts_run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

        for para_text in text.split("\n"):
            p = doc.add_paragraph(para_text)
            p.style.font.size = Pt(11)

    doc.save(out_path)


# ── Public API ────────────────────────────────────────────────────────────────

def load_conversations(source_path, log=None):
    """
    Load conversations from a .zip file or an extracted folder.
    Returns a list of raw conversation dicts.
    """
    def _log(msg):
        if log:
            log(msg)

    # Unzip if needed
    if source_path.lower().endswith(".zip"):
        extract_dir = source_path[:-4] + "_extracted"
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir, exist_ok=True)
            _log("Extracting ZIP archive (this may take a minute)...")
            with zipfile.ZipFile(source_path, "r") as z:
                z.extractall(extract_dir)
            _log("Extraction complete.")
        else:
            _log("ZIP already extracted — loading from cache.")
        source_path = extract_dir

    # Find all conversation JSON files
    conv_files = []
    for root, dirs, files in os.walk(source_path):
        for fname in sorted(files):
            if fname == "conversations.json" or (
                fname.startswith("conversations-") and fname.endswith(".json")
            ):
                conv_files.append(os.path.join(root, fname))

    if not conv_files:
        raise FileNotFoundError(
            f"No conversations JSON file(s) found in:\n{source_path}"
        )

    _log(f"Found {len(conv_files)} conversation file(s).")

    conversations = []
    for cf in conv_files:
        _log(f"Loading {os.path.basename(cf)}...")
        with open(cf, "r", encoding="utf-8") as f:
            chunk = json.load(f)
        conversations.extend(chunk)
        _log(f"  -> {len(chunk)} conversations")

    _log(f"Total loaded: {len(conversations)} conversations.")
    return conversations


def parse_conversation(conv):
    """Parse a raw conversation dict into a clean structured dict."""
    title = conv.get("title") or "Untitled"
    create_ts = conv.get("create_time")
    update_ts = conv.get("update_time")
    mapping = conv.get("mapping", {})

    created_str = fmt_ts(create_ts)
    updated_str = fmt_ts(update_ts)
    date_prefix = created_str[:10] if create_ts else "0000-00-00"

    msgs = ordered_messages(mapping)
    filtered = filter_messages(msgs)
    story = is_story(title, filtered) if filtered else False

    return {
        "title": title,
        "created": created_str,
        "updated": updated_str,
        "date_prefix": date_prefix,
        "messages": filtered,
        "is_story": story,
        "message_count": len(filtered),
    }


def extract_conversations(parsed_convs, md_output, story_output, log=None, progress=None):
    """
    Write parsed conversations to disk.
    - All conversations -> .md files in md_output
    - Story conversations -> .docx files in story_output

    Calls:
        log(msg_str) for notable events
        progress(current_int, total_int) for progress updates
    """
    def _log(msg):
        if log:
            log(msg)

    os.makedirs(md_output, exist_ok=True)
    os.makedirs(story_output, exist_ok=True)

    md_written = 0
    docx_written = 0
    skipped = 0
    total = len(parsed_convs)

    for i, conv in enumerate(parsed_convs):
        if progress:
            progress(i, total)

        filtered = conv["messages"]
        if not filtered:
            skipped += 1
            continue

        title = conv["title"]
        safe_title = sanitize(title)
        date_prefix = conv["date_prefix"]
        created_str = conv["created"]
        updated_str = conv["updated"]

        # ── Write Markdown ────────────────────────────────────────────────────
        md = f"# {title}\n\n"
        md += f"**Created:** {created_str}  \n"
        md += f"**Last Updated:** {updated_str}  \n"
        md += f"**Messages:** {len(filtered)}\n\n"
        md += "---\n\n"

        for msg in filtered:
            role = get_role(msg)
            text = get_text(msg)
            ts = msg.get("create_time")
            ts_str = fmt_ts(ts) if ts else ""
            md += f"### **{role}**"
            if ts_str:
                md += f" <sup>{ts_str}</sup>"
            md += f"\n\n{text}\n\n---\n\n"

        md_path = unique_path(os.path.join(md_output, f"{date_prefix} - {safe_title}.md"))
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        md_written += 1

        # ── Write DOCX if story ───────────────────────────────────────────────
        if DOCX_AVAILABLE and conv["is_story"]:
            docx_path = unique_path(os.path.join(story_output, f"{safe_title}.docx"))
            write_docx(title, created_str, updated_str, filtered, docx_path)
            docx_written += 1
            _log(f"Story -> {os.path.basename(docx_path)}")

    if progress:
        progress(total, total)

    _log(f"Done!  Markdown: {md_written}  |  Stories: {docx_written}  |  Skipped: {skipped}")
    return md_written, docx_written, skipped
