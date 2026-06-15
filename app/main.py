from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import Base, engine, get_db
from app.services.recommendation_service import recommend_projects_for_user, recommend_users_for_project

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Team Building Platform")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def ensure_user_exists(db: Session, user_id: int):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user

def get_project_or_404(db: Session, project_id: int):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return project

def delete_project_with_dependencies(db: Session, project: models.Project):
    db.query(models.ProjectSkill).filter(models.ProjectSkill.project_id == project.id).delete()
    db.query(models.ProjectRole).filter(models.ProjectRole.project_id == project.id).delete()
    db.query(models.Application).filter(models.Application.project_id == project.id).delete()
    db.query(models.RecommendationResult).filter(models.RecommendationResult.project_id == project.id).delete()
    db.delete(project)

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).limit(10).all()
    projects = db.query(models.Project).limit(10).all()
    return templates.TemplateResponse("index.html", {"request": request, "users": users, "projects": projects})



@app.get("/web/users", response_class=HTMLResponse)
def web_users_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.id.desc()).all()
    roles = db.query(models.Role).order_by(models.Role.id.asc()).all()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "roles": roles,
        "edit_user": None,
    })

@app.get("/web/users/{user_id}/edit", response_class=HTMLResponse)
def web_user_edit_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    edit_user = ensure_user_exists(db, user_id)
    users = db.query(models.User).order_by(models.User.id.desc()).all()
    roles = db.query(models.Role).order_by(models.Role.id.asc()).all()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "roles": roles,
        "edit_user": edit_user,
    })

@app.post("/web/users")
def web_create_user(
    name: str = Form(...),
    email: str = Form(...),
    bio: str = Form(""),
    experience_level: int = Form(...),
    available_hours: int = Form(...),
    collaboration_style: str = Form(...),
    preferred_role_id: int = Form(...),
    interest_domain: str = Form(...),
    preferred_team_atmosphere: str = Form(...),
    db: Session = Depends(get_db),
):
    exists = db.query(models.User).filter(models.User.email == email).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")

    user = models.User(
        name=name,
        email=email,
        bio=bio,
        experience_level=experience_level,
        available_hours=available_hours,
        collaboration_style=collaboration_style,
        preferred_role_id=preferred_role_id,
        interest_domain=interest_domain,
        preferred_team_atmosphere=preferred_team_atmosphere,
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/web/users", status_code=303)

@app.post("/web/users/{user_id}/edit")
def web_update_user(
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
    bio: str = Form(""),
    experience_level: int = Form(...),
    available_hours: int = Form(...),
    collaboration_style: str = Form(...),
    preferred_role_id: int = Form(...),
    interest_domain: str = Form(...),
    preferred_team_atmosphere: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    duplicated = (
        db.query(models.User)
        .filter(models.User.email == email, models.User.id != user_id)
        .first()
    )
    if duplicated:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")

    user.name = name
    user.email = email
    user.bio = bio
    user.experience_level = experience_level
    user.available_hours = available_hours
    user.collaboration_style = collaboration_style
    user.preferred_role_id = preferred_role_id
    user.interest_domain = interest_domain
    user.preferred_team_atmosphere = preferred_team_atmosphere

    db.commit()
    return RedirectResponse(url="/web/users", status_code=303)

@app.post("/web/users/{user_id}/delete")
def web_delete_user(user_id: int, db: Session = Depends(get_db)):
    user = ensure_user_exists(db, user_id)

    # 사용자가 만든 프로젝트까지 안전하게 삭제한다.
    created_projects = db.query(models.Project).filter(models.Project.creator_id == user_id).all()
    for project in created_projects:
        delete_project_with_dependencies(db, project)

    # 사용자와 직접 연결된 데이터 삭제
    db.query(models.UserSkill).filter(models.UserSkill.user_id == user_id).delete()
    db.query(models.Application).filter(models.Application.user_id == user_id).delete()
    db.query(models.RecommendationResult).filter(models.RecommendationResult.user_id == user_id).delete()
    db.delete(user)
    db.commit()

    return RedirectResponse(url="/web/users", status_code=303)

@app.get("/web/projects", response_class=HTMLResponse)
def web_projects_page(request: Request, db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id.desc()).all()
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects,
        "users": users,
        "edit_project": None,
    })

