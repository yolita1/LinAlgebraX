"""Construction des scènes envoyées à l'observatoire."""


from algebre import (
    Matrice,
    Vecteur,
    base_intersection,
    base_somme,
    changement_de_base,
    complement_de_base,
    coordonnees_dans_base,
    cramer,
    joli,
    orthogonaliser,
    produit_vectoriel,
    projection_orthogonale,
    relation_dependance,
    spectre_2d,
    symetrie_orthogonale,
)
from polynomes import Polynome


def _f(nombre) -> float:
    # Les fractions ne deviennent approchées qu'au moment de placer les pixels.
    return float(nombre)


def _vecteur(vecteur: Vecteur) -> list[float]:
    return [_f(x) for x in vecteur]


def _matrice(matrice: Matrice) -> list[list[float]]:
    return [[_f(x) for x in ligne] for ligne in matrice.lignes]


def _matrice_texte(matrice: Matrice) -> list[list[str]]:
    return [[joli(x) for x in ligne] for ligne in matrice.lignes]


def _identite(dimension: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(dimension)] for i in range(dimension)]


def _cadre(
    formule: str,
    explication: str,
    donnees: dict | None = None,
    operation: str = "",
) -> dict:
    return {
        "formule": formule,
        "explication": explication,
        "donnees": donnees or {},
        "operation": operation,
    }


def _vue(nom: str, type_vue: str, cadres: list[dict]) -> dict:
    return {"nom": nom, "type": type_vue, "cadres": cadres}


def _scene(titre: str, vues: list[dict], legende: list[str] | None = None) -> dict:
    return {"titre": titre, "vues": vues, "legende": legende or []}


def _etapes_matrices(
    matrice_initiale: Matrice,
    etapes,
    formule: str,
    explication: str,
) -> list[dict]:
    cadres = [
        _cadre(
            formule,
            explication,
            {"matrice": _matrice_texte(matrice_initiale)},
            "Matrice initiale",
        )
    ]
    for etape in etapes:
        matrice = Matrice(etape.matrice)
        cadres.append(
            _cadre(
                formule,
                "Chaque opération élémentaire conserve l'ensemble des solutions.",
                {"matrice": _matrice_texte(matrice)},
                etape.operation,
            )
        )
    return cadres


def _scene_transformation(matrice: Matrice, titre: str, formule: str, explication: str):
    """Prépare la déformation géométrique de la grille par une matrice."""
    donnees = {
        "depart": _identite(matrice.largeur),
        "arrivee": _matrice(matrice),
        "hauteur": matrice.hauteur,
        "largeur": matrice.largeur,
    }
    return {
        "titre": titre,
        "vues": [
            {
                "nom": "Géométrie",
                "type": "transformation",
                "cadres": [
                    {
                        "formule": formule,
                        "explication": explication,
                        "donnees": donnees,
                        "operation": "",
                    }
                ],
            },
            {
                "nom": "Calcul",
                "type": "matrice",
                "cadres": [
                    {
                        "formule": formule,
                        "explication": (
                            "La colonne j est l'image du j-ième vecteur de base."
                        ),
                        "donnees": {"matrice": _matrice_texte(matrice)},
                        "operation": (
                            f"Application R^{matrice.largeur} "
                            f"→ R^{matrice.hauteur}"
                        ),
                    }
                ],
            },
        ],
        "legende": [
            "doré : image de e₁",
            "bleu-gris : image de e₂",
            "gris : quadrillage",
        ],
    }


def _separer(arguments: str) -> tuple[str, str]:
    gauche, droite = (morceau.strip() for morceau in arguments.split(";", 1))
    return gauche, droite


def scene_attente(message: str = "En attente du terminal") -> dict:
    """Retourne une scène neutre, sans logo ni animation décorative."""
    return {
        "titre": "Observatoire",
        "vues": [
            {
                "nom": "Vue",
                "type": "attente",
                "cadres": [
                    {
                        "formule": "",
                        "explication": message,
                        "donnees": {"message": message},
                        "operation": "",
                    }
                ],
            }
        ],
        "legende": [],
    }


