# 물리적(Production) 아키텍처 설계

생성일: 2025-12-01


목표: 이 문서는 PythonProject4 애플리케이션을 운영 환경에서 안전하고 안정적으로 운영하기 위한 물리적(인프라) 아키텍처 권장안을 제공합니다. 가용성(HA), 확장성, 보안, 백업/복구, 모니터링, 배포(CI/CD)를 포함합니다.

## 전체 요약

AWS 기반 컨테이너 아키텍처(CDN → ALB → ECS/EKS 컨테이너)와 RDS(Aurora/MySQL, Multi‑AZ)를 중심으로 설계합니다. 정적 자산 및 업로드 이미지는 S3/CloudFront로 오프로드하고, 비동기 작업은 Celery(또는 SQS) + Redis로 처리합니다. 보안은 VPC 분리·HTTPS(ACM)·WAF·IAM 최소권한으로, 가용성은 Auto Scaling과 RDS Multi‑AZ/리드 리플리카로 보장합니다. 운영은 GitHub Actions 기반 CI/CD로 Docker 이미지를 빌드해 ECR에 푸시하고 ECS/EKS로 배포(롤링/블루그린)합니다.

핵심 포인트: CDN, ALB(WAF), 컨테이너(App), RDS(다중 AZ), S3(정적/업로드), Redis(캐시/큐), 모니터링(Sentry/Prometheus/Grafana), 자동화된 CI/CD.


---

## 1. 요약 아키텍처(권장 - AWS를 예로 듦)

- DNS: `Route 53`  
- CDN: `CloudFront` (정적 리소스 `static/` 및 이미지 `uploads/` 캐싱)  
- Load Balancer: `ALB` (HTTPS 종료, HTTP->HTTPS 리다이렉트, WAF 연결)  
- Application: 컨테이너화된 Flask 앱(예: `ECS` 서비스 또는 `EKS` 클러스터) — Nginx + Gunicorn/uvicorn(ASGI) 사용  
- Background workers: `Celery` + `Redis`(ElastiCache) 또는 AWS SQS + Lambda  
- Database: `Amazon RDS (MySQL / Aurora MySQL)` — Multi-AZ, 자동 백업, PITR  
- Cache / Session: `ElastiCache (Redis)`  
- Object storage: `S3` (이미지 업로드, 정적 파일) + 버전/수명주기 정책  
- 파일 공유(필요 시): `EFS` (공유 파일시스템) — 권장하지 않음(가능하면 S3 사용)  
- Monitoring & Logging: `CloudWatch`, `Prometheus/Grafana`, `Sentry`(에러)  
- CI/CD: `GitHub Actions` -> 빌드 Docker 이미지 -> `ECR` -> 배포(Blue/Green 혹은 Rolling)

---

## 2. 컴포넌트 상세 및 매핑 (프로젝트 파일 기준)

- 사용자(브라우저, 모바일) → `CloudFront`(CDN) → `ALB` → 컨테이너(Nginx + Gunicorn)  
  - `templates/`, `static/`, `view_post.js` 등은 CDN 캐시 가능  
- 컨테이너 내부: `app.routes`, `app.routes_auth`가 라우트 처리 → `app.services`(권장) → `app.dm_interfaces`(Repository) → `RDS`  
- 파일 업로드: 요청 수신 후 S3에 저장(직접 업로드 또는 서버→S3 업로드), DB에는 메타(파일명, 순서)만 저장(`post_images` 테이블)  
- 비동기 작업: 영상/이미지 처리, 알림, 통계 집계 등은 `Celery` 워커에서 처리(큐: Redis 혹은 SQS)  

파일 매핑 표 (예시):

- `app/models.py` → RDS 테이블 (DDL: `diagrams/dm_database_schema.sql`)  
- `app/dm_interfaces.py` → repository contract (DM 계층)  
- `app/schemas.py`, `app/hci_interfaces.py` → HCI 레이어(컨트롤러/DTO/검증/렌더러)  
- `scripts/` → 운영 툴(PlantUML 렌더러, PDF 생성 등)

---

## 3. 네트워크 / 보안

