"""Tests du projet final CS50P  """

from fractions import Fraction
import time

from algebre import (
    Matrice,
    Vecteur,
    base_intersection,
    base_somme,
    complement_de_base,
    orthogonaliser,
    projection_orthogonale,
    relation_dependance,
)
from analyseur import analyser_systeme, construire_objet, evaluer_structure
from moteur import Laboratoire, Reponse
from visualisation.fenetre_observatoire import FenetreLinAlgebraX
from polynomes import analyser_polynome
from project import (
    BARRE_COMMANDES,
    afficher_reponse,
    executer_commande,
    lire_commande,
)


def doit_lever(type_erreur, fonction, *arguments):
    try:
        fonction(*arguments)
    except type_erreur:
        return
    assert False, f"{type_erreur.__name__} aurait dû être levée"


def test_lire_commande(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda invite: "det A")
    assert lire_commande() == "det A"
    assert BARRE_COMMANDES in capsys.readouterr().out


def test_afficher_reponse(capsys):
    afficher_reponse(Reponse("Résultat", r"x=\frac{1}{2}"), True)
    sortie = capsys.readouterr().out
    assert "Résultat" in sortie
    assert r"x=\frac{1}{2}" in sortie


def test_evaluer_et_construire_les_objets():
    assert evaluer_structure("3/4") == Fraction(3, 4)
    vecteur = construire_objet("(1, 2/3, -4)")
    assert vecteur == Vecteur((1, Fraction(2, 3), -4))
    matrice = construire_objet("[[1, 2], [3/2, 4]]")
    assert matrice == Matrice([[1, 2], [Fraction(3, 2), 4]])
    assert matrice.determinant() == 1


def test_analyser_systeme():
    matrice, second_membre, variables = analyser_systeme(
        "2x + y = 3 ; x - y = 0"
    )
    assert matrice == Matrice([[2, 1], [1, -1]])
    assert second_membre == Vecteur((3, 0))
    assert variables == ("x", "y")


def test_executer_commande():
    laboratoire = Laboratoire()
    executer_commande("A = [[1, 2], [3, 4]]", laboratoire)
    reponse = executer_commande("det A", laboratoire)
    assert "det(A) = -2" in reponse.texte
    assert r"\det" in reponse.latex


def test_classes_ordinaires_et_absence_du_cours():
    """La variante simple n'utilise ni dataclass ni commande de cours."""
    assert not hasattr(Vecteur, "__dataclass_fields__")
    assert not hasattr(Reponse, "__dataclass_fields__")
    doit_lever(ValueError, executer_commande, "cours", Laboratoire())


def test_reduction_noyau_et_image():
    matrice = Matrice([[1, 2, 3], [2, 4, 6]])
    assert matrice.rang() == 1
    assert len(matrice.base_noyau()) == 2
    assert len(matrice.base_image()) == 1
    for vecteur in matrice.base_noyau():
        assert matrice.appliquer(vecteur).est_nul()


def test_inverse_exacte():
    matrice = Matrice([[2, 1], [1, 2]])
    inverse, _ = matrice.inverse()
    assert matrice @ inverse == Matrice.identite(2)
    assert inverse == Matrice(
        [[Fraction(2, 3), Fraction(-1, 3)], [Fraction(-1, 3), Fraction(2, 3)]]
    )


def test_systemes_unique_infini_et_impossible():
    unique = Matrice([[1, 1], [1, -1]]).resoudre(Vecteur((4, 2)))
    assert unique.unique
    assert unique.particuliere == Vecteur((3, 1))

    infini = Matrice([[1, 1], [2, 2]]).resoudre(Vecteur((2, 4)))
    assert infini.compatible
    assert len(infini.directions) == 1

    impossible = Matrice([[1, 1], [2, 2]]).resoudre(Vecteur((2, 5)))
    assert not impossible.compatible


def test_famille_et_relation_de_dependance():
    famille = (Vecteur((1, 0)), Vecteur((0, 1)), Vecteur((1, 1)))
    relations = relation_dependance(famille)
    assert len(relations) == 1
    assert Matrice.par_colonnes(famille).appliquer(relations[0]).est_nul()


def test_gram_schmidt_et_projection():
    famille = (Vecteur((1, 1)), Vecteur((1, 0)))
    orthogonale = orthogonaliser(famille)
    assert orthogonale[0].produit_scalaire(orthogonale[1]) == 0
    projection = projection_orthogonale(Vecteur((3, 2)), [Vecteur((1, 1))])
    assert projection == Vecteur((Fraction(5, 2), Fraction(5, 2)))


