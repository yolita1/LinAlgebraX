"""  Calcul exact sur les vecteurs, matrices et sous-espaces """


from fractions import Fraction
from math import isqrt, sqrt

from typing import Iterable, Sequence


def fraction(valeur) -> Fraction:
    if isinstance(valeur, Fraction):
        return valeur
    if isinstance(valeur, float):
        return Fraction(str(valeur))
    return Fraction(valeur)


def joli(nombre: Fraction | float | int) -> str:
    if isinstance(nombre, float):
        return f"{nombre:.6g}"
    
    nombre = fraction(nombre)
    if nombre.denominator == 1:
        return str(nombre.numerator)
    return f"{nombre.numerator}/{nombre.denominator}"


class Vecteur:
    """Vecteur de dimension finie à coordonnées rationnelles

    Les coordonnées sont regroupées dans un tuple afin qu'elles ne soient pas
    modifiées élément par élément pendant un calcul.
    """

    def __init__(self, composantes: Iterable):
        valeurs = []
        for composante in composantes:
            valeurs.append(fraction(composante))

        if not valeurs:
            raise ValueError("Un vecteur doit avoir au moins une composante.")
        self.composantes = tuple(valeurs)

    def __len__(self) -> int:
        return len(self.composantes)

    def __iter__(self):
        return iter(self.composantes)

    def __getitem__(self, indice: int) -> Fraction:
        return self.composantes[indice]

    def __eq__(self, autre) -> bool:
        return (
            isinstance(autre, Vecteur)
            and self.composantes == autre.composantes
        )

    def _verifier_dimension(self, autre: "Vecteur") -> None:
        if len(self) != len(autre):
            raise ValueError("Les vecteurs n'ont pas la même dimension.")

    def __add__(self, autre: "Vecteur") -> "Vecteur":
        self._verifier_dimension(autre)
        resultat = []
        for indice in range(len(self)):
            resultat.append(self[indice] + autre[indice])
        return Vecteur(resultat)

    def __sub__(self, autre: "Vecteur") -> "Vecteur":
        self._verifier_dimension(autre)
        resultat = []
        for indice in range(len(self)):
            resultat.append(self[indice] - autre[indice])
        return Vecteur(resultat)

    def __mul__(self, scalaire) -> "Vecteur":
        coefficient = fraction(scalaire)
        resultat = []
        for composante in self:
            resultat.append(coefficient * composante)
        return Vecteur(resultat)

    __rmul__ = __mul__

    def __neg__(self) -> "Vecteur":
        return -1 * self

    def produit_scalaire(self, autre: "Vecteur") -> Fraction:
        self._verifier_dimension(autre)
        resultat = Fraction(0)
        for indice in range(len(self)):
            resultat += self[indice] * autre[indice]
        return resultat

    def norme_carree(self) -> Fraction:
        return self.produit_scalaire(self)

    def est_nul(self) -> bool:
        for composante in self:
            if composante != 0:
                return False
        return True

    def __str__(self) -> str:
        composantes = []
        for composante in self:
            composantes.append(joli(composante))
        return "(" + ", ".join(composantes) + ")"


class EtapeGauss:
    def __init__(self, operation, matrice):
        self.operation = operation
        self.matrice = matrice


class Reduction:
    def __init__(self, matrice, pivots, etapes):
        self.matrice = matrice
        self.pivots = pivots
        self.etapes = etapes


class SolutionSysteme:
    def __init__(self, compatible, particuliere, directions, etapes):
        self.compatible = compatible
        self.particuliere = particuliere
        self.directions = directions
        self.etapes = etapes

    @property
    def unique(self) -> bool:
        return self.compatible and not self.directions


