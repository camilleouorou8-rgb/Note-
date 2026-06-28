import sqlite3
import tkinter as tk
from tkinter import messagebox

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
    for i, nom in cur.execute("SELECT id, nom FROM notes"):
        liste.insert(tk.END, f"{i} - {nom}")

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

fenetre = tk.Tk()
fenetre.title("Notes")

nom = tk.Entry(fenetre, width=40)
nom.pack(pady=5)

contenu = tk.Text(fenetre, width=40, height=8)
contenu.pack()

tk.Button(fenetre, text="Ajouter", command=ajouter).pack()
tk.Button(fenetre, text="Modifier", command=modifier).pack()
tk.Button(fenetre, text="Supprimer", command=supprimer).pack()

liste = tk.Listbox(fenetre, width=45)
liste.pack(pady=5)
liste.bind("<Double-Button-1>", charger)

afficher()

fenetre.mainloop()
conn.close()