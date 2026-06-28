import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog
import textwrap
import datetime

conn = sqlite3.connect("note_base.db")
cur = conn.cursor()

# Create table with created_at and updated_at (if not exists)
cur.execute("""
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT,
    contenu TEXT,
    created_at TEXT,
    updated_at TEXT
)
""")
conn.commit()

# Ensure existing databases get the new columns
cols = [row[1] for row in cur.execute("PRAGMA table_info(notes)")]
if 'created_at' not in cols:
    cur.execute("ALTER TABLE notes ADD COLUMN created_at TEXT")
if 'updated_at' not in cols:
    cur.execute("ALTER TABLE notes ADD COLUMN updated_at TEXT")
conn.commit()

note_id = None

def _now_str():
    return datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

def afficher():
    liste.delete(0, tk.END)
    for i, nom_note, created, updated in cur.execute("SELECT id, nom, updated_at FROM notes"):
        # show id - title (updated date)
        date_str = ''
        if updated:
            date_str = updated.split(' ')[0]
        liste.insert(tk.END, f"{i} - {nom_note} ({date_str})")

def ajouter():
    now = _now_str()
    cur.execute(
        "INSERT INTO notes(nom, contenu, created_at, updated_at) VALUES(?, ?, ?, ?)",
        (nom.get(), contenu.get("1.0", tk.END).strip(), now, now)
    )
    conn.commit()
    vider()
    afficher()

def charger(event):
    global note_id
    if not liste.curselection():
        return

    note_id = int(liste.get(liste.curselection()[0]).split(" - ")[0])

    n, c, created, updated = cur.execute(
        "SELECT nom, contenu, created_at, updated_at FROM notes WHERE id=?",
        (note_id,)
    ).fetchone()

    nom.delete(0, tk.END)
    nom.insert(0, n)

    contenu.delete("1.0", tk.END)
    contenu.insert("1.0", c)

    created_label.config(text=f"Créée: {created if created else '—'}")
    updated_label.config(text=f"Modifiée: {updated if updated else '—'}")

def modifier():
    if note_id is None:
        return

    now = _now_str()
    cur.execute(
        "UPDATE notes SET nom=?, contenu=?, updated_at=? WHERE id=?",
        (nom.get(), contenu.get("1.0", tk.END).strip(), now, note_id)
    )
    conn.commit()
    # refresh labels
    updated_label.config(text=f"Modifiée: {now}")
    afficher()

def supprimer():
    global note_id
    if note_id is None:
        return

    if messagebox.askyesno("Suppression", "Supprimer cette note ?"):
        cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
        note_id = None
        vider()
        afficher()

def vider():
    nom.delete(0, tk.END)
    contenu.delete("1.0", tk.END)
    created_label.config(text="Créée: —")
    updated_label.config(text="Modifiée: —")