class Matrice:
    """Matrice rationnelle avec opérations du prog de sup 

    Les lignes sont stockées dans un tuple de tuples. Comme pour ``Vecteur``,
    cette immutabilité évite qu'une étape de Gauss ne modifie une ancienne
    matrice déjà conservée dans l'historique ou dans une animation
    """

    def __init__(self, lignes: Iterable[Iterable]):
        donnees = []
        for ligne in lignes:
            nouvelle_ligne = []
            for valeur in ligne:
                nouvelle_ligne.append(fraction(valeur))

            donnees.append(tuple(nouvelle_ligne))

        if not donnees or not donnees[0]:
            raise ValueError("Une matrice ne peut pas être vide.")

        largeur = len(donnees[0])
        for ligne in donnees:
            if len(ligne) != largeur:
                raise ValueError("Toutes les lignes doivent avoir la même longueur")

        self.lignes = tuple(donnees)

    @property
    def hauteur(self) -> int:
        return len(self.lignes)

    @property
    def largeur(self) -> int:
        return len(self.lignes[0])

    @property
    def taille(self) -> tuple[int, int]:
        return self.hauteur, self.largeur

    def __getitem__(self, indice: int) -> tuple[Fraction, ...]:
        return self.lignes[indice]

    def __eq__(self, autre) -> bool:
        return isinstance(autre, Matrice) and self.lignes == autre.lignes

    def __str__(self) -> str:
        largeurs = []
        for colonne in range(self.largeur):
            largeur_maximale = 0
            for ligne in range(self.hauteur):
                texte = joli(self.lignes[ligne][colonne])
                if len(texte) > largeur_maximale:
                    largeur_maximale = len(texte)
            largeurs.append(largeur_maximale)

        sorties = []
        for ligne in self.lignes:
            valeurs = []
            for colonne in range(self.largeur):
                texte = joli(ligne[colonne])
                valeurs.append(texte.rjust(largeurs[colonne]))
            contenu = "  ".join(valeurs)
            sorties.append(f"│ {contenu} │")
        return "\n".join(sorties)

    @classmethod
    def identite(cls, dimension: int) -> "Matrice":
        if dimension < 1:
            raise ValueError("La dimension doit être positive")

        lignes = []
        for i in range(dimension):
            ligne = []
            for j in range(dimension):
                if i == j:
                    ligne.append(1)
                else:
                    ligne.append(0)
            lignes.append(ligne)
        return cls(lignes)

    @classmethod
    def par_colonnes(cls, colonnes: Sequence[Vecteur]) -> "Matrice":
        if not colonnes:
            raise ValueError("Il faut au moins une colonne.")

        dimension = len(colonnes[0])
        for colonne in colonnes:
            if len(colonne) != dimension:
                raise ValueError("Les colonnes n'ont pas la même dimension.")

        lignes = []
        for i in range(dimension):
            ligne = []
            for colonne in colonnes:
                ligne.append(colonne[i])
            lignes.append(ligne)
        return cls(lignes)

    def colonne(self, indice: int) -> Vecteur:
        valeurs = []
        for ligne in self.lignes:
            valeurs.append(ligne[indice])
        return Vecteur(valeurs)

    def colonnes(self) -> tuple[Vecteur, ...]:
        resultat = []
        for indice in range(self.largeur):
            resultat.append(self.colonne(indice))
        return tuple(resultat)

    def transposee(self) -> "Matrice":
        lignes_transposees = []
        for colonne in range(self.largeur):
            nouvelle_ligne = []
            for ligne in range(self.hauteur):
                nouvelle_ligne.append(self.lignes[ligne][colonne])
            lignes_transposees.append(nouvelle_ligne)
        return Matrice(lignes_transposees)

    def augmenter(self, autre: "Matrice") -> "Matrice":
        if self.hauteur != autre.hauteur:
            raise ValueError("Les matrices n'ont pas le même nombre de lignes.")

        lignes = []
        for indice in range(self.hauteur):
            ligne = list(self.lignes[indice])
            ligne.extend(autre.lignes[indice])
            lignes.append(ligne)
        return Matrice(lignes)

    def appliquer(self, vecteur: Vecteur) -> Vecteur:
        if self.largeur != len(vecteur):
            raise ValueError("Dimensions incompatibles pour A·v.")

        resultat = []
        for ligne in self.lignes:
            somme = Fraction(0)
            for colonne in range(self.largeur):
                somme += ligne[colonne] * vecteur[colonne]
            resultat.append(somme)
        return Vecteur(resultat)

    def __matmul__(self, autre: "Matrice") -> "Matrice":
        """Compose deux applications linéaires par le produit matriciel """
        if self.largeur != autre.hauteur:
            raise ValueError("Dimensions incompatibles pour le produit matriciel.")
        resultat = []
        for i in range(self.hauteur):
            ligne_resultat = []
            for j in range(autre.largeur):
                somme = Fraction(0)
                for k in range(self.largeur):
                    somme += self.lignes[i][k] * autre.lignes[k][j]
                ligne_resultat.append(somme)
            resultat.append(ligne_resultat)
        return Matrice(resultat)

    def reduire(self) -> Reduction:
        """Calcule la forme échelonnée réduite et mémorise chaque opération

        Pour chaque colonne, on cherche un pivot sous la ligne courante. On le
        place, on le normalise à 1, puis on annule tous les autres coefficients
        de sa colonne. Les étapes servent à la fois aux explications du terminal
        et aux animations de l'observatoire
        """
        tableau = []
        for ligne in self.lignes:
            tableau.append(list(ligne))

        etapes: list[EtapeGauss] = []
        pivots: list[int] = []
        ligne_pivot = 0

        def memoriser(operation: str) -> None:
            copie = []
            for ligne in tableau:
                copie.append(tuple(ligne))
            etapes.append(EtapeGauss(operation, tuple(copie)))

        # Gauss-Jordan annule les coefficients au-dessus et au-dessous du pivot
        for colonne in range(self.largeur):

            candidate = None
            for i in range(ligne_pivot, self.hauteur):
                if tableau[i][colonne] != 0:
                    candidate = i
                    break

            if candidate is None:
                continue

            if candidate != ligne_pivot:
                tableau[ligne_pivot], tableau[candidate] = (
                    tableau[candidate],
                    tableau[ligne_pivot],
                )
                memoriser(f"L{ligne_pivot + 1} ↔ L{candidate + 1}")

            pivot = tableau[ligne_pivot][colonne]
            if pivot != 1:
                nouvelle_ligne = []
                for valeur in tableau[ligne_pivot]:
                    nouvelle_ligne.append(valeur / pivot)
                tableau[ligne_pivot] = nouvelle_ligne
                memoriser(f"L{ligne_pivot + 1} ← L{ligne_pivot + 1} / ({joli(pivot)})")

            for i in range(self.hauteur):
                if i == ligne_pivot:
                    continue
                coefficient = tableau[i][colonne]
                if coefficient:
                    nouvelle_ligne = []
                    for j in range(self.largeur):
                        valeur = tableau[i][j]
                        valeur_pivot = tableau[ligne_pivot][j]
                        nouvelle_ligne.append(valeur - coefficient * valeur_pivot)
                    tableau[i] = nouvelle_ligne
                    memoriser(
                        f"L{i + 1} ← L{i + 1} - ({joli(coefficient)})L{ligne_pivot + 1}"
                    )

            pivots.append(colonne)
            ligne_pivot += 1
            if ligne_pivot == self.hauteur:
                break

        return Reduction(Matrice(tableau), tuple(pivots), tuple(etapes))

    def rang(self) -> int:
        
        return len(self.reduire().pivots)

    def determinant_detaille(self) -> tuple[Fraction, tuple[EtapeGauss, ...]]:
        """Triangularise la matrice et suit l'effet des opérations sur det(A) """
        if self.hauteur != self.largeur:
            raise ValueError("Le déterminant exige une matrice carrée.")
        tableau = []
        for ligne in self.lignes:
            tableau.append(list(ligne))

        signe = Fraction(1)
        pivots: list[Fraction] = []
        etapes: list[EtapeGauss] = []

        def memoriser(operation: str) -> None:
            copie = []
            for ligne in tableau:
                copie.append(tuple(ligne))
            etapes.append(EtapeGauss(operation, tuple(copie)))

        # Ajouter un multiple d'une ligne ne change pas le déterminant ; un
        # échange de lignes change son signe.
        for colonne in range(self.largeur):
            candidate = None
            for i in range(colonne, self.hauteur):
                if tableau[i][colonne] != 0:
                    candidate = i
                    break

            if candidate is None:
                return Fraction(0), tuple(etapes)
            if candidate != colonne:
                tableau[colonne], tableau[candidate] = (
                    tableau[candidate],
                    tableau[colonne],
                )
                signe *= -1
                memoriser(f"L{colonne + 1} ↔ L{candidate + 1} : le signe change")
            pivot = tableau[colonne][colonne]
            pivots.append(pivot)
            for i in range(colonne + 1, self.hauteur):
                if tableau[i][colonne]:
                    coefficient = tableau[i][colonne] / pivot
                    nouvelle_ligne = []
                    for j in range(self.largeur):
                        valeur = tableau[i][j]
                        valeur_pivot = tableau[colonne][j]
                        nouvelle_ligne.append(valeur - coefficient * valeur_pivot)
                    tableau[i] = nouvelle_ligne
                    memoriser(
                        f"L{i + 1} ← L{i + 1} - ({joli(coefficient)})L{colonne + 1}"
                    )
        determinant = signe
        for pivot in pivots:
            determinant *= pivot
        return determinant, tuple(etapes)

    def determinant(self) -> Fraction:
        return self.determinant_detaille()[0]

    def inverse(self) -> tuple["Matrice", tuple[EtapeGauss, ...]]:
        """Applique Gauss-Jordan à [A | I] pour obtenir [I | A⁻¹]."""
        if self.hauteur != self.largeur:
            raise ValueError("L'inverse exige une matrice carrée.")
        reduction = self.augmenter(Matrice.identite(self.hauteur)).reduire()

        lignes_gauche = []
        lignes_droite = []
        for ligne in reduction.matrice.lignes:
            lignes_gauche.append(ligne[:self.largeur])
            lignes_droite.append(ligne[self.largeur:])

        gauche = Matrice(lignes_gauche)
        if gauche != Matrice.identite(self.hauteur):
            raise ValueError("La matrice n'est pas inversible.")
        droite = Matrice(lignes_droite)
        return droite, reduction.etapes

    def base_noyau(self) -> tuple[Vecteur, ...]:
        """Construit une base de Ker(A) à partir des variables libres."""
        reduction = self.reduire()
        libres = []
        for colonne in range(self.largeur):
            if colonne not in reduction.pivots:
                libres.append(colonne)

        base = []
        # Chaque variable libre vaut successivement 1, les autres 0.
        for libre in libres:
            composantes = []
            for _ in range(self.largeur):
                composantes.append(Fraction(0))
            composantes[libre] = 1
            for ligne in range(len(reduction.pivots)):
                pivot = reduction.pivots[ligne]
                composantes[pivot] = -reduction.matrice[ligne][libre]
            base.append(Vecteur(composantes))
        return tuple(base)

    def base_image(self) -> tuple[Vecteur, ...]:
        pivots = self.reduire().pivots
        # On conserve les colonnes pivots de la matrice originale.
        base = []
        for pivot in pivots:
            base.append(self.colonne(pivot))
        return tuple(base)

    def resoudre(self, second_membre: Vecteur) -> SolutionSysteme:
        """Résout Ax=b et décrit l'ensemble affine de toutes les solutions."""
        if len(second_membre) != self.hauteur:
            raise ValueError("Le second membre n'a pas la bonne dimension.")

        colonne_second_membre = []
        for valeur in second_membre:
            colonne_second_membre.append([valeur])

        augmentee = self.augmenter(Matrice(colonne_second_membre))
        reduction = augmentee.reduire()
        r = reduction.matrice

        for ligne in r.lignes:
            partie_gauche_nulle = True
            for colonne in range(self.largeur):
                if ligne[colonne] != 0:
                    partie_gauche_nulle = False
                    break
            if partie_gauche_nulle and ligne[-1] != 0:
                return SolutionSysteme(False, None, (), reduction.etapes)

        pivots = []
        for pivot in reduction.pivots:
            if pivot < self.largeur:
                pivots.append(pivot)

        solution = []
        for _ in range(self.largeur):
            solution.append(Fraction(0))

        for i in range(len(pivots)):
            pivot = pivots[i]
            solution[pivot] = r[i][-1]
        return SolutionSysteme(
            True,
            Vecteur(solution),
            self.base_noyau(),
            reduction.etapes,
        )


