"""Serving layer: turns trained artifacts + the synthetic world into live answers for the API.

Artifacts are looked up in order: artifacts/ (official Kaggle results), then _outputs/dev/ (local quick build).
"""
