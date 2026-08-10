"""Lecture sûre des objets écrits dans le terminal."""


import ast
import re
from fractions import Fraction

from algebre import Matrice, Vecteur, fraction






DIMENSION_MAX = 5


def verifier_dimension_utilisateur(objet):
    if isinstance(objet, Vecteur) and len(objet) > DIMENSION_MAX:
        raise ValueError("LinAlgebraX accepte les dimensions 1 à 5.")
    if isinstance(objet, Matrice) and (
        objet.hauteur > DIMENSION_MAX or objet.largeur > DIMENSION_MAX
    ):
        raise ValueError("Une matrice saisie peut avoir au maximum 5 lignes et 5 colonnes.")
    if isinstance(objet, tuple) and objet and all(
        isinstance(vecteur, Vecteur) for vecteur in objet
    ):
        if any(len(vecteur) > DIMENSION_MAX for vecteur in objet):
            raise ValueError("Une famille doit appartenir à un espace de dimension 1 à 5.")
    return objet


def _normaliser(texte: str) -> str:
    texte = texte.strip().replace("^", "**").replace("−", "-")
    return texte


def evaluer_structure(texte: str):
    """Évalue nombres, fractions, listes et tuples sans appeler eval."""
    arbre = ast.parse(_normaliser(texte), mode="eval")

    # Seuls les nœuds nécessaires aux expressions mathématiques sont acceptés.
    def visiter(noeud):
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
            return fraction(noeud.value)
        if isinstance(noeud, ast.List):
            return [visiter(element) for element in noeud.elts]
        if isinstance(noeud, ast.Tuple):
            return tuple(visiter(element) for element in noeud.elts)
        if isinstance(noeud, ast.UnaryOp):
            valeur = visiter(noeud.operand)
            if not isinstance(valeur, Fraction):
                raise ValueError("Le signe ne peut porter que sur un nombre.")
            if isinstance(noeud.op, ast.USub):
                return -valeur
            if isinstance(noeud.op, ast.UAdd):
                return valeur
        if isinstance(noeud, ast.BinOp):
            gauche = visiter(noeud.left)
            droite = visiter(noeud.right)
            if not isinstance(gauche, Fraction) or not isinstance(droite, Fraction):
                raise ValueError("Opération invalide dans la structure.")
            if isinstance(noeud.op, ast.Add):
                return gauche + droite
            if isinstance(noeud.op, ast.Sub):
                return gauche - droite
            if isinstance(noeud.op, ast.Mult):
                return gauche * droite
            if isinstance(noeud.op, ast.Div):
                return gauche / droite
            if isinstance(noeud.op, ast.Pow):
                if droite.denominator != 1:
                    raise ValueError("L'exposant doit être entier.")
                return gauche ** int(droite)
        raise ValueError("Expression non reconnue.")

    return visiter(arbre.body)


class FormeAffine:
    def __init__(self, coefficients, constante=Fraction(0)):
        self.coefficients = coefficients
        self.constante = constante

    @classmethod
    def constante_seule(cls, valeur) -> "FormeAffine":
        return cls({}, fraction(valeur))

    @classmethod
    def variable(cls, nom: str) -> "FormeAffine":
        return cls({nom: Fraction(1)}, Fraction(0))

    def __add__(self, autre: "FormeAffine") -> "FormeAffine":
        coefficients = self.coefficients.copy()
        for nom, valeur in autre.coefficients.items():
            coefficients[nom] = coefficients.get(nom, Fraction(0)) + valeur
            if coefficients[nom] == 0:
                coefficients.pop(nom)
        return FormeAffine(coefficients, self.constante + autre.constante)

    def __neg__(self) -> "FormeAffine":
        return FormeAffine(
            {nom: -valeur for nom, valeur in self.coefficients.items()},
            -self.constante,
        )

    def __sub__(self, autre: "FormeAffine") -> "FormeAffine":
        return self + (-autre)

    def multiplier(self, scalaire) -> "FormeAffine":
        scalaire = fraction(scalaire)
        return FormeAffine(
            {nom: scalaire * valeur for nom, valeur in self.coefficients.items()},
            scalaire * self.constante,
        )


