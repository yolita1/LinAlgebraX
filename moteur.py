"""Commandes et mémoire de la session LinAlgebraX."""


import re

import unicodedata

from algebre import (

    Matrice,
    Vecteur,
    base_intersection,
    base_somme,
    changement_de_base,
    complement_de_base,
    coordonnees_dans_base,
    cramer,
    est_orthogonale,
    est_orthonormale,
    joli,
    orthogonaliser,
    produit_vectoriel,
    projection_orthogonale,
    relation_dependance,
    spectre_2d,
    symetrie_orthogonale,
)
from analyseur import analyser_systeme, construire_objet
from polynomes import Polynome, analyser_polynome
from presentation import (
    afficher_etapes,
    decomposition_affine,

    latex_etapes,
    latex_famille,
    latex_matrice,
    latex_nombre,
    latex_polynome,
    latex_vecteur,
    texte_famille,
)


class Systeme:
    def __init__(self, matrice, second_membre, variables):

        self.matrice = matrice
        self.second_membre = second_membre
        self.variables = variables


class Reponse:
    def __init__(self, texte, latex="", quitter=False, scene=None):
        self.texte = texte
        self.latex = latex
        self.quitter = quitter
        self.scene = scene

class EntreeHistorique:
    def __init__(self, commande, objets_avant, scene_avant):
        self.commande = commande
        self.objets_avant = objets_avant
        self.scene_avant = scene_avant

AIDE = """Commandes principales

Dimensions disponibles : 1 à 5

Définir
  A = [[1, 2], [3, 4]]          matrice
  v = (2, -1)                   vecteur
  F = [(1, 0), (1, 1)]         famille
  S = {2x + y = 3 ; x - y = 0} système
  P = X^3 - 2X + 1             polynôme

Calculer
  etudier A          reduire A       det A          inverse A
  rang A             noyau A         image A         resoudre S
  famille F          coordonnees v ; F
  somme F ; G        intersection F ; G                supplement F
  orthogonaliser F   projection v ; F                symetrie v ; F
  estorthogonale F   orthonormale F                   hyperplan H
  scalaire u ; v     vectoriel u ; v                 projecteur F
  produit A ; B      changement B ; C                cramer A ; b
  application A      isomorphisme A  automorphisme A
  spectre A          diagonaliser A  orthogonale A
  derivee P          primitive P

La fenêtre noire est automatique : « etudier A », « inverse A », « det A »,
« resoudre S », etc. lancent directement leur animation.

Session
  memoire            retour             supprimer A     supprimer tout
  commandes          aide               quitter
"""


def _commande_sans_accents(mot: str) -> str:
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", mot.lower())
        if unicodedata.category(caractere) != "Mn"
    )


def _separer(texte: str, nombre: int = 2) -> list[str]:
    morceaux = [morceau.strip() for morceau in texte.split(";")]
    if len(morceaux) != nombre or any(not morceau for morceau in morceaux):
        raise ValueError(f"Cette commande attend {nombre} arguments séparés par « ; ».")
    return morceaux


