"""Chemins du dépôt, relatifs à la racine (aucun chemin absolu)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "processed"
RES = ROOT / "results"
FIG = ROOT / "figures"
