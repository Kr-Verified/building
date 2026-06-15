import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.db import Base, engine, SessionLocal
from app import models

DATA_DIR = ROOT / "data"
DB_FILE = ROOT / "team_building.db"

TABLES = [
    (models.Role, "roles.csv"),
    (models.Skill, "skills.csv"),
    (models.User, "users.csv"),
    (models.UserSkill, "user_skills.csv"),
    (models.Project, "projects.csv"),
    (models.ProjectSkill, "project_skills.csv"),
    (models.ProjectRole, "project_roles.csv"),
    (models.Application, "applications.csv"),
]

def normalize_record(record: dict) -> dict:
    result = {}
    for key, value in record.items():
        if pd.isna(value):
            result[key] = None
        else:
            result[key] = value
    return result

def main():
    if DB_FILE.exists():
        DB_FILE.unlink()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        for model_class, filename in TABLES:
            path = DATA_DIR / filename
            df = pd.read_csv(path)
            records = [model_class(**normalize_record(row)) for row in df.to_dict("records")]
            db.add_all(records)
            db.commit()
            print(f"{filename}: {len(records)}개 삽입 완료")
    finally:
        db.close()

    print("DB seed 완료: team_building.db")

if __name__ == "__main__":
    main()