def creer_scene(laboratoire, ligne: str, reponse) -> dict | None:
    """Construit la scène déclenchée automatiquement après une commande."""
    if not ligne.strip() or "=" in ligne.split(" ", 1)[0] or reponse.quitter:
        return None
    commande, _, arguments = ligne.strip().partition(" ")
    commande = commande.lower()
    arguments = arguments.strip()
    commande = (
        commande.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
    )

    if commande in {"etudier", "etude", "application", "applicationlineaire"}:
        objet = laboratoire.objets.get(arguments)
        if isinstance(objet, Matrice):
            return _scene_transformation(
                objet,
                f"Étude de {arguments}",
                r"$x\longmapsto Ax$",
                "Toute l'application est déterminée par les images des vecteurs de base.",
            )
        if isinstance(objet, tuple) and objet and isinstance(objet[0], Vecteur):
            return _scene_famille(objet, f"Étude de {arguments}")
        if hasattr(objet, "matrice"):
            return _scene_systeme(objet, f"Étude de {arguments}")

    if commande in {"isomorphisme", "automorphisme"}:
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice):
            return _scene_transformation(
                matrice,
                f"{commande.capitalize()} {arguments}",
                r"$\det(A)\neq0\Longleftrightarrow A\in GL_n$",
                "Aucune direction n'est perdue : la transformation peut être remontée.",
            )

    if commande in {"reduire", "rref", "gauss"}:
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice):
            reduction = matrice.reduire()
            calcul = _vue(
                "Calcul",
                "matrice",
                _etapes_matrices(
                    matrice,
                    reduction.etapes,
                    r"$A\sim\operatorname{rref}(A)$",
                    "On cherche successivement les pivots.",
                ),
            )
            vues = [calcul]
            if matrice.taille in {(2, 2), (3, 3), (3, 2), (2, 3)}:
                vues.insert(
                    0,
                    _scene_transformation(
                        matrice,
                        "",
                        r"$x\longmapsto Ax$",
                        "La réduction révèle les dimensions conservées.",
                    )["vues"][0],
                )
            return _scene(f"Réduction de {arguments}", vues)

    if commande in {"det", "determinant"}:
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice) and matrice.hauteur == matrice.largeur:
            determinant, etapes = matrice.determinant_detaille()
            geometrie = _vue(
                "Géométrie",
                "determinant",
                [
                    _cadre(
                        rf"$\det(A)={joli(determinant)}$",
                        "La valeur absolue mesure le facteur d'aire ou de volume ; le signe mesure l'orientation.",
                        {
                            "depart": _identite(matrice.largeur),
                            "arrivee": _matrice(matrice),
                            "determinant": _f(determinant),
                            "dimension": matrice.largeur,
                        },
                    )
                ],
            )
            if matrice.taille == (2, 2):
                a, b = matrice[0]
                c, d = matrice[1]
                formule = rf"$\det(A)=({joli(a)})({joli(d)})-({joli(b)})({joli(c)})={joli(determinant)}$"
            else:
                formule = rf"$\det(A)={joli(determinant)}$"
            calcul = _vue(
                "Calcul",
                "matrice",
                _etapes_matrices(
                    matrice,
                    etapes,
                    formule,
                    "Les additions de lignes conservent le déterminant ; un échange change son signe.",
                ),
            )
            return _scene(
                f"Déterminant de {arguments}",
                [geometrie, calcul],
                ["surface dorée : image du carré unité", "signe : orientation"],
            )

    if commande == "inverse":
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice):
            inverse, etapes = matrice.inverse()
            geometrie = _vue(
                "Géométrie",
                "transformation",
                [
                    _cadre(
                        r"$I\longrightarrow A$",
                        "La matrice A déforme tout l'espace.",
                        {
                            "depart": _identite(matrice.largeur),
                            "arrivee": _matrice(matrice),
                            "hauteur": matrice.hauteur,
                            "largeur": matrice.largeur,
                        },
                    ),
                    _cadre(
                        r"$A^{-1}A=I$",
                        "L'inverse joue exactement la transformation à rebours.",
                        {
                            "depart": _matrice(matrice),
                            "arrivee": _identite(matrice.largeur),
                            "hauteur": matrice.hauteur,
                            "largeur": matrice.largeur,
                        },
                    ),
                ],
            )
            augmentee = matrice.augmenter(Matrice.identite(matrice.hauteur))
            calcul = _vue(
                "Calcul",
                "matrice",
                _etapes_matrices(
                    augmentee,
                    etapes,
                    r"$[A\mid I]\sim[I\mid A^{-1}]$",
                    "Les mêmes opérations qui ramènent A à I construisent A⁻¹.",
                ),
            )
            return _scene(
                f"Inverse de {arguments}",
                [geometrie, calcul],
                ["Tab ou boutons : géométrie / calcul", "A⁻¹ annule exactement A"],
            )

    if commande in {"rang", "noyau", "ker", "image", "im"}:
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice):
            reduction = matrice.reduire()
            noyau = [_vecteur(v) for v in matrice.base_noyau()]
            image = [_vecteur(v) for v in matrice.base_image()]
            geometrie = _vue(
                "Géométrie",
                "sous_espaces",
                [
                    _cadre(
                        rf"$\dim\ker A+\dim\operatorname{{Im}}A={matrice.largeur}$",
                        "Le noyau contient les directions écrasées ; l'image contient toutes les sorties possibles.",
                        {
                            "matrice": _matrice(matrice),
                            "noyau": noyau,
                            "image": image,
                            "commande": commande,
                        },
                    )
                ],
            )
            calcul = _vue(
                "Calcul",
                "matrice",
                _etapes_matrices(
                    matrice,
                    reduction.etapes,
                    rf"$\operatorname{{rg}}(A)={matrice.rang()}$",
                    "Les colonnes pivots donnent l'image ; les variables libres donnent le noyau.",
                ),
            )
            return _scene(f"{commande.capitalize()} de {arguments}", [geometrie, calcul])

    if commande in {"resoudre", "solve"}:
        systeme = laboratoire.objets.get(arguments)
        if systeme is not None and hasattr(systeme, "second_membre"):
            return _scene_systeme(systeme, f"Résolution de {arguments}")
        if ";" in arguments:
            nom_matrice, nom_second = _separer(arguments)
            matrice = laboratoire.objets.get(nom_matrice)
            second = laboratoire.objets.get(nom_second)
            if isinstance(matrice, Matrice) and isinstance(second, Vecteur):
                from moteur import Systeme

                systeme = Systeme(
                    matrice,
                    second,
                    tuple(f"x{i + 1}" for i in range(matrice.largeur)),
                )
                return _scene_systeme(systeme, "Résolution du système")

    if commande in {"famille", "base"}:
        famille = laboratoire.objets.get(arguments)
        if isinstance(famille, tuple):
            return _scene_famille(famille, f"Famille {arguments}")

    if commande in {"somme", "intersection"} and ";" in arguments:
        nom_f, nom_g = _separer(arguments)
        f, g = laboratoire.objets.get(nom_f), laboratoire.objets.get(nom_g)
        if isinstance(f, tuple) and isinstance(g, tuple):
            resultat = base_somme(f, g) if commande == "somme" else base_intersection(f, g)
            if resultat:
                return _scene_famille(
                    resultat,
                    f"{commande.capitalize()} de Vect({nom_f}) et Vect({nom_g})",
                )

    if commande in {"supplement", "supplementaire"}:
        famille = laboratoire.objets.get(arguments)
        if isinstance(famille, tuple):
            complement = complement_de_base(famille)
            total = famille + complement
            return _scene_famille(
                total,
                f"Complétion de {arguments} en une base",
            )

    if commande in {
        "estorthogonale",
        "familleorthogonale",
        "orthonormale",
        "familleorthonormale",
    }:
        famille = laboratoire.objets.get(arguments)
        if isinstance(famille, tuple):
            return _scene_famille(famille, f"Orthogonalité de {arguments}")

    if commande in {"orthogonale", "orthogonal"}:
        objet = laboratoire.objets.get(arguments)
        if isinstance(objet, Matrice):
            return _scene_transformation(
                objet,
                f"Transformation orthogonale {arguments}",
                r"$A^TA=I$",
                "Les longueurs et les angles sont conservés.",
            )
        if isinstance(objet, tuple):
            return _scene_famille(objet, f"Orthogonalité de {arguments}")

    if commande in {"orthogonaliser", "gram-schmidt", "gramschmidt"}:
        famille = laboratoire.objets.get(arguments)
        if isinstance(famille, tuple):
            resultat = orthogonaliser(famille)
            cadres = []
            construits = []
            for i, (avant, apres) in enumerate(zip(famille, resultat), 1):
                construits.append(apres)
                cadres.append(
                    _cadre(
                        rf"$u_{i}=v_{i}-\sum_{{j<i}}\operatorname{{proj}}_{{u_j}}(v_i)$",
                        "On retire à chaque vecteur ses composantes dans les directions déjà construites.",
                        {
                            "famille": [_vecteur(v) for v in famille],
                            "resultat": [_vecteur(v) for v in construits],
                        },
                    )
                )
            return _scene(
                f"Gram-Schmidt sur {arguments}",
                [_vue("Géométrie", "gram_schmidt", cadres)],
            )

    if commande in {"projection", "symetrie"} and ";" in arguments:
        nom_v, nom_f = _separer(arguments)
        vecteur = laboratoire.objets.get(nom_v)
        famille = laboratoire.objets.get(nom_f)
        if isinstance(vecteur, Vecteur) and isinstance(famille, tuple):
            projection = projection_orthogonale(vecteur, famille)
            cible = (
                symetrie_orthogonale(vecteur, famille)
                if commande == "symetrie"
                else projection
            )
            return _scene(
                f"{commande.capitalize()} de {nom_v}",
                [
                    _vue(
                        "Géométrie",
                        "projection",
                        [
                            _cadre(
                                r"$v=\operatorname{proj}_F(v)+(v-\operatorname{proj}_F(v))$",
                                "Le reste est orthogonal au sous-espace ; la symétrie prolonge le même segment.",
                                {
                                    "vecteur": _vecteur(vecteur),
                                    "famille": [_vecteur(v) for v in famille],
                                    "projection": _vecteur(projection),
                                    "cible": _vecteur(cible),
                                    "symetrie": commande == "symetrie",
                                },
                            )
                        ],
                    ),
                    _vue(
                        "Calcul",
                        "formule",
                        [
                            _cadre(
                                r"$\operatorname{proj}_u(v)=\frac{\langle v,u\rangle}{\langle u,u\rangle}u$",
                                f"Résultat exact dans le terminal : {cible}.",
                            )
                        ],
                    ),
                ],
            )

    if commande == "projecteur":
        famille = laboratoire.objets.get(arguments)
        if isinstance(famille, tuple):
            dimension = len(famille[0])
            colonnes = [
                projection_orthogonale(
                    Vecteur(1 if i == j else 0 for i in range(dimension)),
                    famille,
                )
                for j in range(dimension)
            ]
            projecteur = Matrice.par_colonnes(colonnes)
            return _scene_transformation(
                projecteur,
                f"Projecteur sur Vect({arguments})",
                r"$P^2=P$",
                "Les directions du sous-espace restent fixes ; les directions complémentaires sont écrasées.",
            )

    if commande in {"scalaire", "dot"} and ";" in arguments:
        nom_u, nom_v = _separer(arguments)
        u, v = laboratoire.objets.get(nom_u), laboratoire.objets.get(nom_v)
        if isinstance(u, Vecteur) and isinstance(v, Vecteur):
            valeur = u.produit_scalaire(v)
            return _scene(
                f"Produit scalaire de {nom_u} et {nom_v}",
                [
                    _vue(
                        "Géométrie",
                        "produit_scalaire",
                        [
                            _cadre(
                                rf"$\langle u,v\rangle={joli(valeur)}$",
                                "Le produit scalaire est une projection signée multipliée par une norme.",
                                {"u": _vecteur(u), "v": _vecteur(v)},
                            )
                        ],
                    )
                ],
            )

    if commande in {"vectoriel", "cross"} and ";" in arguments:
        nom_u, nom_v = _separer(arguments)
        u, v = laboratoire.objets.get(nom_u), laboratoire.objets.get(nom_v)
        if isinstance(u, Vecteur) and isinstance(v, Vecteur):
            produit = produit_vectoriel(u, v)
            return _scene(
                f"Produit vectoriel {nom_u} × {nom_v}",
                [
                    _vue(
                        "Géométrie",
                        "produit_vectoriel",
                        [
                            _cadre(
                                r"$\|u\times v\|=\text{aire du parallélogramme}$",
                                "u×v est perpendiculaire au plan orienté par u et v.",
                                {"u": _vecteur(u), "v": _vecteur(v), "w": _vecteur(produit)},
                            )
                        ],
                    )
                ],
            )

    if commande in {"produit", "composer", "composition"} and ";" in arguments:
        nom_a, nom_b = _separer(arguments)
        a, b = laboratoire.objets.get(nom_a), laboratoire.objets.get(nom_b)
        if isinstance(a, Matrice) and isinstance(b, Matrice):
            produit = a @ b
            return _scene(
                f"Composition {nom_a}{nom_b}",
                [
                    _vue(
                        "Géométrie",
                        "transformation",
                        [
                            _cadre(
                                rf"$I\longrightarrow {nom_b}$",
                                f"On applique d'abord {nom_b}.",
                                {
                                    "depart": _identite(b.largeur),
                                    "arrivee": _matrice(b),
                                    "hauteur": b.hauteur,
                                    "largeur": b.largeur,
                                },
                            ),
                            _cadre(
                                rf"${nom_b}\longrightarrow {nom_a}{nom_b}$",
                                f"Puis {nom_a} agit sur le résultat.",
                                {
                                    "depart": _matrice(b),
                                    "arrivee": _matrice(produit),
                                    "hauteur": produit.hauteur,
                                    "largeur": produit.largeur,
                                },
                            ),
                        ],
                    ),
                    _vue(
                        "Calcul",
                        "matrice",
                        [
                            _cadre(
                                rf"${nom_a}{nom_b}$",
                                "La j-ième colonne est A appliquée à la j-ième colonne de B.",
                                {"matrice": _matrice_texte(produit)},
                            )
                        ],
                    ),
                ],
            )

    if commande == "cramer" and ";" in arguments:
        nom_a, nom_b = _separer(arguments)
        a, b = laboratoire.objets.get(nom_a), laboratoire.objets.get(nom_b)
        if isinstance(a, Matrice) and isinstance(b, Vecteur):
            solution = cramer(a, b)
            colonnes = list(a.colonnes())
            matrices = [a]
            for j in range(a.largeur):
                copie = colonnes.copy()
                copie[j] = b
                matrices.append(Matrice.par_colonnes(copie))
            return _scene(
                "Règle de Cramer",
                [
                    _vue(
                        "Géométrie",
                        "cramer",
                        [
                            _cadre(
                                r"$x_i=\frac{\det(A_i)}{\det(A)}$",
                                "Chaque coordonnée compare deux aires ou volumes orientés.",
                                {
                                    "matrices": [_matrice(m) for m in matrices],
                                    "determinants": [_f(m.determinant()) for m in matrices],
                                    "solution": _vecteur(solution),
                                },
                            )
                        ],
                    )
                ],
            )

    if commande in {"changement", "coordonnees"} and ";" in arguments:
        gauche, droite = _separer(arguments)
        if commande == "changement":
            ancienne, nouvelle = laboratoire.objets.get(gauche), laboratoire.objets.get(droite)
            if isinstance(ancienne, tuple) and isinstance(nouvelle, tuple):
                passage = changement_de_base(ancienne, nouvelle)
                return _scene_changement(ancienne, nouvelle, passage, gauche, droite)
        else:
            vecteur, base = laboratoire.objets.get(gauche), laboratoire.objets.get(droite)
            if isinstance(vecteur, Vecteur) and isinstance(base, tuple):
                coord = coordonnees_dans_base(vecteur, base)
                return _scene(
                    f"Coordonnées de {gauche} dans {droite}",
                    [
                        _vue(
                            "Géométrie",
                            "changement_base",
                            [
                                _cadre(
                                    rf"$v=\sum_i [v]_{{B,i}}b_i$",
                                    "Le vecteur ne bouge pas : seul le langage de coordonnées change.",
                                    {
                                        "ancienne": _identite(len(vecteur)),
                                        "nouvelle": [_vecteur(v) for v in base],
                                        "vecteur": _vecteur(vecteur),
                                        "coordonnees": _vecteur(coord),
                                    },
                                )
                            ],
                        )
                    ],
                )

    if commande in {"spectre", "valeurspropres", "valeurs_propres", "diagonaliser", "diagonalisation"}:
        matrice = laboratoire.objets.get(arguments)
        if isinstance(matrice, Matrice) and matrice.taille == (2, 2):
            spectre = spectre_2d(matrice)
            return _scene(
                f"Directions propres de {arguments}",
                [
                    _vue(
                        "Géométrie",
                        "spectre",
                        [
                            _cadre(
                                r"$Av=\lambda v$",
                                "Ces directions restent sur leur propre droite pendant toute la transformation.",
                                {
                                    "matrice": _matrice(matrice),
                                    "spectre": [
                                        {"valeur": _f(valeur), "vecteur": _vecteur(vecteur)}
                                        for valeur, vecteur in spectre
                                    ],
                                },
                            )
                        ],
                    )
                ],
            )

    if commande in {"derivee", "deriver", "primitive"}:
        polynome = laboratoire.objets.get(arguments)
        if isinstance(polynome, Polynome):
            resultat = (
                polynome.primitive()
                if commande == "primitive"
                else polynome.derivee()
            )
            return _scene(
                f"{commande.capitalize()} de {arguments}",
                [
                    _vue(
                        "Géométrie",
                        "polynome",
                        [
                            _cadre(
                                r"$D(P+Q)=D(P)+D(Q)$",
                                "La courbe change, tandis que les coefficients révèlent une simple application linéaire.",
                                {
                                    "avant": [_f(x) for x in polynome.coefficients],
                                    "apres": [_f(x) for x in resultat.coefficients],
                                    "nom_avant": str(polynome),
                                    "nom_apres": str(resultat),
                                },
                            )
                        ],
                    )
                ],
            )

    if commande == "hyperplan":
        systeme = laboratoire.objets.get(arguments)
        if systeme is not None and hasattr(systeme, "matrice"):
            return _scene_hyperplan(systeme, arguments)

    return None