def _preparer_equation(texte: str) -> str:
    texte = _normaliser(texte)
    texte = re.sub(r"(?<=\d)(?=[A-Za-z])", "*", texte)
    texte = re.sub(r"(?<=[A-Za-z])(?=\()", "*", texte)
    return texte


def _forme_affine(texte: str) -> FormeAffine:
    arbre = ast.parse(_preparer_equation(texte), mode="eval")


   
    def visiter(noeud) -> FormeAffine:
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
            return FormeAffine.constante_seule(noeud.value)
        if isinstance(noeud, ast.Name):
            return FormeAffine.variable(noeud.id)
        if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, ast.USub):
            return -visiter(noeud.operand)
        if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, ast.UAdd):
            return visiter(noeud.operand)
        if isinstance(noeud, ast.BinOp):
            gauche = visiter(noeud.left)
            droite = visiter(noeud.right)
            if isinstance(noeud.op, ast.Add):
                return gauche + droite
            if isinstance(noeud.op, ast.Sub):
                return gauche - droite
            if isinstance(noeud.op, ast.Mult):
                if not gauche.coefficients:
                    return droite.multiplier(gauche.constante)
                if not droite.coefficients:
                    return gauche.multiplier(droite.constante)
                raise ValueError("Le produit de deux inconnues n'est pas linéaire.")
            if isinstance(noeud.op, ast.Div):
                if droite.coefficients or droite.constante == 0:
                    raise ValueError("Le dénominateur doit être une constante non nulle.")
                return gauche.multiplier(1 / droite.constante)
        raise ValueError("L'équation n'est pas linéaire.")

    return visiter(arbre.body)


def analyser_systeme(
    texte: str,
) -> tuple[Matrice, Vecteur, tuple[str, ...]]:
    """Transforme ``2x+y=3 ; x-y=0`` en A, b et liste d'inconnues."""
    texte = texte.strip()
    if texte.startswith("{") and texte.endswith("}"):
        texte = texte[1:-1]
    equations = [morceau.strip() for morceau in texte.split(";") if morceau.strip()]
    if not equations:
        raise ValueError("Le système est vide.")

    formes = []
    ordre_variables: list[str] = []
    for equation in equations:
        if equation.count("=") != 1:
            raise ValueError("Chaque équation doit contenir exactement un signe =.")
        gauche, droite = equation.split("=")
        forme = _forme_affine(gauche) - _forme_affine(droite)
        formes.append(forme)
        for nom in forme.coefficients:
            if nom not in ordre_variables:
                ordre_variables.append(nom)

    if not ordre_variables:
        raise ValueError("Le système ne contient aucune inconnue.")
    matrice = Matrice(
        [
            [forme.coefficients.get(nom, Fraction(0)) for nom in ordre_variables]
            for forme in formes
        ]
    )
    second_membre = Vecteur(-forme.constante for forme in formes)
    verifier_dimension_utilisateur(matrice)
    return matrice, second_membre, tuple(ordre_variables)


def construire_objet(texte: str):
    """Reconnaît une matrice, une famille, un vecteur ou un scalaire.

    Cette fonction est l'entrée générale utilisée par ``moteur.py`` lors d'une
    définition.  elle construit un objet fiable.
    """
    valeur = evaluer_structure(texte)
    if isinstance(valeur, Fraction):
        return valeur
    if isinstance(valeur, tuple):
        return verifier_dimension_utilisateur(Vecteur(valeur))
    if isinstance(valeur, list):
        if not valeur:
            raise ValueError("La liste est vide.")
        if all(isinstance(ligne, list) for ligne in valeur):
            return verifier_dimension_utilisateur(Matrice(valeur))
        if all(isinstance(element, tuple) for element in valeur):
            return verifier_dimension_utilisateur(
                tuple(Vecteur(element) for element in valeur)
            )
    raise ValueError("Utilisez [[...]] pour une matrice, (...) pour un vecteur.")