def relation_dependance(famille: Sequence[Vecteur]) -> tuple[Vecteur, ...]:
    """Retourne les relations Σ λᵢvᵢ=0."""
    if not famille:
        return ()
    return Matrice.par_colonnes(famille).base_noyau()


def base_extraite(famille: Sequence[Vecteur]) -> tuple[Vecteur, ...]:
    """Extrait une base du sous-espace engendré par la famille."""
    if not famille:
        return ()
    return Matrice.par_colonnes(famille).base_image()


def base_somme(
    premiere: Sequence[Vecteur], seconde: Sequence[Vecteur]
) -> tuple[Vecteur, ...]:
    """Base de Vect(première)+Vect(seconde)."""
    return base_extraite(tuple(premiere) + tuple(seconde))


def base_intersection(
    premiere: Sequence[Vecteur], seconde: Sequence[Vecteur]
) -> tuple[Vecteur, ...]:
    """Base de l'intersection de deux sous-espaces donnés par générateurs."""
    if not premiere or not seconde:
        return ()
    if len(premiere[0]) != len(seconde[0]):
        raise ValueError("Les sous-espaces ne vivent pas dans le même espace.")
    matrice_f = Matrice.par_colonnes(premiere)
    # Fa = Gb équivaut à chercher le noyau de la matrice [F | -G].
    colonnes = list(premiere)
    for vecteur in seconde:
        colonnes.append(-vecteur)

    relations = Matrice.par_colonnes(colonnes).base_noyau()
    candidats = []
    for relation in relations:
        coefficients_f = Vecteur(relation.composantes[: len(premiere)])
        candidat = matrice_f.appliquer(coefficients_f)
        if not candidat.est_nul():
            candidats.append(candidat)
    return base_extraite(candidats)


