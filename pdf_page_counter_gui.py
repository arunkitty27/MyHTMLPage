import os
import threading
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfReader

def count_pages_in_folder(folder, recursive=True, on_progress=None):
    total_pages = 0
    per_file = []
    skipped = 0

    def pdf_paths():
        if recursive:
            for root, _, files in os.walk(folder):
                for name in files:
                    if name.lower().endswith(".pdf"):
                        yield os.path.join(root, name)
        else:
            for name in os.listdir(folder):
                if name.lower().endswith(".pdf"):
                    yield os.path.join(folder, name)

    for i, path in enumerate(pdf_paths(), start=1):
        pages = None
        try:
            reader = PdfReader(path)
            # try empty password for simple encrypted PDFs
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            pages = len(reader.pages)
            total_pages += pages
            per_file.append((path, pages))
        except Exception as e:
            skipped += 1
            per_file.append((path, f"SKIPPED ({e})"))
        if on_progress:
            on_progress(i, path, pages)

    return total_pages, per_file, skipped

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Page Counter")
        self.geometry("760x520")
        self.resizable(True, True)

        self.folder = tk.StringVar()
        self.recursive = tk.BooleanVar(value=True)
        self.total_pages = tk.IntVar(value=0)

        # Top controls
        frm_top = ttk.Frame(self); frm_top.pack(fill="x", padx=10, pady=10)
        ttk.Label(frm_top, text="Folder:").pack(side="left")
        self.ent_folder = ttk.Entry(frm_top, textvariable=self.folder)
        self.ent_folder.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(frm_top, text="Choose…", command=self.choose_folder).pack(side="left", padx=5)
        ttk.Checkbutton(frm_top, text="Include subfolders", variable=self.recursive).pack(side="left")

        # Action buttons
        frm_btns = ttk.Frame(self); frm_btns.pack(fill="x", padx=10)
        self.btn_count = ttk.Button(frm_btns, text="Count Pages", command=self.start_count)
        self.btn_count.pack(side="left")
        self.btn_export = ttk.Button(frm_btns, text="Export CSV", command=self.export_csv, state="disabled")
        self.btn_export.pack(side="left", padx=6)

        # Progress
        frm_prog = ttk.Frame(self); frm_prog.pack(fill="x", padx=10, pady=(6,0))
        self.prog = ttk.Progressbar(frm_prog, mode="indeterminate")
        self.prog.pack(fill="x")

        # Results area
        frm_results = ttk.Frame(self); frm_results.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("File", "Pages")
        self.tree = ttk.Treeview(frm_results, columns=cols, show="headings")
        self.tree.heading("File", text="File")
        self.tree.heading("Pages", text="Pages")
        self.tree.column("File", width=560, anchor="w")
        self.tree.column("Pages", width=80, anchor="center")

        vsb = ttk.Scrollbar(frm_results, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Summary
        frm_sum = ttk.Frame(self); frm_sum.pack(fill="x", padx=10, pady=(0,10))
        self.lbl_total = ttk.Label(frm_sum, text="TOTAL PAGES: 0")
        self.lbl_total.pack(side="left")

        self.per_file = []

    def choose_folder(self):
        path = filedialog.askdirectory(title="Select folder that contains PDFs")
        if path:
            self.folder.set(path.replace("\\", "/"))

    def start_count(self):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showwarning("Missing folder", "Please choose a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Invalid folder", f"Not a folder:\n{folder}")
            return

        # Reset UI
        self.tree.delete(*self.tree.get_children())
        self.total_pages.set(0)
        self.lbl_total.config(text="TOTAL PAGES: 0")
        self.per_file = []
        self.btn_count.config(state="disabled")
        self.btn_export.config(state="disabled")
        self.prog.start(10)

        # Run in background so UI stays responsive
        threading.Thread(
            target=self._do_count,
            args=(folder, self.recursive.get()),
            daemon=True
        ).start()

    def _do_count(self, folder, recursive):
        def on_progress(i, path, pages):
            # Update UI safely from main thread
            self.after(0, self._add_row, path, pages)

        total, per_file, skipped = count_pages_in_folder(folder, recursive, on_progress=on_progress)
        self.per_file = per_file
        self.total_pages.set(total)
        self.after(0, self._finish_count, total)

    def _add_row(self, path, pages):
        display_pages = pages if isinstance(pages, int) else str(pages)
        self.tree.insert("", "end", values=(path, display_pages))

    def _finish_count(self, total):
        self.prog.stop()
        self.lbl_total.config(text=f"TOTAL PAGES: {total}")
        self.btn_count.config(state="normal")
        self.btn_export.config(state="normal")

    def export_csv(self):
        if not self.per_file:
            messagebox.showinfo("Nothing to export", "No results to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save results as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["File", "Pages"])
                for file_path, pages in self.per_file:
                    w.writerow([file_path, pages])
                w.writerow([])
                w.writerow(["TOTAL PAGES", self.total_pages.get()])
            messagebox.showinfo("Saved", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

if __name__ == "__main__":
    App().mainloop()
