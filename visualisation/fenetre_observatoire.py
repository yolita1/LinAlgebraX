"""Fenêtre, animations et caméra de l'observatoire."""


import base64
import math
import os
import queue
import re
import tempfile
import time
from io import BytesIO
from pathlib import Path


FOND = "#050505"
PANNEAU = "#0b0b0b"
GRILLE = "#343434"
GRILLE_FORTE = "#626262"
TEXTE = "#dedbd3"
SECONDAIRE = "#8b8b87"
DORE = "#d1a85b"
DORE_SOMBRE = "#4a3a20"
BLEU = "#8aa1ad"
BLEU_SOMBRE = "#29343a"
ROUGE = "#c85a54"
ROUGE_SOMBRE = "#4a2220"


def _identite_locale(dimension):
    return [
        [1.0 if i == j else 0.0 for j in range(dimension)]
        for i in range(dimension)
    ]


class FenetreLinAlgebraX:
    """Observatoire animé et navigable."""

    def __init__(self, racine, file_messages):
        import tkinter as tk

        self.tk = tk
        self.racine = racine
        self.file_messages = file_messages
        self.scene = self._scene_attente()
        self.vue = 0
        self.position = 0.0
        self.lecture = False
        self.animation_id = None
        self.debut_animation = 0.0
        self.duree_cadre = 2.4
        self.echelle_active = 1.0
        self.zoom_vue = 1.0
        self.decalage_vue = [0.0, 0.0]
        self.pan_depart = None
        self.orientation_3d = self._orientation_initiale_3d()
        self.orientation_plan = self._quaternion_identite()
        self.rotation_depart = None
        self.formule_actuelle = None
        self.image_formule = None
        self.boutons_vues = []
        self.modification_curseur = False

        racine.title("LinAlgebraX : observatoire")
        self._placer_a_droite()
        racine.minsize(640, 500)
        racine.configure(bg=FOND)
        racine.protocol("WM_DELETE_WINDOW", self.fermer)
        try:
            racine.attributes("-topmost", True)
        except Exception:
            pass

        self._construire_interface()
        self._lier_evenements()
        self._charger_scene(self.scene)
        self.racine.after(30, self._lire_messages)

    def _placer_a_droite(self):
        """Occupe la partie droite de l'écran, comme un volet du terminal."""
        largeur_ecran = self.racine.winfo_screenwidth()
        hauteur_ecran = self.racine.winfo_screenheight()
        largeur = max(640, min(900, int(largeur_ecran * 0.48)))
        hauteur = max(500, hauteur_ecran - 90)
        x = max(0, largeur_ecran - largeur - 12)
        self.racine.geometry(f"{largeur}x{hauteur}+{x}+34")

    def _apparaitre(self):
        """Ramène la fenêtre au-dessus sans voler le clavier au terminal."""
        try:
            self.racine.deiconify()
            self.racine.lift()
            self.racine.attributes("-topmost", True)
        except Exception:
            pass

    @staticmethod
    def _scene_attente():
        return {
            "titre": "Observatoire",
            "vues": [
                {
                    "nom": "Vue",
                    "type": "attente",
                    "cadres": [
                        {
                            "formule": "",
                            "explication": "En attente d'une commande du terminal.",
                            "donnees": {"message": "En attente du terminal"},
                            "operation": "",
                        }
                    ],
                }
            ],
            "legende": [],
        }


    def _construire_interface(self):
        tk = self.tk
        haut = tk.Frame(self.racine, bg=FOND)
        haut.pack(fill="x", padx=18, pady=(14, 6))
        self.titre = tk.Label(
            haut,
            text="",
            bg=FOND,
            fg=TEXTE,
            font=("DejaVu Sans", 13),
            anchor="w",
        )
        self.titre.pack(side="left", fill="x", expand=True)
        self.zone_vues = tk.Frame(haut, bg=FOND)
        self.zone_vues.pack(side="right")

        self.canvas = tk.Canvas(
            self.racine,
            bg=FOND,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=12, pady=4)

        bas = tk.Frame(self.racine, bg=PANNEAU)
        bas.pack(fill="x")
        self.zone_formule = tk.Label(
            bas,
            text="",
            bg=PANNEAU,
            fg=TEXTE,
            font=("DejaVu Sans", 13),
            height=2,
        )
        self.zone_formule.pack(fill="x", padx=16, pady=(8, 0))
        self.explication = tk.Label(
            bas,
            text="",
            bg=PANNEAU,
            fg=SECONDAIRE,
            font=("DejaVu Sans", 10),
            wraplength=1000,
        )
        self.explication.pack(fill="x", padx=16, pady=(0, 5))

        controle = tk.Frame(bas, bg=PANNEAU)
        controle.pack(fill="x", padx=12, pady=(0, 6))
        self.bouton_lecture = self._bouton(controle, "PLAY", self.basculer_lecture)
        self.bouton_lecture.configure(width=8, relief="groove", bd=1)
        self.bouton_lecture.pack(side="left", padx=(2, 8))

        self.curseur = tk.Scale(
            controle,
            from_=0,
            to=1000,
            orient="horizontal",
            showvalue=False,
            bg=PANNEAU,
            fg=TEXTE,
            troughcolor=GRILLE,
            activebackground=GRILLE_FORTE,
            highlightthickness=0,
            bd=0,
        )
        self.curseur.pack(side="left", fill="x", expand=True)
        self.curseur.bind("<Button-1>", self._deplacer_curseur_evenement)
        self.curseur.bind("<B1-Motion>", self._deplacer_curseur_evenement)
        self.indicateur = tk.Label(
            controle,
            text="1 / 1",
            bg=PANNEAU,
            fg=SECONDAIRE,
            width=9,
            font=("DejaVu Sans Mono", 9),
        )
        self.indicateur.pack(side="right", padx=(8, 0))

        aide = tk.Label(
            bas,
            text="Gauche : déplacer · molette : zoomer · droite : orbite 360° · double clic : recentrer · PLAY : rejouer",
            bg=PANNEAU,
            fg=SECONDAIRE,
            font=("DejaVu Sans", 8),
        )
        aide.pack(fill="x", padx=16, pady=(0, 7))

    def _bouton(self, parent, texte, commande):
        return self.tk.Button(
            parent,
            text=texte,
            command=commande,
            bg=PANNEAU,
            fg=TEXTE,
            activebackground=GRILLE,
            activeforeground=TEXTE,
            relief="flat",
            bd=0,
            padx=9,
            pady=4,
            font=("DejaVu Sans", 10),
        )

    def _lier_evenements(self):
        self.racine.bind("<space>", lambda _: self.basculer_lecture())
        self.racine.bind("<Key-r>", lambda _: self.rejouer())
        self.racine.bind("<Key-R>", lambda _: self.rejouer())
        self.racine.bind("<Tab>", self._vue_suivante)
        self.canvas.bind("<ButtonPress-1>", self._debut_pan)
        self.canvas.bind("<B1-Motion>", self._pan)
        self.canvas.bind("<Double-Button-1>", self._reinitialiser_vue)
        self.canvas.bind("<ButtonPress-3>", self._debut_rotation)
        self.canvas.bind("<B3-Motion>", self._rotation)
        self.canvas.bind("<MouseWheel>", self._zoom_molette)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_molette(e, 1))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_molette(e, -1))
        self.canvas.bind("<Configure>", lambda _: self._dessiner())

    def _lire_messages(self):
        """Vide régulièrement la file sans bloquer la boucle Tkinter."""
        try:
            while True:
                message = self.file_messages.get_nowait()
                if message.get("type") == "fermer":
                    self.fermer()
                    return
                if message.get("type") == "scene":
                    self._charger_scene(message["scene"])
                elif message.get("type") == "montrer":
                    self._apparaitre()
        except queue.Empty:
            pass
        if self.racine.winfo_exists():
            self.racine.after(30, self._lire_messages)

    def _charger_scene(self, scene):
        """Remplace la scène et remet la caméra dans son état lisible."""
        self.scene = scene
        self.vue = 0
        self.zoom_vue = 1.0
        self.decalage_vue = [0.0, 0.0]
        self.pan_depart = None
        self.orientation_3d = self._orientation_initiale_3d()
        self.orientation_plan = self._quaternion_identite()
        self.rotation_depart = None
        self.titre.configure(text=scene.get("titre", "LinAlgebraX"))
        self._reconstruire_boutons_vues()
        self.rejouer()
        self._apparaitre()

    def _reconstruire_boutons_vues(self):
        for bouton in self.boutons_vues:
            bouton.destroy()
        self.boutons_vues = []
        for indice, vue in enumerate(self.scene["vues"]):
            bouton = self._bouton(
                self.zone_vues,
                vue["nom"],
                lambda i=indice: self._choisir_vue(i),
            )
            bouton.pack(side="left", padx=2)
            self.boutons_vues.append(bouton)
        self._style_boutons_vues()

    def _style_boutons_vues(self):
        for i, bouton in enumerate(self.boutons_vues):
            bouton.configure(
                bg=GRILLE if i == self.vue else PANNEAU,
                fg=TEXTE,
            )

    def _choisir_vue(self, indice):
        self.vue = indice
        self._style_boutons_vues()
        self.rejouer()

    def _vue_suivante(self, _=None):
        self._choisir_vue((self.vue + 1) % len(self.scene["vues"]))
        return "break"


    def _vue_courante(self):
        return self.scene["vues"][self.vue]

    def _cadres(self):
        return self._vue_courante()["cadres"]

    def _etat_temps(self):
        """Sépare la position en numéro de cadre et progression locale."""
        cadres = self._cadres()
        n = len(cadres)
        if n == 1:
            return 0, min(max(self.position, 0.0), 1.0)
        if self.position >= n:
            return n - 1, 1.0
        indice = max(0, min(n - 1, int(self.position)))
        return indice, self.position - indice

    def basculer_lecture(self):
        """PLAY relance toujours toute la scène depuis son premier instant."""
        if self._vue_courante()["type"] == "formule":
            for indice, vue in enumerate(self.scene["vues"]):
                if vue["type"] != "formule":
                    self.vue = indice
                    self._style_boutons_vues()
                    break
        self.rejouer()

    def rejouer(self):
        """Replace l'animation à zéro et programme le premier rafraîchissement."""
        self._annuler_animation()
        self.position = 0.0
        self.lecture = True
        self.debut_animation = time.monotonic()
        self._mettre_a_jour_interface()
        self._dessiner()
        self.animation_id = self.racine.after(16, self._animer)

    def _annuler_animation(self):
        if self.animation_id is not None:
            try:
                self.racine.after_cancel(self.animation_id)
            except Exception:
                pass
            self.animation_id = None

    def _animer(self):
        """Calcule directement la position depuis le clic sur PLAY."""
        if not self.lecture:
            self.animation_id = None
            return
        maximum = float(len(self._cadres()))
        # Le temps réel garde une durée stable même si une image est plus lente.
        ecoule = max(0.0, time.monotonic() - self.debut_animation)
        self.position = min(maximum, ecoule / self.duree_cadre)
        self._mettre_a_jour_interface()
        self._dessiner()
        if self.position >= maximum:
            self.lecture = False
            self.animation_id = None
        else:
            self.animation_id = self.racine.after(16, self._animer)

    def _deplacer_curseur(self, valeur):
        if self.modification_curseur:
            return
        self._annuler_animation()
        self.position = float(valeur) / 1000 * len(self._cadres())
        self.lecture = False
        self._mettre_a_jour_interface(depuis_curseur=True)
        self._dessiner()

    def _deplacer_curseur_evenement(self, evenement):
        """Ne réagit qu'à la souris, jamais aux mises à jour automatiques."""
        largeur = max(1, self.curseur.winfo_width())
        fraction = max(0.0, min(1.0, evenement.x / largeur))
        valeur = 1000 * fraction
        self.curseur.set(valeur)
        self._deplacer_curseur(str(valeur))

    def _mettre_a_jour_interface(self, depuis_curseur=False):
        indice, progression = self._etat_temps()
        cadre = self._cadres()[indice]
        self.bouton_lecture.configure(text="PLAY")
        nombre_cadres = len(self._cadres())
        if nombre_cadres == 1:
            indication = f"{round(100 * progression):>3} %"
        else:
            indication = f"{indice + 1}/{nombre_cadres} {round(100 * progression):>3}%"
        self.indicateur.configure(text=indication)
        if not depuis_curseur:
            self.modification_curseur = True
            maximum = max(1, len(self._cadres()))
            self.curseur.set(int(1000 * min(self.position, maximum) / maximum))
            self.modification_curseur = False
        formule = cadre.get("formule", "")
        if formule != self.formule_actuelle:
            self.formule_actuelle = formule
            self._afficher_formule(formule)
        texte = cadre.get("explication", "")
        operation = cadre.get("operation", "")
        if operation:
            texte = operation + " : " + texte
        self.explication.configure(text=texte)
        largeur_texte = max(280, self.racine.winfo_width() - 48)
        self.explication.configure(wraplength=largeur_texte)
        self.zone_formule.configure(wraplength=largeur_texte)


    def _afficher_formule(self, formule):
        if not formule:
            self.image_formule = None
            self.zone_formule.configure(image="", text="")
            return
        image = self._rendre_latex(formule)
        largeur_max = max(280, self.racine.winfo_width() - 48)
        if image is not None and image.width() <= largeur_max:
            self.image_formule = image
            self.zone_formule.configure(image=image, text="")
        else:
            self.image_formule = None
            self.zone_formule.configure(
                image="",
                text=self._latex_vers_unicode(formule),
                font=("DejaVu Sans", 13),
            )

    def _rendre_latex(self, formule):
        """Tente un rendu PNG MathText, sans exiger une installation LaTeX."""
        try:
            cache = Path(tempfile.gettempdir()) / "linalgebrax-matplotlib"
            cache.mkdir(exist_ok=True)
            os.environ["MPLCONFIGDIR"] = str(cache)
            from matplotlib.font_manager import FontProperties
            from matplotlib.mathtext import math_to_image

            tampon = BytesIO()
            math_to_image(
                self._latex_pour_mathtext(formule),
                tampon,
                prop=FontProperties(size=max(9, 15 - len(formule) // 35)),
                dpi=130,
                format="png",
                color=TEXTE,
            )
            donnees = base64.b64encode(tampon.getvalue())
            return self.tk.PhotoImage(data=donnees)
        except Exception:
            return None

    @staticmethod
    def _latex_pour_mathtext(formule):
        """Adapte les formules au sous-ensemble compris par Matplotlib."""
        texte = formule.replace(r"\iff", r"\Longleftrightarrow")
        texte = re.sub(
            r"\\text\{([^{}]*)\}",
            lambda m: r"\mathrm{" + m.group(1).replace(" ", r"\ ") + "}",
            texte,
        )
        texte = re.sub(
            r"\\operatorname\{([^{}]*)\}",
            r"\\mathrm{\1}",
            texte,
        )
        texte = re.sub(
            r"\\mathcal\s+([A-Za-z])",
            r"\\mathcal{\1}",
            texte,
        )
        texte = re.sub(
            r"\\xrightarrow\{([^{}]+)\}",
            r"\\overset{\1}{\\longrightarrow}",
            texte,
        )
        return texte

    @staticmethod
    def _latex_vers_unicode(formule):
        """Produit une formule lisible même sans moteur LaTeX installé.

        Cette fonction constitue le dernier filet de sécurité : même si
        Matplotlib est absent, l'utilisateur voit des symboles mathématiques et
        jamais une longue suite de commandes commençant par une barre oblique.
        """
        texte = formule.strip().strip("$")
        texte = texte.replace(r"\{", "\uFFF0").replace(r"\}", "\uFFF1")

        scriptes = {
            "A": "𝒜", "B": "ℬ", "C": "𝒞", "D": "𝒟", "E": "ℰ",
            "F": "ℱ", "G": "𝒢", "H": "ℋ", "I": "ℐ", "J": "𝒥",
            "K": "𝒦", "L": "ℒ", "M": "ℳ", "N": "𝒩", "O": "𝒪",
            "P": "𝒫", "Q": "𝒬", "R": "ℛ", "S": "𝒮", "T": "𝒯",
            "U": "𝒰", "V": "𝒱", "W": "𝒲", "X": "𝒳", "Y": "𝒴",
            "Z": "𝒵",
        }

        def calligraphique(contenu):
            return "".join(scriptes.get(caractere, caractere) for caractere in contenu)

        texte = re.sub(
            r"\\mathcal\s*\{([^{}]+)\}",
            lambda m: calligraphique(m.group(1)),
            texte,
        )
        texte = re.sub(
            r"\\mathcal\s*([A-Za-z])",
            lambda m: calligraphique(m.group(1)),
            texte,
        )
        texte = re.sub(
            r"\\text\{([^{}]*)\}",
            lambda m: " " + m.group(1) + " ",
            texte,
        )
        texte = re.sub(
            r"\\(?:mathrm|operatorname)\{([^{}]*)\}",
            lambda m: " " + m.group(1) + " ",
            texte,
        )
        texte = re.sub(
            r"\\frac\{([^{}]*)\}\{([^{}]*)\}",
            r"(\1)/(\2)",
            texte,
        )
        texte = re.sub(r"\\xrightarrow\{([^{}]+)\}", r"⟶ \1", texte)
        texte = texte.replace(r"\begin{pmatrix}", "(")
        texte = texte.replace(r"\end{pmatrix}", ")")
        texte = texte.replace(r"\begin{bmatrix}", "[")
        texte = texte.replace(r"\end{bmatrix}", "]")

        commandes = {
            "Longleftrightarrow": "⇔",
            "longleftrightarrow": "⇔",
            "leftrightarrow": "↔",
            "Rightarrow": "⇒",
            "longrightarrow": "⟶",
            "longmapsto": "↦",
            "rightarrow": "→",
            "leftarrow": "←",
            "to": "→",
            "rightsquigarrow": "⇝",
            "langle": "⟨",
            "rangle": "⟩",
            "iff": "⇔",
            "oplus": "⊕",
            "cap": "∩",
            "cup": "∪",
            "perp": "⊥",
            "times": "×",
            "cdot": "·",
            "lambda": "λ",
            "sigma": "σ",
            "varepsilon": "ε",
            "theta": "θ",
            "varphi": "φ",
            "chi": "χ",
            "delta": "δ",
            "infty": "∞",
            "varnothing": "∅",
            "exists": "∃",
            "forall": "∀",
            "in": "∈",
            "neq": "≠",
            "leq": "≤",
            "le": "≤",
            "geq": "≥",
            "ge": "≥",
            "sum": "Σ",
            "prod": "∏",
            "int": "∫",
            "ldots": "…",
            "mid": "│",
            "sim": "∼",
            "det": "det ",
            "dim": "dim ",
            "ker": "Ker ",
            "cos": "cos ",
            "left": "",
            "right": "",
            "quad": " ",
            "qquad": "  ",
        }
        texte = re.sub(
            r"\\([A-Za-z]+)",
            lambda m: commandes.get(m.group(1), m.group(1)),
            texte,
        )
        ponctuation = {
            r"\#": "#",
            r"\|": "‖",
            r"\,": " ",
            r"\;": " ",
            r"\:": " ",
            "\\ ": " ",
            r"\\": " ; ",
        }
        for source, cible in ponctuation.items():
            texte = texte.replace(source, cible)

        indices = str.maketrans(
            "0123456789+-=()aehijklmnoprstuvx",
            "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ",
        )
        exposants = str.maketrans(
            "0123456789+-=()ikmnT",
            "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱᵏᵐⁿᵀ",
        )

        def indice(contenu):
            converti = contenu.translate(indices)
            if all(ord(caractere) in indices for caractere in contenu):
                return converti
            return "₍" + contenu + "₎"

        def exposant(contenu):
            converti = contenu.translate(exposants)
            if all(ord(caractere) in exposants for caractere in contenu):
                return converti
            return "^(" + contenu + ")"

        texte = re.sub(
            r"_\{([^{}]+)\}",
            lambda m: indice(m.group(1)),
            texte,
        )
        texte = re.sub(r"_([A-Za-z0-9])", lambda m: indice(m.group(1)), texte)
        texte = re.sub(
            r"\^\{([^{}]+)\}",
            lambda m: exposant(m.group(1)),
            texte,
        )
        texte = re.sub(r"\^([A-Za-z0-9])", lambda m: exposant(m.group(1)), texte)
        texte = texte.replace("_⊥", "⊥").replace("^⊥", "⊥")
        texte = texte.replace("{", "").replace("}", "")
        texte = texte.replace("\uFFF0", "{").replace("\uFFF1", "}")
        texte = texte.replace("&", " ")
        texte = " ".join(texte.split())
        texte = re.sub(
            r"\s*(⇔|⇒|↔|⟶|→|←|↦|⇝|⊕|∩|∪|≠|≤|≥|∈|∼|=|\+)\s*",
            r" \1 ",
            texte,
        )
        return " ".join(texte.split())


    def _debut_rotation(self, evenement):
        self.rotation_depart = (
            self._point_sphere(evenement.x, evenement.y),
            self.orientation_3d,
            self.orientation_plan,
        )

    def _rotation(self, evenement):
        if self.rotation_depart is None:
            return
        depart, orientation_3d, orientation_plan = self.rotation_depart
        arrivee = self._point_sphere(evenement.x, evenement.y)
        mouvement = self._quaternion_entre(depart, arrivee)
        self.orientation_3d = self._quaternion_normaliser(
            self._quaternion_produit(mouvement, orientation_3d)
        )
        self.orientation_plan = self._quaternion_normaliser(
            self._quaternion_produit(mouvement, orientation_plan)
        )
        self._dessiner()

    def _point_sphere(self, x, y):
        """Projette la souris sur une sphère virtuelle centrée sur la scène."""
        largeur = max(1.0, float(self.canvas.winfo_width()))
        hauteur = max(1.0, float(self.canvas.winfo_height()))
        rayon = max(1.0, 0.46 * min(largeur, hauteur))
        cx, cy = largeur / 2, hauteur / 2
        sx = (x - cx) / rayon
        sy = (cy - y) / rayon
        carre = sx * sx + sy * sy
        if carre <= 1.0:
            sz = math.sqrt(1.0 - carre)
        else:
            norme = math.sqrt(carre)
            sx, sy, sz = sx / norme, sy / norme, 0.0
        return sx, sy, sz

    @staticmethod
    def _quaternion_identite():
        return 1.0, 0.0, 0.0, 0.0

    @staticmethod
    def _quaternion_normaliser(quaternion):
        norme = math.sqrt(sum(composante * composante for composante in quaternion))
        if norme < 1e-12:
            return FenetreLinAlgebraX._quaternion_identite()
        return tuple(composante / norme for composante in quaternion)

    @staticmethod
    def _quaternion_produit(premier, second):
        """Compose deux rotations, sans angles d'Euler ni verrouillage d'axe."""
        w1, x1, y1, z1 = premier
        w2, x2, y2, z2 = second
        return (
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    @classmethod
    def _quaternion_entre(cls, depart, arrivee):
        """Construit la rotation la plus courte entre deux points de la sphère."""
        produit = sum(a * b for a, b in zip(depart, arrivee))
        croix = (
            depart[1] * arrivee[2] - depart[2] * arrivee[1],
            depart[2] * arrivee[0] - depart[0] * arrivee[2],
            depart[0] * arrivee[1] - depart[1] * arrivee[0],
        )
        if produit < -0.999999:
            # Deux points opposés ne donnent pas directement un axe stable.
            axe = (1.0, 0.0, 0.0)
            if abs(depart[0]) > 0.8:
                axe = (0.0, 1.0, 0.0)
            croix = (
                depart[1] * axe[2] - depart[2] * axe[1],
                depart[2] * axe[0] - depart[0] * axe[2],
                depart[0] * axe[1] - depart[1] * axe[0],
            )
            return cls._quaternion_normaliser((0.0, *croix))
        return cls._quaternion_normaliser((1.0 + produit, *croix))

    @classmethod
    def _quaternion_depuis_axe(cls, axe, angle):
        demi = angle / 2
        sinus = math.sin(demi)
        return cls._quaternion_normaliser(
            (math.cos(demi), axe[0] * sinus, axe[1] * sinus, axe[2] * sinus)
        )

    @classmethod
    def _orientation_initiale_3d(cls):
        rotation_z = cls._quaternion_depuis_axe((0, 0, 1), -0.65)
        rotation_x = cls._quaternion_depuis_axe((1, 0, 0), 0.48)
        return cls._quaternion_produit(rotation_x, rotation_z)

    @classmethod
    def _tourner_point(cls, point, orientation):
        """Applique un quaternion unitaire à un point de l'espace."""
        w, x, y, z = orientation
        px, py, pz = point
        tx = 2 * (y * pz - z * py)
        ty = 2 * (z * px - x * pz)
        tz = 2 * (x * py - y * px)
        return (
            px + w * tx + (y * tz - z * ty),
            py + w * ty + (z * tx - x * tz),
            pz + w * tz + (x * ty - y * tx),
        )

    def _debut_pan(self, evenement):
        self.pan_depart = (
            evenement.x,
            evenement.y,
            self.decalage_vue[0],
            self.decalage_vue[1],
        )

    def _pan(self, evenement):
        if self.pan_depart is None:
            return
        x, y, dx, dy = self.pan_depart
        self.decalage_vue = [
            dx + evenement.x - x,
            dy + evenement.y - y,
        ]
        self._borner_decalage()
        self._dessiner()

    def _zoom_molette(self, evenement, direction=None):
        if direction is None:
            direction = 1 if evenement.delta > 0 else -1
        ancien_zoom = self.zoom_vue
        facteur = 1.12 if direction > 0 else 1 / 1.12
        self.zoom_vue = max(0.55, min(2.5, ancien_zoom * facteur))
        facteur_reel = self.zoom_vue / ancien_zoom
        cx, cy = self._centre()
        relatif_x = evenement.x - cx - self.decalage_vue[0]
        relatif_y = evenement.y - cy - self.decalage_vue[1]
        self.decalage_vue[0] += (1 - facteur_reel) * relatif_x
        self.decalage_vue[1] += (1 - facteur_reel) * relatif_y
        self._borner_decalage()
        self._dessiner()

    def _borner_decalage(self):
        limite_x = max(80, self.canvas.winfo_width() * 0.38)
        limite_y = max(80, self.canvas.winfo_height() * 0.38)
        self.decalage_vue[0] = max(
            -limite_x,
            min(limite_x, self.decalage_vue[0]),
        )
        self.decalage_vue[1] = max(
            -limite_y,
            min(limite_y, self.decalage_vue[1]),
        )

    def _reinitialiser_vue(self, _=None):
        self.zoom_vue = 1.0
        self.decalage_vue = [0.0, 0.0]
        self.pan_depart = None
        self.orientation_3d = self._orientation_initiale_3d()
        self.orientation_plan = self._quaternion_identite()
        self.rotation_depart = None
        self._dessiner()
        return "break"

    def _centre(self):
        return (
            self.canvas.winfo_width() / 2,
            self.canvas.winfo_height() / 2,
        )

    def _echelle(self):
        return self.echelle_active * self.zoom_vue

    @staticmethod

    def _amplitude(donnees) -> float:
        """Estime l'amplitude utile sans confondre un déterminant avec une coordonnée."""
        valeurs = []
        cles_ignorees = {"determinant", "determinants", "valeur", "coefficients"}

        def parcourir(objet, cle=""):
            if cle in cles_ignorees:
                return
            if isinstance(objet, (int, float)):
                if math.isfinite(float(objet)):
                    valeurs.append(abs(float(objet)))
            elif isinstance(objet, dict):
                for nom, valeur in objet.items():
                    parcourir(valeur, nom)
            elif isinstance(objet, (list, tuple)):
                for valeur in objet:
                    parcourir(valeur, cle)

        parcourir(donnees)
        return max(valeurs, default=3.0)

    def _ajuster_echelle(self, donnees):
        """Centre et ajuste chaque nouvelle image sans interaction libre."""
        largeur = max(1, self.canvas.winfo_width())
        hauteur = max(1, self.canvas.winfo_height())
        rayon = max(4.0, self._amplitude(donnees) + 1.0)
        self.echelle_active = min(largeur, hauteur) * 0.39 / rayon

    def _texte_borne(self, x, y, **options):
        """Place une étiquette dans le cadre, même près d'un bord."""
        marge = 14
        largeur = max(2 * marge, self.canvas.winfo_width())
        hauteur = max(2 * marge, self.canvas.winfo_height())
        x = max(marge, min(largeur - marge, x))
        y = max(marge, min(hauteur - marge, y))
        options.setdefault("anchor", "center")
        return self.canvas.create_text(x, y, **options)

    def _point2(self, x, y):
        """Projette un point du plan, éventuellement incliné par l'utilisateur."""
        x, y, z = self._tourner_point((x, y, 0.0), self.orientation_plan)
        profondeur = max(0.35, 1 + z * 0.055)
        cx, cy = self._centre()
        echelle = self._echelle()
        return (
            cx + self.decalage_vue[0] + echelle * x / profondeur,
            cy + self.decalage_vue[1] - echelle * y / profondeur,
        )

    def _point3(self, point):
        """Tourne puis projette un point 3D avec une perspective légère."""
        x, y, z = self._tourner_point(point, self.orientation_3d)
        profondeur = max(0.35, 1 + z * 0.055)
        cx, cy = self._centre()
        echelle = self._echelle()
        return (
            cx + self.decalage_vue[0] + echelle * x / profondeur,
            cy + self.decalage_vue[1] - echelle * y / profondeur,
            z,
        )

    @staticmethod
    def _interpoler_matrice(depart, arrivee, t):
        lignes = min(len(depart), len(arrivee))
        colonnes = min(len(depart[0]), len(arrivee[0]))
        return [
            [
                (1 - t) * depart[i][j] + t * arrivee[i][j]
                for j in range(colonnes)
            ]
            for i in range(lignes)
        ]

    @staticmethod
    def _appliquer(matrice, vecteur):
        return [
            sum(a * x for a, x in zip(ligne, vecteur))
            for ligne in matrice
        ]

    def _ligne_lumineuse(self, points, couleur=DORE, sombre=DORE_SOMBRE, largeur=2):
        aplatis = [coord for point in points for coord in point[:2]]
        self.canvas.create_line(*aplatis, fill=sombre, width=largeur + 5, smooth=True)
        self.canvas.create_line(*aplatis, fill=couleur, width=largeur, smooth=True)

    def _fleche2(self, vecteur, couleur=DORE, etiquette=""):
        depart = self._point2(0, 0)
        arrivee = self._point2(vecteur[0], vecteur[1])
        sombre = DORE_SOMBRE if couleur == DORE else BLEU_SOMBRE
        self._ligne_lumineuse([depart, arrivee], couleur, sombre, 3)
        self.canvas.create_line(
            *depart,
            *arrivee,
            fill=couleur,
            width=3,
            arrow="last",
            arrowshape=(12, 15, 5),
        )
        if etiquette:
            self._texte_borne(
                arrivee[0] + 9,
                arrivee[1] - 9,
                text=etiquette,
                fill=TEXTE,
                anchor="w",
                font=("DejaVu Sans", 10),
            )

    def _fleche3(self, vecteur, couleur=DORE, etiquette=""):
        depart = self._point3((0, 0, 0))
        arrivee = self._point3(vecteur)
        self._ligne_lumineuse([depart, arrivee], couleur, DORE_SOMBRE, 3)
        self.canvas.create_line(
            depart[0],
            depart[1],
            arrivee[0],
            arrivee[1],
            fill=couleur,
            width=3,
            arrow="last",
        )
        if etiquette:
            self._texte_borne(
                arrivee[0] + 8,
                arrivee[1] - 8,
                text=etiquette,
                fill=TEXTE,
                anchor="w",
            )


    def _dessiner(self):
        if not self.canvas.winfo_exists():
            return
        self.canvas.delete("all")
        indice, t = self._etat_temps()
        cadre = self._cadres()[indice]
        type_vue = self._vue_courante()["type"]
        self._ajuster_echelle(cadre.get("donnees", {}))
        t = t * t * (3 - 2 * t)
        # L'aiguillage reste explicite : aucun nom de méthode n'est fabriqué.
        dessinateurs = {
            "attente": self._dessiner_attente,
            "transformation": self._dessiner_transformation,
            "determinant": self._dessiner_determinant,
            "matrice": self._dessiner_matrice,
            "sous_espaces": self._dessiner_sous_espaces,
            "systeme": self._dessiner_systeme,
            "famille": self._dessiner_famille,
            "gram_schmidt": self._dessiner_gram_schmidt,
            "projection": self._dessiner_projection,
            "formule": self._dessiner_formule,
            "produit_scalaire": self._dessiner_produit_scalaire,
            "produit_vectoriel": self._dessiner_produit_vectoriel,
            "cramer": self._dessiner_cramer,
            "changement_base": self._dessiner_changement_base,
            "spectre": self._dessiner_spectre,
            "polynome": self._dessiner_polynome,
            "hyperplan": self._dessiner_hyperplan,
        }
        fonction = dessinateurs.get(type_vue, self._dessiner_attente)
        fonction(cadre.get("donnees", {}), t)
        self._dessiner_legende()

    def _dessiner_legende(self):
        legende = self.scene.get("legende", [])
        if not legende:
            return
        y = 18
        for ligne in legende:
            self.canvas.create_text(
                18,
                y,
                text=ligne,
                fill=SECONDAIRE,
                anchor="nw",
                font=("DejaVu Sans", 9),
            )
            y += 18

    def _dessiner_attente(self, donnees, _):
        cx, cy = self._centre()
        self.canvas.create_line(cx - 38, cy, cx + 38, cy, fill=GRILLE)
        self.canvas.create_line(cx, cy - 38, cx, cy + 38, fill=GRILLE)
        self.canvas.create_text(
            cx,
            cy + 62,
            text=donnees.get("message", "En attente du terminal"),
            fill=SECONDAIRE,
            font=("DejaVu Sans", 10),
        )

    def _dessiner_transformation(self, donnees, t):
        depart = donnees.get("depart")
        arrivee = donnees.get("arrivee")
        if not depart or not arrivee:
            return
        hauteur = donnees.get("hauteur", len(arrivee))
        largeur = donnees.get("largeur", len(arrivee[0]))
        if hauteur == largeur == 2:
            self._grille2(self._interpoler_matrice(depart, arrivee, t))
        elif hauteur == largeur == 3:
            self._grille3(self._interpoler_matrice(depart, arrivee, t))
        else:
            self._transformation_rectangulaire(arrivee, hauteur, largeur, t)

    def _grille2(self, matrice, surface=False):
        """Dessine l'image d'un quadrillage du plan par une matrice."""
        etendue = 7
        for k in range(-etendue, etendue + 1):
            p1 = self._appliquer(matrice, [k, -etendue])
            p2 = self._appliquer(matrice, [k, etendue])
            self.canvas.create_line(
                *self._point2(*p1),
                *self._point2(*p2),
                fill=GRILLE_FORTE if k == 0 else GRILLE,
                width=2 if k == 0 else 1,
            )
            p1 = self._appliquer(matrice, [-etendue, k])
            p2 = self._appliquer(matrice, [etendue, k])
            self.canvas.create_line(
                *self._point2(*p1),
                *self._point2(*p2),
                fill=GRILLE_FORTE if k == 0 else GRILLE,
                width=2 if k == 0 else 1,
            )
        e1 = self._appliquer(matrice, [1, 0])
        e2 = self._appliquer(matrice, [0, 1])
        if surface:
            points = [
                self._point2(0, 0),
                self._point2(*e1),
                self._point2(e1[0] + e2[0], e1[1] + e2[1]),
                self._point2(*e2),
            ]
            self.canvas.create_polygon(
                *[coord for point in points for coord in point],
                fill=DORE_SOMBRE,
                outline=DORE,
                width=2,
            )
        self._fleche2(e1, DORE, "A(e₁)")
        self._fleche2(e2, BLEU, "A(e₂)")
        self._dessiner_neutre2()

    def _grille3(self, matrice):
        """Dessine trois familles de droites formant une grille de l'espace."""
        etendue = 2
        for axe in range(3):
            autres = [indice for indice in range(3) if indice != axe]
            for a in range(-etendue, etendue + 1):
                for b in range(-etendue, etendue + 1):
                    debut = [0, 0, 0]
                    fin = [0, 0, 0]
                    debut[axe], fin[axe] = -etendue, etendue
                    debut[autres[0]] = fin[autres[0]] = a
                    debut[autres[1]] = fin[autres[1]] = b
                    p1 = self._point3(self._appliquer(matrice, debut))
                    p2 = self._point3(self._appliquer(matrice, fin))
                    principal = a == b == 0
                    self.canvas.create_line(
                        p1[0],
                        p1[1],
                        p2[0],
                        p2[1],
                        fill=GRILLE_FORTE if principal else GRILLE,
                        width=2 if principal else 1,
                    )
        points = []
        for x in range(-1, 2):
            for y in range(-1, 2):
                for z in range(-1, 2):
                    projection = self._point3(self._appliquer(matrice, [x, y, z]))
                    points.append((projection[2], projection))
        for _, point in sorted(points):
            rayon = 1.5
            self.canvas.create_oval(
                point[0] - rayon,
                point[1] - rayon,
                point[0] + rayon,
                point[1] + rayon,
                fill=GRILLE_FORTE,
                outline="",
            )
        for j, couleur in enumerate((DORE, BLEU, TEXTE)):
            self._fleche3([matrice[i][j] for i in range(3)], couleur, f"A(e{j + 1})")
        self._dessiner_neutre3()

    def _transformation_rectangulaire(self, matrice, hauteur, largeur, t):
        """Traite R^n vers R^m lorsque la matrice n'est pas carrée."""
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_line(w / 2, 40, w / 2, h - 40, fill=GRILLE)
        self.canvas.create_text(w / 4, 35, text=f"Départ R^{largeur}", fill=TEXTE)
        self.canvas.create_text(3 * w / 4, 35, text=f"Arrivée R^{hauteur}", fill=TEXTE)
        points = []
        if largeur == 2:
            points = [[x, y] for x in range(-2, 3) for y in range(-2, 3)]
        elif largeur == 3:
            points = [
                [x, y, z]
                for x in range(-2, 3)
                for y in range(-2, 3)
                for z in range(-2, 3)
            ]
        for point in points:
            if largeur == 2:
                gauche = (w / 4 + point[0] * 34, h / 2 - point[1] * 34)
            else:
                p = self._point3(point)
                gauche = (p[0] - w / 4, p[1])
            image = self._appliquer(matrice, point)
            if hauteur == 2:
                droite = (3 * w / 4 + image[0] * 28, h / 2 - image[1] * 28)
            else:
                p = self._point3(image)
                droite = (p[0] + w / 4, p[1])
            self.canvas.create_oval(
                gauche[0] - 2,
                gauche[1] - 2,
                gauche[0] + 2,
                gauche[1] + 2,
                fill=BLEU,
                outline="",
            )
            courant = (
                (1 - t) * gauche[0] + t * droite[0],
                (1 - t) * gauche[1] + t * droite[1],
            )
            self.canvas.create_line(
                gauche[0],
                gauche[1],
                courant[0],
                courant[1],
                fill=GRILLE,
            )
            rayon = 2 + t
            self.canvas.create_oval(
                courant[0] - rayon,
                courant[1] - rayon,
                courant[0] + rayon,
                courant[1] + rayon,
                fill=DORE,
                outline="",
            )
        self._dessiner_neutre_centre(w / 4, h / 2, "0 départ")
        self._dessiner_neutre_centre(3 * w / 4, h / 2, "0 arrivée")

    def _dessiner_determinant(self, donnees, t):
        """Fait évoluer le carré ou cube unité et son aire ou volume orienté."""
        matrice = self._interpoler_matrice(donnees["depart"], donnees["arrivee"], t)
        if donnees.get("dimension") == 2:
            self._grille2(matrice, surface=True)
            det_t = matrice[0][0] * matrice[1][1] - matrice[0][1] * matrice[1][0]
            self.canvas.create_text(
                self.canvas.winfo_width() - 20,
                20,
                text=f"aire orientée = {det_t:.3g}",
                fill=TEXTE,
                anchor="ne",
                font=("DejaVu Sans", 11),
            )
        else:
            self._grille3(matrice)

    def _dessiner_matrice(self, donnees, t):
        """Affiche une matrice comme objet de calcul, sans géométrie inventée."""
        matrice = donnees.get("matrice", [])
        if not matrice:
            return
        lignes = len(matrice)
        colonnes = len(matrice[0])
        largeur_cellule = min(100, max(54, self.canvas.winfo_width() / (colonnes + 4)))
        hauteur_cellule = 44
        largeur = colonnes * largeur_cellule
        hauteur = lignes * hauteur_cellule
        x0 = self.canvas.winfo_width() / 2 - largeur / 2
        y0 = self.canvas.winfo_height() / 2 - hauteur / 2
        self.canvas.create_line(x0 - 16, y0 - 10, x0 - 16, y0 + hauteur + 10, fill=TEXTE, width=2)
        self.canvas.create_line(x0 - 16, y0 - 10, x0 - 7, y0 - 10, fill=TEXTE, width=2)
        self.canvas.create_line(x0 - 16, y0 + hauteur + 10, x0 - 7, y0 + hauteur + 10, fill=TEXTE, width=2)
        self.canvas.create_line(x0 + largeur + 16, y0 - 10, x0 + largeur + 16, y0 + hauteur + 10, fill=TEXTE, width=2)
        self.canvas.create_line(x0 + largeur + 7, y0 - 10, x0 + largeur + 16, y0 - 10, fill=TEXTE, width=2)
        self.canvas.create_line(x0 + largeur + 7, y0 + hauteur + 10, x0 + largeur + 16, y0 + hauteur + 10, fill=TEXTE, width=2)
        for i, ligne in enumerate(matrice):
            for j, valeur in enumerate(ligne):
                couleur = DORE if j == i else TEXTE
                self.canvas.create_text(
                    x0 + (j + 0.5) * largeur_cellule,
                    y0 + (i + 0.5) * hauteur_cellule,
                    text=valeur,
                    fill=couleur,
                    font=("DejaVu Sans Mono", 13),
                )
        for i in donnees.get("lignes_actives", []):
            if 0 <= i < lignes:
                y = y0 + i * hauteur_cellule
                self.canvas.create_rectangle(
                    x0,
                    y,
                    x0 + t * largeur,
                    y + hauteur_cellule,
                    outline=DORE,
                    width=2,
                )

    def _dessiner_sous_espaces(self, donnees, t):
        matrice = donnees.get("matrice")
        if matrice and len(matrice) == len(matrice[0]) == 2:
            interpolee = self._interpoler_matrice(_identite_locale(2), matrice, t)
            self._grille2(interpolee)
        noyau = donnees.get("noyau", [])
        image = donnees.get("image", [])
        for i, vecteur in enumerate(noyau):
            if len(vecteur) == 2:
                p1 = self._point2(-6 * vecteur[0], -6 * vecteur[1])
                p2 = self._point2(6 * vecteur[0], 6 * vecteur[1])
                self._ligne_lumineuse([p1, p2], DORE, DORE_SOMBRE, 2)
        for i, vecteur in enumerate(image):
            if len(vecteur) == 2:
                self._fleche2(vecteur, BLEU, f"Im {i + 1}")

    def _dessiner_systeme(self, donnees, t):
        """Dessine les contraintes et leur intersection en dimensions 2 ou 3."""
        matrice = donnees.get("matrice", [])
        second = donnees.get("second", [])
        if not matrice or len(matrice[0]) != 2:
            self._dessiner_matrice({"matrice": [[str(x) for x in ligne] for ligne in matrice]}, t)
            return
        self._axes2()
        couleurs = (DORE, BLEU)
        for i, (ligne, valeur) in enumerate(zip(matrice, second)):
            a, b = ligne
            if abs(b) > 1e-12:
                p1 = [-6, (valeur + 6 * a) / b]
                p2 = [6, (valeur - 6 * a) / b]
            elif abs(a) > 1e-12:
                p1 = [valeur / a, -6]
                p2 = [valeur / a, 6]
            else:
                continue
            self._ligne_lumineuse(
                [self._point2(*p1), self._point2(*p2)],
                couleurs[i % 2],
                DORE_SOMBRE if i % 2 == 0 else BLEU_SOMBRE,
                2,
            )
        solution = donnees.get("solution")
        if solution and len(solution) >= 2:
            x, y = self._point2(solution[0], solution[1])
            rayon = 3 + 5 * t
            self.canvas.create_oval(
                x - rayon,
                y - rayon,
                x + rayon,
                y + rayon,
                fill=TEXTE,
                outline="",
            )

    def _axes2(self):
        self.canvas.create_line(*self._point2(-8, 0), *self._point2(8, 0), fill=GRILLE_FORTE)
        self.canvas.create_line(*self._point2(0, -8), *self._point2(0, 8), fill=GRILLE_FORTE)
        self._dessiner_neutre2()

    def _dessiner_neutre2(self, etiquette="0"):
        x, y = self._point2(0, 0)
        self.canvas.create_oval(
            x - 10,
            y - 10,
            x + 10,
            y + 10,
            fill=ROUGE_SOMBRE,
            outline="",
        )
        self.canvas.create_oval(
            x - 5,
            y - 5,
            x + 5,
            y + 5,
            fill=ROUGE,
            outline="",
        )
        self.canvas.create_text(
            x + 10,
            y + 13,
            text=etiquette,
            fill=ROUGE,
            anchor="nw",
        )

    def _dessiner_neutre3(self, etiquette="0"):
        x, y, _ = self._point3((0, 0, 0))
        self.canvas.create_oval(
            x - 10,
            y - 10,
            x + 10,
            y + 10,
            fill=ROUGE_SOMBRE,
            outline="",
        )
        self.canvas.create_oval(
            x - 5,
            y - 5,
            x + 5,
            y + 5,
            fill=ROUGE,
            outline="",
        )
        self.canvas.create_text(x + 10, y + 10, text=etiquette, fill=ROUGE, anchor="nw")

    def _dessiner_famille(self, donnees, t):
        """Choisit une représentation fidèle selon la dimension ambiante."""
        famille = donnees.get("famille", [])
        dimension = donnees.get("dimension", 2)
        apparition = 1 - (1 - t) ** 3
        if dimension == 1:
            self._dessiner_famille_dimension_un(famille, apparition)
        elif dimension == 2:
            self._axes2()
            if len(famille) >= 2 and all(len(v) == 2 for v in famille[:2]):
                u, v = famille[:2]
                determinant = u[0] * v[1] - u[1] * v[0]
                if abs(determinant) > 1e-12:
                    for k in range(-4, 5):
                        debut = [
                            apparition * (-4 * u[i] + k * v[i])
                            for i in range(2)
                        ]
                        fin = [
                            apparition * (4 * u[i] + k * v[i])
                            for i in range(2)
                        ]
                        self.canvas.create_line(
                            *self._point2(*debut),
                            *self._point2(*fin),
                            fill=GRILLE,
                        )
                        debut = [
                            apparition * (-4 * v[i] + k * u[i])
                            for i in range(2)
                        ]
                        fin = [
                            apparition * (4 * v[i] + k * u[i])
                            for i in range(2)
                        ]
                        self.canvas.create_line(
                            *self._point2(*debut),
                            *self._point2(*fin),
                            fill=GRILLE,
                        )
            for i, vecteur in enumerate(famille):
                self._fleche2(
                    [apparition * x for x in vecteur],
                    DORE if i % 2 == 0 else BLEU,
                    f"v{i + 1}",
                )
        elif dimension == 3:
            for i, vecteur in enumerate(famille):
                self._fleche3(
                    [apparition * x for x in vecteur],
                    DORE if i % 2 == 0 else BLEU,
                    f"v{i + 1}",
                )
        else:
            self._portrait_dimension_superieure(
                famille,
                donnees.get("relations", []),
                dimension,
                apparition,
            )

    def _dessiner_famille_dimension_un(self, famille, t):
        """Représente fidèlement un espace de dimension un par une droite."""
        cx, cy = self._centre()
        largeur = self.canvas.winfo_width()
        self.canvas.create_line(
            35,
            cy,
            largeur - 35,
            cy,
            fill=GRILLE_FORTE,
            arrow="last",
        )
        self.canvas.create_text(largeur - 35, cy - 18, text="R", fill=SECONDAIRE)
        maximum = max((abs(float(v[0])) for v in famille if v), default=1.0)
        echelle = largeur * 0.34 / max(1.0, maximum)
        for i, vecteur in enumerate(famille):
            if len(vecteur) != 1:
                continue
            x = cx + t * echelle * float(vecteur[0])
            couleur = DORE if i % 2 == 0 else BLEU
            self.canvas.create_line(
                cx,
                cy,
                x,
                cy,
                fill=couleur,
                width=3,
                arrow="last",
            )
            self._texte_borne(x, cy - 20, text=f"v{i + 1}", fill=TEXTE)

    def _portrait_dimension_superieure(self, famille, relations, dimension, t):
        """Représente R^4 et R^5 par coordonnées parallèles.

        Ce portrait n'affirme pas qu'un espace de dimension 5 ressemble à un
        plan. Chaque axe vertical représente une coordonnée et chaque vecteur
        devient une ligne brisée qui traverse ces axes.
        """
        cx, cy = self._centre()
        largeur = self.canvas.winfo_width()
        hauteur = self.canvas.winfo_height()
        marge = max(70, largeur * 0.12)
        xs = [
            marge + i * (largeur - 2 * marge) / max(1, dimension - 1)
            for i in range(dimension)
        ]
        demi_hauteur = hauteur * 0.29
        maximum = max(
            (abs(float(x)) for vecteur in famille for x in vecteur),
            default=1.0,
        )
        maximum = max(1.0, maximum)
        self.canvas.create_line(marge, cy, largeur - marge, cy, fill=GRILLE)
        for i, x in enumerate(xs):
            self.canvas.create_line(
                x,
                cy - demi_hauteur,
                x,
                cy + demi_hauteur,
                fill=GRILLE_FORTE,
            )
            self.canvas.create_text(
                x,
                cy + demi_hauteur + 20,
                text=f"x{i + 1}",
                fill=TEXTE,
            )
            self.canvas.create_text(
                x,
                cy - demi_hauteur - 14,
                text=f"+{maximum:g}",
                fill=SECONDAIRE,
            )
            self.canvas.create_text(
                x,
                cy + demi_hauteur + 40,
                text=f"−{maximum:g}",
                fill=SECONDAIRE,
            )
        for indice, vecteur in enumerate(famille[:3]):
            points = [
                (
                    x,
                    cy - t * demi_hauteur * float(valeur) / maximum,
                )
                for x, valeur in zip(xs, vecteur)
            ]
            if points:
                couleur = DORE if indice % 2 == 0 else BLEU
                self.canvas.create_line(
                    *[coord for point in points for coord in point],
                    fill=couleur,
                    width=2,
                )
                for x, y in points:
                    self.canvas.create_oval(
                        x - 3,
                        y - 3,
                        x + 3,
                        y + 3,
                        fill=couleur,
                        outline="",
                    )
                self.canvas.create_text(
                    20,
                    52 + 20 * indice,
                    text=f"v{indice + 1}",
                    fill=couleur,
                    anchor="w",
                )
        self.canvas.create_text(
            cx,
            self.canvas.winfo_height() - 24,
            text=(
                f"coordonnées parallèles dans R^{dimension} : "
                "chaque axe vertical porte une coordonnée"
            ),
            fill=SECONDAIRE,
        )
        if relations:
            self.canvas.create_text(
                cx,
                24,
                text=f"{len(relations)} relation(s) de dépendance détectée(s)",
                fill=SECONDAIRE,
            )

    def _dessiner_gram_schmidt(self, donnees, t):
        self._axes2()
        for i, vecteur in enumerate(donnees.get("famille", [])):
            if len(vecteur) == 2:
                self._fleche2(vecteur, GRILLE_FORTE, f"v{i + 1}")
        for i, vecteur in enumerate(donnees.get("resultat", [])):
            if len(vecteur) == 2:
                self._fleche2(
                    [t * x for x in vecteur],
                    DORE if i % 2 == 0 else BLEU,
                    f"u{i + 1}",
                )

    def _dessiner_projection(self, donnees, t):
        vecteur = donnees.get("vecteur", [])
        projection = donnees.get("projection", [])
        cible = donnees.get("cible", projection)
        famille = donnees.get("famille", [])
        if len(vecteur) != 2:
            return
        self._axes2()
        if famille and len(famille[0]) == 2:
            direction = famille[0]
            p1 = self._point2(-7 * direction[0], -7 * direction[1])
            p2 = self._point2(7 * direction[0], 7 * direction[1])
            self._ligne_lumineuse([p1, p2], BLEU, BLEU_SOMBRE, 1)
        self._fleche2(vecteur, DORE, "v")
        courant = [
            (1 - t) * vecteur[i] + t * cible[i]
            for i in range(2)
        ]
        self._fleche2(courant, BLEU, "image")
        if projection:
            p = self._point2(*projection)
            v = self._point2(*vecteur)
            self.canvas.create_line(*p, *v, fill=TEXTE, dash=(5, 5), width=1)

    def _dessiner_formule(self, donnees, __):
        cx, cy = self._centre()
        lignes = donnees.get(
            "lignes",
            [
                "Corps K",
                "Espace vectoriel E",
                "Application linéaire",
                "Matrice dans une base",
            ],
        )
        intervalle = 80 if len(lignes) > 2 else 96
        depart = cy - intervalle * (len(lignes) - 1) / 2
        niveaux = [(texte, depart + i * intervalle) for i, texte in enumerate(lignes)]
        for i, (texte, y) in enumerate(niveaux):
            self.canvas.create_text(
                cx,
                y,
                text=texte,
                fill=TEXTE,
                font=("DejaVu Sans", 13),
                width=max(220, self.canvas.winfo_width() - 120),
                justify="center",
            )
            if i:
                self.canvas.create_line(cx, y - 52, cx, y - 20, fill=DORE, arrow="last")

    def _dessiner_neutre_centre(self, x, y, etiquette):
        self.canvas.create_oval(
            x - 14,
            y - 14,
            x + 14,
            y + 14,
            fill=ROUGE_SOMBRE,
            outline="",
        )
        self.canvas.create_oval(
            x - 7,
            y - 7,
            x + 7,
            y + 7,
            fill=ROUGE,
            outline="",
        )
        self.canvas.create_text(x, y + 23, text=etiquette, fill=ROUGE)

    def _dessiner_produit_scalaire(self, donnees, t):
        u, v = donnees.get("u", []), donnees.get("v", [])
        if len(u) == len(v) == 2:
            self._axes2()
            self._fleche2(u, BLEU, "u")
            self._fleche2(v, DORE, "v")
            norme = sum(x * x for x in u)
            coefficient = sum(a * b for a, b in zip(u, v)) / norme if norme else 0
            projection = [coefficient * x for x in u]
            self._fleche2([t * x for x in projection], TEXTE, "proj")

    def _dessiner_produit_vectoriel(self, donnees, t):
        u, v, w = donnees.get("u", []), donnees.get("v", []), donnees.get("w", [])
        if len(u) != 3:
            return
        sommets = [(0, 0, 0), u, [u[i] + v[i] for i in range(3)], v]
        points = [self._point3(point) for point in sommets]
        self.canvas.create_polygon(
            *[coord for point in points for coord in point[:2]],
            fill=DORE_SOMBRE,
            outline=DORE,
        )
        self._fleche3(u, DORE, "u")
        self._fleche3(v, BLEU, "v")
        self._fleche3([t * x for x in w], TEXTE, "u×v")
        self._dessiner_neutre3()

    def _dessiner_cramer(self, donnees, t):
        matrices = donnees.get("matrices", [])
        determinants = donnees.get("determinants", [])
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        largeur = w / max(1, len(matrices))
        for i, matrice in enumerate(matrices):
            if len(matrice) != 2:
                continue
            e1 = [matrice[0][0], matrice[1][0]]
            e2 = [matrice[0][1], matrice[1][1]]
            centre = ((i + 0.5) * largeur, h / 2)
            echelle = min(largeur, h) / 7
            points_monde = [[0, 0], e1, [e1[0] + e2[0], e1[1] + e2[1]], e2]
            points = [
                (centre[0] + echelle * p[0], centre[1] - echelle * p[1])
                for p in points_monde
            ]
            self.canvas.create_polygon(
                *[coord for point in points for coord in point],
                fill=DORE_SOMBRE,
                outline=DORE,
                width=2,
            )
            self.canvas.create_text(
                centre[0],
                35,
                text=f"det = {determinants[i]:.3g}",
                fill=TEXTE,
            )

    def _dessiner_changement_base(self, donnees, t):
        ancienne = donnees.get("ancienne", _identite_locale(2))
        nouvelle = donnees.get("nouvelle", _identite_locale(2))
        if len(ancienne) == 2 and isinstance(ancienne[0], list) and len(ancienne[0]) == 2:
            if len(ancienne) == len(nouvelle) == 2:
                depart = [
                    [ancienne[0][0], ancienne[1][0]],
                    [ancienne[0][1], ancienne[1][1]],
                ]
                arrivee = [
                    [nouvelle[0][0], nouvelle[1][0]],
                    [nouvelle[0][1], nouvelle[1][1]],
                ]
                self._grille2(self._interpoler_matrice(depart, arrivee, t))
        vecteur = donnees.get("vecteur")
        if vecteur and len(vecteur) == 2:
            self._fleche2(vecteur, DORE, "même vecteur")

    def _dessiner_spectre(self, donnees, t):
        """Montre les directions qui restent stables sous la transformation."""
        matrice = donnees.get("matrice")
        if matrice:
            self._grille2(self._interpoler_matrice(_identite_locale(2), matrice, t))
        for i, propre in enumerate(donnees.get("spectre", [])):
            vecteur = propre["vecteur"]
            if len(vecteur) == 2:
                norme = math.hypot(*vecteur)
                if norme:
                    direction = [x / norme for x in vecteur]
                    p1 = self._point2(-7 * direction[0], -7 * direction[1])
                    p2 = self._point2(7 * direction[0], 7 * direction[1])
                    self._ligne_lumineuse(
                        [p1, p2],
                        DORE if i == 0 else BLEU,
                        DORE_SOMBRE if i == 0 else BLEU_SOMBRE,
                        2,
                    )
                    self._texte_borne(
                        p2[0],
                        p2[1],
                        text=f"λ={propre['valeur']:.3g}",
                        fill=TEXTE,
                    )

    def _dessiner_polynome(self, donnees, t):
        avant = donnees.get("avant", [])
        apres = donnees.get("apres", [])
        n = max(len(avant), len(apres))
        coefficients = [
            (1 - t) * (avant[i] if i < len(avant) else 0)
            + t * (apres[i] if i < len(apres) else 0)
            for i in range(n)
        ]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        separation = w * 0.66
        self.canvas.create_line(separation, 30, separation, h - 30, fill=GRILLE)
        origine = (separation / 2, h / 2)
        echelle_x = separation / 10
        echelle_y = h / 14
        points = []
        for k in range(201):
            x = -5 + 10 * k / 200
            y = sum(c * x**i for i, c in enumerate(coefficients))
            y = max(-7, min(7, y))
            points.append((origine[0] + echelle_x * x, origine[1] - echelle_y * y))
        self._ligne_lumineuse(points, DORE, DORE_SOMBRE, 2)
        zone_x = separation + 20
        zone_w = w - separation - 40
        maximum = max(1, *(abs(c) for c in coefficients))
        for i, coefficient in enumerate(coefficients):
            x = zone_x + (i + 0.5) * zone_w / max(1, n)
            hauteur = coefficient / maximum * h * 0.3
            self.canvas.create_rectangle(
                x - 12,
                h / 2,
                x + 12,
                h / 2 - hauteur,
                fill=BLEU,
                outline="",
            )
            self.canvas.create_text(x, h / 2 + 18, text=f"X^{i}", fill=SECONDAIRE)

    def _dessiner_hyperplan(self, donnees, t):
        """Dessine l'ensemble de niveau défini par un vecteur normal."""
        normale = donnees.get("normale", [])
        constante = donnees.get("constante", 0)
        if len(normale) == 2:
            self._axes2()
            a, b = normale
            if abs(b) > 1e-12:
                p1 = [-7, (constante + 7 * a) / b]
                p2 = [7, (constante - 7 * a) / b]
            else:
                p1 = [constante / a, -7]
                p2 = [constante / a, 7]
            self._ligne_lumineuse([self._point2(*p1), self._point2(*p2)], BLEU, BLEU_SOMBRE, 2)
            self._fleche2([t * x for x in normale], DORE, "n")
        elif len(normale) == 3:
            a, b, c = normale
            if abs(c) < 1e-12:
                return
            for k in range(-3, 4):
                ligne = []
                for s in range(-3, 4):
                    x, y = k, s
                    z = (constante - a * x - b * y) / c
                    ligne.append(self._point3((x, y, z)))
                self.canvas.create_line(
                    *[coord for point in ligne for coord in point[:2]],
                    fill=BLEU,
                )
            self._fleche3([t * x for x in normale], DORE, "n")
            self._dessiner_neutre3()

    def fermer(self):
        self._annuler_animation()
        try:
            self.racine.destroy()
        except Exception:
            pass


def lancer_fenetre(file_messages) -> None:
    """Point d'entrée du processus graphique."""
    try:
        import tkinter as tk

        racine = tk.Tk()
    except Exception as erreur:
        print(f"Fenêtre graphique indisponible : {erreur}")
        return
    FenetreLinAlgebraX(racine, file_messages)
    racine.mainloop()