def complement_de_base(famille: Sequence[Vecteur]) -> tuple[Vecteur, ...]:
    """Directions canoniques ajoutées pour compléter une famille libre en base."""
    if not famille:
        raise ValueError("Indiquez au moins un vecteur pour connaître la dimension.")
    dimension = len(famille[0])
    base = list(base_extraite(famille))
    ajoutes = []
    rang = len(base)
    for j in range(dimension):
        composantes = []
        for i in range(dimension):
            if i == j:
                composantes.append(1)
            else:
                composantes.append(0)
        canonique = Vecteur(composantes)

        nouveau_rang = Matrice.par_colonnes(base + [canonique]).rang()
        if nouveau_rang > rang:
            base.append(canonique)
            ajoutes.append(canonique)
            rang = nouveau_rang
        if rang == dimension:
            break
    return tuple(ajoutes)


def est_orthogonale(famille: Sequence[Vecteur]) -> bool:
    """Vrai si les vecteurs non nuls sont deux à deux orthogonaux."""
    for i in range(len(famille)):
        for j in range(i + 1, len(famille)):
            if famille[i].produit_scalaire(famille[j]) != 0:
                return False
    return True


def est_orthonormale(famille: Sequence[Vecteur]) -> bool:
    """Vrai si la famille est orthogonale et tous ses vecteurs sont unitaires."""
    if not est_orthogonale(famille):
        return False
    for vecteur in famille:
        if vecteur.norme_carree() != 1:
            return False
    return True