def test_polynome_comme_vecteur():
    polynome = analyser_polynome("X^3 - 2X + 1")
    assert str(polynome) == "X^3 - 2X + 1"
    assert str(polynome.derivee()) == "3X^2 - 2"
    assert polynome.evaluer(2) == 5


def test_somme_intersection_et_supplementaire():
    f = (Vecteur((1, 0, 0)), Vecteur((0, 1, 0)))
    g = (Vecteur((0, 1, 0)), Vecteur((0, 0, 1)))
    assert len(base_somme(f, g)) == 3
    assert base_intersection(f, g) == (Vecteur((0, 1, 0)),)
    assert complement_de_base(f) == (Vecteur((0, 0, 1)),)


def test_hyperplan_et_isomorphisme():
    laboratoire = Laboratoire()
    executer_commande("H = {2x-y+z=3}", laboratoire)
    assert "Hyperplan affine" in executer_commande("hyperplan H", laboratoire).texte
    executer_commande("A = [[1, 1], [0, 1]]", laboratoire)
    assert "Isomorphisme : oui" in executer_commande(
        "isomorphisme A", laboratoire
    ).texte
    assert "Automorphisme : oui" in executer_commande(
        "automorphisme A", laboratoire
    ).texte


def test_visualisation_automatique():
    laboratoire = Laboratoire()
    definition = executer_commande("A = [[2, 1], [1, 2]]", laboratoire)
    assert definition.scene is None

    etude = executer_commande("etudier A", laboratoire)
    assert etude.scene["vues"][0]["type"] == "transformation"

    inverse = executer_commande("inverse A", laboratoire)
    assert [vue["nom"] for vue in inverse.scene["vues"]] == [
        "Géométrie",
        "Calcul",
    ]
    assert len(inverse.scene["vues"][0]["cadres"]) == 2
    assert len(inverse.scene["vues"][1]["cadres"]) >= 2


def test_suppression_memoire_et_retour():
    laboratoire = Laboratoire()
    executer_commande("A = [[1, 2], [3, 4]]", laboratoire)
    executer_commande("v = (2, 1)", laboratoire)

    memoire = executer_commande("memoire", laboratoire)
    assert "ACTIONS RÉCENTES" in memoire.texte
    assert "A = [[1, 2], [3, 4]]" in memoire.texte
    assert "v" in memoire.texte

    suppression = executer_commande("supprimer A", laboratoire)
    assert "A" not in laboratoire.objets
    assert suppression.scene["vues"][0]["type"] == "attente"

    retour = executer_commande("retour", laboratoire)
    assert "A" in laboratoire.objets
    assert "supprimer A" in retour.texte


def test_barre_terminale_condensee():
    assert BARRE_COMMANDES == "[commandes] [memoire] [retour]"
    laboratoire = Laboratoire()
    liste = executer_commande("commandes", laboratoire)
    assert "supprimer A" in liste.texte
    assert "inverse A" in liste.texte
    assert "quitter" in liste.texte


def test_retour_annule_une_definition_et_une_scene():
    laboratoire = Laboratoire()
    executer_commande("A = [[2, 1], [1, 2]]", laboratoire)
    transformation = executer_commande("etudier A", laboratoire)
    assert laboratoire.scene_courante == transformation.scene

    executer_commande("retour", laboratoire)
    assert laboratoire.scene_courante["vues"][0]["type"] == "attente"

    executer_commande("retour", laboratoire)
    assert "A" not in laboratoire.objets


def test_retour_retablit_un_objet_remplace():
    laboratoire = Laboratoire()
    executer_commande("A = [[1, 0], [0, 1]]", laboratoire)
    ancienne = laboratoire.objets["A"]
    executer_commande("A = [[2, 0], [0, 2]]", laboratoire)
    assert laboratoire.objets["A"] != ancienne

    executer_commande("annuler", laboratoire)
    assert laboratoire.objets["A"] == ancienne
    assert "annulation" in executer_commande("historique", laboratoire).texte


def test_observatoire_place_a_droite_et_reapparait():
    class FausseRacine:
        def __init__(self):
            self.geometrie = ""
            self.actions = []

        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

        def geometry(self, valeur):
            self.geometrie = valeur

        def deiconify(self):
            self.actions.append("deiconify")

        def lift(self):
            self.actions.append("lift")

        def attributes(self, nom, valeur):
            self.actions.append((nom, valeur))

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.racine = FausseRacine()
    fenetre._placer_a_droite()
    assert fenetre.racine.geometrie == "900x990+1008+34"

    fenetre._apparaitre()
    assert "deiconify" in fenetre.racine.actions
    assert "lift" in fenetre.racine.actions
    assert ("-topmost", True) in fenetre.racine.actions