# --- Export PDF functions ---
def _create_pdf_for_notes(path, notes):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
    except ImportError:
        messagebox.showerror("Dépendance manquante", "Le module 'reportlab' est requis pour exporter en PDF. Installez-le avec: pip install reportlab")
        return False

    width, height = A4
    left_margin = 20 * mm
    right_margin = 20 * mm
    top_margin = 20 * mm
    bottom_margin = 20 * mm
    content_width = width - left_margin - right_margin

    c = canvas.Canvas(path, pagesize=A4)

    total_pages = 0
    page_num = 0

    def _draw_header(page_num):
        # Header: app name left, export date right
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_margin, height - top_margin + 6 * mm, "Notes App")
        c.setFont("Helvetica", 8)
        date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        c.drawRightString(width - right_margin, height - top_margin + 6 * mm, f"Exporté: {date_str}")
        # horizontal rule
        c.setLineWidth(0.5)
        c.line(left_margin, height - top_margin + 4 * mm, width - right_margin, height - top_margin + 4 * mm)

    def _draw_footer(page_num):
        # Footer: page number centered
        c.setLineWidth(0.5)
        c.line(left_margin, bottom_margin - 6 * mm, width - right_margin, bottom_margin - 6 * mm)
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2.0, bottom_margin - 10 * mm, f"Page {page_num}")

    # Estimate characters per line based on content_width and font size
    body_font_size = 12
    approx_char_width = body_font_size * 0.5  # rough estimate in points
    chars_per_line = max(40, int(content_width / approx_char_width))

    for note_idx, note in enumerate(notes, start=1):
        # note can be (title, body) or (title, body, created, updated)
        if len(note) == 2:
            title, body = note
            created = updated = None
        else:
            title, body, created, updated = note

        page_num += 1
        _draw_header(page_num)

        # Title
        c.setFont("Helvetica-Bold", 16)
        y = height - top_margin - 10 * mm
        c.drawString(left_margin, y, f"{note_idx}. {title}")
        y -= 8 * mm

        # Metadata
        c.setFont("Helvetica-Oblique", 9)
        meta = []
        if created:
            meta.append(f"Créée: {created}")
        if updated:
            meta.append(f"Modifiée: {updated}")
        if meta:
            c.drawString(left_margin, y, " — ".join(meta))
            y -= 6 * mm

        # Body
        c.setFont("Times-Roman", body_font_size)
        leading = 14

        lines = []
        if body:
            for paragraph in body.splitlines():
                if not paragraph:
                    lines.append("")
                    continue
                wrapped = textwrap.wrap(paragraph, width=chars_per_line)
                if not wrapped:
                    lines.append("")
                else:
                    lines.extend(wrapped)
        else:
            lines = [""]

        for line in lines:
            if y < bottom_margin + 15:  # need new page
                _draw_footer(page_num)
                c.showPage()
                page_num += 1
                _draw_header(page_num)
                y = height - top_margin - 10 * mm
                c.setFont("Helvetica-Bold", 16)
                # put continuation marker
                c.drawString(left_margin, y, f"{note_idx}. {title} (suite)")
                y -= 8 * mm
                c.setFont("Times-Roman", body_font_size)

            c.drawString(left_margin, y, line)
            y -= leading

        # After finishing note, draw footer and new page
        _draw_footer(page_num)
        c.showPage()

    c.save()
    return True


def exporter_note_pdf():
    # Export the currently loaded note
    if note_id is None:
        # If no note is selected, allow exporting what's in the fields
        if not nom.get().strip() and not contenu.get("1.0", tk.END).strip():
            messagebox.showinfo("Aucune note", "Aucune note sélectionnée ou saisie à exporter.")
            return
        now = _now_str()
        notes = [(nom.get().strip() or "Sans titre", contenu.get("1.0", tk.END).strip(), now, now)]
    else:
        n, c_text, created, updated = cur.execute("SELECT nom, contenu, created_at, updated_at FROM notes WHERE id=?", (note_id,)).fetchone()
        notes = [(n or "Sans titre", c_text or "", created, updated)]

    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Fichiers PDF", "*.pdf")], title="Enregistrer la note en PDF")
    if not path:
        return

    ok = _create_pdf_for_notes(path, notes)
    if ok:
        messagebox.showinfo("Export réussi", f"La note a été exportée en PDF:\n{path}")


def exporter_tout_pdf():
    # Export all notes in the database into one PDF (one note per page)
    rows = list(cur.execute("SELECT nom, contenu, created_at, updated_at FROM notes"))
    if not rows:
        messagebox.showinfo("Aucune note", "Il n'y a aucune note à exporter.")
        return

    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Fichiers PDF", "*.pdf")], title="Enregistrer toutes les notes en PDF")
    if not path:
        return

    ok = _create_pdf_for_notes(path, rows)
    if ok:
        messagebox.showinfo("Export réussi", f"Toutes les notes ont été exportées en PDF:\n{path}")

# --- Fin export PDF ---

fenetre = tk.Tk()
fenetre.title("Notes")

nom = tk.Entry(fenetre, width=40)
nom.pack(pady=5)

contenu = tk.Text(fenetre, width=40, height=8)
contenu.pack()

# Labels for created/updated
created_label = tk.Label(fenetre, text="Créée: —")
created_label.pack()
updated_label = tk.Label(fenetre, text="Modifiée: —")
updated_label.pack()

button_frame = tk.Frame(fenetre)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Ajouter", command=ajouter).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Modifier", command=modifier).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Supprimer", command=supprimer).pack(side=tk.LEFT, padx=5)
# New export buttons
tk.Button(button_frame, text="Exporter la note (PDF)", command=exporter_note_pdf).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Exporter tout (PDF)", command=exporter_tout_pdf).pack(side=tk.LEFT, padx=5)

liste = tk.Listbox(fenetre, width=60)
liste.pack(pady=5)
liste.bind("<Double-Button-1>", charger)

afficher()

fenetre.mainloop()
conn.close()
