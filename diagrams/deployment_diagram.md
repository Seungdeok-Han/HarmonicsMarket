# Deployment Diagram — Mapping & Notes

파일: `diagrams/deployment_diagram.puml`

요약: 이 PlantUML 파일은 `diagrams/physical_architecture.md`의 권장 AWS 아키텍처(CDN → ALB → ECS/EKS 컨테이너 → RDS + Redis + S3)를 배치(Deployment) 관점에서 표현합니다. 주요 컴포넌트와 코드 매핑은 아래와 같습니다.

- **CloudFront (CDN)** : `static/`, `templates/`, `uploads/` 등 정적 자산을 캐시합니다.
- **ALB / WAF** : HTTPS 종료(ACM) 및 OWASP 규칙 적용 — 애플리케이션으로의 진입점.
- **ECS / EKS (App Service)** : 컨테이너로 배포되는 Flask 앱(`app/routes.py`, `app/routes_auth.py`, `app/__init__.py`) — Nginx + Gunicorn/uvicorn 권장.
- **Worker (Celery)** : 비동기 작업(이미지 처리, 통계, 알림) — `scripts/` 및 백그라운드 작업 관련 코드 매핑.
- **RDS (Aurora / MySQL)** : `app/models.py`에 매핑되는 영속화 계층(테이블: users, instrument_posts, post_images 등).
- **ElastiCache (Redis)** : 캐시, 세션, Celery 브로커 대체 가능성.
- **S3** : 이미지/업로드 오브젝트 저장 — DB에는 메타만 저장(`post_images` 테이블).
- **ECR / GitHub Actions** : CI/CD 파이프라인(이미지 빌드 → ECR 푸시 → ECS/EKS 배포).
- **Monitoring / Logging** : Prometheus/Grafana, Sentry, CloudWatch로 지표/로그/에러 추적.

렌더링: 로컬에서 PlantUML JAR 또는 VSCode PlantUML extension으로 `deployment_diagram.puml`을 렌더하십시오. 예:

```powershell
# (로컬 plantuml.jar 사용 예)
java -jar plantuml.jar -tpng diagrams/deployment_diagram.puml -o diagrams

# 또는 VSCode PlantUML: 파일을 열고 "Preview Current Diagram" 실행
```

운영 팁: 실제 배포 템플릿(Terraform/CloudFormation/Helm)은 이 배치 다이어그램을 기준으로 리소스(Subnet, Security Group, ALB listeners, IAM roles, S3 bucket policy 등)를 생성하면 됩니다.
