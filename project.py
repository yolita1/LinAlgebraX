"""Point d'entrée de LinAlgebraX"""

from moteur import Laboratoire, Reponse
from visualisation.liaison_observatoire import Observatoire


BARRE_COMMANDES = (
    "[commandes] [memoire] [retour]"
)


def executer_commande(
    commande: str, laboratoire: Laboratoire | None = None
) -> Reponse:
    session = laboratoire if laboratoire is not None else Laboratoire()
    return session.executer(commande)

def afficher_reponse(reponse: Reponse, afficher_latex: bool = False) -> None:
    if reponse.texte:
        print(reponse.texte)
    if afficher_latex and reponse.latex:
        print("\nLaTeX :")
        print(reponse.latex)



def lire_commande() -> str:
    print("\n" + BARRE_COMMANDES)
    return input("LinAlgeX> ")


def main() -> None:
    """Lance le laboratoire interactif."""
    print(
        "\nLinAlgebraX Simple : algèbre linéaire dans le terminal\n"
        "Calcul exact en Python | observatoire noir automatique\n"
        "Tapez « aide » pour afficher les commandes disponibles.\n"
    )
    laboratoire = Laboratoire()
    observatoire = Observatoire()
    observatoire.demarrer()

    try:
        while True:
            try:
                commande = lire_commande()
                reponse = executer_commande(commande, laboratoire)
                afficher_reponse(reponse, not observatoire.actif)
                observatoire.envoyer(reponse.scene)
                if reponse.quitter:
                    break
            except (EOFError, KeyboardInterrupt):
                print("\nÀ bientôt.")
                break
            except (ValueError, ZeroDivisionError) as erreur:
                print(f"Erreur : {erreur}")
                observatoire.envoyer(None)
    finally:

        observatoire.fermer()











if __name__ == "__main__":
    main()
