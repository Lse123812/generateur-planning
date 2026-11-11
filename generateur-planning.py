#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La Bonne Frite fast food – Planning des équipiers (version Python / Tkinter).

Lancer :  python3 la_bonne_frite.py
Deux fenêtres s'ouvrent : la vue du patron et la vue d'un équipier.
Aucune base de données, aucune donnée enregistrée : tout disparaît à la fermeture.
"""
import base64
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk

LOGO = "%%LOGO%%"
PRUNE, ROSE, MAUVE, CREME, OR = "#542D43", "#D98BAA", "#86536A", "#FFF0D9", "#F5B642"
BLANC, ROUGE, VERT, ROSEPALE = "#FFFFFF", "#B3261E", "#2F7D4F", "#F7DDE6"
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
PAUSE = 30  # minutes de pause : fixe pour tous les services
# poste -> (jours de service [0 = lundi], début, fin)
POSTES = {
    "Caisse": ([1, 2, 3, 4, 5], "11:00", "18:30"),
    "Friteuse et cuisine": ([0, 1, 2, 3, 4], "10:30", "18:00"),
    "Grill et burgers": ([2, 3, 4, 5, 6], "11:30", "19:00"),
    "Préparation et stock": ([0, 1, 2, 3, 4], "07:30", "15:00"),
    "Salle et accueil": ([0, 3, 4, 5, 6], "12:00", "19:30"),
    "Livraison et plonge": ([3, 4, 5, 6, 0], "17:00", "22:00"),
}


# ------------------------------------------------------------------ outils
def hm(s):
    """'HH:MM' -> minutes, ou None si vide / invalide."""
    try:
        h, m = s.split(":")
        h, m = int(h), int(m)
        return h * 60 + m if 0 <= h < 24 and 0 <= m < 60 else None
    except (ValueError, AttributeError):
        return None


def ft(m):
    return "%02d:%02d" % ((m // 60) % 24, m % 60)


def fh(m):
    m = int(round(m))
    return "%d h %02d" % (m // 60, m % 60)


def now_min():
    n = datetime.now()
    return n.hour * 60 + n.minute


def semaine():
    lun = date.today() - timedelta(days=date.today().weekday())
    return [lun + timedelta(days=i) for i in range(7)]


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


class Equipier:
    def __init__(self, n, poste, entree, naiss):
        self.n, self.poste, self.entree, self.naiss = n, poste, entree, naiss
        self.nom = self.prenom = ""
        self.photo = None
        self.days = {}  # "AAAA-MM-JJ" -> {ps, pe, pp, as, ae, pb, pst}

    def nom_affiche(self):
        t = ("%s %s" % (self.prenom, self.nom)).strip()
        return t or "Équipier n°%d" % self.n

    def age(self):
        t = date.today()
        return t.year - self.naiss.year - ((t.month, t.day) < (self.naiss.month, self.naiss.day))

    def limites(self):
        a = self.age()
        if a < 16:
            return dict(d=420, pb=270, pm=30, r=840, n=20)
        if a < 18:
            return dict(d=480, pb=270, pm=30, r=720, n=22)
        return dict(d=600, pb=360, pm=20, r=660, n=None)

    def eff(self, d):
        """Horaire effectif d'un jour : pointage s'il existe, sinon planning."""
        r = self.days.get(d.isoformat(), {})
        if r.get("as"):
            live = not r.get("ae") and d == date.today()
            p = r.get("pb", 0) + ((now_min() - r["pst"]) if r.get("pst") is not None and live else 0)
            return dict(s=r["as"], e=r.get("ae") or (ft(now_min()) if live else None), p=p, live=live)
        return dict(s=r.get("ps"), e=r.get("pe"), p=r.get("pp", 0) if r.get("ps") or r.get("pe") else 0, live=False)

    @staticmethod
    def span(x):
        a, b = hm(x["s"]), hm(x["e"])
        if a is None or b is None:
            return None
        return (a, b + 1440) if b < a else (a, b)

    def travail(self, x):
        q = self.span(x)
        return q[1] - q[0] - x["p"] if q else 0

    def totaux(self):
        s = p = 0
        for d in semaine():
            x = self.eff(d)
            if self.span(x):
                s += self.travail(x)
                p += x["p"]
        return s, p

    def alertes(self):
        """Liste de (avertissement?, texte) : horaires impossibles."""
        L, out, tot, prev, any_ = self.limites(), [], 0, None, False
        if not self.nom or not self.prenom:
            out.append((True, "Profil incomplet : nom ou prénom manquant."))
        for i, d in enumerate(semaine()):
            x, j = self.eff(d), JOURS[i]
            q = self.span(x)
            if x["s"] and not x["e"] and not x["live"]:
                out.append((False, "%s : case vide, heure de fin manquante. Comptabilisation impossible." % j))
                prev = None
                continue
            if not x["s"] and x["e"]:
                out.append((False, "%s : case vide, heure de début manquante." % j))
                prev = None
                continue
            if not q:
                prev = None
                continue
            any_ = True
            w, g = self.travail(x), q[1] - q[0]
            tot += w
            if w > L["d"]:
                out.append((False, "%s : %s de travail, maximum %s par jour." % (j, fh(w), fh(L["d"]))))
            if g > L["pb"] and x["p"] < L["pm"]:
                out.append((False, "%s : pause de %d min obligatoire (actuelle : %d min)." % (j, L["pm"], x["p"])))
            if L["n"] and (q[1] > L["n"] * 60 or q[0] < 360):
                out.append((False, "%s : travail de nuit interdit (entre %d h et 6 h) pour ce salarié." % (j, L["n"])))
            if prev is not None and q[0] + 1440 - prev < L["r"]:
                out.append((False, "%s : repos de %s seulement avant ce service, minimum %d h consécutives."
                            % (j, fh(q[0] + 1440 - prev), L["r"] // 60)))
            prev = q[1]
        if tot > 2100:
            out.append((False, "Semaine : %s de travail, maximum 35 h." % fh(tot)))
        if any_:
            off = [not self.span(self.eff(d)) for d in semaine()]
            if self.age() < 18:
                if not (off[6] and (off[5] or off[0])):
                    out.append((False, "Repos hebdomadaire : 2 jours consécutifs minimum, dimanche inclus, pour un mineur."))
            elif not any(off):
                out.append((False, "Repos hebdomadaire : 24 h consécutives minimum par semaine."))
        return out


# ------------------------------------------------------------------ widgets
class Scroll(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=CREME)
        self.c = tk.Canvas(self, bg=CREME, highlightthickness=0)
        sb = tk.Scrollbar(self, command=self.c.yview)
        self.inner = tk.Frame(self.c, bg=CREME)
        self.win = self.c.create_window((0, 0), window=self.inner, anchor="nw")
        self.c.configure(yscrollcommand=sb.set)
        self.c.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.c.configure(scrollregion=self.c.bbox("all")))
        self.c.bind("<Configure>", lambda e: self.c.itemconfigure(self.win, width=e.width))
        self.c.bind("<Enter>", self._bind)

    def _bind(self, _):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.c.bind_all(ev, self._wheel)

    def _wheel(self, e):
        self.c.yview_scroll(-1 if (getattr(e, "delta", 0) > 0 or e.num == 4) else 1, "units")

    def vider(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.c.yview_moveto(0)


class Glisseur(tk.Canvas):
    """Bouton à faire glisser (comme FAIRTIQ) : valide quand on arrive au bout."""

    def __init__(self, master, texte, cmd, bg=ROSE, fg=PRUNE, font=None, w=340, h=60):
        super().__init__(master, width=w, height=h, bg=CREME, highlightthickness=0)
        self.w, self.h, self.cmd = w, h, cmd
        r = h // 2
        self.create_oval(0, 0, h, h, fill=bg, outline="")
        self.create_oval(w - h, 0, w, h, fill=bg, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=bg, outline="")
        self.create_text(w / 2 + 25, r, text=texte, fill=fg, font=font)
        self.th = self.create_oval(5, 5, h - 5, h - 5, fill=PRUNE, outline="")
        self.ar = self.create_text(r, r, text="➜", fill="white", font=font)
        self.pos = r
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)

    def _place(self, x):
        r = self.h // 2
        x = max(r, min(self.w - r, x))
        self.coords(self.th, x - r + 5, 5, x + r - 5, self.h - 5)
        self.coords(self.ar, x, r)
        self.pos = x

    def _move(self, e):
        self._place(e.x)

    def _release(self, _):
        if self.pos >= self.w - self.h // 2 - 8:
            self.cmd()
        else:
            self._place(self.h // 2)
            messagebox.showinfo("Pointage", "Faites glisser le bouton jusqu’au bout pour valider.")


def charger_photo(chemin, taille=96):
    try:
        from PIL import Image, ImageDraw, ImageTk
        im = Image.open(chemin).convert("RGB")
        w, h = im.size
        m = min(w, h)
        im = im.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2)).resize((taille, taille))
        masque = Image.new("L", (taille, taille), 0)
        ImageDraw.Draw(masque).ellipse((0, 0, taille - 1, taille - 1), fill=255)
        im.putalpha(masque)
        return ImageTk.PhotoImage(im)
    except ImportError:  # sans Pillow : PNG / GIF seulement
        img = tk.PhotoImage(file=chemin)
        return img.subsample(max(1, min(img.width(), img.height()) // taille))


MENTIONS = [
    ("Nom de l’application", "La Bonne Frite fast food – Planning des équipiers"),
    ("Éditeurs", "Juliette V et Louise S, classe de 1re STMG, lycée."),
    ("Hébergeur", "GitHub Pages (version web)."),
    ("Sources des données", "Code du travail (Légifrance) et Service-Public.fr, consultés en novembre 2026."),
    ("Avertissement", "Simulation pédagogique : les résultats sont indicatifs et ne remplacent pas l’avis d’un professionnel."),
    ("Données personnelles", "Aucune donnée personnelle n’est collectée ni enregistrée, aucun cookie n’est utilisé."),
    ("Crédits", "Logo « La Bonne Frite » : créé pour le projet des éditeurs. Police : celle du système "
                "(Nunito dans la version web, licence SIL OFL, Vernon Adams). Icônes : symboles du système."),
]


# ------------------------------------------------------------------ application
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("La Bonne Frite – Vue du patron")
        self.root.geometry("470x820+30+20")
        self.emp_win = tk.Toplevel(self.root)
        self.emp_win.title("La Bonne Frite – Vue de l’équipier")
        self.emp_win.geometry("440x820+530+20")
        self.emp_win.protocol("WM_DELETE_WINDOW", self.root.destroy)
        fams = set(tkfont.families())
        self.F = next((f for f in ("Nunito", "Arial Rounded MT Bold", "Segoe UI", "Helvetica Neue", "DejaVu Sans")
                       if f in fams), "Helvetica")
        self.logo = tk.PhotoImage(data=base64.b64decode(LOGO)) if LOGO and not LOGO.startswith("%%") else None
        self.staff, self.n = [], 0
        self.cur = self.pl = None
        self.tb, self.te = "team", "home"
        self.rg = dict(en=tk.StringVar(), nb=tk.StringVar(), poste=tk.StringVar(), s=tk.StringVar(),
                       e=tk.StringVar(), d=[tk.BooleanVar() for _ in range(7)])
        self.pv = [(tk.StringVar(), tk.StringVar()) for _ in range(7)]
        self.vars_profil = (tk.StringVar(), tk.StringVar())
        self.bz, self.ez = Scroll(self.root), Scroll(self.emp_win)
        self.bn, self.en_ = tk.Frame(self.root, bg=BLANC), tk.Frame(self.emp_win, bg=BLANC)
        for z, n in ((self.bz, self.bn), (self.ez, self.en_)):
            n.pack(side="bottom", fill="x")
            z.pack(fill="both", expand=True)
        self.nav_b = self._nav(self.bn, [("team", "👥\nÉquipe"), ("plan", "▦\nPlanning"), ("alerts", "🔔\nAlertes")],
                               lambda k: self.go("b", k))
        self.nav_e = self._nav(self.en_, [("home", "⌂\nAccueil"), ("plan", "▦\nPlanning"),
                                          ("alerts", "🔔\nAlertes"), ("profil", "☺\nProfil")],
                               lambda k: self.go("e", k))
        self.refresh()
        self.root.after(30000, self.tick)

    # -- petits constructeurs
    def f(self, size=11, bold=False):
        return (self.F, size, "bold" if bold else "normal")

    def lab(self, p, t, size=11, bold=False, fg=PRUNE, bg=CREME, **kw):
        return tk.Label(p, text=t, font=self.f(size, bold), fg=fg, bg=bg, **kw)

    def btn(self, p, t, cmd, bg=PRUNE, fg="white"):
        return tk.Button(p, text=t, command=cmd, font=self.f(12, True), bg=bg, fg=fg, activebackground=ROSE,
                         relief="flat", bd=0, padx=16, pady=10, cursor="hand2")

    def card(self, p):
        c = tk.Frame(p, bg=BLANC, padx=12, pady=10)
        c.pack(fill="x", padx=12, pady=6)
        return c

    def _nav(self, parent, items, cmd):
        bs = {}
        for k, t in items:
            b = tk.Button(parent, text=t, font=self.f(9, True), relief="flat", bd=0, bg=BLANC, fg=MAUVE,
                          activebackground=ROSEPALE, pady=6, cursor="hand2", command=lambda k=k: cmd(k))
            b.pack(side="left", expand=True, fill="x")
            bs[k] = b
        return bs

    def go(self, v, k):
        if v == "b":
            self.tb = k
        else:
            self.te = k
        self.refresh()

    def tick(self):
        if not isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            self.refresh()
        self.root.after(30000, self.tick)

    def refresh(self):
        for bs, cur in ((self.nav_b, self.tb), (self.nav_e, self.te)):
            for k, b in bs.items():
                b.configure(bg=ROSEPALE if k == cur else BLANC, fg=PRUNE if k == cur else MAUVE)
        nb = sum(len(e.alertes()) for e in self.staff)
        self.nav_b["alerts"].configure(text="🔔\nAlertes" + (" (%d)" % nb if nb else ""))
        ec = self.get(self.cur)
        na = len(ec.alertes()) if ec else 0
        self.nav_e["alerts"].configure(text="🔔\nAlertes" + (" (%d)" % na if na else ""))
        self.bz.vider()
        {"team": self.p_equipe, "plan": self.p_planning, "alerts": self.p_alertes}[self.tb](self.bz.inner)
        self.ez.vider()
        self.e_page(self.ez.inner)

    def get(self, i):
        return next((e for e in self.staff if e.n == i), None)

    # -- alertes
    def liste_alertes(self, p, al, qui=None):
        if not al:
            c = tk.Frame(p, bg="#E8F5EC", padx=10, pady=8)
            c.pack(fill="x", padx=12, pady=4)
            self.lab(c, "Aucune alerte : tous les horaires respectent les règles.", 10, bg="#E8F5EC", fg=VERT,
                     wraplength=360, justify="left").pack(anchor="w")
        for warn, t in al:
            c = tk.Frame(p, bg="#FFF6DF" if warn else "#FDECEA", padx=10, pady=8)
            c.pack(fill="x", padx=12, pady=4)
            self.lab(c, (qui + " – " if qui else "") + t, 10, True, bg=c["bg"], wraplength=360,
                     justify="left").pack(anchor="w")

    # ================================================================ PATRON
    def p_equipe(self, p):
        self.lab(p, "Mon équipe (%d/6)" % len(self.staff), 18, True).pack(anchor="w", padx=14, pady=(12, 4))
        c, r = self.card(p), self.rg
        self.lab(c, "Inscrire un équipier", 12, True, bg=BLANC).pack(anchor="w")
        for t, v in (("Date d’entrée (JJ/MM/AAAA)", r["en"]), ("Date de naissance (JJ/MM/AAAA)", r["nb"])):
            self.lab(c, t, 9, True, MAUVE, BLANC).pack(anchor="w", pady=(6, 0))
            tk.Entry(c, textvariable=v, font=self.f(11), relief="solid", bd=1).pack(fill="x", ipady=4)
        self.lab(c, "Poste occupé", 9, True, MAUVE, BLANC).pack(anchor="w", pady=(6, 0))
        cb = ttk.Combobox(c, textvariable=r["poste"], values=list(POSTES), state="readonly")
        cb.pack(fill="x", ipady=3)
        cb.bind("<<ComboboxSelected>>", self.choix_poste)
        self.lab(c, "Jours de service", 9, True, MAUVE, BLANC).pack(anchor="w", pady=(6, 0))
        jf = tk.Frame(c, bg=BLANC)
        jf.pack(fill="x")
        for i, j in enumerate(JOURS):
            tk.Checkbutton(jf, text=j[:3], variable=r["d"][i], bg=BLANC, font=self.f(9),
                           activebackground=BLANC).grid(row=0, column=i)
        hf = tk.Frame(c, bg=BLANC)
        hf.pack(fill="x", pady=(6, 0))
        for k, (t, v) in enumerate((("Début (HH:MM)", r["s"]), ("Fin (HH:MM)", r["e"]))):
            sf = tk.Frame(hf, bg=BLANC)
            sf.pack(side="left", expand=True, fill="x", padx=2)
            self.lab(sf, t, 9, True, MAUVE, BLANC).pack(anchor="w")
            tk.Entry(sf, textvariable=v, font=self.f(11), relief="solid", bd=1, width=8).pack(fill="x", ipady=4)
        self.lab(c, "Pause : %d minutes (fixe). Horaires proposés selon le poste, modifiables.\n"
                    "L’équipier complète ensuite nom, prénom et photo." % PAUSE, 9, False, MAUVE, BLANC,
                 justify="left", wraplength=370).pack(anchor="w", pady=6)
        self.btn(c, "Inscrire l’équipier", self.inscrire, OR, PRUNE).pack(fill="x")
        for e in self.staff:
            c = self.card(p)
            self.lab(c, "%s   (%d ans)" % (e.nom_affiche(), e.age()), 12, True, bg=BLANC).pack(anchor="w")
            self.lab(c, "%s · entré le %s" % (e.poste, e.entree.strftime("%d/%m/%Y")), 9, False, MAUVE,
                     BLANC).pack(anchor="w")
            s, pz = e.totaux()
            self.lab(c, "Semaine : %s · Pauses : %s" % (fh(s), fh(pz)), 10, bg=BLANC).pack(anchor="w")
            self.btn(c, "Retirer", lambda e=e: self.retirer(e), ROSE, PRUNE).pack(anchor="e", pady=(4, 0))
        self.btn(p, "Mentions légales", lambda: self.mentions("b"), BLANC, PRUNE).pack(fill="x", padx=12, pady=10)

    def choix_poste(self, _=None):
        jours, s, e = POSTES[self.rg["poste"].get()]
        for i in range(7):
            self.rg["d"][i].set(i in jours)
        self.rg["s"].set(s)
        self.rg["e"].set(e)

    def inscrire(self):
        r = self.rg
        if len(self.staff) >= 6:
            return messagebox.showwarning("Équipe complète", "L’équipe est limitée à 6 équipiers.")
        en, nb = parse_date(r["en"].get()), parse_date(r["nb"].get())
        if not en or not nb:
            return messagebox.showwarning("Dates", "Saisissez les dates au format JJ/MM/AAAA.")
        if not r["poste"].get() or not any(v.get() for v in r["d"]):
            return messagebox.showwarning("Poste", "Choisissez un poste et au moins un jour de service.")
        if hm(r["s"].get()) is None or hm(r["e"].get()) is None:
            return messagebox.showwarning("Horaires", "Saisissez les horaires au format HH:MM.")
        self.n += 1
        e = Equipier(self.n, r["poste"].get(), en, nb)
        for i, d in enumerate(semaine()):
            if r["d"][i].get():
                e.days[d.isoformat()] = dict(ps=r["s"].get(), pe=r["e"].get(), pp=PAUSE)
        self.staff.append(e)
        self.cur = self.cur or e.n
        self.pl = self.pl or e.n
        for v in (r["en"], r["nb"], r["poste"], r["s"], r["e"]):
            v.set("")
        for v in r["d"]:
            v.set(False)
        self.refresh()

    def retirer(self, e):
        self.staff.remove(e)
        self.cur = self.staff[0].n if self.staff else None
        self.pl = self.cur
        self.refresh()

    def p_planning(self, p):
        self.lab(p, "Planning de la semaine", 18, True).pack(anchor="w", padx=14, pady=(12, 4))
        if not self.staff:
            return self.lab(p, "Inscrivez d’abord un équipier.", 11).pack(padx=14, pady=10)
        e = self.get(self.pl) or self.staff[0]
        self.pl = e.n
        names = ["%d – %s" % (x.n, x.nom_affiche()) for x in self.staff]
        cb = ttk.Combobox(p, values=names, state="readonly")
        cb.set("%d – %s" % (e.n, e.nom_affiche()))
        cb.pack(fill="x", padx=12, pady=4)
        cb.bind("<<ComboboxSelected>>", lambda _: (setattr(self, "pl", int(cb.get().split(" – ")[0])), self.refresh()))
        for i, d in enumerate(semaine()):
            r = e.days.get(d.isoformat(), {})
            self.pv[i][0].set(r.get("ps", ""))
            self.pv[i][1].set(r.get("pe", ""))
            c = self.card(p)
            self.lab(c, "%s %s" % (JOURS[i], d.strftime("%d/%m")), 11, True, bg=BLANC).grid(row=0, column=0, columnspan=4,
                                                                                         sticky="w")
            for k, v in enumerate(self.pv[i]):
                tk.Entry(c, textvariable=v, width=7, font=self.f(11), relief="solid", bd=1).grid(
                    row=1, column=k * 2, padx=(0, 4), pady=2, ipady=3)
                self.lab(c, "début" if k == 0 else "fin", 9, False, MAUVE, BLANC).grid(row=1, column=k * 2 + 1,
                                                                                    padx=(0, 10))
            self.lab(c, "pause %d min · vide = repos" % PAUSE, 9, False, MAUVE, BLANC).grid(row=1, column=4)
        self.btn(p, "Enregistrer le planning", lambda: self.sauver_planning(e), OR, PRUNE).pack(fill="x", padx=12,
                                                                                               pady=10)

    def sauver_planning(self, e):
        for i, d in enumerate(semaine()):
            s, f = self.pv[i][0].get().strip(), self.pv[i][1].get().strip()
            if (s and hm(s) is None) or (f and hm(f) is None):
                return messagebox.showwarning("Horaires", "%s : format attendu HH:MM." % JOURS[i])
        for i, d in enumerate(semaine()):
            s, f = self.pv[i][0].get().strip(), self.pv[i][1].get().strip()
            r = e.days.setdefault(d.isoformat(), {})
            r["ps"], r["pe"], r["pp"] = s, f, PAUSE if (s or f) else 0
        self.refresh()

    def p_alertes(self, p):
        self.lab(p, "Alertes", 18, True).pack(anchor="w", padx=14, pady=(12, 4))
        if not self.staff:
            self.lab(p, "Aucun équipier inscrit.", 11).pack(padx=14, pady=10)
        for e in self.staff:
            self.liste_alertes(p, e.alertes(), e.nom_affiche()) if e.alertes() else None
        if self.staff and not any(e.alertes() for e in self.staff):
            self.liste_alertes(p, [])

    # ================================================================ ÉQUIPIER
    def e_page(self, p):
        e = self.get(self.cur)
        if not e:
            if self.logo:
                tk.Label(p, image=self.logo, bg=CREME).pack(pady=10)
            return self.lab(p, "Aucun équipier pour le moment.\nLe patron doit d’abord vous inscrire.", 12,
                            wraplength=360).pack(pady=20)
        names = ["%d – %s" % (x.n, x.nom_affiche()) for x in self.staff]
        cb = ttk.Combobox(p, values=names, state="readonly")
        cb.set("%d – %s" % (e.n, e.nom_affiche()))
        cb.pack(fill="x", padx=12, pady=(8, 0))
        cb.bind("<<ComboboxSelected>>", lambda _: (setattr(self, "cur", int(cb.get().split(" – ")[0])), self.refresh()))
        if self.te == "legal":
            return self.e_mentions(p)
        {"home": self.e_accueil, "plan": self.e_planning, "alerts": self.e_alertes, "profil": self.e_profil}[self.te](p, e)

    def e_accueil(self, p, e):
        if self.logo:
            tk.Label(p, image=self.logo, bg=CREME).pack(pady=(8, 2))
        self.lab(p, "Bonjour %s !" % e.prenom if e.prenom else "Bonjour !", 18, True).pack()
        td = date.today().isoformat()
        r = e.days.setdefault(td, {})
        c = self.card(p)
        self.lab(c, "Horaire de la journée", 9, False, MAUVE, BLANC).pack()
        self.lab(c, "%s – %s" % (r["ps"], r["pe"]) if r.get("ps") and r.get("pe") else "Repos", 24, True,
                 bg=BLANC).pack()
        if r.get("ps"):
            self.lab(c, "Pause prévue : %d min" % PAUSE, 9, False, MAUVE, BLANC).pack()
        if e.alertes():
            self.lab(p, "⚠ %d alerte(s) : voir l’onglet Alertes." % len(e.alertes()), 10, True, ROUGE).pack(pady=4)
        fnt = self.f(12, True)
        if not r.get("as"):
            Glisseur(p, "Début de service", lambda: self.pointer("start"), OR, PRUNE, fnt).pack(pady=8)
        elif not r.get("ae"):
            x = e.eff(date.today())
            c = self.card(p)
            self.lab(c, "En service depuis %s\nTravaillé : %s" % (r["as"], fh(e.travail(x))), 11, True,
                     bg=BLANC, justify="center").pack()
            if r.get("pst") is not None:
                Glisseur(p, "Fin de pause", lambda: self.pointer("resume"), MAUVE, "white", fnt).pack(pady=6)
            else:
                Glisseur(p, "Début de pause", lambda: self.pointer("pause"), MAUVE, "white", fnt).pack(pady=6)
            Glisseur(p, "Fin de service", lambda: self.pointer("end"), ROSE, PRUNE, fnt).pack(pady=6)
        else:
            c = self.card(p)
            self.lab(c, "À demain !", 24, True, bg=BLANC).pack()
            self.lab(c, "Service de %s à %s · Travaillé : %s" % (r["as"], r["ae"], fh(e.travail(e.eff(date.today())))),
                     10, bg=BLANC).pack()

    def pointer(self, a):
        e = self.get(self.cur)
        r = e.days.setdefault(date.today().isoformat(), {})
        t = now_min()
        if a == "start":
            r["as"], r["pb"], r["pst"] = ft(t), 0, None
        elif a == "pause":
            r["pst"] = t
        elif a == "resume":
            r["pb"], r["pst"] = r.get("pb", 0) + t - r["pst"], None
        elif a == "end":
            if r.get("pst") is not None:
                r["pb"], r["pst"] = r.get("pb", 0) + t - r["pst"], None
            r["ae"] = ft(t)
        self.refresh()
        if e.alertes():
            messagebox.showwarning("Alerte horaire", "Un horaire est impossible : voir l’onglet Alertes.")

    def e_planning(self, p, e):
        self.lab(p, "Planning de la semaine", 18, True).pack(anchor="w", padx=14, pady=(8, 4))
        for i, d in enumerate(semaine()):
            x = e.eff(d)
            c = self.card(p)
            if d == date.today():
                c.configure(highlightbackground=OR, highlightthickness=2)
            ok = e.span(x)
            self.lab(c, "%s %s" % (JOURS[i], d.strftime("%d/%m")), 11, True, bg=BLANC).pack(side="left")
            self.lab(c, "%s – %s · pause %d min" % (x["s"], x["e"] or "…", x["p"]) if ok else "Repos", 10, True,
                     bg=BLANC, fg=MAUVE).pack(side="right")

    def e_alertes(self, p, e):
        self.lab(p, "Alertes", 18, True).pack(anchor="w", padx=14, pady=(8, 2))
        self.lab(p, "Horaire impossible", 12, True, MAUVE).pack(anchor="w", padx=14)
        self.liste_alertes(p, e.alertes())
        self.lab(p, "Notifications", 12, True, MAUVE).pack(anchor="w", padx=14, pady=(10, 0))
        r = e.days.get(date.today().isoformat(), {})
        notes = []
        if r.get("pst") is not None:
            notes.append("Reprise de service à %s h" % ft(r["pst"] + PAUSE))
        elif r.get("ps") and not r.get("as"):
            notes.append("Début de service à %s h" % r["ps"])
        if r.get("pe") and not r.get("ae"):
            notes.append("Fin de service à %s h" % r["pe"])
        for t in notes or ["Aucune notification pour le moment."]:
            c = tk.Frame(p, bg="#FFF6DF", padx=10, pady=8)
            c.pack(fill="x", padx=12, pady=3)
            self.lab(c, t, 10, True, bg="#FFF6DF").pack(anchor="w")
        self.lab(p, "Les deux prochains jours", 12, True, MAUVE).pack(anchor="w", padx=14, pady=(10, 0))
        for k in (1, 2):
            d = date.today() + timedelta(days=k)
            x = e.eff(d)
            c = self.card(p)
            self.lab(c, "%s %s : %s" % (JOURS[d.weekday()], d.strftime("%d/%m"),
                                        "%s – %s" % (x["s"], x["e"]) if e.span(x) else "Repos"), 10, True,
                     bg=BLANC).pack(anchor="w")

    def e_profil(self, p, e):
        self.lab(p, "Mon profil", 18, True).pack(pady=(8, 2))
        if e.photo:
            tk.Label(p, image=e.photo, bg=CREME).pack()
        else:
            tk.Label(p, text=(e.prenom[:1] or "?").upper(), font=self.f(30, True), fg=PRUNE, bg=ROSE, width=3,
                     height=1).pack(pady=4)
        self.lab(p, e.nom_affiche(), 14, True).pack()
        self.lab(p, "%s · entré le %s" % (e.poste, e.entree.strftime("%d/%m/%Y")), 10, False, MAUVE).pack()
        s, pz = e.totaux()
        g = tk.Frame(p, bg=CREME)
        g.pack(fill="x", padx=12, pady=8)
        for t, v in (("Heures de service", s), ("Heures de pause", pz)):
            c = tk.Frame(g, bg=BLANC, padx=10, pady=8)
            c.pack(side="left", expand=True, fill="x", padx=4)
            self.lab(c, t, 9, False, MAUVE, BLANC).pack()
            self.lab(c, fh(v), 18, True, bg=BLANC).pack()
        c = self.card(p)
        self.lab(c, "Mes informations", 12, True, bg=BLANC).pack(anchor="w")
        nom, pre = self.vars_profil
        nom.set(e.nom)
        pre.set(e.prenom)
        for t, v in (("Nom", nom), ("Prénom", pre)):
            self.lab(c, t, 9, True, MAUVE, BLANC).pack(anchor="w", pady=(6, 0))
            tk.Entry(c, textvariable=v, font=self.f(11), relief="solid", bd=1).pack(fill="x", ipady=4)
        self.lab(c, "Poste occupé (défini par le patron) : %s" % e.poste, 9, True, MAUVE, BLANC).pack(anchor="w", pady=6)
        self.btn(c, "Choisir une photo (facultatif)", lambda: self.photo(e), ROSE, PRUNE).pack(fill="x", pady=2)
        self.btn(c, "Enregistrer", lambda: self.maj_profil(e), OR, PRUNE).pack(fill="x", pady=2)
        self.btn(p, "Mentions légales", lambda: self.mentions("e"), BLANC, PRUNE).pack(fill="x", padx=12, pady=8)

    def maj_profil(self, e):
        e.nom, e.prenom = self.vars_profil[0].get().strip(), self.vars_profil[1].get().strip()
        self.refresh()

    def photo(self, e):
        ch = filedialog.askopenfilename(title="Photo de profil", filetypes=[("Images", "*.png *.gif *.jpg *.jpeg")])
        if ch:
            try:
                e.photo = charger_photo(ch)
            except Exception as ex:  # image illisible
                messagebox.showwarning("Photo", "Image non lisible (PNG ou GIF sans Pillow) : %s" % ex)
            self.refresh()

    # ================================================================ mentions
    def mentions(self, v):
        if v == "e":
            self.te = "legal"
            self.refresh()
        else:
            w = tk.Toplevel(self.root)
            w.title("Mentions légales")
            w.geometry("440x640+300+60")
            w.configure(bg=CREME)
            z = Scroll(w)
            z.pack(fill="both", expand=True)
            self._texte_mentions(z.inner)

    def e_mentions(self, p):
        self._texte_mentions(p)
        self.btn(p, "Retour", lambda: self.go("e", "profil"), BLANC, PRUNE).pack(fill="x", padx=12, pady=10)

    def _texte_mentions(self, p):
        self.lab(p, "Mentions légales", 18, True).pack(anchor="w", padx=14, pady=(10, 4))
        c = self.card(p)
        for t, v in MENTIONS:
            self.lab(c, t, 11, True, MAUVE, BLANC).pack(anchor="w", pady=(8, 0))
            self.lab(c, v, 10, False, PRUNE, BLANC, wraplength=360, justify="left").pack(anchor="w")


if __name__ == "__main__":
    App().root.mainloop()
