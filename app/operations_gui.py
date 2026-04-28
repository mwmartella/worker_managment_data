"""
Operations Setup GUI
Launched from the Santa Rita Control Panel.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import app.api_client as api
from app.org_gui import _apply_style, _maximize, _build_header, build_tree, EditDialog, _top


# ─────────────────────────────────────────────
# Job Types Tab
# ─────────────────────────────────────────────

class JobTypesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_form()
        self._build_controls()
        self._build_tree()
        self.refresh()

    def _build_form(self):
        form = ttk.LabelFrame(self, text="  New Job Type")
        form.pack(fill="x", padx=10, pady=(12, 0))
        f = ttk.Frame(form)
        f.pack(side="left", padx=10, pady=10)
        ttk.Label(f, text="Name:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.name_entry = ttk.Entry(f, width=28)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(f, text="Category (optional):").grid(row=0, column=2, sticky="e", padx=6, pady=4)
        self.category_entry = ttk.Entry(f, width=28)
        self.category_entry.grid(row=0, column=3, sticky="w", padx=6, pady=4)
        ttk.Label(f, text="Notes (optional):").grid(row=0, column=4, sticky="e", padx=6, pady=4)
        self.notes_entry = ttk.Entry(f, width=40)
        self.notes_entry.grid(row=0, column=5, sticky="w", padx=6, pady=4)
        ttk.Button(f, text="Save", command=self._save).grid(row=0, column=6, padx=12)

    def _build_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Button(bar, text="⟳  Refresh",       command=self.refresh).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="✎  Edit Selected",  command=self._edit).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="🗑  Delete Record",  command=self._delete).pack(side="left")

    def _build_tree(self):
        cols = ["id", "name", "category", "notes", "created_at", "updated_at"]
        self.tree = build_tree(self, cols, {
            "id": 90, "name": 220, "category": 160,
            "notes": 300, "created_at": 160, "updated_at": 160,
        })

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            for jt in api.get_job_types():
                self.tree.insert("", "end", iid=jt["id"], values=(
                    jt["id"][:8] + "…",
                    jt["name"],
                    jt["category"] or "",
                    jt["notes"] or "",
                    (jt["created_at"] or "")[:16],
                    (jt["updated_at"] or "")[:16],
                ))
        except RuntimeError as e:
            messagebox.showerror("API Error",
                f"Could not load job types.\n\n{e}\n\nMake sure the API server has been restarted and 'alembic upgrade head' has been run.",
                parent=_top(self))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _save(self):
        name     = self.name_entry.get().strip()
        category = self.category_entry.get().strip() or None
        notes    = self.notes_entry.get().strip() or None
        if not name:
            messagebox.showerror("Validation", "Name is required.", parent=_top(self))
            return
        try:
            api.create_job_type(name, category, notes)
            self.name_entry.delete(0, tk.END)
            self.category_entry.delete(0, tk.END)
            self.notes_entry.delete(0, tk.END)
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
        row = next((jt for jt in api.get_job_types() if jt["id"] == iid), None)
        if not row:
            return
        dlg = EditDialog(_top(self), "Edit Job Type", {
            "Name":     row["name"],
            "Category": row["category"] or "",
            "Notes":    row["notes"] or "",
        })
        if dlg.result is None:
            return
        try:
            api.update_job_type(
                iid,
                dlg.result["Name"],
                dlg.result["Category"] or None,
                dlg.result["Notes"] or None,
            )
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))

    def _delete(self):
        iid = self._selected_id()
        if not iid:
            return
        if not messagebox.askyesno("Confirm Delete", "Permanently delete this job type?", parent=_top(self)):
            return
        try:
            api.delete_job_type(iid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=_top(self))


# ─────────────────────────────────────────────
# Operations Setup Window
# ─────────────────────────────────────────────

class OperationsSetupWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Operations Setup")
        self.configure(bg="#f4f1ea")
        self.resizable(True, True)
        self.minsize(960, 560)
        _apply_style(self)
        _maximize(self)
        _build_header(self, "Operations Setup",
                      "Santa Rita Farm  •  Configure operational reference data")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        notebook.add(JobTypesTab(notebook), text="  Job Types  ")
        self.grab_set()