@app.get("/web/projects/{project_id}/edit", response_class=HTMLResponse)
def web_project_edit_page(request: Request, project_id: int, db: Session = Depends(get_db)):
    edit_project = get_project_or_404(db, project_id)
    projects = db.query(models.Project).order_by(models.Project.id.desc()).all()
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects,
        "users": users,
        "edit_project": edit_project,
    })

@app.post("/web/projects")
def web_create_project(
    creator_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    domain: str = Form(...),
    difficulty: int = Form(...),
    required_hours: int = Form(...),
    max_members: int = Form(...),
    team_atmosphere: str = Form(...),
    desired_collaboration_style: str = Form(...),
    db: Session = Depends(get_db),
):
    ensure_user_exists(db, creator_id)
    project = models.Project(
        creator_id=creator_id,
        title=title,
        description=description,
        domain=domain,
        difficulty=difficulty,
        required_hours=required_hours,
        max_members=max_members,
        team_atmosphere=team_atmosphere,
        desired_collaboration_style=desired_collaboration_style,
    )
    db.add(project)
    db.commit()
    return RedirectResponse(url="/web/projects", status_code=303)

@app.post("/web/projects/{project_id}/edit")
def web_update_project(
    project_id: int,
    creator_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    domain: str = Form(...),
    difficulty: int = Form(...),
    required_hours: int = Form(...),
    max_members: int = Form(...),
    team_atmosphere: str = Form(...),
    desired_collaboration_style: str = Form(...),
    db: Session = Depends(get_db),
):
    project = get_project_or_404(db, project_id)
    ensure_user_exists(db, creator_id)

    project.creator_id = creator_id
    project.title = title
    project.description = description
    project.domain = domain
    project.difficulty = difficulty
    project.required_hours = required_hours
    project.max_members = max_members
    project.team_atmosphere = team_atmosphere
    project.desired_collaboration_style = desired_collaboration_style

    db.commit()
    return RedirectResponse(url="/web/projects", status_code=303)

@app.post("/web/projects/{project_id}/delete")
def web_delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    delete_project_with_dependencies(db, project)
    db.commit()
    return RedirectResponse(url="/web/projects", status_code=303)

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.post("/users")
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
    user = models.User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/projects")
def get_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@app.post("/projects")
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    ensure_user_exists(db, payload.creator_id)
    project = models.Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@app.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    return get_project_or_404(db, project_id)

@app.patch("/projects/{project_id}")
def update_project(project_id: int, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    data = payload.model_dump(exclude_unset=True)
    if "creator_id" in data:
        ensure_user_exists(db, data["creator_id"])
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project

@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    delete_project_with_dependencies(db, project)
    db.commit()
    return {"detail": "프로젝트가 삭제되었습니다."}

@app.get("/projects/{project_id}/recommendations")
def api_recommend_users(project_id: int, top_n: int = 10, db: Session = Depends(get_db)):
    results = recommend_users_for_project(db, project_id, top_n)
    if not results:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없거나 추천 결과가 없습니다.")
    return results

@app.get("/users/{user_id}/recommendations")
def api_recommend_projects(user_id: int, top_n: int = 10, db: Session = Depends(get_db)):
    results = recommend_projects_for_user(db, user_id, top_n)
    if not results:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없거나 추천 결과가 없습니다.")
    return results

@app.get("/web/projects/{project_id}/recommendations", response_class=HTMLResponse)
def web_recommend_users(request: Request, project_id: int, top_n: int = 10, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    results = recommend_users_for_project(db, project_id, top_n)
    return templates.TemplateResponse("project_recommendations.html", {
        "request": request,
        "project": project,
        "results": results,
    })

@app.get("/web/users/{user_id}/recommendations", response_class=HTMLResponse)
def web_recommend_projects(request: Request, user_id: int, top_n: int = 10, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    results = recommend_projects_for_user(db, user_id, top_n)
    return templates.TemplateResponse("user_recommendations.html", {
        "request": request,
        "user": user,
        "results": results,
    })

@app.post("/applications")
def create_application(payload: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    app_row = models.Application(**payload.model_dump(), status="pending")
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return app_row

@app.post("/web/applications")
def web_apply(
    user_id: int = Form(...),
    project_id: int = Form(...),
    role_id: int = Form(...),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    app_row = models.Application(
        user_id=user_id,
        project_id=project_id,
        role_id=role_id,
        status="pending",
        message=message,
    )
    db.add(app_row)
    db.commit()
    return RedirectResponse(url=f"/web/users/{user_id}/recommendations", status_code=303)