class Laboratoire:
    """État et commandes d'une session interactive."""

    def __init__(self):
        self.objets: dict[str, object] = {}
        self.historique: list[EntreeHistorique] = []
        self.journal: list[str] = []
        self.scene_courante: dict | None = None

    def _objet(self, nom: str, type_attendu=None):
        nom = nom.strip()
        if nom not in self.objets:
            raise ValueError(f"Objet inconnu : {nom}.")
        objet = self.objets[nom]
        if type_attendu is not None and not isinstance(objet, type_attendu):
            raise ValueError(f"{nom} n'est pas du type attendu.")
        return objet
    def _vecteur_ou_litteral(self, texte: str) -> Vecteur:
        texte = texte.strip()
        if texte in self.objets:
            return self._objet(texte, Vecteur)
        objet = construire_objet(texte)
        if not isinstance(objet, Vecteur):
            raise ValueError("Un vecteur est attendu.")
        return objet

    def _famille_ou_litteral(self, texte: str) -> tuple[Vecteur, ...]:
        texte = texte.strip()
        if texte in self.objets:
            objet = self.objets[texte]
        else:
            objet = construire_objet(texte)
        if not (
            isinstance(objet, tuple)
            and objet
            and all(isinstance(v, Vecteur) for v in objet)
        ):
            raise ValueError("Une famille non vide de vecteurs est attendue.")
        return objet

    @staticmethod
    def _format_objet(objet) -> str:
        if isinstance(objet, Matrice):
            return "\n" + str(objet)
        if isinstance(objet, tuple) and all(isinstance(v, Vecteur) for v in objet):
            return texte_famille(objet)
        return str(objet)

    def definir(self, ligne: str) -> Reponse:
        """Crée un objet nommé en choisissant l'analyseur adapté à sa syntaxe."""
        nom, expression = (morceau.strip() for morceau in ligne.split("=", 1))
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", nom):
            raise ValueError("Le nom doit commencer par une lettre.")
        if expression.startswith("{") and expression.endswith("}"):
            matrice, second_membre, variables = analyser_systeme(expression)
            objet = Systeme(matrice, second_membre, variables)
            texte = (
                f"{nom} : système de {matrice.hauteur} équation(s) "
                f"à {matrice.largeur} inconnue(s) {variables}."
            )
        elif re.search(r"\bX\b", expression, re.IGNORECASE):
            objet = analyser_polynome(expression)
            texte = f"{nom} = {objet}"
        else:
            objet = construire_objet(expression)
            texte = f"{nom} = {self._format_objet(objet)}"
        self.objets[nom] = objet
        return Reponse(texte)

    def executer(self, ligne: str) -> Reponse:
        """Exécute le calcul puis prépare automatiquement sa scène."""
        ligne = ligne.strip()
        commande_brute = ligne.partition(" ")[0] if ligne else ""
        commande = _commande_sans_accents(commande_brute)

        if commande in {"retour", "revenir", "annuler", "undo"}:
            return self._revenir_en_arriere()

        objets_avant = dict(self.objets)
        scene_avant = self.scene_courante
        reponse = self._calculer_commande(ligne)
        if reponse.scene is None:
            # Import local pour éviter la dépendance circulaire avec les scènes.
            from visualisation.creation_scenes import creer_scene

            reponse.scene = creer_scene(self, ligne, reponse)

        if reponse.scene is not None:
            self.scene_courante = reponse.scene

        commandes_de_consultation = {
            "",
            "aide",
            "commandes",
            "help",
            "?",
            "objets",
            "historique",
            "journal",
            "memoire",
            "etat",
            "quitter",
            "quit",
            "exit",
        }
        # Lire l'aide ou la mémoire ne consomme pas une étape de retour.
        if commande not in commandes_de_consultation and not reponse.quitter:
            self.historique.append(
                EntreeHistorique(
                    ligne,
                    objets_avant,
                    scene_avant,
                )
            )
        if commande not in commandes_de_consultation and not reponse.quitter:
            self.journal.append(ligne)
        return reponse

    def _revenir_en_arriere(self) -> Reponse:
        """Annule la dernière action et restaure aussi la scène précédente."""
        if not self.historique:
            raise ValueError("Aucune action à annuler.")
        entree = self.historique.pop()
        self.objets = dict(entree.objets_avant)
        self.scene_courante = entree.scene_avant
        if self.scene_courante is None:
            from visualisation.creation_scenes import scene_attente

            self.scene_courante = scene_attente()
        self.journal.append(f"retour → annulation de « {entree.commande} »")
        return Reponse(
            f"Retour effectué : « {entree.commande} » a été annulée.",
            scene=self.scene_courante,
        )

    def _afficher_objets(self) -> str:
        if not self.objets:
            return "Aucun objet défini."
        lignes = []
        for nom, objet in self.objets.items():
            valeur = self._format_objet(objet).replace("\n", " ")
            if len(valeur) > 72:
                valeur = valeur[:69] + "..."
            lignes.append(f"{nom:<10} {type(objet).__name__:<10} {valeur}")
        return "\n".join(lignes)

    def _afficher_historique(self) -> str:
        if not self.journal:
            return "Aucune action enregistrée."
        return "\n".join(
            f"{indice + 1:>3}. {commande}"
            for indice, commande in enumerate(self.journal)
        )

    def _calculer_commande(self, ligne: str) -> Reponse:
        """Traite la commande mathématique sans s'occuper du dessin.

        Cette longue fonction joue le rôle d'un aiguilleur. Chaque branche
        valide ses arguments, appelle le cœur mathématique, puis produit une
        ``Reponse``. La création automatique de la scène se fait ensuite dans
        ``executer``.
        """
        ligne = ligne.strip()
        if not ligne:
            return Reponse("")

        if "=" in ligne and re.match(r"^[A-Za-z][A-Za-z0-9_]*\s*=", ligne):
            return self.definir(ligne)

        commande_brute, _, arguments = ligne.partition(" ")
        commande = _commande_sans_accents(commande_brute)
        arguments = arguments.strip()

        if commande in {"quitter", "quit", "exit"}:
            return Reponse("À bientôt.", quitter=True)
        if commande in {"aide", "commandes", "help", "?"}:
            return Reponse(AIDE)
        if commande == "objets":
            return Reponse(self._afficher_objets())
        if commande in {"historique", "journal"}:
            return Reponse(self._afficher_historique())
        if commande in {"memoire", "etat"}:
            return Reponse(
                "OBJETS ACTUELS\n"
                + self._afficher_objets()
                + "\n\nACTIONS RÉCENTES\n"
                + self._afficher_historique()
            )
        if commande in {"supprimer", "effacer"}:
            if not arguments:
                raise ValueError("Indiquez un nom, par exemple « supprimer A ».")
            if _commande_sans_accents(arguments) in {"tout", "tous"}:
                if not self.objets:
                    raise ValueError("Aucun objet à supprimer.")
                noms = ", ".join(self.objets)
                self.objets.clear()
                texte = f"Objets supprimés : {noms}."
            else:
                noms = [
                    nom
                    for nom in re.split(r"[\s,]+", arguments)
                    if nom
                ]
                inconnus = [nom for nom in noms if nom not in self.objets]
                if inconnus:
                    raise ValueError("Objet(s) inconnu(s) : " + ", ".join(inconnus) + ".")
                for nom in noms:
                    del self.objets[nom]
                texte = "Objet(s) supprimé(s) : " + ", ".join(noms) + "."
            from visualisation.creation_scenes import scene_attente

            return Reponse(
                texte + "\nLa commande « retour » peut annuler cette suppression.",
                scene=scene_attente("État modifié dans le terminal"),
            )
        if commande in {"etudier", "etude"}:
            objet = self._objet(arguments)
            if isinstance(objet, Matrice):
                return self._etudier(objet)
            if isinstance(objet, tuple):
                return self._etudier_famille(self._famille_ou_litteral(arguments))
            if isinstance(objet, Systeme):
                return self._hyperplan_ou_systeme(objet)
            raise ValueError("Cet objet ne peut pas être étudié.")
        if commande in {"application", "applicationlineaire"}:
            return self._etudier(self._objet(arguments, Matrice))
        if commande == "isomorphisme":
            matrice = self._objet(arguments, Matrice)
            oui = matrice.hauteur == matrice.largeur == matrice.rang()
            return Reponse(
                f"Isomorphisme : {'oui' if oui else 'non'}.\n"
                "Il faut une application à la fois injective et surjective.",
                rf"{arguments}\text{{ est un isomorphisme}}\iff "
                rf"\operatorname{{rg}}({arguments})=\dim E=\dim F",
            )
        if commande == "automorphisme":
            matrice = self._objet(arguments, Matrice)
            oui = matrice.hauteur == matrice.largeur and matrice.determinant() != 0
            return Reponse(
                f"Automorphisme : {'oui' if oui else 'non'}.\n"
                "Un automorphisme est un isomorphisme d'un espace sur lui-même.",
                rf"{arguments}\in GL_{matrice.largeur}\iff "
                rf"\det({arguments})\ne 0",
            )
        if commande in {"reduire", "rref", "gauss"}:
            matrice = self._objet(arguments, Matrice)
            reduction = matrice.reduire()
            return Reponse(
                f"Forme échelonnée réduite :\n{reduction.matrice}\n\n"
                f"Étapes :\n{afficher_etapes(reduction.etapes)}",
                latex_matrice(matrice) + latex_etapes(reduction.etapes),
            )
        if commande in {"det", "determinant"}:
            return self._determinant(self._objet(arguments, Matrice))
        if commande == "rang":
            matrice = self._objet(arguments, Matrice)
            rang = matrice.rang()

            return Reponse(
                f"rang({arguments}) = {rang}\n"
                f"dim Ker = {matrice.largeur - rang} et dim Im = {rang}.",
                rf"\operatorname{{rg}}({arguments})={rang}",
            )
        if commande == "inverse":
            matrice = self._objet(arguments, Matrice)
            inverse, etapes = matrice.inverse()
            return Reponse(
                f"{arguments}⁻¹ =\n{inverse}\n\nÉtapes sur [A|I] :\n"
                f"{afficher_etapes(etapes)}",
                rf"{arguments}^{{-1}}={latex_matrice(inverse)}",
            )
        if commande in {"noyau", "ker"}:
            matrice = self._objet(arguments, Matrice)
            base = matrice.base_noyau()
            return Reponse(
                f"Base de Ker({arguments}) : {texte_famille(base) if base else '()'}\n"
                f"Dimension : {len(base)}.",
                rf"\ker({arguments})=\operatorname{{Vect}}{latex_famille(base)}",
            )
        if commande in {"image", "im"}:
            matrice = self._objet(arguments, Matrice)
            base = matrice.base_image()
            return Reponse(
                f"Base de Im({arguments}) : {texte_famille(base)}\nDimension : {len(base)}.",
                rf"\operatorname{{Im}}({arguments})=\operatorname{{Vect}}{latex_famille(base)}",
            )
        if commande in {"resoudre", "solve"}:
            return self._resoudre(arguments)
        if commande in {"famille", "base"}:
            return self._etudier_famille(self._famille_ou_litteral(arguments))
        if commande == "somme":
            gauche, droite = _separer(arguments)
            premiere = self._famille_ou_litteral(gauche)
            seconde = self._famille_ou_litteral(droite)
            base = base_somme(premiere, seconde)
            return Reponse(
                f"Base de Vect({gauche}) + Vect({droite}) : {texte_famille(base)}\n"
                f"Dimension : {len(base)}.",
                rf"\dim(F+G)={len(base)}",
            )
        if commande == "intersection":
            gauche, droite = _separer(arguments)
            premiere = self._famille_ou_litteral(gauche)
            seconde = self._famille_ou_litteral(droite)
            base = base_intersection(premiere, seconde)
            return Reponse(
                f"Base de Vect({gauche}) ∩ Vect({droite}) : "
                f"{texte_famille(base) if base else '()'}\nDimension : {len(base)}.",
                rf"\dim(F\cap G)={len(base)}",
            )
        if commande in {"supplement", "supplementaire"}:
            famille = self._famille_ou_litteral(arguments)
            complement = complement_de_base(famille)
            return Reponse(
                f"Directions à ajouter : {texte_famille(complement) if complement else '()'}.\n"
                "Leur espace engendré est un supplémentaire du sous-espace initial.",
                rf"E=F\oplus\operatorname{{Vect}}{latex_famille(complement)}",
            )
        if commande == "hyperplan":
            return self._hyperplan_ou_systeme(self._objet(arguments, Systeme))
        if commande in {"scalaire", "dot"}:
            gauche, droite = _separer(arguments)
            u, v = self._vecteur_ou_litteral(gauche), self._vecteur_ou_litteral(droite)
            valeur = u.produit_scalaire(v)
            return Reponse(
                f"⟨u,v⟩ = {joli(valeur)}.\n"
                "Interprétation : norme de u × projection signée de v sur la direction de u.",
                rf"\langle u,v\rangle={latex_nombre(valeur)}",
            )
        if commande in {"vectoriel", "cross"}:
            gauche, droite = _separer(arguments)
            u, v = self._vecteur_ou_litteral(gauche), self._vecteur_ou_litteral(droite)
            resultat = produit_vectoriel(u, v)
            return Reponse(
                f"u × v = {resultat}\n"
                f"Il est orthogonal à u et v ; sa norme est l'aire du parallélogramme.",
                rf"u\times v={latex_vecteur(resultat)}",
            )
        if commande in {"orthogonaliser", "gram-schmidt", "gramschmidt"}:
            famille = self._famille_ou_litteral(arguments)
            orthogonale = orthogonaliser(famille)

            details = self._etapes_gram_schmidt(famille, orthogonale)
            return Reponse(
                f"Famille orthogonale : {texte_famille(orthogonale)}\n\n{details}",
                latex_famille(orthogonale),
            )
        if commande in {"estorthogonale", "familleorthogonale"}:
            famille = self._famille_ou_litteral(arguments)
            resultat = est_orthogonale(famille)
            return Reponse(
                f"Famille orthogonale : {'oui' if resultat else 'non'}.\n"
                "On vérifie tous les produits scalaires deux à deux.",
                r"\forall i\ne j,\ \langle v_i,v_j\rangle=0"
                if resultat
                else r"\exists i\ne j,\ \langle v_i,v_j\rangle\ne0",
            )
        if commande in {"orthonormale", "familleorthonormale"}:
            famille = self._famille_ou_litteral(arguments)
            resultat = est_orthonormale(famille)
            return Reponse(
                f"Famille orthonormale : {'oui' if resultat else 'non'}.\n"
                "Il faut l'orthogonalité et une norme égale à 1 pour chaque vecteur.",
                r"\langle v_i,v_j\rangle=\delta_{ij}",
            )
        if commande == "projection":
            vecteur_texte, famille_texte = _separer(arguments)
            vecteur = self._vecteur_ou_litteral(vecteur_texte)
            famille = self._famille_ou_litteral(famille_texte)
            projection = projection_orthogonale(vecteur, famille)
            reste = vecteur - projection
            return Reponse(
                f"proj_F(v) = {projection}\n"
                f"Reste orthogonal : v - proj_F(v) = {reste}\n"
                f"Vérification ⟨projection,reste⟩ = "
                f"{joli(projection.produit_scalaire(reste))}.",
                rf"\operatorname{{proj}}_F(v)={latex_vecteur(projection)}",
            )
        if commande == "symetrie":
            vecteur_texte, famille_texte = _separer(arguments)
            vecteur = self._vecteur_ou_litteral(vecteur_texte)
            famille = self._famille_ou_litteral(famille_texte)
            image = symetrie_orthogonale(vecteur, famille)
            return Reponse(
                f"s_F(v) = 2proj_F(v) - v = {image}.",
                rf"s_F(v)=2\operatorname{{proj}}_F(v)-v={latex_vecteur(image)}",
            )
        if commande == "projecteur":
            famille = self._famille_ou_litteral(arguments)
            dimension = len(famille[0])
            colonnes = [
                projection_orthogonale(
                    Vecteur(1 if i == j else 0 for i in range(dimension)), famille
                )
                for j in range(dimension)
            ]
            projecteur = Matrice.par_colonnes(colonnes)
            return Reponse(
                f"Matrice du projecteur orthogonal :\n{projecteur}\n"
                f"Vérification P²=P : {projecteur @ projecteur == projecteur}.",
                rf"P={latex_matrice(projecteur)},\qquad P^2=P",
            )
        if commande == "coordonnees":
            vecteur_texte, base_texte = _separer(arguments)
            vecteur = self._vecteur_ou_litteral(vecteur_texte)
            base = self._famille_ou_litteral(base_texte)
            coordonnees = coordonnees_dans_base(vecteur, base)
            return Reponse(
                f"[{vecteur_texte}]_{base_texte} = {coordonnees}.",
                rf"[{vecteur_texte}]_{{{base_texte}}}={latex_vecteur(coordonnees)}",
            )
        if commande == "changement":
            ancienne_texte, nouvelle_texte = _separer(arguments)
            ancienne = self._famille_ou_litteral(ancienne_texte)
            nouvelle = self._famille_ou_litteral(nouvelle_texte)
            passage = changement_de_base(ancienne, nouvelle)
            return Reponse(
                f"Passage des coordonnées dans {ancienne_texte} vers {nouvelle_texte} :\n"
                f"{passage}\nChaque colonne traduit un vecteur de l'ancienne base "
                "dans la nouvelle.",
                rf"P_{{{ancienne_texte}\to {nouvelle_texte}}}={latex_matrice(passage)}",
            )
        if commande in {"produit", "composer", "composition"}:
            gauche, droite = _separer(arguments)
            a, b = self._objet(gauche, Matrice), self._objet(droite, Matrice)
            produit = a @ b
            return Reponse(
                f"{gauche}{droite} =\n{produit}\n"
                f"Ordre géométrique : on applique d'abord {droite}, puis {gauche}.",
                rf"{gauche}{droite}={latex_matrice(produit)}",
            )
        if commande == "cramer":
            matrice_texte, vecteur_texte = _separer(arguments)
            matrice = self._objet(matrice_texte, Matrice)
            vecteur = self._vecteur_ou_litteral(vecteur_texte)
            solution = cramer(matrice, vecteur)
            return Reponse(
                f"Solution par Cramer : {solution}\n"
                "Chaque coordonnée est le rapport de deux aires/volumes orientés.",
                rf"x={latex_vecteur(solution)}",
            )
        if commande in {"spectre", "valeurspropres", "valeurs_propres"}:
            return self._spectre(self._objet(arguments, Matrice), arguments)
        if commande in {"diagonaliser", "diagonalisation"}:
            return self._diagonaliser(self._objet(arguments, Matrice), arguments)
        if commande in {"orthogonale", "orthogonal"}:
            objet = self._objet(arguments)
            if isinstance(objet, tuple):
                resultat = est_orthogonale(objet)
                return Reponse(f"Famille orthogonale : {'oui' if resultat else 'non'}.")
            matrice = self._objet(arguments, Matrice)
            if matrice.hauteur != matrice.largeur:
                raise ValueError("Une matrice orthogonale est carrée.")
            test = matrice.transposee() @ matrice
            resultat = test == Matrice.identite(matrice.largeur)
            return Reponse(
                f"AᵀA =\n{test}\nMatrice orthogonale : {'oui' if resultat else 'non'}.",
                rf"{arguments}^T{arguments}={latex_matrice(test)}",
            )
        if commande in {"derivee", "deriver"}:
            polynome = self._objet(arguments, Polynome)
            resultat = polynome.derivee()
            return Reponse(
                f"{arguments}' = {resultat}\n"
                "La dérivation est linéaire : D(P+Q)=D(P)+D(Q).",
                rf"{arguments}'={latex_polynome(resultat)}",
            )
        if commande == "primitive":
            polynome = self._objet(arguments, Polynome)
            resultat = polynome.primitive()
            return Reponse(
                f"Une primitive de {arguments} est {resultat}.",
                rf"\int {arguments}\,dX={latex_polynome(resultat)}+C",
            )

        raise ValueError("Commande inconnue. Tapez « aide ».")


    def _etudier(self, matrice: Matrice) -> Reponse:
        """Réunit les invariants essentiels d'une application linéaire"""
        rang = matrice.rang()

        lignes = [
            f"Format : {matrice.hauteur} × {matrice.largeur}",
            f"Application : R^{matrice.largeur} → R^{matrice.hauteur}",
            f"Rang : {rang}",
            f"dim Ker : {matrice.largeur - rang}",
            f"dim Im : {rang}",
            f"Injective : {'oui' if rang == matrice.largeur else 'non'}",
            f"Surjective : {'oui' if rang == matrice.hauteur else 'non'}",
        ]
        if matrice.hauteur == matrice.largeur:
            determinant = matrice.determinant()
            lignes.extend(
                [
                    f"Déterminant : {joli(determinant)}",
                    f"Automorphisme : {'oui' if determinant else 'non'}",
                ]
            )
        return Reponse(
            "\n".join(lignes),
            rf"\dim\ker A+\dim\operatorname{{Im}}A="
            rf"{matrice.largeur-rang}+{rang}={matrice.largeur}",
        )

    @staticmethod
    def _hyperplan_ou_systeme(systeme: Systeme) -> Reponse:
        nombre_equations = systeme.matrice.hauteur
        if nombre_equations != 1:
            rang = systeme.matrice.rang()
            return Reponse(

                f"Système de {nombre_equations} contraintes dans R^{systeme.matrice.largeur}.\n"
                f"Rang des contraintes : {rang}.\n"
                f"Dimension de l'espace directeur si compatible : "
                f"{systeme.matrice.largeur-rang}."
            )
        normale = Vecteur(systeme.matrice[0])
        second = systeme.second_membre[0]
        nature = "vectoriel" if second == 0 else "affine"
        return Reponse(
            f"Hyperplan {nature} de R^{systeme.matrice.largeur}.\n"
            f"Vecteur normal : {normale}\n"
            f"Dimension de la direction : {systeme.matrice.largeur - 1}.",
            rf"H=\{{x\mid\langle {latex_vecteur(normale)},x\rangle"
            rf"={latex_nombre(second)}\}}",
        )

    def _determinant(self, matrice: Matrice) -> Reponse:
        """Associe au calcul exact son interprétation géométrique."""
        determinant, etapes = matrice.determinant_detaille()
        sens = (
            "aires/volumes conservés"
            if abs(determinant) == 1
            else "espace écrasé dans une dimension plus petite"
            if determinant == 0
            else f"aires/volumes multipliés par {joli(abs(determinant))}"
        )
        orientation = (
            "orientation conservée"
            if determinant > 0
            else "orientation inversée"
            if determinant < 0
            else "orientation perdue"
        )
        texte = (
            f"det(A) = {joli(determinant)}\n"
            f"Sens géométrique : {sens}, {orientation}."
        )

        if matrice.taille == (2, 2):
            a, b = matrice[0]
            c, d = matrice[1]
            texte += (
                f"\nCalcul direct : ({joli(a)}×{joli(d)}) "
                f"- ({joli(b)}×{joli(c)}) = {joli(determinant)}."
            )
        elif etapes:
            texte += f"\n\nTriangularisation :\n{afficher_etapes(etapes)}"
        texte += "\nLien : det(A)=0 ⇔ A n'est pas inversible ⇔ Ker(A)≠{0}."
        return Reponse(
            texte,
            rf"\det({latex_matrice(matrice)})={latex_nombre(determinant)}",
        )

    def _resoudre(self, arguments: str) -> Reponse:
        """Accepte un système nommé ou le couple matrice ; second membre."""
        if arguments in self.objets and isinstance(self.objets[arguments], Systeme):
            systeme = self.objets[arguments]
            matrice = systeme.matrice
            second_membre = systeme.second_membre
            variables = systeme.variables
        else:
            matrice_texte, second_texte = _separer(arguments)
            matrice = self._objet(matrice_texte, Matrice)
            second_membre = self._vecteur_ou_litteral(second_texte)
            variables = tuple(f"x{i + 1}" for i in range(matrice.largeur))
        solution = matrice.resoudre(second_membre)
        if not solution.compatible:
            conclusion = "Système incompatible : aucune solution."
            latex = r"\mathcal S=\varnothing"
        else:
            conclusion = decomposition_affine(
                solution.particuliere, solution.directions, variables
            )
            latex = rf"\mathcal S={latex_vecteur(solution.particuliere)}"
            if solution.directions:
                latex += (
                    r"+\operatorname{Vect}"
                    + latex_famille(solution.directions)
                )
        return Reponse(
            f"Réduction de la matrice augmentée :\n"
            f"{afficher_etapes(solution.etapes)}\n\n{conclusion}",
            latex + "\n" + latex_etapes(solution.etapes),
        )

    def _etudier_famille(self, famille: tuple[Vecteur, ...]) -> Reponse:
        """Relie rang, liberté, génération et notion de base."""
        matrice = Matrice.par_colonnes(famille)
        rang = matrice.rang()
        dimension = len(famille[0])
        libre = rang == len(famille)
        generatrice = rang == dimension
        relations = relation_dependance(famille)
        lignes = [
            f"Dimension ambiante : {dimension}",
            f"Nombre de vecteurs : {len(famille)}",
            f"Rang : {rang}",
            f"Libre : {'oui' if libre else 'non'}",
            f"Génératrice : {'oui' if generatrice else 'non'}",
            f"Base : {'oui' if libre and generatrice else 'non'}",
        ]
        if relations:
            lignes.append(f"Relation de dépendance : coefficients {relations[0]}.")

        return Reponse("\n".join(lignes), rf"\operatorname{{rg}}(F)={rang}")

    @staticmethod
    def _etapes_gram_schmidt(
        famille: tuple[Vecteur, ...], resultat: tuple[Vecteur, ...]
    ) -> str:
        lignes = []
        construits: list[Vecteur] = []
        for indice, vecteur in enumerate(famille, 1):
            if not construits:
                candidat = vecteur
                formule = f"u{indice} = v{indice} = {candidat}"
            else:
                candidat = vecteur
                termes = []
                for u in construits:
                    coefficient = vecteur.produit_scalaire(u) / u.norme_carree()
                    candidat = candidat - coefficient * u
                    termes.append(f"({joli(coefficient)}){u}")

                formule = (
                    f"u{indice} = v{indice} - "
                    + " - ".join(termes)
                    + f" = {candidat}"
                )
            if not candidat.est_nul():
                construits.append(candidat)
            lignes.append(formule)
        return "\n".join(lignes)



    def _spectre(self, matrice: Matrice, nom: str) -> Reponse:
        """Présente le spectre réel d'une matrice 2 par 2."""
        valeurs = spectre_2d(matrice)
        trace = matrice[0][0] + matrice[1][1]
        determinant = matrice.determinant()
        lignes = [
            f"χ_A(λ) = λ² - ({joli(trace)})λ + ({joli(determinant)})",
            "Racines :",
        ]
        latex_lignes = [
            rf"\chi_A(\lambda)=\lambda^2-({latex_nombre(trace)})\lambda"
            rf"+({latex_nombre(determinant)})"
        ]
        for valeur, vecteur in valeurs:
            lignes.append(f"  λ = {joli(valeur)}, direction propre {vecteur}")
            latex_lignes.append(
                rf"\lambda={latex_nombre(valeur)},\quad "
                rf"E_\lambda=\operatorname{{Vect}}({latex_vecteur(vecteur)})"
            )
        lignes.append("Sens : sur chaque direction propre, A agit comme un simple scalaire.")
        return Reponse("\n".join(lignes), r"\\".join(latex_lignes))

    def _diagonaliser(self, matrice: Matrice, nom: str) -> Reponse:
        """Construit P et D lorsque les directions propres forment une base."""
        spectre = spectre_2d(matrice)
        if len(spectre) < 2:
            identite = Matrice.identite(2)
            if matrice == Matrice(
                [[matrice[0][0], 0], [0, matrice[0][0]]]
            ):
                return Reponse("La matrice est déjà scalaire, donc diagonale dans toute base.")
            raise ValueError("Une seule direction propre : matrice non diagonalisable ici.")
        p = Matrice.par_colonnes([vecteur for _, vecteur in spectre])
        if p.determinant() == 0:
            raise ValueError("Les directions propres ne forment pas une base.")
        
        d = Matrice(
            [
                [spectre[0][0], 0],
                [0, spectre[1][0]],
            ]
        )
        return Reponse(

            f"P =\n{p}\n\nD =\n{d}\n\n{nom} = P D P⁻¹.\n"
            "Dans la base propre, la transformation devient deux dilatations indépendantes.",
            rf"{nom}=PDP^{{-1}},\quad P={latex_matrice(p)},\quad D={latex_matrice(d)}",
        )
