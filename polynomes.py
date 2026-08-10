"""Polynômes à coefficients rationnels """


import ast
import re
from fractions import Fraction
from typing import Iterable

from algebre import fraction, joli


class Polynome:
    """Polynôme rationnel stocké par coefficients croissants."""

    def __init__(self, coefficients: Iterable):
        valeurs = [fraction(x) for x in coefficients]
        while len(valeurs) > 1 and valeurs[-1] == 0:
            valeurs.pop()
        self.coefficients = tuple(valeurs or [Fraction(0)])

    def est_nul(self) -> bool:
        return all(coefficient == 0 for coefficient in self.coefficients)

    @property
    def degre(self) -> int:
        return -1 if self.est_nul() else len(self.coefficients) - 1

    def __eq__(self, autre) -> bool:
        if not isinstance(autre, Polynome):
            autre = Polynome([autre])
        return self.coefficients == autre.coefficients

    def __add__(self, autre) -> "Polynome":
        if not isinstance(autre, Polynome):
            autre = Polynome([autre])
        taille = max(len(self.coefficients), len(autre.coefficients))
        return Polynome(
            [
                (self.coefficients[i] if i < len(self.coefficients) else 0)
                + (autre.coefficients[i] if i < len(autre.coefficients) else 0)
                for i in range(taille)
            ]
        )

    __radd__ = __add__

    def __neg__(self) -> "Polynome":
        return Polynome(-x for x in self.coefficients)

    def __sub__(self, autre) -> "Polynome":
        return self + (-autre)

    def __rsub__(self, autre) -> "Polynome":
        return Polynome([autre]) - self

    def __mul__(self, autre) -> "Polynome":
        if not isinstance(autre, Polynome):
            autre = Polynome([autre])
        resultat = [Fraction(0)] * (
            len(self.coefficients) + len(autre.coefficients) - 1
        )
        for i, a in enumerate(self.coefficients):
            for j, b in enumerate(autre.coefficients):
                resultat[i + j] += a * b
        return Polynome(resultat)

    __rmul__ = __mul__

    def __truediv__(self, scalaire) -> "Polynome":
        scalaire = fraction(scalaire)
        if scalaire == 0:
            raise ZeroDivisionError("Division par zéro.")
        return Polynome(x / scalaire for x in self.coefficients)

    def __pow__(self, puissance: int) -> "Polynome":
        if not isinstance(puissance, int) or puissance < 0:
            raise ValueError("La puissance doit être un entier positif ou nul.")
        resultat = Polynome([1])
        base = self
        n = puissance
        while n:
            if n % 2:
                resultat *= base
            base *= base
            n //= 2
        return resultat

    def derivee(self) -> "Polynome":
        if len(self.coefficients) == 1:
            return Polynome([0])
        return Polynome(
            i * self.coefficients[i] for i in range(1, len(self.coefficients))
        )

    def primitive(self, constante=0) -> "Polynome":
        return Polynome(
            [fraction(constante)]
            + [
                coefficient / (i + 1)
                for i, coefficient in enumerate(self.coefficients)
            ]
        )

    def evaluer(self, x) -> Fraction:
        x = fraction(x)
        resultat = Fraction(0)
        # Schéma de Horner.
        for coefficient in reversed(self.coefficients):
            resultat = resultat * x + coefficient
        return resultat

    def __str__(self) -> str:
        
        if self.est_nul():
            return "0"
        morceaux = []
        for degre in range(len(self.coefficients) - 1, -1, -1):
            coefficient = self.coefficients[degre]
            if coefficient == 0:
                continue
            signe = "-" if coefficient < 0 else "+"
            valeur = abs(coefficient)
            if degre == 0:
                terme = joli(valeur)
            else:
                facteur = "" if valeur == 1 else joli(valeur)
                puissance = "X" if degre == 1 else f"X^{degre}"
                terme = facteur + puissance
            if not morceaux:
                morceaux.append(("-" if signe == "-" else "") + terme)
            else:
                morceaux.append(f" {signe} {terme}")
        return "".join(morceaux)


def _normaliser(texte: str) -> str:
    texte = texte.replace("^", "**").replace("−", "-")
    texte = re.sub(r"(?<=\d)(?=[Xx])", "*", texte)
    texte = re.sub(r"(?<=[Xx])(?=\d)", "*", texte)
    return texte


def analyser_polynome(texte: str) -> Polynome:
    """Analyse une expression comme X^3 - 2X + 1 sans utiliser ``eval``.

    Comme dans ``analyseur.py``, seuls les nœuds AST utiles sont acceptés. La
    variable ``X`` est la seule variable autorisée.
    """
    arbre = ast.parse(_normaliser(texte), mode="eval")
    x = Polynome([0, 1])

    def visiter(noeud):
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
            return Polynome([fraction(noeud.value)])
        if isinstance(noeud, ast.Name) and noeud.id.lower() == "x":
            return x
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
                return gauche * droite
            if isinstance(noeud.op, ast.Div):
                if droite.degre > 0:
                    raise ValueError("La division par un polynôme n'est pas permise.")
                return gauche / droite.coefficients[0]
            if isinstance(noeud.op, ast.Pow):
                if droite.degre != 0 or droite.coefficients[0].denominator != 1:
                    raise ValueError("La puissance doit être entière.")
                return gauche ** int(droite.coefficients[0])
        raise ValueError("Expression polynomiale non reconnue.")

    return visiter(arbre.body)
