# AI 기반 프로젝트 팀 빌딩 플랫폼 - FastAPI Web App

## 실행 방법

```bash
pip install -r requirements.txt
python scripts/seed_db.py
uvicorn app.main:app --reload
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

웹 관리 화면:

```text
http://127.0.0.1:8000/web/users
http://127.0.0.1:8000/web/projects
```

## ML 모델 사용 방법

Colab에서 저장한 모델 파일 `team_recommendation_model.pkl`을 아래 경로에 넣으세요.

```text
app/ml/team_recommendation_model.pkl
```

모델 파일이 없으면 서비스가 멈추지 않도록 규칙 기반 fallback 점수를 사용합니다.

## 주요 API

```text
GET  /users
GET  /projects
GET  /projects/{project_id}
POST /projects
PATCH /projects/{project_id}
DELETE /projects/{project_id}
GET  /projects/{project_id}/recommendations?top_n=10
GET  /users/{user_id}/recommendations?top_n=10
POST /applications
```