- 네트워크 분리: `VPC` 내 Public Subnet(Load Balancer)과 Private Subnet(app, DB, cache)를 분리  
- Security Groups: 최소 권한 접근 원칙(포트: 80/443 → ALB, ALB→App: 8080, App→RDS: 3306 등)  
- HTTPS: ACM에서 인증서 관리 및 ALB에 연결  
- WAF: OWASP 룰셋 적용(알려진 취약점 차단)  
- IAM: S3, ECR, RDS 접근은 역할 기반(Roles)으로만 허용  
- 데이터 암호화: RDS 암호화(at-rest), S3 암호화, 전송 암호화(TLS)  

---

## 4. 가용성 / 확장성

- Application: Auto Scaling Group (ECS Service AutoScale 또는 EKS HPA)으로 수평 확장  
- Database: RDS Multi-AZ(Primary + Sync replica), 리드 리플리카로 읽기 확장  
- Redis(ElastiCache): 복제/클러스터 모드, 노드 교체 시 무중단  
- S3: 내구성/가용성 확보(객체 저장소)  

---

## 5. 백업 / 복구

- RDS 자동 스냅샷 + 수동 스냅샷(주기적)  
- S3 버전 관리 + 수명주기 규칙(오브젝트 보존/삭제 정책)  
- 정기적 스키마/데이터 덤프(예: 전체 덤프)와 복구 연습 문서화  

---

## 6. 로깅 / 모니터링

- 에러 추적: `Sentry` (애플리케이션 예외, 성능 트래킹)  
- 지표 수집: `Prometheus`(application + infra) + `Grafana` 대시보드  
- 로그 중앙화: `Fluentd`/`FluentBit` → `CloudWatch`/ELK(ElasticSearch)  
- 알람: CPU/Memory/Latency/Errors 기준 알람(CloudWatch / PagerDuty 연동)

---

## 7. CI/CD 및 배포 전략

- GitHub Actions pipeline:  
  1) Lint / Unit tests  
  2) Build Docker image  
  3) Push to `ECR` (or Docker Hub)  
  4) Deploy: update ECS service or apply K8s manifests (kubectl/helm)  
- 배포 방식: Blue/Green 또는 Rolling update 권장(무중단 배포)  

---

## 8. 운영 고려사항 & 권장 인스턴스/사이징 (초기)

- 소규모(프로토타입):  
  - App: 2x t3.small (or t3.medium) 컨테이너 인스턴스  
  - DB: db.t3.medium Multi-AZ  
  - Redis: cache.t3.medium (클러스터 없음)  
  - Storage: S3 + EBS gp3 (로그/일시적 파일)  
- 중대형(트래픽 증가 시): AutoScaling (min 2, max 10+), RDS 리드 리플리카, ElastiCache 클러스터

---

## 9. 비용 최적화 팁

- S3 + CloudFront로 정적/이미지 트래픽 오프로드  
- 예약 인스턴스/저장소 절약 플랜으로 RDS 비용 절감  
- 권장: 개발/스테이징/프로덕션 분리(리소스 태깅으로 비용 추적)

---

## 10. 마이그레이션 / 적용 체크리스트

1. 컨테이너화: `Dockerfile` 준비 및 로컬 이미지 테스트  
2. IaC(권장): `Terraform` 또는 `CloudFormation`으로 인프라 정의  
3. RDS/prod DB 준비 및 스키마 적용(마이그레이션 단계 계획)  
4. S3 버킷/권한 설정 및 업로드 경로 정리  
5. CI/CD 파이프라인 구성(자동 빌드/배포)  
6. 모니터링/알람/로그 파이프라인 설정  

---

## 11. 추가 옵션(비클라우드 환경 등)

- 온프레미스: 리버스 프록시(Nginx), HAProxy, L4 LB, VM으로 애플리케이션 배포(권장: 컨테이너화 후 k8s on-prem)  
- PaaS(간단): Heroku / Render / Azure App Service — 운영 부담 최소, 규모 확장 제약 존재

---

## 12. 참고: 간단한 배포 흐름 (명령 예시)

```bash
# 빌드 & 푸시 (GitHub Actions 권장 자동화)
docker build -t myorg/pythonproject4:latest .
docker tag myorg/pythonproject4:latest <account>.dkr.ecr.<region>.amazonaws.com/pythonproject4:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/pythonproject4:latest

# ECS/EKS 배포는 각각의 CLI/도구 사용(aws ecs update-service / kubectl apply)
```

---

파일: `diagrams/physical_architecture.puml`을 PlantUML로 렌더하면 배포 다이어그램을 얻을 수 있습니다.