def orthogonaliser(famille: Sequence[Vecteur]) -> tuple[Vecteur, ...]:
    """Procédé exact de Gram-Schmidt, sans normalisation irrationnelle."""
    # La normalisation est évitée pour garder des coefficients rationnels.
    resultat: list[Vecteur] = []
    for vecteur in famille:
        courant = vecteur
        for direction in resultat:
            courant = courant - (
                courant.produit_scalaire(direction) / direction.norme_carree()
            ) * direction
        if not courant.est_nul():
            resultat.append(courant)
    return tuple(resultat)


def projection_orthogonale(
    vecteur: Vecteur, famille: Sequence[Vecteur]
) -> Vecteur:
    """Projette sur le sous-espace engendré par une famille libre."""
    orthogonale = orthogonaliser(famille)
    if not orthogonale:
        return Vecteur([0] * len(vecteur))
    projection = Vecteur([0] * len(vecteur))
    for direction in orthogonale:
        coefficient = (
            vecteur.produit_scalaire(direction) / direction.norme_carree()

        )
        projection = projection + coefficient * direction
    return projection


def symetrie_orthogonale(vecteur: Vecteur, famille: Sequence[Vecteur]) -> Vecteur:
    """Symétrie par rapport au sous-espace engendré par la famille."""
    return 2 * projection_orthogonale(vecteur, famille) - vecteur