def test_bouton_lecture_relance_une_animation_terminee():
    class FausseRacine:
        def after(self, delai, fonction):
            self.programme = (delai, fonction)
            return "animation"

        def after_cancel(self, _):
            pass

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.racine = FausseRacine()
    fenetre.scene = {
        "vues": [{"nom": "Vue", "type": "attente", "cadres": [{}, {}]}]
    }
    fenetre.vue = 0
    fenetre.position = 2.0
    fenetre.lecture = False
    fenetre.animation_id = None
    fenetre.duree_cadre = 2.4
    fenetre._mettre_a_jour_interface = lambda: None
    fenetre._dessiner = lambda: None

    fenetre.basculer_lecture()
    assert fenetre.lecture
    assert fenetre.position == 0.0
    assert fenetre.animation_id == "animation"


def test_bouton_lecture_relance_aussi_pendant_la_lecture():
    class FausseRacine:
        def after(self, delai, fonction):
            self.programme = (delai, fonction)
            return "nouvelle-animation"

        def after_cancel(self, identifiant):
            self.annule = identifiant

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.racine = FausseRacine()
    fenetre.scene = {
        "vues": [{"nom": "Vue", "type": "attente", "cadres": [{}, {}]}]
    }
    fenetre.vue = 0
    fenetre.position = 0.65
    fenetre.lecture = True
    fenetre.animation_id = "ancienne-animation"
    fenetre.duree_cadre = 2.4
    fenetre._mettre_a_jour_interface = lambda: None
    fenetre._dessiner = lambda: None

    fenetre.basculer_lecture()
    assert fenetre.lecture
    assert fenetre.position == 0.0
    assert fenetre.racine.annule == "ancienne-animation"
    assert fenetre.animation_id == "nouvelle-animation"


def test_dimensions_limitees_a_cinq():
    assert construire_objet("(1, 2, 3, 4, 5)") == Vecteur((1, 2, 3, 4, 5))
    doit_lever(ValueError, construire_objet, "(1, 2, 3, 4, 5, 6)")
    assert construire_objet("[[1, 0, 0, 0, 0]]").taille == (1, 5)
    doit_lever(ValueError, construire_objet, "[[1, 0, 0, 0, 0, 0]]")


def test_animation_directement_pilotee_par_play():
    class FausseRacine:
        def after(self, delai, fonction):
            self.programme = (delai, fonction)
            return "image-suivante"

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.racine = FausseRacine()
    fenetre.scene = {
        "vues": [{"nom": "Vue", "type": "attente", "cadres": [{}]}]
    }
    fenetre.vue = 0
    fenetre.position = 0.0
    fenetre.lecture = True
    fenetre.animation_id = "animation"
    fenetre.duree_cadre = 2.4
    fenetre.debut_animation = time.monotonic() - 1.2
    fenetre._mettre_a_jour_interface = lambda: None
    fenetre._dessiner = lambda: None

    fenetre._animer()
    assert 0.45 < fenetre.position < 0.55
    assert fenetre.lecture
    assert fenetre.animation_id == "image-suivante"


def test_play_parcourt_toute_animation(monkeypatch):
    import visualisation.fenetre_observatoire as module_fenetre

    class Horloge:
        valeur = 0.0

        @classmethod
        def monotonic(cls):
            return cls.valeur

    class FausseRacine:
        def __init__(self):
            self.fonction = None
            self.compteur = 0

        def after(self, _, fonction):
            self.compteur += 1
            self.fonction = fonction
            return f"image-{self.compteur}"

        def after_cancel(self, _):
            self.fonction = None

    monkeypatch.setattr(module_fenetre.time, "monotonic", Horloge.monotonic)
    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.racine = FausseRacine()
    fenetre.scene = {
        "vues": [{"nom": "Vue", "type": "attente", "cadres": [{}]}]
    }
    fenetre.vue = 0
    fenetre.position = 1.0
    fenetre.lecture = False
    fenetre.animation_id = None
    fenetre.duree_cadre = 2.4
    fenetre._mettre_a_jour_interface = lambda: None
    fenetre._dessiner = lambda: None

    fenetre.basculer_lecture()
    assert fenetre.position == 0.0
    for instant, attendu in ((0.6, 0.25), (1.2, 0.5), (2.4, 1.0)):
        Horloge.valeur = instant
        fonction = fenetre.racine.fonction
        assert fonction is not None
        fonction()
        assert abs(fenetre.position - attendu) < 1e-9
    assert not fenetre.lecture
    assert fenetre.animation_id is None


