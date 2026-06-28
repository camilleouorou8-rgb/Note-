import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog
import textwrap

conn = sqlite3.connect("note_base.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT,
    contenu TEXT
)
""")
conn.commit()

note_id = None

def afficher():
    liste.delete(0, tk.END)
    for i, nom_note in cur.execute("SELECT id, nom FROM notes"):
        liste.insert(tk.END, f"{i} - {nom_note}")

def ajouter():
    cur.execute(
        "INSERT INTO notes(nom, contenu) VALUES(?, ?)",
        (nom.get(), contenu.get("1.0", tk.END).strip())
    )
    conn.commit()
    vider()
    afficher()

def charger(event):
    global note_id
    if not liste.curselection():
        return

    note_id = int(liste.get(liste.curselection()[0]).split(" - ")[0])

    n, c = cur.execute(
        "SELECT nom, contenu FROM notes WHERE id=?",
        (note_id,)
    ).fetchone()

    nom.delete(0, tk.END)
    nom.insert(0, n)

    contenu.delete("1.0", tk.END)
    contenu.insert("1.0", c)

def modifier():
    if note_id is None:
        return

    cur.execute(
        "UPDATE notes SET nom=?, contenu=? WHERE id=?",
        (nom.get(), contenu.get("1.0", tk.END).strip(), note_id)
    )
    conn.commit()
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

# --- Export PDF functions ---
def _create_pdf_for_notes(path, notes):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        messagebox.showerror("Dépendance manquante", "Le module 'reportlab' est requis pour exporter en PDF. Installez-le avec: pip install reportlab")
        return False

    width, height = A4
    c = canvas.Canvas(path, pagesize=A4)

    for idx, (title, body) in enumerate(notes, start=1):
        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 50, f"{idx}. {title}")

        # Body
        c.setFont("Helvetica", 11)
        textobject = c.beginText(40, height - 70)
        textobject.setLeading(14)

        if not body:
            body = ""

        for paragraph in body.splitlines():
            if not paragraph:
                textobject.textLine("")
                continue
            wrapped = textwrap.wrap(paragraph, 90)
            for line in wrapped:
                textobject.textLine(line)
        c.drawText(textobject)
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
        notes = [(nom.get().strip() or "Sans titre", contenu.get("1.0", tk.END).strip())]
    else:
        n, c = cur.execute("SELECT nom, contenu FROM notes WHERE id=?", (note_id,)).fetchone()
        notes = [(n or "Sans titre", c or "")]

    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Fichiers PDF", "*.pdf")], title="Enregistrer la note en PDF")
    if not path:
        return

    ok = _create_pdf_for_notes(path, notes)
    if ok:
        messagebox.showinfo("Export réussi", f"La note a été exportée en PDF:\n{path}")


def exporter_tout_pdf():
    # Export all notes in the database into one PDF (one note per page)
    rows = list(cur.execute("SELECT nom, contenu FROM notes"))
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

button_frame = tk.Frame(fenetre)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Ajouter", command=ajouter).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Modifier", command=modifier).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Supprimer", command=supprimer).pack(side=tk.LEFT, padx=5)
# New export buttons
tk.Button(button_frame, text="Exporter la note (PDF)", command=exporter_note_pdf).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Exporter tout (PDF)", command=exporter_tout_pdf).pack(side=tk.LEFT, padx=5)

liste = tk.Listbox(fenetre, width=45)
liste.pack(pady=5)
liste.bind("<Double-Button-1>", charger)

afficher()

fenetre.mainloop()
conn.close()