def coordonnees_dans_base(vecteur: Vecteur, base: Sequence[Vecteur]) -> Vecteur:
    """Coordonnées d'un vecteur dans une base donnée."""
    solution = Matrice.par_colonnes(base).resoudre(vecteur)
    if not solution.compatible or not solution.unique:
        raise ValueError("La famille donnée n'est pas une base adaptée au vecteur.")
    return solution.particuliere


def changement_de_base(
    ancienne_base: Sequence[Vecteur], nouvelle_base: Sequence[Vecteur]
) -> Matrice:
    """Matrice qui transforme [x]_ancienne en [x]_nouvelle."""
    # La colonne j contient les coordonnées du j-ième ancien vecteur.
    colonnes = []
    for vecteur in ancienne_base:
        coordonnees = coordonnees_dans_base(vecteur, nouvelle_base)
        colonnes.append(coordonnees)
    return Matrice.par_colonnes(colonnes)


def produit_vectoriel(u: Vecteur, v: Vecteur) -> Vecteur:
    """Produit vectoriel dans R³."""
    if len(u) != 3 or len(v) != 3:
        raise ValueError("Le produit vectoriel est défini ici dans R³.")
    return Vecteur(
        (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
    )


def _racine_fraction_exacte(nombre: Fraction) -> Fraction | None:
    if nombre < 0:
        return None
    racine_num = isqrt(nombre.numerator)
    racine_den = isqrt(nombre.denominator)
    if racine_num**2 == nombre.numerator and racine_den**2 == nombre.denominator:
        return Fraction(racine_num, racine_den)
    return None


def spectre_2d(matrice: Matrice) -> tuple[tuple[Fraction | float, Vecteur], ...]:
    """Valeurs/vecteurs propres d'une matrice réelle 2×2."""
    if matrice.taille != (2, 2):
        raise ValueError("Le calcul du spectre est limité aux matrices 2×2.")
    a, b = matrice[0]
    c, d = matrice[1]
    trace = a + d
    discriminant = trace * trace - 4 * matrice.determinant()
    if discriminant < 0:
        raise ValueError("Cette matrice n'a pas de valeurs propres réelles.")
    # Une racine rationnelle reste exacte ; sinon on passe localement en float.
    racine = _racine_fraction_exacte(discriminant)
    if racine is None:
        racine_flottante = sqrt(float(discriminant))
        valeurs: tuple[Fraction | float, ...] = (
            (float(trace) + racine_flottante) / 2,
            (float(trace) - racine_flottante) / 2,
        )
    else:
        valeurs = ((trace + racine) / 2, (trace - racine) / 2)

    resultat = []
    for valeur in valeurs:
        vf = float(valeur)
        af = float(a)
        bf = float(b)
        cf = float(c)
        df = float(d)
        if abs(bf) + abs(vf - af) > abs(vf - df) + abs(cf):
            vecteur = Vecteur((Fraction(str(bf)), Fraction(str(vf - af))))
        else:
            vecteur = Vecteur((Fraction(str(vf - df)), Fraction(str(cf))))
        if vecteur.est_nul():
            vecteur = Vecteur((1, 0))
        resultat.append((valeur, vecteur))
    if valeurs[0] == valeurs[1]:
        resultat = resultat[:1]
    return tuple(resultat)


def cramer(matrice: Matrice, second_membre: Vecteur) -> Vecteur:
    """Résout un système carré inversible par la règle de Cramer"""
    if matrice.hauteur != matrice.largeur:
        raise ValueError("La règle de Cramer exige un système carré.")
    determinant = matrice.determinant()
    if determinant == 0:
        raise ValueError("Cramer exige un déterminant non nul.")
    colonnes = list(matrice.colonnes())
    solutions = []
    for j in range(matrice.largeur):
        remplacees = colonnes.copy()
        remplacees[j] = second_membre
        solutions.append(Matrice.par_colonnes(remplacees).determinant() / determinant)

    return Vecteur(solutions)