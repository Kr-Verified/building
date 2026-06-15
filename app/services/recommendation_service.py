from pathlib import Path
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from app import models
from app.services.feature_builder import FEATURE_COLUMNS, build_feature_dict

MODEL_PATH = Path(__file__).resolve().parents[1] / "ml" / "team_recommendation_model.pkl"

class RuleBasedFallbackModel:
    def predict(self, X):
        if isinstance(X, pd.DataFrame):
            rows = X.to_dict("records")
        else:
            rows = [dict(zip(FEATURE_COLUMNS, row)) for row in X]

        scores = []
        for row in rows:
            score = 0
            score += row["skill_match_score"] * 35
            score += min(row["average_skill_level"] / 5, 1) * 15
            score += row["role_match"] * 15
            score += row["time_match_score"] * 10
            score += row["domain_match"] * 10
            score += max(0, 1 - abs(row["experience_gap"]) / 4) * 5
            score += row["collaboration_style_match"] * 5
            score += row["team_atmosphere_match"] * 5
            scores.append(min(max(score, 0), 100))
        return scores

def load_model():
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    print(f"[WARN] 모델 파일이 없습니다: {MODEL_PATH}. 규칙 기반 fallback을 사용합니다.")
    return RuleBasedFallbackModel()

model = load_model()

def make_reason(feature: dict[str, float]) -> str:
    reasons = []
    if feature["skill_match_score"] >= 0.75:
        reasons.append("요구 기술과 보유 기술의 일치도가 높음")
    elif feature["skill_match_score"] >= 0.45:
        reasons.append("일부 요구 기술과 일치함")

    if feature["average_skill_level"] >= 4:
        reasons.append("요구 기술에 대한 숙련도가 높음")
    elif feature["average_skill_level"] >= 3:
        reasons.append("요구 기술에 대한 기본 숙련도를 보유함")

    if feature["role_match"] == 1:
        reasons.append("선호 역할이 프로젝트 요구 역할과 일치함")
    if feature["time_match_score"] >= 1.0:
        reasons.append("주간 활동 가능 시간이 충분함")
    if feature["domain_match"] == 1:
        reasons.append("관심 분야와 프로젝트 분야가 일치함")
    if -1 <= feature["experience_gap"] <= 1:
        reasons.append("프로젝트 난이도와 경험 수준이 적절함")
    if feature["collaboration_style_match"] == 1:
        reasons.append("협업 스타일이 잘 맞음")
    if feature["team_atmosphere_match"] == 1:
        reasons.append("선호 팀 분위기가 프로젝트 분위기와 일치함")

    return " · ".join(reasons) if reasons else "일부 조건이 프로젝트 요구사항과 부분적으로 일치함"

def _score_feature(feature: dict[str, float]) -> float:
    X = pd.DataFrame([{col: feature[col] for col in FEATURE_COLUMNS}])
    return float(model.predict(X)[0])

def _format_result(feature: dict[str, float], score: float, reason: str) -> dict:
    return {
        "score": round(score, 2),
        "skill_score": round(feature["skill_match_score"] * 100, 2),
        "role_score": round(feature["role_match"] * 100, 2),
        "time_score": round(min(feature["time_match_score"], 1) * 100, 2),
        "domain_score": round(feature["domain_match"] * 100, 2),
        "style_score": round(feature["collaboration_style_match"] * 100, 2),
        "team_atmosphere_score": round(feature["team_atmosphere_match"] * 100, 2),
        "reason": reason,
    }

def recommend_users_for_project(db: Session, project_id: int, top_n: int = 10) -> list[dict]:
    project = db.get(models.Project, project_id)
    if not project:
        return []

    users = db.query(models.User).filter(models.User.id != project.creator_id).all()
    results = []

    for user in users:
        feature = build_feature_dict(db, user, project)
        score = _score_feature(feature)
        reason = make_reason(feature)
        item = _format_result(feature, score, reason)
        item.update({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "experience_level": user.experience_level,
            "available_hours": user.available_hours,
        })
        results.append(item)

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

def recommend_projects_for_user(db: Session, user_id: int, top_n: int = 10) -> list[dict]:
    user = db.get(models.User, user_id)
    if not user:
        return []

    projects = db.query(models.Project).all()
    results = []

    for project in projects:
        feature = build_feature_dict(db, user, project)
        score = _score_feature(feature)
        reason = make_reason(feature)
        item = _format_result(feature, score, reason)
        item.update({
            "project_id": project.id,
            "title": project.title,
            "domain": project.domain,
            "difficulty": project.difficulty,
            "required_hours": project.required_hours,
            "team_atmosphere": project.team_atmosphere,
        })
        results.append(item)

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