def _scene_famille(famille: tuple[Vecteur, ...], titre: str) -> dict:
    matrice = Matrice.par_colonnes(famille)
    relations = relation_dependance(famille)
    dimension = len(famille[0])
    if dimension <= 3:
        legende = ["flèche : vecteur", "grille : espace engendré"]
    else:
        # En dimensions 4 et 5, chaque axe porte une coordonnée.
        legende = [
            "axes verticaux : coordonnées x₁,…,xₙ",
            "ligne brisée : portrait coordonné exact d'un vecteur",
        ]
    return _scene(
        titre,
        [
            _vue(
                "Géométrie",
                "famille",
                [
                    _cadre(
                        rf"$\operatorname{{rg}}(F)={matrice.rang()}$",
                        "Le rang est le nombre de directions réellement indépendantes.",
                        {
                            "famille": [_vecteur(v) for v in famille],
                            "relations": [_vecteur(v) for v in relations],
                            "dimension": dimension,
                        },
                    )
                ],
            )
        ],
        legende,
    )


def _scene_systeme(systeme, titre: str) -> dict:
    """Réunit la géométrie des contraintes et les étapes de Gauss."""
    solution = systeme.matrice.resoudre(systeme.second_membre)
    augmentee = systeme.matrice.augmenter(
        Matrice([[x] for x in systeme.second_membre])
    )
    geometrie = _vue(
        "Géométrie",
        "systeme",
        [
            _cadre(
                r"$Ax=b$",
                "Résoudre revient à chercher l'intersection des contraintes.",
                {
                    "matrice": _matrice(systeme.matrice),
                    "second": _vecteur(systeme.second_membre),
                    "variables": list(systeme.variables),
                    "solution": (
                        _vecteur(solution.particuliere)
                        if solution.compatible and solution.particuliere
                        else None
                    ),
                },
            )
        ],
    )
    calcul = _vue(
        "Calcul",
        "matrice",
        _etapes_matrices(
            augmentee,
            solution.etapes,
            r"$[A\mid b]\sim[R\mid c]$",
            "La forme réduite rend la compatibilité et les paramètres visibles.",
        ),
    )
    return _scene(titre, [geometrie, calcul])


