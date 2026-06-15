from sqlalchemy.orm import Session
from app import models

FEATURE_COLUMNS = [
    "skill_match_score",
    "average_skill_level",
    "role_match",
    "time_match_score",
    "domain_match",
    "experience_gap",
    "collaboration_style_match",
    "team_atmosphere_match",
]

def build_feature_dict(db: Session, user: models.User, project: models.Project) -> dict[str, float]:
    user_skill_rows = db.query(models.UserSkill).filter(models.UserSkill.user_id == user.id).all()
    project_skill_rows = db.query(models.ProjectSkill).filter(models.ProjectSkill.project_id == project.id).all()
    project_role_rows = db.query(models.ProjectRole).filter(models.ProjectRole.project_id == project.id).all()

    user_skill_level = {row.skill_id: row.level for row in user_skill_rows}

    total_importance = sum(row.importance for row in project_skill_rows)
    matched_importance = sum(
        row.importance for row in project_skill_rows
        if row.skill_id in user_skill_level
    )
    skill_match_score = matched_importance / total_importance if total_importance else 0.0

    matched_levels = [
        user_skill_level[row.skill_id]
        for row in project_skill_rows
        if row.skill_id in user_skill_level
    ]
    average_skill_level = sum(matched_levels) / len(matched_levels) if matched_levels else 0.0

    required_role_ids = {row.role_id for row in project_role_rows}
    role_match = 1.0 if user.preferred_role_id in required_role_ids else 0.0

    time_match_score = min(user.available_hours / project.required_hours, 1.0) if project.required_hours else 0.0
    domain_match = 1.0 if user.interest_domain == project.domain else 0.0
    experience_gap = float(project.difficulty - user.experience_level)
    collaboration_style_match = 1.0 if user.collaboration_style == project.desired_collaboration_style else 0.0
    team_atmosphere_match = 1.0 if user.preferred_team_atmosphere == project.team_atmosphere else 0.0

    return {
        "skill_match_score": round(skill_match_score, 4),
        "average_skill_level": round(average_skill_level, 4),
        "role_match": role_match,
        "time_match_score": round(time_match_score, 4),
        "domain_match": domain_match,
        "experience_gap": experience_gap,
        "collaboration_style_match": collaboration_style_match,
        "team_atmosphere_match": team_atmosphere_match,
    }
