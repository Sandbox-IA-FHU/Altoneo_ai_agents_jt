"""Exceptions de l'agent.

Un message d'exception ne contient jamais le contenu d'un prompt, d'un document
lu ou d'une réponse de modèle : seulement des identifiants et des compteurs.
"""


class ConfigError(Exception):
    """Configuration absente ou invalide au démarrage."""


class ToolError(Exception):
    """Erreur d'exécution d'un outil, renvoyée au modèle comme résultat."""


class UnknownToolError(Exception):
    """Le modèle a demandé un outil qui n'existe pas dans le registre."""


class ModelCallError(Exception):
    """L'appel au LLM a échoué de façon définitive."""


class DocumentStoreError(Exception):
    """Document introuvable, magasin de documents ou jeu de tâches illisible."""
