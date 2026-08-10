"""Mise en forme du texte et du LaTeX."""


from fractions import Fraction
import re

from algebre import EtapeGauss, Matrice, Vecteur, joli
from polynomes import Polynome


def latex_nombre(nombre: Fraction | float | int) -> str:
    if isinstance(nombre, float):
        return f"{nombre:.6g}"
    nombre = Fraction(nombre)
    if nombre.denominator == 1:
        return str(nombre.numerator)
    return rf"\frac{{{nombre.numerator}}}{{{nombre.denominator}}}"


def latex_vecteur(vecteur: Vecteur) -> str:
    contenu = r" \\ ".join(latex_nombre(x) for x in vecteur)
    return rf"\begin{{pmatrix}}{contenu}\end{{pmatrix}}"


def latex_matrice(matrice: Matrice) -> str:
    lignes = [
        " & ".join(latex_nombre(x) for x in ligne) for ligne in matrice.lignes
    ]
    return rf"\begin{{pmatrix}}{' \\\\ '.join(lignes)}\end{{pmatrix}}"


def latex_polynome(polynome: Polynome) -> str:
    return re.sub(r"X\^(\d+)", r"X^{\1}", str(polynome))


def texte_famille(famille: tuple[Vecteur, ...] | list[Vecteur]) -> str:
    return "(" + ", ".join(str(vecteur) for vecteur in famille) + ")"

def latex_famille(famille: tuple[Vecteur, ...] | list[Vecteur]) -> str:
    return r"\left(" + ", ".join(latex_vecteur(v) for v in famille) + r"\right)"


def afficher_etapes(etapes: tuple[EtapeGauss, ...]) -> str:
    if not etapes:
        return "La matrice est déjà sous la forme voulue."
    blocs = []
    for numero, etape in enumerate(etapes, 1):
        blocs.append(f"{numero:>2}. {etape.operation}\n{Matrice(etape.matrice)}")
    return "\n".join(blocs)


def latex_etapes(etapes: tuple[EtapeGauss, ...]) -> str:
    if not etapes:
        return r"\text{Aucune opération élémentaire nécessaire.}"
    morceaux = []
    for etape in etapes:
        operation = (
            etape.operation.replace("←", r"\leftarrow")
            .replace("↔", r"\leftrightarrow")
            .replace("·", r"\cdot ")
        )
        morceaux.append(
            rf"\xrightarrow{{\ {operation}\ }}{latex_matrice(Matrice(etape.matrice))}"
        )
    return "\n".join(morceaux)


def decomposition_affine(
    particuliere: Vecteur, directions: tuple[Vecteur, ...], variables: tuple[str, ...]) -> str:
    if not directions:

        return ", ".join(
            f"{nom} = {joli(valeur)}"
            for nom, valeur in zip(variables, particuliere)
        )
    
    parametres = [chr(ord("s") + i) for i in range(len(directions))]
    morceaux = [str(particuliere)]
    morceaux.extend(
        f"{parametre}{direction}"
        for parametre, direction in zip(parametres, directions)
    )
    return "x = " + " + ".join(morceaux)
