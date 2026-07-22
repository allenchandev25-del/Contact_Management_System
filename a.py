"""
===============================================================
  Campus Lost Item Image Finder
  ─────────────────────────────
  • Upload images of lost/found items
  • Store them in MySQL (blob or file path)
  • Compare uploaded query image against database
  • Tkinter GUI  |  PIL image processing  |  MySQL backend

  Requirements:
      pip install mysql-connector-python pillow

  MySQL Setup (run once in MySQL Workbench):
      CREATE DATABASE IF NOT EXISTS campus_lost_found;
===============================================================
"""

import io
import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import mysql.connector
from mysql.connector import Error
from PIL import Image, ImageTk, ImageFilter

# ─────────────────────────────────────────────
#  DATABASE CONFIGURATION
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "Kishore@2412",      # ← change this
    "database": "campus_lost_found",
}

THUMB_SIZE = (120, 120)   # thumbnail dimensions for grid view
MATCH_THUMB = (200, 200)  # larger thumbnail for match results


# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────
def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn if conn.is_connected() else None
    except Error as e:
        messagebox.showerror("DB Error", str(e))
        return None


def initialise_db():
    """Create tables if they do not exist."""
    conn = get_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lost_items (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(255)  NOT NULL,
            description TEXT,
            location    VARCHAR(255),
            status      ENUM('lost','found') DEFAULT 'lost',
            image_data  LONGBLOB,
            image_name  VARCHAR(255),
            posted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def insert_item(name, description, location, status, image_bytes, image_name):
    conn = get_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lost_items
              (name, description, location, status, image_data, image_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, description, location, status, image_bytes, image_name))
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return new_id