def test_latex_reste_lisible_sans_matplotlib():
    formule = r"$E=F\oplus G\iff E=F+G\ \text{et}\ F\cap G=\{0\}$"
    texte = FenetreLinAlgebraX._latex_vers_unicode(formule)
    assert texte == "E = F ⊕ G ⇔ E = F + G et F ∩ G = {0}"
    assert "\\" not in texte

    base = r"$v=\sum_i x_i e_i\Longleftrightarrow[v]_{\mathcal B}=(x_1,\ldots,x_n)$"
    texte_base = FenetreLinAlgebraX._latex_vers_unicode(base)
    assert texte_base == "v = Σᵢ xᵢ eᵢ ⇔ [v]₍ℬ₎ = (x₁,…,xₙ)"
    assert not any(
        commande in texte_base
        for commande in ("Longleftrightarrow", "mathcal", "ldots")
    )


def test_latex_est_normalise_pour_matplotlib():
    formule = r"$[v]_{\mathcal B}\iff K^n\xrightarrow{\ A\ }K^m$"
    normalisee = FenetreLinAlgebraX._latex_pour_mathtext(formule)
    assert r"\mathcal{B}" in normalisee
    assert r"\Longleftrightarrow" in normalisee
    assert r"\overset{\ A\ }{\longrightarrow}" in normalisee


def test_navigation_de_la_camera():
    class FauxCanvas:
        @staticmethod
        def winfo_width():
            return 800

        @staticmethod
        def winfo_height():
            return 600

    class Evenement:
        def __init__(self, x, y, delta=0):
            self.x = x
            self.y = y
            self.delta = delta

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.canvas = FauxCanvas()
    fenetre.echelle_active = 20
    fenetre.zoom_vue = 1.0
    fenetre.decalage_vue = [0.0, 0.0]
    fenetre.pan_depart = None
    fenetre.orientation_3d = fenetre._orientation_initiale_3d()
    fenetre.orientation_plan = fenetre._quaternion_identite()
    fenetre.rotation_depart = None
    fenetre._dessiner = lambda: None

    assert fenetre._point2(1, 1) == (420.0, 280.0)

    fenetre._debut_pan(Evenement(100, 100))
    fenetre._pan(Evenement(160, 130))
    assert fenetre.decalage_vue == [60.0, 30.0]

    fenetre._zoom_molette(Evenement(400, 300, 120))
    assert 1.0 < fenetre.zoom_vue <= 2.5

    fenetre._debut_rotation(Evenement(200, 200))
    fenetre._rotation(Evenement(260, 240))
    assert fenetre.orientation_3d != fenetre._orientation_initiale_3d()
    assert fenetre.orientation_plan != fenetre._quaternion_identite()

    fenetre._reinitialiser_vue()
    assert fenetre.zoom_vue == 1.0
    assert fenetre.decalage_vue == [0.0, 0.0]
    assert fenetre.orientation_3d == fenetre._orientation_initiale_3d()
    assert fenetre.orientation_plan == fenetre._quaternion_identite()


def test_camera_orbitale_passe_derriere_le_plan():
    class FauxCanvas:
        @staticmethod
        def winfo_width():
            return 800

        @staticmethod
        def winfo_height():
            return 600

    class Evenement:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    fenetre = FenetreLinAlgebraX.__new__(FenetreLinAlgebraX)
    fenetre.canvas = FauxCanvas()
    fenetre.echelle_active = 20
    fenetre.zoom_vue = 1.0
    fenetre.decalage_vue = [0.0, 0.0]
    fenetre.orientation_3d = fenetre._orientation_initiale_3d()
    fenetre.orientation_plan = fenetre._quaternion_identite()
    fenetre.rotation_depart = None
    fenetre._dessiner = lambda: None

    devant = fenetre._tourner_point((0, 1, 0), fenetre.orientation_plan)
    fenetre._debut_rotation(Evenement(400, 80))
    fenetre._rotation(Evenement(400, 520))
    derriere = fenetre._tourner_point((0, 1, 0), fenetre.orientation_plan)

    assert devant[1] > 0
    assert derriere[1] < 0
    assert abs(sum(x * x for x in fenetre.orientation_plan) - 1) < 1e-9