def _scene_changement(ancienne, nouvelle, passage, nom_ancienne, nom_nouvelle):
    """Montre que l'objet reste fixe tandis que son quadrillage change."""
    return _scene(
        f"Passage de {nom_ancienne} vers {nom_nouvelle}",
        [
            _vue(
                "Géométrie",
                "changement_base",
                [
                    _cadre(
                        rf"$[x]_{{{nom_nouvelle}}}=P[x]_{{{nom_ancienne}}}$",
                        "L'espace reste le même ; le quadrillage représente seulement un langage de coordonnées.",
                        {
                            "ancienne": [_vecteur(v) for v in ancienne],
                            "nouvelle": [_vecteur(v) for v in nouvelle],
                            "passage": _matrice(passage),
                        },
                    )
                ],
            ),
            _vue(
                "Calcul",
                "matrice",
                [
                    _cadre(
                        r"$P_{B\to C}$",
                        "Chaque colonne traduit un vecteur de l'ancienne base dans la nouvelle.",
                        {"matrice": _matrice_texte(passage)},
                    )
                ],
            ),
        ],
    )


def _scene_hyperplan(systeme, nom: str):
    """Prépare un hyperplan à partir de son vecteur normal et de sa constante."""
    normale = Vecteur(systeme.matrice[0])
    return _scene(
        f"Hyperplan {nom}",
        [
            _vue(
                "Géométrie",
                "hyperplan",
                [
                    _cadre(
                        r"$H=\{x\mid\langle n,x\rangle=c\}$",
                        "Le vecteur normal fixe l'orientation ; la constante déplace l'hyperplan.",
                        {
                            "normale": _vecteur(normale),
                            "constante": _f(systeme.second_membre[0]),
                        },
                    )
                ],
            )
        ],
    )
