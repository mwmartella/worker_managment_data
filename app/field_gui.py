"""
Field Management GUI
Manages the Fields database table.
Launched from the Santa Rita Control Panel.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math

import app.api_client as api
from app.org_gui import (
    FieldsTab,
    _apply_style,
    _maximize,
    _build_header,
    build_tree,
    EditDialog,
    _top,
)
from app.planting_gui import BlocksTab

SIDES = ["N", "S", "E", "W"]

# Rotating colour palette for variety colouring in the map
_VARIETY_PALETTE = [
    "#a8d8a8", "#f4a261", "#9ecae1", "#fdae6b", "#c5b0d5",
    "#f7b7a3", "#b7d4a8", "#ffdd94", "#d4a5a5", "#aec6e8",
    "#b5ead7", "#ffc8a2", "#d7bde2", "#a9cce3", "#f9e79f",
    "#a3d977", "#ffb347", "#87ceeb", "#dda0dd", "#98fb98",
]


# ─────────────────────────────────────────────────────────────────────
# Block Map Window – visual representation of a single block's rows
# ─────────────────────────────────────────────────────────────────────

class BlockMapWindow(tk.Toplevel):
    """Opens a canvas diagram showing all rows (and portions) of a block."""

    ROW_H    = 36   # height of each row bar in pixels
    ROW_GAP  = 8    # gap between rows
    LPAD     = 80   # left padding for row-number labels
    RPAD     = 220  # right padding for legend
    TPAD     = 60   # top padding
    BAR_W    = 820  # width of the bar area

    def __init__(self, parent, block: dict):
        super().__init__(parent)
        self.title(f"Block Map  —  {block['name']}")
        self.configure(bg="#f4f1ea")
        self.resizable(True, True)
        self.minsize(900, 400)

        _apply_style(self)

        # Header
        hdr = tk.Frame(self, bg="#2e5e2e", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"  🌿  {block['name']}",
                 font=("Segoe UI", 14, "bold"), bg="#2e5e2e", fg="white").pack(side="left", padx=14)
        if block.get("block_type"):
            tk.Label(hdr, text=block["block_type"],
                     font=("Segoe UI", 10), bg="#2e5e2e", fg="#c8e6c9").pack(side="left", padx=6)

        # Canvas in a scrollable frame
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        self._canvas = tk.Canvas(outer, bg="#fdfdf8", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical",   command=self._canvas.yview)
        hsb = ttk.Scrollbar(outer, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        ttk.Button(self, text="✕  Close", command=self.destroy).pack(pady=(0, 8))

        self._block  = block
        self._draw(block)

    # ── data loading & drawing ──────────────────────────────────────

    def _draw(self, block):
        try:
            rows     = api.get_block_rows(block_id=block["id"])
            portions = api.get_row_portions()          # get all, filter below
            varieties= api.get_varieties()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load map data:\n{e}", parent=self)
            return

        # index data
        var_map   = {v["id"]: v["name"] for v in varieties}
        port_by_row = {}
        for p in portions:
            port_by_row.setdefault(p["row_id"], []).append(p)
        for v in port_by_row.values():
            v.sort(key=lambda p: (p["sequence_no"] or 0))

        # assign colours to varieties encountered
        colour_map = {}
        palette_idx = 0
        def _colour(vid):
            nonlocal palette_idx
            if vid and vid not in colour_map:
                colour_map[vid] = _VARIETY_PALETTE[palette_idx % len(_VARIETY_PALETTE)]
                palette_idx += 1
            return colour_map.get(vid, "#e0e0e0")

        # pre-assign colours
        for p in portions:
            _colour(p.get("variety_id"))

        rows_sorted = sorted(rows, key=lambda r: (r["row_number"], r["side"] or ""))

        c        = self._canvas
        BAR_W    = self.BAR_W
        ROW_H    = self.ROW_H
        ROW_GAP  = self.ROW_GAP
        LPAD     = self.LPAD
        TPAD     = self.TPAD

        total_h  = TPAD + len(rows_sorted) * (ROW_H + ROW_GAP) + 60
        total_w  = LPAD + BAR_W + self.RPAD + 20

        c.configure(scrollregion=(0, 0, total_w, total_h))
        c.delete("all")

        # Title
        c.create_text(LPAD + BAR_W // 2, 20,
                      text=f"{block['name']}  —  {len(rows_sorted)} rows",
                      font=("Segoe UI", 12, "bold"), fill="#2e5e2e")

        if not rows_sorted:
            c.create_text(LPAD + BAR_W // 2, TPAD + 40,
                          text="No rows found for this block.",
                          font=("Segoe UI", 10, "italic"), fill="#888")
            return

        y = TPAD
        for row in rows_sorted:
            row_ports = port_by_row.get(row["id"], [])
            row_label = f"Row {row['row_number']}"
            if row.get("side"):
                row_label += f" ({row['side']})"

            # Row label on the left
            c.create_text(LPAD - 8, y + ROW_H // 2,
                          text=row_label, anchor="e",
                          font=("Segoe UI", 9, "bold"), fill="#333")

            if row_ports:
                # Divide bar proportionally by length_m
                lengths = [float(p["length_m"]) if p.get("length_m") else 1.0
                           for p in row_ports]
                total_len = sum(lengths) or 1.0

                x = LPAD
                for idx, (port, plen) in enumerate(zip(row_ports, lengths)):
                    seg_w = max(4, int(BAR_W * plen / total_len))
                    if idx == len(row_ports) - 1:
                        seg_w = LPAD + BAR_W - x  # fill remainder

                    col  = _colour(port.get("variety_id"))
                    vname= var_map.get(port.get("variety_id"), "?") if port.get("variety_id") else "—"

                    c.create_rectangle(x, y, x + seg_w, y + ROW_H,
                                       fill=col, outline="#888", width=1)

                    # Label inside segment if wide enough
                    lbl = vname
                    if port.get("clone_id"):
                        lbl += " ✦"
                    if seg_w > 50:
                        c.create_text(x + seg_w // 2, y + ROW_H // 2,
                                      text=lbl, font=("Segoe UI", 8),
                                      fill="#222", width=seg_w - 4)

                    # Tooltip-style popup
                    rect_id = c.create_rectangle(x, y, x + seg_w, y + ROW_H,
                                                  fill="", outline="", width=0)
                    tip_text = (f"Variety: {vname}\n"
                                f"Seq: {port.get('sequence_no', '')}\n"
                                f"Trees: {port.get('tree_count', '') or ''}\n"
                                f"Length: {port.get('length_m', '') or ''}m\n"
                                f"Year: {port.get('planting_year', '') or ''}")
                    self._bind_tooltip(c, rect_id, tip_text)
                    x += seg_w
            else:
                # Empty row – grey bar
                c.create_rectangle(LPAD, y, LPAD + BAR_W, y + ROW_H,
                                   fill="#e8e8e8", outline="#bbb", width=1)
                c.create_text(LPAD + BAR_W // 2, y + ROW_H // 2,
                              text="no portions", font=("Segoe UI", 8, "italic"), fill="#999")

            # Row length annotation on the right
            if row.get("row_length_m"):
                c.create_text(LPAD + BAR_W + 8, y + ROW_H // 2,
                              text=f"{row['row_length_m']} m", anchor="w",
                              font=("Segoe UI", 8), fill="#555")

            y += ROW_H + ROW_GAP

        # ── Legend ──────────────────────────────────────────────────
        lx = LPAD + BAR_W + 80
        ly = TPAD
        c.create_text(lx, ly - 16, text="Varieties", anchor="w",
                      font=("Segoe UI", 9, "bold"), fill="#333")
        for vid, col in colour_map.items():
            c.create_rectangle(lx, ly, lx + 18, ly + 14, fill=col, outline="#888")
            c.create_text(lx + 24, ly + 7, text=var_map.get(vid, vid[:8]),
                          anchor="w", font=("Segoe UI", 8), fill="#222")
            ly += 20

    # ── Tooltip helper ───────────────────────────────────────────────

    def _bind_tooltip(self, canvas, item_id, text):
        tip_win = []

        def _show(event):
            if tip_win:
                return
            tw = tk.Toplevel(self)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
            tk.Label(tw, text=text, justify="left",
                     background="#ffffcc", relief="solid", borderwidth=1,
                     font=("Segoe UI", 8), padx=4, pady=3).pack()
            tip_win.append(tw)

        def _hide(event):
            while tip_win:
                tip_win.pop().destroy()

        canvas.tag_bind(item_id, "<Enter>", _show)
        canvas.tag_bind(item_id, "<Leave>", _hide)


# ─────────────────────────────────────────────────────────────────────
# Block Maps Tab – grid of buttons, one per block
# ─────────────────────────────────────────────────────────────────────

class BlockMapsTab(ttk.Frame):
    COLS = 4  # buttons per row in the grid

    def __init__(self, parent):
        super().__init__(parent)
        self._block_buttons_frame = None
        self._build()
        try:
            self._load()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load blocks:\n{e}", parent=_top(self))

    def _build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(bar, text="Select a block to view its row map:",
                  font=("Segoe UI", 10, "italic")).pack(side="left")
        ttk.Button(bar, text="⟳  Refresh", command=self._load).pack(side="right")

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=10, pady=8)

        self._canvas = tk.Canvas(outer, bg="#f4f1ea", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", lambda e: self._reflow())
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._inner = ttk.Frame(self._canvas)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

    def _load(self):
        try:
            blocks = api.get_blocks()
            fields = {f["id"]: f["name"] for f in api.get_fields()}
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))
            return

        # Clear existing buttons
        for w in self._inner.winfo_children():
            w.destroy()

        if not blocks:
            ttk.Label(self._inner, text="No blocks found.",
                      font=("Segoe UI", 10, "italic")).grid(row=0, column=0, padx=20, pady=20)
            return

        # Group blocks by field
        from collections import defaultdict
        by_field = defaultdict(list)
        for b in sorted(blocks, key=lambda x: (fields.get(x.get("field_id"), ""), x["name"])):
            by_field[fields.get(b.get("field_id"), "Unknown Field")].append(b)

        row_idx = 0
        for field_name, field_blocks in sorted(by_field.items()):
            # Field header
            lbl = ttk.Label(self._inner, text=f"  📍  {field_name}",
                            font=("Segoe UI", 11, "bold"))
            lbl.grid(row=row_idx, column=0, columnspan=self.COLS,
                     sticky="w", padx=8, pady=(14, 4))
            row_idx += 1

            for col_idx, block in enumerate(field_blocks):
                btn_frame = tk.Frame(self._inner, bg="#2e5e2e",
                                     cursor="hand2", bd=0, relief="flat")
                btn_frame.grid(row=row_idx + col_idx // self.COLS,
                               column=col_idx % self.COLS,
                               padx=8, pady=6, sticky="nsew", ipadx=4, ipady=4)
                self._inner.columnconfigure(col_idx % self.COLS, weight=1, minsize=180)

                name_lbl = tk.Label(btn_frame, text=block["name"],
                                    font=("Segoe UI", 11, "bold"),
                                    bg="#2e5e2e", fg="white", padx=12, pady=8, cursor="hand2")
                name_lbl.pack(fill="x")

                sub_parts = []
                if block.get("block_type"):
                    sub_parts.append(block["block_type"])
                if block.get("code"):
                    sub_parts.append(f"Code: {block['code']}")
                if sub_parts:
                    sub_lbl = tk.Label(btn_frame, text="  ".join(sub_parts),
                                       font=("Segoe UI", 8), bg="#3d7a3d",
                                       fg="#c8e6c9", padx=12, pady=2, cursor="hand2")
                    sub_lbl.pack(fill="x")

                # Bind click to open map
                _b = block
                for widget in (btn_frame, name_lbl) + ((sub_lbl,) if sub_parts else ()):
                    widget.bind("<Button-1>", lambda e, b=_b: self._open_map(b))
                    widget.bind("<Enter>",
                                lambda e, f=btn_frame: f.configure(bg="#1a4a1a") or
                                [c.configure(bg="#1a4a1a") for c in f.winfo_children()])
                    widget.bind("<Leave>",
                                lambda e, f=btn_frame: f.configure(bg="#2e5e2e") or
                                [c.configure(bg="#2e5e2e" if i == 0 else "#3d7a3d")
                                 for i, c in enumerate(f.winfo_children())])

            row_idx += math.ceil(len(field_blocks) / self.COLS) + 1

    def _reflow(self):
        self._canvas.itemconfig(self._canvas_win, width=self._canvas.winfo_width())

    def _open_map(self, block):
        BlockMapWindow(self.winfo_toplevel(), block)


# ─────────────────────────────────────────────────────────────────────
# Block Rows Tab  (stripped: block, row#, side, lengths, notes)
# ─────────────────────────────────────────────────────────────────────

class BlockRowsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._block_map = {}
        self._build_form()
        self._build_filter()
        self._build_controls()
        self._build_tree()
        try:
            self._load_blocks()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load block rows on startup:\n{e}", parent=_top(self))

    def _build_form(self):
        form = ttk.LabelFrame(self, text="  New Block Row")
        form.pack(fill="x", padx=10, pady=(12, 0))
        f = ttk.Frame(form)
        f.pack(side="left", padx=10, pady=10)

        ttk.Label(f, text="Block:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.block_var = tk.StringVar()
        self.block_cb = ttk.Combobox(f, textvariable=self.block_var, state="readonly", width=22)
        self.block_cb.grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Button(f, text="\u27f3", width=3, command=self._load_blocks).grid(row=0, column=2, padx=2)

        ttk.Label(f, text="Row #:").grid(row=0, column=3, sticky="e", padx=6, pady=4)
        self.row_num_entry = ttk.Entry(f, width=6)
        self.row_num_entry.grid(row=0, column=4, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Side:").grid(row=0, column=5, sticky="e", padx=6, pady=4)
        self.side_var = tk.StringVar(value="")
        self.side_cb = ttk.Combobox(f, textvariable=self.side_var,
                                    values=[""] + SIDES, state="readonly", width=5)
        self.side_cb.grid(row=0, column=6, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Row L (m):").grid(row=0, column=7, sticky="e", padx=6, pady=4)
        self.rlength_entry = ttk.Entry(f, width=8)
        self.rlength_entry.grid(row=0, column=8, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Row W (m):").grid(row=0, column=9, sticky="e", padx=6, pady=4)
        self.rwidth_entry = ttk.Entry(f, width=8)
        self.rwidth_entry.grid(row=0, column=10, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Notes:").grid(row=0, column=11, sticky="e", padx=6, pady=4)
        self.notes_entry = ttk.Entry(f, width=26)
        self.notes_entry.grid(row=0, column=12, sticky="w", padx=6, pady=4)

        ttk.Button(f, text="Save", command=self._save).grid(row=0, column=13, padx=12)

    def _build_filter(self):
        fbar = ttk.Frame(self)
        fbar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(fbar, text="Filter by Block:").pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar(value="\u2014 All Blocks \u2014")
        self.filter_cb = ttk.Combobox(fbar, textvariable=self.filter_var,
                                      state="readonly", width=28)
        self.filter_cb.pack(side="left")
        self.filter_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

    def _build_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Button(bar, text="\u27f3  Refresh",           command=self.refresh).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="\u270e  Edit Selected",      command=self._edit).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="\U0001f5d1  Delete Record",  command=self._delete).pack(side="left")

    def _build_tree(self):
        cols = ["id", "block", "row_number", "side", "row_length_m",
                "row_width_m", "notes", "created_at", "updated_at"]
        widths = {"id": 80, "block": 150, "row_number": 60, "side": 44,
                  "row_length_m": 90, "row_width_m": 90,
                  "notes": 220, "created_at": 130, "updated_at": 130}
        self.tree = build_tree(self, cols, widths)

    def _load_blocks(self):
        try:
            self._block_map = {b["name"]: b["id"] for b in api.get_blocks()}
        except Exception as e:
            messagebox.showerror("Error loading blocks", str(e), parent=_top(self))
        self.block_cb["values"] = list(self._block_map.keys())
        if self._block_map:
            self.block_cb.current(0)
        all_lbl = "\u2014 All Blocks \u2014"
        choices = [all_lbl] + list(self._block_map.keys())
        current = self.filter_var.get()
        self.filter_cb["values"] = choices
        if current not in choices:
            self.filter_var.set(all_lbl)

    def _apply_filter(self):
        try:
            self._draw_rows(api.get_block_rows())
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def refresh(self):
        self._load_blocks()
        try:
            self._draw_rows(api.get_block_rows())
        except RuntimeError as e:
            messagebox.showerror("API Error",
                f"Could not load block rows.\n\n{e}\n\nMake sure the API server is running.",
                parent=_top(self))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _draw_rows(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        all_lbl   = "\u2014 All Blocks \u2014"
        filter_id = None if self.filter_var.get() == all_lbl else self._block_map.get(self.filter_var.get())
        blk_lkp   = {v: k for k, v in self._block_map.items()}
        for r in rows:
            if filter_id and r["block_id"] != filter_id:
                continue
            self.tree.insert("", "end", iid=r["id"], values=(
                r["id"][:8] + "\u2026",
                blk_lkp.get(r["block_id"], ""),
                r["row_number"],
                r["side"] or "",
                r["row_length_m"] or "",
                r["row_width_m"] or "",
                r["notes"] or "",
                (r["created_at"] or "")[:16],
                (r["updated_at"] or "")[:16],
            ))

    def _collect_form(self):
        block_id = self._block_map.get(self.block_var.get())
        side = self.side_var.get() or None
        if not block_id:
            messagebox.showerror("Validation", "Please select a Block.", parent=_top(self))
            return None
        try:
            row_number = int(self.row_num_entry.get().strip())
        except ValueError:
            messagebox.showerror("Validation", "Row # must be an integer.", parent=_top(self))
            return None
        def _od(e): v = e.get().strip(); return v if v else None
        return {
            "block_id":     str(block_id),
            "row_number":   row_number,
            "side":         side,
            "row_length_m": _od(self.rlength_entry),
            "row_width_m":  _od(self.rwidth_entry),
            "notes":        self.notes_entry.get().strip() or None,
        }

    def _save(self):
        payload = self._collect_form()
        if payload is None:
            return
        try:
            api.create_block_row(payload)
            for e in (self.row_num_entry, self.rlength_entry, self.rwidth_entry, self.notes_entry):
                e.delete(0, tk.END)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Please select a record first.", parent=_top(self))
            return None
        return sel[0]

    def _edit(self):
        iid = self._selected_id()
        if not iid:
            return
        row = next((r for r in api.get_block_rows() if r["id"] == iid), None)
        if not row:
            return

        result = {}

        dlg = tk.Toplevel(_top(self))
        dlg.title("Edit Block Row")
        dlg.resizable(False, False)
        dlg.grab_set()

        inner = ttk.Frame(dlg)
        inner.pack(padx=20, pady=16)

        def _lbl(text, r):
            ttk.Label(inner, text=text + ":").grid(row=r, column=0, sticky="e", padx=10, pady=6)

        # Block dropdown
        _lbl("Block", 0)
        block_var = tk.StringVar(value=next((k for k, v in self._block_map.items()
                                             if v == row["block_id"]), ""))
        ttk.Combobox(inner, textvariable=block_var, values=list(self._block_map.keys()),
                     state="readonly", width=30).grid(row=0, column=1, sticky="w", padx=10, pady=6)

        # Row number
        _lbl("Row #", 1)
        rn_var = tk.StringVar(value=str(row["row_number"]))
        ttk.Entry(inner, textvariable=rn_var, width=8).grid(row=1, column=1, sticky="w", padx=10, pady=6)

        # Side dropdown
        _lbl("Side", 2)
        side_var = tk.StringVar(value=row["side"] or "")
        ttk.Combobox(inner, textvariable=side_var, values=[""] + SIDES,
                     state="readonly", width=8).grid(row=2, column=1, sticky="w", padx=10, pady=6)

        # Row length
        _lbl("Row Length (m)", 3)
        rl_var = tk.StringVar(value=str(row["row_length_m"] or ""))
        ttk.Entry(inner, textvariable=rl_var, width=12).grid(row=3, column=1, sticky="w", padx=10, pady=6)

        # Row width
        _lbl("Row Width (m)", 4)
        rw_var = tk.StringVar(value=str(row["row_width_m"] or ""))
        ttk.Entry(inner, textvariable=rw_var, width=12).grid(row=4, column=1, sticky="w", padx=10, pady=6)

        # Notes
        _lbl("Notes", 5)
        notes_var = tk.StringVar(value=row["notes"] or "")
        ttk.Entry(inner, textvariable=notes_var, width=36).grid(row=5, column=1, sticky="w", padx=10, pady=6)

        def _save():
            side = side_var.get() or None
            if side is not None and side not in SIDES:
                messagebox.showerror("Validation", "Side must be N, S, E, W or blank.", parent=dlg)
                return
            try:
                rn = int(rn_var.get().strip())
            except ValueError:
                messagebox.showerror("Validation", "Row # must be an integer.", parent=dlg)
                return
            block_id = self._block_map.get(block_var.get())
            payload = {k: v for k, v in {
                "block_id":     str(block_id) if block_id else None,
                "row_number":   rn,
                "side":         side,
                "row_length_m": rl_var.get().strip() or None,
                "row_width_m":  rw_var.get().strip() or None,
                "notes":        notes_var.get().strip() or None,
            }.items() if v is not None}
            result["payload"] = payload
            dlg.destroy()

        btn = ttk.Frame(inner)
        btn.grid(row=6, column=0, columnspan=2, pady=12)
        ttk.Button(btn, text="Save",   command=_save).pack(side="left", padx=6)
        ttk.Button(btn, text="Cancel", command=dlg.destroy).pack(side="left", padx=6)

        dlg.wait_window()
        if not result.get("payload"):
            return
        try:
            api.update_block_row(iid, result["payload"])
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _delete(self):
        iid = self._selected_id()
        if not iid:
            return
        if not messagebox.askyesno("Confirm Delete", "Permanently delete this block row?", parent=_top(self)):
            return
        try:
            api.delete_block_row(iid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))


# ─────────────────────────────────────────────────────────────────────
# Row Portions Tab
# ─────────────────────────────────────────────────────────────────────

class RowPortionsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._row_map        = {}   # display label -> row_id
        self._row_id_to_block = {}  # row_id -> block_name
        self._row_id_to_block_id = {}  # row_id -> block_id
        self._row_id_to_number = {}  # row_id -> row_number
        self._row_id_to_side   = {}  # row_id -> side
        self._block_map      = {}   # block_name -> block_id
        self._variety_map    = {}
        self._clone_map      = {}
        self._rootstock_map  = {}
        self._build_form()
        self._build_filter()
        self._build_controls()
        self._build_tree()
        try:
            self._load_lookups()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load row portions on startup:\n{e}", parent=_top(self))

    # ...existing code...

    def _build_form(self):
        form = ttk.LabelFrame(self, text="  New Row Portion")
        form.pack(fill="x", padx=10, pady=(12, 0))

        r0 = ttk.Frame(form)
        r0.pack(fill="x", padx=10, pady=(8, 2))

        ttk.Label(r0, text="Row:").grid(row=0, column=0, sticky="e", padx=6, pady=3)
        self.row_var = tk.StringVar()
        self.row_cb = ttk.Combobox(r0, textvariable=self.row_var, state="readonly", width=24)
        self.row_cb.grid(row=0, column=1, sticky="w", padx=6, pady=3)
        ttk.Button(r0, text="\u27f3", width=3, command=self._load_lookups).grid(row=0, column=2, padx=2)

        ttk.Label(r0, text="Variety:").grid(row=0, column=3, sticky="e", padx=6, pady=3)
        self.variety_var = tk.StringVar()
        self.variety_cb = ttk.Combobox(r0, textvariable=self.variety_var, state="readonly", width=20)
        self.variety_cb.grid(row=0, column=4, sticky="w", padx=6, pady=3)

        ttk.Label(r0, text="Clone:").grid(row=0, column=5, sticky="e", padx=6, pady=3)
        self.clone_var = tk.StringVar()
        self.clone_cb = ttk.Combobox(r0, textvariable=self.clone_var, state="readonly", width=20)
        self.clone_cb.grid(row=0, column=6, sticky="w", padx=6, pady=3)

        ttk.Label(r0, text="Rootstock:").grid(row=0, column=7, sticky="e", padx=6, pady=3)
        self.rootstock_var = tk.StringVar()
        self.rootstock_cb = ttk.Combobox(r0, textvariable=self.rootstock_var, state="readonly", width=20)
        self.rootstock_cb.grid(row=0, column=8, sticky="w", padx=6, pady=3)

        r1 = ttk.Frame(form)
        r1.pack(fill="x", padx=10, pady=(2, 8))

        def _le(label, col, width=8):
            ttk.Label(r1, text=label).grid(row=0, column=col, sticky="e", padx=6, pady=3)
            e = ttk.Entry(r1, width=width)
            e.grid(row=0, column=col + 1, sticky="w", padx=6, pady=3)
            return e

        self.label_entry   = _le("Label:",         0, 14)
        self.seq_entry     = _le("Seq #:",          2, 6)
        self.year_entry    = _le("Plant Year:",     4, 6)
        self.tcount_entry  = _le("Tree Count:",     6, 7)
        self.length_entry  = _le("Length (m):",     8, 8)
        self.area_entry    = _le("Area (m\u00b2):", 10, 9)

        ttk.Label(r1, text="Notes:").grid(row=0, column=12, sticky="e", padx=6, pady=3)
        self.notes_entry = ttk.Entry(r1, width=26)
        self.notes_entry.grid(row=0, column=13, sticky="w", padx=6, pady=3)

        ttk.Button(r1, text="Save", command=self._save).grid(row=0, column=14, padx=12)

    def _build_filter(self):
        fbar = ttk.Frame(self)
        fbar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(fbar, text="Filter by Block:").pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar(value="\u2014 All Blocks \u2014")
        self.filter_cb = ttk.Combobox(fbar, textvariable=self.filter_var,
                                      state="readonly", width=28)
        self.filter_cb.pack(side="left")
        self.filter_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

    # ...existing code...

    def _build_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Button(bar, text="\u27f3  Refresh",           command=self.refresh).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="\u270e  Edit Selected",      command=self._edit).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="\U0001f5d1  Delete Record",  command=self._delete).pack(side="left")

    def _build_tree(self):
        cols = ["id", "block", "row_number", "side", "seq", "variety", "clone", "rootstock",
                "plant_year", "trees", "length_m", "area_m2", "notes",
                "created_at", "updated_at"]
        widths = {"id": 80, "block": 150, "row_number": 60, "side": 44, "seq": 44,
                  "variety": 140, "clone": 140, "rootstock": 130,
                  "plant_year": 72, "trees": 58, "length_m": 80, "area_m2": 74,
                  "notes": 180, "created_at": 128, "updated_at": 128}
        self.tree = build_tree(self, cols, widths)

    def _load_lookups(self):
        try:
            rows   = api.get_block_rows()
            blocks = {b["id"]: b["name"] for b in api.get_blocks()}
            self._block_map = {v: k for k, v in blocks.items()}  # name -> id

            self._row_map = {}
            self._row_id_to_block    = {}
            self._row_id_to_block_id = {}
            self._row_id_to_number   = {}
            self._row_id_to_side     = {}
            for r in rows:
                label = f"Row {r['row_number']}{(' ' + r['side']) if r['side'] else ''}"
                self._row_map[label]             = r["id"]
                self._row_id_to_block[r["id"]]    = blocks.get(r["block_id"], "")
                self._row_id_to_block_id[r["id"]] = r["block_id"]
                self._row_id_to_number[r["id"]]   = r["row_number"]
                self._row_id_to_side[r["id"]]     = r["side"] or ""

            self._variety_map   = {v["name"]: v["id"] for v in api.get_varieties()}
            self._clone_map     = {c["name"]: c["id"] for c in api.get_variety_clones()}
            self._rootstock_map = {"\u2014 None \u2014": None}
            self._rootstock_map.update({r["name"]: r["id"] for r in api.get_rootstocks()})
        except Exception as e:
            messagebox.showerror("Error loading lookups", str(e), parent=_top(self))

        self.row_cb["values"] = list(self._row_map.keys())
        if self._row_map:
            self.row_cb.current(0)

        self.variety_cb["values"] = list(self._variety_map.keys())
        if self._variety_map:
            self.variety_cb.current(0)

        self.clone_cb["values"] = [""] + list(self._clone_map.keys())
        self.clone_cb.current(0)

        self.rootstock_cb["values"] = list(self._rootstock_map.keys())
        self.rootstock_cb.current(0)

        all_lbl = "\u2014 All Blocks \u2014"
        choices = [all_lbl] + sorted(self._block_map.keys())
        current = self.filter_var.get()
        self.filter_cb["values"] = choices
        if current not in choices:
            self.filter_var.set(all_lbl)

    def _apply_filter(self):
        try:
            self._draw_portions(api.get_row_portions())
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def refresh(self):
        self._load_lookups()
        try:
            self._draw_portions(api.get_row_portions())
        except RuntimeError as e:
            messagebox.showerror("API Error",
                f"Could not load row portions.\n\n{e}\n\nMake sure the API server is running.",
                parent=_top(self))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _draw_portions(self, portions):
        for item in self.tree.get_children():
            self.tree.delete(item)
        all_lbl      = "\u2014 All Blocks \u2014"
        selected     = self.filter_var.get()
        filter_block_id = None if selected == all_lbl else self._block_map.get(selected)

        row_lkp = {v: k for k, v in self._row_map.items()}
        var_lkp = {v: k for k, v in self._variety_map.items()}
        cln_lkp = {v: k for k, v in self._clone_map.items()}
        rs_lkp  = {v: k for k, v in self._rootstock_map.items() if v is not None}

        for p in portions:
            row_block_id = self._row_id_to_block_id.get(p["row_id"])
            if filter_block_id and row_block_id != filter_block_id:
                continue
            self.tree.insert("", "end", iid=p["id"], values=(
                p["id"][:8] + "\u2026",
                self._row_id_to_block.get(p["row_id"], ""),
                self._row_id_to_number.get(p["row_id"], ""),
                self._row_id_to_side.get(p["row_id"], ""),
                p["sequence_no"] or "",
                var_lkp.get(p["variety_id"], ""),
                cln_lkp.get(p["clone_id"], "") if p["clone_id"] else "",
                rs_lkp.get(p["rootstock_id"], "") if p["rootstock_id"] else "",
                p["planting_year"] or "",
                p["tree_count"] or "",
                p["length_m"] or "",
                p["area_m2"] or "",
                p["notes"] or "",
                (p["created_at"] or "")[:16],
                (p["updated_at"] or "")[:16],
            ))

    def _collect_form(self):
        row_id       = self._row_map.get(self.row_var.get())
        variety_id   = self._variety_map.get(self.variety_var.get())
        clone_id     = self._clone_map.get(self.clone_var.get())
        rootstock_id = self._rootstock_map.get(self.rootstock_var.get())
        if not row_id:
            messagebox.showerror("Validation", "Please select a Row.", parent=_top(self))
            return None
        if not variety_id:
            messagebox.showerror("Validation", "Please select a Variety.", parent=_top(self))
            return None
        def _oi(e): v = e.get().strip(); return int(v) if v else None
        def _od(e): v = e.get().strip(); return v if v else None
        return {
            "row_id":        str(row_id),
            "portion_label": self.label_entry.get().strip() or None,
            "sequence_no":   _oi(self.seq_entry),
            "variety_id":    str(variety_id),
            "clone_id":      str(clone_id) if clone_id else None,
            "rootstock_id":  str(rootstock_id) if rootstock_id else None,
            "planting_year": _oi(self.year_entry),
            "tree_count":    _oi(self.tcount_entry),
            "length_m":      _od(self.length_entry),
            "area_m2":       _od(self.area_entry),
            "notes":         self.notes_entry.get().strip() or None,
        }

    def _save(self):
        payload = self._collect_form()
        if payload is None:
            return
        try:
            api.create_row_portion(payload)
            for e in (self.label_entry, self.seq_entry, self.year_entry,
                      self.tcount_entry, self.length_entry, self.area_entry, self.notes_entry):
                e.delete(0, tk.END)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Please select a record first.", parent=_top(self))
            return None
        return sel[0]

    def _edit(self):
        iid = self._selected_id()
        if not iid:
            return
        p = next((x for x in api.get_row_portions() if x["id"] == iid), None)
        if not p:
            return

        result = {}
        row_lkp = {v: k for k, v in self._row_map.items()}
        var_lkp = {v: k for k, v in self._variety_map.items()}
        cln_lkp = {v: k for k, v in self._clone_map.items()}
        rs_lkp  = {v: k for k, v in self._rootstock_map.items() if v is not None}

        dlg = tk.Toplevel(_top(self))
        dlg.title("Edit Row Portion")
        dlg.resizable(False, False)
        dlg.grab_set()

        inner = ttk.Frame(dlg)
        inner.pack(padx=20, pady=16)

        def _lbl(text, r):
            ttk.Label(inner, text=text + ":").grid(row=r, column=0, sticky="e", padx=10, pady=5)

        # Row (FK)
        _lbl("Row", 0)
        row_var = tk.StringVar(value=row_lkp.get(p["row_id"], ""))
        ttk.Combobox(inner, textvariable=row_var, values=list(self._row_map.keys()),
                     state="readonly", width=34).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # Variety (FK)
        _lbl("Variety", 1)
        var_var = tk.StringVar(value=var_lkp.get(p["variety_id"], ""))
        ttk.Combobox(inner, textvariable=var_var, values=list(self._variety_map.keys()),
                     state="readonly", width=34).grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Clone (FK, nullable)
        _lbl("Clone", 2)
        cln_var = tk.StringVar(value=cln_lkp.get(p["clone_id"], "") if p["clone_id"] else "")
        ttk.Combobox(inner, textvariable=cln_var,
                     values=[""] + list(self._clone_map.keys()),
                     state="readonly", width=34).grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Rootstock (FK, nullable)
        _lbl("Rootstock", 3)
        rs_var = tk.StringVar(value=rs_lkp.get(p["rootstock_id"], "") if p["rootstock_id"] else "\u2014 None \u2014")
        ttk.Combobox(inner, textvariable=rs_var,
                     values=list(self._rootstock_map.keys()),
                     state="readonly", width=34).grid(row=3, column=1, sticky="w", padx=10, pady=5)

        # Plain text fields
        def _entry(label, row_idx, current):
            _lbl(label, row_idx)
            v = tk.StringVar(value=str(current) if current is not None else "")
            ttk.Entry(inner, textvariable=v, width=20).grid(row=row_idx, column=1, sticky="w", padx=10, pady=5)
            return v

        lbl_var   = _entry("Label",         4, p["portion_label"])
        seq_var   = _entry("Seq #",         5, p["sequence_no"])
        year_var  = _entry("Planting Year", 6, p["planting_year"])
        tc_var    = _entry("Tree Count",    7, p["tree_count"])
        len_var   = _entry("Length (m)",    8, p["length_m"])
        area_var  = _entry("Area (m²)",     9, p["area_m2"])
        notes_var = _entry("Notes",        10, p["notes"])

        def _save():
            row_id      = self._row_map.get(row_var.get())
            variety_id  = self._variety_map.get(var_var.get())
            clone_id    = self._clone_map.get(cln_var.get()) if cln_var.get() else None
            rootstock_id = self._rootstock_map.get(rs_var.get())

            if not row_id:
                messagebox.showerror("Validation", "Please select a Row.", parent=dlg)
                return
            if not variety_id:
                messagebox.showerror("Validation", "Please select a Variety.", parent=dlg)
                return

            def _oi(v): s = v.get().strip(); return int(s) if s else None
            def _od(v): s = v.get().strip(); return s if s else None

            payload = {k: val for k, val in {
                "row_id":        str(row_id),
                "variety_id":    str(variety_id),
                "clone_id":      str(clone_id) if clone_id else None,
                "rootstock_id":  str(rootstock_id) if rootstock_id else None,
                "portion_label": _od(lbl_var),
                "sequence_no":   _oi(seq_var),
                "planting_year": _oi(year_var),
                "tree_count":    _oi(tc_var),
                "length_m":      _od(len_var),
                "area_m2":       _od(area_var),
                "notes":         _od(notes_var),
            }.items() if val is not None}
            result["payload"] = payload
            dlg.destroy()

        btn = ttk.Frame(inner)
        btn.grid(row=11, column=0, columnspan=2, pady=12)
        ttk.Button(btn, text="Save",   command=_save).pack(side="left", padx=6)
        ttk.Button(btn, text="Cancel", command=dlg.destroy).pack(side="left", padx=6)

        dlg.wait_window()
        if not result.get("payload"):
            return
        try:
            api.update_row_portion(iid, result["payload"])
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _delete(self):
        iid = self._selected_id()
        if not iid:
            return
        if not messagebox.askyesno("Confirm Delete", "Permanently delete this row portion?", parent=_top(self)):
            return
        try:
            api.delete_row_portion(iid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))


# ─────────────────────────────────────────────────────────────────────
# Window
# ─────────────────────────────────────────────────────────────────────

class FieldManagementWindow(tk.Toplevel):
    """Field Management UI — launched from the Santa Rita Control Panel."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Field Management")
        self.configure(bg="#f4f1ea")
        self.resizable(True, True)
        self.minsize(1100, 600)

        _apply_style(self)
        _maximize(self)
        _build_header(self, "Field Management",
                      "Santa Rita Farm  •  Manage farm fields")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        notebook.add(BlockMapsTab(notebook),   text="  🗺  Maps  ")
        notebook.add(FieldsTab(notebook),     text="  Fields  ")
        notebook.add(BlocksTab(notebook),     text="  Blocks  ")
        notebook.add(BlockRowsTab(notebook),  text="  Block Rows  ")
        notebook.add(RowPortionsTab(notebook), text="  Row Portions  ")

        self.grab_set()

