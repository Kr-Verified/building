from pydantic import BaseModel, Field

class ApplicationCreate(BaseModel):
    user_id: int
    project_id: int
    role_id: int
    message: str | None = None

class RecommendationItem(BaseModel):
    user_id: int | None = None
    project_id: int | None = None
    name: str | None = None
    title: str | None = None
    score: float
    skill_score: float
    role_score: float
    time_score: float
    domain_score: float
    style_score: float
    team_atmosphere_score: float
    reason: str

class UserCreate(BaseModel):
    name: str
    email: str
    bio: str | None = None
    experience_level: int = Field(ge=1, le=5)
    available_hours: int = Field(ge=0)
    collaboration_style: str
    preferred_role_id: int
    interest_domain: str
    preferred_team_atmosphere: str

class ProjectCreate(BaseModel):
    creator_id: int
    title: str
    description: str | None = None
    domain: str
    difficulty: int = Field(ge=1, le=5)
    required_hours: int = Field(ge=1)
    max_members: int = Field(ge=1)
    team_atmosphere: str
    desired_collaboration_style: str

class ProjectUpdate(BaseModel):
    creator_id: int | None = None
    title: str | None = None
    description: str | None = None
    domain: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    required_hours: int | None = Field(default=None, ge=1)
    max_members: int | None = Field(default=None, ge=1)
    team_atmosphere: str | None = None
    desired_collaboration_style: str | None = None
