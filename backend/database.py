"""
Couche de persistance SQLite via SQLAlchemy.

Remplace historique.json — élimine les écritures concurrentes et prépare
la base pour de futures fonctionnalités (comptes utilisateurs, filtres, pagination).
"""

from __future__ import annotations

import json
import random
import string
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Float, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(__file__).parent / "coursegen.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class HistoriqueEntry(Base):
    __tablename__ = "historique"

    id = Column(String(6), primary_key=True)
    date = Column(DateTime, nullable=False, default=datetime.now)
    specialite = Column(String(200), nullable=False)
    niveau = Column(String(20), nullable=False)
    module = Column(String(200), nullable=False)
    chapitre = Column(String(300), nullable=False)
    moteur = Column(String(100), nullable=False)
    duree_secondes = Column(Float, nullable=False)
    is_pipeline_v2 = Column(Boolean, nullable=False, default=False, server_default="0")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(timespec="seconds") if self.date else None,
            "specialite": self.specialite,
            "niveau": self.niveau,
            "module": self.module,
            "chapitre": self.chapitre,
            "moteur": self.moteur,
            "duree_secondes": self.duree_secondes,
            "is_pipeline_v2": bool(self.is_pipeline_v2),
        }


# ─────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────

def generate_id(length: int = 6) -> str:
    """Génère un identifiant aléatoire alphanumérique."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore."""
    Base.metadata.create_all(bind=engine)


def migrate_db_schema() -> None:
    """Ajoute les colonnes manquantes si la DB existe déjà avec un ancien schéma."""
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(historique)")).fetchall()
        col_names = {row[1] for row in rows}
        if "is_pipeline_v2" not in col_names:
            conn.execute(text("ALTER TABLE historique ADD COLUMN is_pipeline_v2 INTEGER NOT NULL DEFAULT 0"))
            conn.commit()


def get_db():
    """Dépendance FastAPI — fournit une session DB et la ferme après la requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_history_entry(entry: HistoriqueEntry) -> None:
    """Sauvegarde une entrée d'historique (utilisé dans les routes streaming)."""
    db = SessionLocal()
    try:
        db.add(entry)
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────
# Migration depuis historique.json
# ─────────────────────────────────────────────

def migrate_from_json(json_path: Path) -> None:
    """Migre les entrées de historique.json vers SQLite (exécuté une seule fois au démarrage)."""
    if not json_path.exists():
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        db = SessionLocal()
        try:
            migrated = 0
            for e in entries:
                if db.get(HistoriqueEntry, e.get("id")):
                    continue  # déjà migré
                db.add(HistoriqueEntry(
                    id=e.get("id", generate_id()),
                    date=datetime.fromisoformat(e["date"]) if e.get("date") else datetime.now(),
                    specialite=e.get("specialite", ""),
                    niveau=e.get("niveau", ""),
                    module=e.get("module", ""),
                    chapitre=e.get("chapitre", ""),
                    moteur=e.get("moteur", ""),
                    duree_secondes=e.get("duree_secondes", 0.0),
                ))
                migrated += 1
            db.commit()
        finally:
            db.close()

        # Renomme le fichier JSON pour indiquer que la migration est faite
        json_path.rename(json_path.with_suffix(".json.migrated"))
        if migrated:
            print(f"[DB] {migrated} entrées migrées depuis {json_path.name}")

    except Exception as exc:
        print(f"[DB] Migration JSON ignorée : {exc}")