def fetch_all_items(status_filter="all"):
    conn = get_connection()
    if not conn:
        return []
    cur = conn.cursor(dictionary=True)
    if status_filter == "all":
        cur.execute("SELECT * FROM lost_items ORDER BY posted_at DESC")
    else:
        cur.execute(
            "SELECT * FROM lost_items WHERE status=%s ORDER BY posted_at DESC",
            (status_filter,)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_item(item_id):
    conn = get_connection()
    if not conn:
        return
    cur = conn.cursor()
    cur.execute("DELETE FROM lost_items WHERE id=%s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────
#  IMAGE SIMILARITY (histogram comparison)
# ─────────────────────────────────────────────
def image_histogram(pil_img: Image.Image) -> list:
    """Return a normalised RGB histogram (256 * 3 bins)."""
    img = pil_img.convert("RGB").resize((64, 64))
    hist = img.histogram()          # 768 values
    total = sum(hist) or 1
    return [v / total for v in hist]


def cosine_similarity(h1: list, h2: list) -> float:
    dot = sum(a * b for a, b in zip(h1, h2))
    mag1 = math.sqrt(sum(a * a for a in h1))
    mag2 = math.sqrt(sum(b * b for b in h2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def find_matches(query_img: Image.Image, items: list, top_n=5) -> list:
    """Return top_n items ranked by image similarity."""
    q_hist = image_histogram(query_img)
    scored = []
    for item in items:
        if not item.get("image_data"):
            continue
        try:
            db_img = Image.open(io.BytesIO(item["image_data"]))
            score = cosine_similarity(q_hist, image_histogram(db_img))
            scored.append((score, item))
        except Exception:
            pass
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]


# ─────────────────────────────────────────────
#  TKINTER APPLICATION
# ─────────────────────────────────────────────
class LostItemApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Campus Lost Item Image Finder")
        self.geometry("1050x700")
        self.configure(bg="#1a1a2e")
        self.resizable(True, True)

        self._photo_refs = []   # keep PhotoImage references alive
        self._upload_bytes = None
        self._upload_path = None
        self._query_bytes = None

        initialise_db()
        self._build_ui()
        self._load_items()

    # ── UI CONSTRUCTION ──────────────────────
    def _build_ui(self):
        # ── Colour palette ──
        BG       = "#1a1a2e"
        PANEL    = "#16213e"
        ACCENT   = "#e94560"
        FG       = "#eaeaea"
        ENTRY_BG = "#0f3460"
        BTN_BG   = "#e94560"

        self.configure(bg=BG)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                         background=PANEL, foreground=FG,
                         fieldbackground=PANEL, rowheight=28,
                         font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=ACCENT,
                         foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#e94560")])

        # ── Header ──
        hdr = tk.Frame(self, bg=ACCENT, height=52)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  Campus Lost Item Image Finder",
                 bg=ACCENT, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=18, pady=10)

        # ── Main pane ──
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # LEFT — form + search
        left = tk.Frame(main, bg=PANEL, width=300, bd=0,
                        highlightthickness=1, highlightbackground=ACCENT)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        self._add_section_label(left, "➕  Report an Item", ACCENT, FG)

        def lbl(parent, text):
            tk.Label(parent, text=text, bg=PANEL, fg=FG,
                     font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(6, 0))

        lbl(left, "Item Name *")
        self.e_name = self._entry(left, ENTRY_BG, FG)

        lbl(left, "Description")
        self.e_desc = tk.Text(left, height=3, bg=ENTRY_BG, fg=FG,
                              insertbackground=FG, relief="flat",
                              font=("Segoe UI", 10), wrap="word")
        self.e_desc.pack(fill="x", padx=12)

        lbl(left, "Last Seen Location")
        self.e_loc = self._entry(left, ENTRY_BG, FG)

        lbl(left, "Status")
        self.v_status = tk.StringVar(value="lost")
        rf = tk.Frame(left, bg=PANEL)
        rf.pack(anchor="w", padx=12, pady=4)
        for val, txt in [("lost", "Lost"), ("found", "Found")]:
            tk.Radiobutton(rf, text=txt, variable=self.v_status,
                           value=val, bg=PANEL, fg=FG,
                           selectcolor=ENTRY_BG,
                           activebackground=PANEL).pack(side="left", padx=6)

        # image upload
        self.upload_label = tk.Label(
            left, text="No image selected", bg=PANEL, fg="#888",
            font=("Segoe UI", 9, "italic"))
        self.upload_label.pack(padx=12, pady=(8, 2))
        self.img_preview = tk.Label(left, bg=PANEL)
        self.img_preview.pack(pady=2)

        tk.Button(left, text="📷  Choose Image", bg=ENTRY_BG, fg=FG,
                  relief="flat", cursor="hand2",
                  command=self._choose_upload_image).pack(padx=12, fill="x")

        tk.Button(left, text="✅  Submit Item", bg=BTN_BG, fg="white",
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 10, "bold"),
                  command=self._submit_item).pack(padx=12, pady=10, fill="x")

        # ── Search section ──
        sep = tk.Frame(left, bg=ACCENT, height=1)
        sep.pack(fill="x", padx=8, pady=4)
        self._add_section_label(left, "🔍  Search by Image", ACCENT, FG)

        self.search_label = tk.Label(
            left, text="No query image", bg=PANEL, fg="#888",
            font=("Segoe UI", 9, "italic"))
        self.search_label.pack(padx=12, pady=(6, 2))
        self.search_preview = tk.Label(left, bg=PANEL)
        self.search_preview.pack(pady=2)

        tk.Button(left, text="🖼  Choose Query Image", bg=ENTRY_BG, fg=FG,
                  relief="flat", cursor="hand2",
                  command=self._choose_query_image).pack(padx=12, fill="x")

        tk.Button(left, text="🔎  Find Matches", bg=BTN_BG, fg="white",
                  relief="flat", cursor="hand2",
                  font=("Segoe UI", 10, "bold"),
                  command=self._search_matches).pack(padx=12, pady=8, fill="x")

        # RIGHT — item list
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # filter bar
        fbar = tk.Frame(right, bg=BG)
        fbar.pack(fill="x", pady=(0, 6))
        tk.Label(fbar, text="Filter:", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(side="left")
        self.v_filter = tk.StringVar(value="all")
        for val, txt in [("all", "All"), ("lost", "Lost"), ("found", "Found")]:
            tk.Radiobutton(fbar, text=txt, variable=self.v_filter,
                           value=val, bg=BG, fg=FG, selectcolor=PANEL,
                           activebackground=BG,
                           command=self._load_items).pack(side="left", padx=6)

        tk.Button(fbar, text="🗑 Delete Selected", bg="#333", fg=FG,
                  relief="flat", cursor="hand2",
                  command=self._delete_selected).pack(side="right", padx=4)
        tk.Button(fbar, text="🔄 Refresh", bg="#333", fg=FG,
                  relief="flat", cursor="hand2",
                  command=self._load_items).pack(side="right", padx=4)

        # Treeview
        cols = ("ID", "Name", "Location", "Status", "Posted")
        self.tree = ttk.Treeview(right, columns=cols, show="headings",
                                 selectmode="browse")
        widths = [40, 200, 160, 70, 140]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center" if w < 100 else "w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._view_item_detail)

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        # ── Match results frame ──
        self.match_frame = tk.Frame(right, bg="#0f3460")
        self.match_title = tk.Label(self.match_frame, text="", bg="#0f3460",
                                    fg="#e94560",
                                    font=("Segoe UI", 11, "bold"))
        self.match_title.pack(pady=6)
        self.match_inner = tk.Frame(self.match_frame, bg="#0f3460")
        self.match_inner.pack(fill="x", padx=8)

    # ── HELPERS ──────────────────────────────
    def _entry(self, parent, bg, fg):
        e = tk.Entry(parent, bg=bg, fg=fg, insertbackground=fg,
                     relief="flat", font=("Segoe UI", 10))
        e.pack(fill="x", padx=12, pady=2)
        return e

    def _add_section_label(self, parent, text, bg, fg):
        tk.Label(parent, text=text, bg=bg, fg=fg,
                 font=("Segoe UI", 10, "bold")).pack(
                     fill="x", padx=0, pady=(10, 4))

    def _pil_to_photoimage(self, pil_img, size=THUMB_SIZE):
        pil_img.thumbnail(size, Image.LANCZOS)
        ph = ImageTk.PhotoImage(pil_img)
        self._photo_refs.append(ph)
        return ph

    # ── IMAGE PICKING ─────────────────────────
    def _choose_upload_image(self):
        path = filedialog.askopenfilename(
            title="Select item image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.webp")])
        if not path:
            return
        self._upload_path = path
        with open(path, "rb") as f:
            self._upload_bytes = f.read()
        img = Image.open(path)
        ph = self._pil_to_photoimage(img.copy())
        self.img_preview.configure(image=ph)
        self.upload_label.configure(
            text=os.path.basename(path), fg="#eaeaea")

    def _choose_query_image(self):
        path = filedialog.askopenfilename(
            title="Select query image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.webp")])
        if not path:
            return
        with open(path, "rb") as f:
            self._query_bytes = f.read()
        img = Image.open(path)
        ph = self._pil_to_photoimage(img.copy())
        self.search_preview.configure(image=ph)
        self.search_label.configure(
            text=os.path.basename(path), fg="#eaeaea")

    # ── SUBMIT ────────────────────────────────
    def _submit_item(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Item name is required.")
            return
        desc     = self.e_desc.get("1.0", "end").strip()
        loc      = self.e_loc.get().strip()
        status   = self.v_status.get()
        img_name = os.path.basename(self._upload_path) if self._upload_path else ""
        new_id = insert_item(name, desc, loc, status,
                              self._upload_bytes, img_name)
        if new_id:
            messagebox.showinfo("Saved", f"Item '{name}' saved (ID: {new_id}).")
            self._clear_form()
            self._load_items()

    def _clear_form(self):
        self.e_name.delete(0, "end")
        self.e_desc.delete("1.0", "end")
        self.e_loc.delete(0, "end")
        self.v_status.set("lost")
        self._upload_bytes = None
        self._upload_path = None
        self.img_preview.configure(image="")
        self.upload_label.configure(text="No image selected", fg="#888")

    # ── LOAD / REFRESH ────────────────────────
    def _load_items(self):
        self.match_frame.pack_forget()
        for row in self.tree.get_children():
            self.tree.delete(row)
        items = fetch_all_items(self.v_filter.get())
        for item in items:
            tag = item["status"]
            self.tree.insert("", "end", iid=str(item["id"]),
                             values=(item["id"], item["name"],
                                     item["location"] or "—",
                                     item["status"].upper(),
                                     str(item["posted_at"])[:16]),
                             tags=(tag,))
        self.tree.tag_configure("lost",  background="#2d1b1b")
        self.tree.tag_configure("found", background="#1b2d1b")

    # ── DELETE ────────────────────────────────
    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select an item first.")
            return
        if messagebox.askyesno("Confirm", "Delete selected item?"):
            delete_item(int(sel[0]))
            self._load_items()

    # ── DETAIL VIEW ───────────────────────────
    def _view_item_detail(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = int(sel[0])
        items = fetch_all_items()
        item = next((i for i in items if i["id"] == item_id), None)
        if not item:
            return

        win = tk.Toplevel(self)
        win.title(f"Item Detail — {item['name']}")
        win.configure(bg="#1a1a2e")
        win.geometry("420x520")
        win.grab_set()

        tk.Label(win, text=item["name"], bg="#1a1a2e", fg="#e94560",
                 font=("Segoe UI", 14, "bold")).pack(pady=(16, 4))
        tk.Label(win, text=f"Status: {item['status'].upper()}",
                 bg="#1a1a2e", fg="#eaeaea",
                 font=("Segoe UI", 11)).pack()
        tk.Label(win, text=f"Location: {item['location'] or '—'}",
                 bg="#1a1a2e", fg="#aaa",
                 font=("Segoe UI", 10)).pack(pady=2)
        tk.Label(win, text=item["description"] or "(no description)",
                 bg="#1a1a2e", fg="#ccc",
                 font=("Segoe UI", 10), wraplength=360,
                 justify="center").pack(pady=6)
        tk.Label(win, text=f"Posted: {str(item['posted_at'])[:16]}",
                 bg="#1a1a2e", fg="#777",
                 font=("Segoe UI", 9)).pack()

        if item.get("image_data"):
            try:
                img = Image.open(io.BytesIO(item["image_data"]))
                img.thumbnail((300, 300), Image.LANCZOS)
                ph = ImageTk.PhotoImage(img)
                self._photo_refs.append(ph)
                lbl = tk.Label(win, image=ph, bg="#1a1a2e")
                lbl.pack(pady=12)
            except Exception:
                tk.Label(win, text="(image unavailable)",
                         bg="#1a1a2e", fg="#888").pack()
        else:
            tk.Label(win, text="(no image)", bg="#1a1a2e", fg="#888").pack(pady=12)

        tk.Button(win, text="Close", bg="#e94560", fg="white",
                  relief="flat", command=win.destroy).pack(pady=8)

    # ── IMAGE SEARCH ──────────────────────────
    def _search_matches(self):
        if not self._query_bytes:
            messagebox.showwarning("No Image", "Please choose a query image first.")
            return
        query_img = Image.open(io.BytesIO(self._query_bytes))
        all_items = fetch_all_items()

        if not all_items:
            messagebox.showinfo("Empty", "No items in the database to compare.")
            return

        matches = find_matches(query_img, all_items, top_n=5)

        # clear previous results
        for w in self.match_inner.winfo_children():
            w.destroy()
        self._photo_refs.clear()

        self.match_title.configure(
            text=f"Top {len(matches)} Matches  (double-click item for details)")
        self.match_frame.pack(fill="x", pady=6)

        if not matches:
            tk.Label(self.match_inner, text="No image data found in DB.",
                     bg="#0f3460", fg="#aaa").pack()
            return

        for idx, (score, item) in enumerate(matches):
            card = tk.Frame(self.match_inner, bg="#16213e", bd=0,
                            highlightthickness=1,
                            highlightbackground="#e94560")
            card.grid(row=0, column=idx, padx=6, pady=4, sticky="n")

            if item.get("image_data"):
                try:
                    img = Image.open(io.BytesIO(item["image_data"]))
                    img.thumbnail(MATCH_THUMB, Image.LANCZOS)
                    ph = ImageTk.PhotoImage(img)
                    self._photo_refs.append(ph)
                    tk.Label(card, image=ph, bg="#16213e").pack(pady=4)
                except Exception:
                    tk.Label(card, text="img err", bg="#16213e",
                             fg="#888").pack(pady=4)

            tk.Label(card, text=item["name"], bg="#16213e", fg="#eaeaea",
                     font=("Segoe UI", 9, "bold"), wraplength=130).pack()
            tk.Label(card, text=f"Match: {score:.1%}", bg="#16213e",
                     fg="#e94560",
                     font=("Segoe UI", 9)).pack(pady=(0, 6))


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = LostItemApp()
    app.mainloop()