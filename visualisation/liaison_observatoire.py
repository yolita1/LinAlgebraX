"""Communication entre le terminal et la fenêtre Tkinter."""


import importlib.util
import multiprocessing
import queue


class Observatoire:
    """Démarre la fenêtre dans un processus et lui transmet les scènes."""

    def __init__(self):
        self.processus = None
        self.file_messages = None

    def demarrer(self) -> bool:
        if importlib.util.find_spec("tkinter") is None:
            print(
                "Fenêtre graphique indisponible : installez python3-tk "
                "avec « sudo apt install python3-tk »."
            )
            return False
        contexte = multiprocessing.get_context("spawn")
        self.file_messages = contexte.Queue(maxsize=8)
        from visualisation.fenetre_observatoire import lancer_fenetre

        self.processus = contexte.Process(
            target=lancer_fenetre,
            args=(self.file_messages,),
            name="LinAlgebraX-Simple-observatoire",
            daemon=True,
        )
        self.processus.start()
        return True

    @property
    def actif(self) -> bool:
        return self.processus is not None and self.processus.is_alive()

    def envoyer(self, scene: dict | None) -> None:
        if not self.actif and not self.demarrer():
            return
        message = (
            {"type": "scene", "scene": scene}
            if scene
            else {"type": "montrer"}
        )
        try:
            self.file_messages.put_nowait(message)
        except queue.Full:
            try:
                self.file_messages.get_nowait()
            except queue.Empty:
                pass
            try:
                self.file_messages.put_nowait(message)
            except queue.Full:
                pass

    def fermer(self) -> None:
        if not self.processus:
            return
        if self.processus.is_alive():
            try:
                self.file_messages.put_nowait({"type": "fermer"})
            except queue.Full:
                pass
            self.processus.join(timeout=1.0)
        if self.processus.is_alive():
            self.processus.terminate()
            self.processus.join(timeout=0.5)
        try:
            self.file_messages.close()
        except Exception:
            pass
