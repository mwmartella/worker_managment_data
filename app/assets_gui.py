"""Assets Management window – Equipment tab."""
import tkinter as tk
from tkinter import ttk, messagebox

import app.api_client as api
from app.gui import (
    _apply_style, _maximize, _build_header, _top,
    build_tree, EditDialog,
    BG_MAIN,
)

STATUS_OPTIONS = ["active", "inactive", "maintenance", "retired"]


class EquipmentTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._site_map: dict[str, str | None] = {}
        self._build_form()
        self._build_controls()
        self._build_tree()
        self.refresh()

    # ── Form ──────────────────────────────────────────────────────────────
    def _build_form(self):
        form = ttk.LabelFrame(self, text="  New Equipment")
        form.pack(fill="x", padx=10, pady=(12, 0))

        f = ttk.Frame(form)
        f.pack(fill="x", padx=10, pady=10)

        # Row 0
        ttk.Label(f, text="Name:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.name_entry = ttk.Entry(f, width=24)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Type:").grid(row=0, column=2, sticky="e", padx=6, pady=4)
        self.type_entry = ttk.Entry(f, width=18)
        self.type_entry.grid(row=0, column=3, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Manufacturer:").grid(row=0, column=4, sticky="e", padx=6, pady=4)
        self.manufacturer_entry = ttk.Entry(f, width=18)
        self.manufacturer_entry.grid(row=0, column=5, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Model:").grid(row=0, column=6, sticky="e", padx=6, pady=4)
        self.model_entry = ttk.Entry(f, width=18)
        self.model_entry.grid(row=0, column=7, sticky="w", padx=6, pady=4)

        # Row 1
        ttk.Label(f, text="Serial No:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.serial_entry = ttk.Entry(f, width=20)
        self.serial_entry.grid(row=1, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Mfg Year:").grid(row=1, column=2, sticky="e", padx=6, pady=4)
        self.mfg_year_entry = ttk.Entry(f, width=8)
        self.mfg_year_entry.grid(row=1, column=3, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Purchase Year:").grid(row=1, column=4, sticky="e", padx=6, pady=4)
        self.purch_year_entry = ttk.Entry(f, width=8)
        self.purch_year_entry.grid(row=1, column=5, sticky="w", padx=6, pady=4)

        ttk.Label(f, text="Status:").grid(row=1, column=6, sticky="e", padx=6, pady=4)
        self.status_var = tk.StringVar(value="active")
        self.status_cb = ttk.Combobox(f, textvariable=self.status_var,
                                      values=STATUS_OPTIONS, state="readonly", width=14)
        self.status_cb.grid(row=1, column=7, sticky="w", padx=6, pady=4)

        # Row 2
        ttk.Label(f, text="Site:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        self.site_var = tk.StringVar(value="— None —")
        self.site_cb = ttk.Combobox(f, textvariable=self.site_var, state="readonly", width=26)
        self.site_cb.grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Button(f, text="⟳", width=3, command=self._load_sites).grid(row=2, column=3, padx=2)

        ttk.Label(f, text="Notes:").grid(row=2, column=4, sticky="e", padx=6, pady=4)
        self.notes_entry = ttk.Entry(f, width=40)
        self.notes_entry.grid(row=2, column=5, columnspan=3, sticky="w", padx=6, pady=4)

        ttk.Button(f, text="Save", command=self._save).grid(row=2, column=8, padx=12)

        self._load_sites()

    def _load_sites(self):
        self._site_map = {"— None —": None}
        try:
            for s in api.get_sites():
                label = f"{s['name']} ({s['code'] or s['id'][:8]})"
                self._site_map[label] = s["id"]
        except Exception:
            pass
        self.site_cb["values"] = list(self._site_map.keys())
        self.site_cb.current(0)

    # ── Controls bar ──────────────────────────────────────────────────────
    def _build_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Button(bar, text="⟳  Refresh",      command=self.refresh).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="✎  Edit Selected", command=self._edit).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="🗑  Delete Record", command=self._delete).pack(side="left")

    # ── Tree ──────────────────────────────────────────────────────────────
    def _build_tree(self):
        cols = ["id", "name", "type", "manufacturer", "model",
                "serial_number", "mfg_year", "purch_year",
                "status", "site_id", "notes"]
        self.tree = build_tree(self, cols, {
            "id": 85, "name": 160, "type": 110, "manufacturer": 130,
            "model": 120, "serial_number": 130, "mfg_year": 80,
            "purch_year": 90, "status": 90, "site_id": 85, "notes": 200,
        })

    # ── Refresh ───────────────────────────────────────────────────────────
    def refresh(self):
        self._load_sites()
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            for eq in api.get_equipment():
                self.tree.insert("", "end", iid=eq["id"], values=(
                    eq["id"][:8] + "…",
                    eq["name"],
                    eq["equipment_type"] or "",
                    eq["manufacturer"] or "",
                    eq["model"] or "",
                    eq["serial_number"] or "",
                    eq["manufactured_year"] or "",
                    eq["purchase_year"] or "",
                    eq["status"],
                    (eq["site_id"] or "")[:8] + ("…" if eq["site_id"] else ""),
                    eq["notes"] or "",
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    # ── Save ──────────────────────────────────────────────────────────────
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Validation", "Name is required.", parent=_top(self))
            return

        def _int_or_none(val: str):
            v = val.strip()
            if not v:
                return None
            try:
                return int(v)
            except ValueError:
                raise ValueError(f"'{v}' is not a valid year.")

        try:
            mfg_year   = _int_or_none(self.mfg_year_entry.get())
            purch_year = _int_or_none(self.purch_year_entry.get())
        except ValueError as e:
            messagebox.showerror("Validation", str(e), parent=_top(self))
            return

        site_label = self.site_var.get()
        site_id = self._site_map.get(site_label)

        try:
            api.create_equipment(
                name=name,
                equipment_type=self.type_entry.get().strip() or None,
                manufacturer=self.manufacturer_entry.get().strip() or None,
                model=self.model_entry.get().strip() or None,
                serial_number=self.serial_entry.get().strip() or None,
                manufactured_year=mfg_year,
                purchase_year=purch_year,
                status=self.status_var.get() or "active",
                site_id=site_id,
                notes=self.notes_entry.get().strip() or None,
            )
            # Clear form
            for w in (self.name_entry, self.type_entry, self.manufacturer_entry,
                      self.model_entry, self.serial_entry, self.mfg_year_entry,
                      self.purch_year_entry, self.notes_entry):
                w.delete(0, tk.END)
            self.status_var.set("active")
            self.site_cb.current(0)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    # ── Helpers ───────────────────────────────────────────────────────────
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
        row = next((eq for eq in api.get_equipment() if eq["id"] == iid), None)
        if not row:
            return
        dlg = EditDialog(_top(self), "Edit Equipment", {
            "Name":          row["name"],
            "Type":          row["equipment_type"] or "",
            "Manufacturer":  row["manufacturer"] or "",
            "Model":         row["model"] or "",
            "Serial No":     row["serial_number"] or "",
            "Mfg Year":      str(row["manufactured_year"]) if row["manufactured_year"] else "",
            "Purchase Year": str(row["purchase_year"]) if row["purchase_year"] else "",
            "Status":        row["status"],
            "Notes":         row["notes"] or "",
        })
        if dlg.result is None:
            return

        def _int_or_none(val: str):
            v = val.strip()
            return int(v) if v else None

        try:
            payload = {
                "name":              dlg.result["Name"],
                "equipment_type":    dlg.result["Type"] or None,
                "manufacturer":      dlg.result["Manufacturer"] or None,
                "model":             dlg.result["Model"] or None,
                "serial_number":     dlg.result["Serial No"] or None,
                "manufactured_year": _int_or_none(dlg.result["Mfg Year"]),
                "purchase_year":     _int_or_none(dlg.result["Purchase Year"]),
                "status":            dlg.result["Status"] or "active",
                "notes":             dlg.result["Notes"] or None,
            }
            api.update_equipment(iid, **payload)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _delete(self):
        iid = self._selected_id()
        if not iid:
            return
        if not messagebox.askyesno("Confirm Delete",
                                   "Permanently delete this equipment record?",
                                   parent=_top(self)):
            return
        try:
            api.delete_equipment(iid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))


# ─────────────────────────────────────────────
# Assets Window
# ─────────────────────────────────────────────

class AssetsWindow(tk.Toplevel):
    """Assets management window launched from the Control Panel."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Assets")
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)
        self.minsize(1100, 600)

        _apply_style(self)
        _maximize(self)
        _build_header(self, "Assets",
                      "Santa Rita Farm  •  Manage equipment and farm assets")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        equipment_tab = EquipmentTab(notebook)
        notebook.add(equipment_tab, text="  Equipment  ")

        self.grab_set()



