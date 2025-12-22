# Deployment Technical Specifications

생성일: 2025-12-01

이 문서는 PythonProject4 시스템을 운영하기 위한 권장 하드웨어, 소프트웨어, 통신(네트워크) 구성요소에 대한 기술 스펙입니다. 세 가지 규모(프로토타입 / 중간 / 대규모)를 제시하고, 각각의 리소스, 운영·백업·성능 목표 및 보안 설정을 포함합니다. 이 스펙은 AWS 기반 배포(제안된 `diagrams/physical_architecture.md`)를 기준으로 작성되었습니다.

요약 요구사항
- SLA 목표: 99.9% 이상(비즈니스 요구에 따라 조정)
- 응답 시간(애플리케이션): p95 < 500ms, p99 < 2s (일반 읽기 요청)
- 데이터 일관성: 쓰기 작업은 강한 일관성(트랜잭션 기반). 읽기 확장 시 eventual consistency 허용(리드 리플리카)
- 백업 RTO 목표: < 1시간(데이터베이스 복구), RPO: 15분(주요 테이블 스냅샷/로그)

---

## 1. 규모별 권장 하드웨어·서비스

A. 소규모 / 프로토타입
- 트래픽/사용자: 수십 ~ 수백 DAU
- 컨테이너: 2 replicas (ECS Fargate or small EC2 instances)
  - CPU: 0.5 vCPU (512m) per task
  - Memory: 1 GB per task
- 데이터베이스: Amazon RDS MySQL / Aurora Serverless (개발) 또는 `db.t3.medium` (Multi-AZ 권장)
  - 스토리지: gp3 20–50 GB, IOPS baseline (3,000) 충분
- 캐시/브로커: ElastiCache Redis — cache.t3.small 또는 managed Redis (single node)
- 스토리지: S3 (Standard) — 정적 + 업로드
- 모니터링: AWS CloudWatch 기본, Sentry(에러) 무료 플랜

B. 중간 규모 (권장 초기 프로덕션)
- 트래픽/사용자: 수천 DAU
- 컨테이너: ECS Fargate tasks (or EKS) with auto-scaling
  - CPU: 1 vCPU per task
  - Memory: 2–4 GB per task
  - 최소 2 tasks (AZ별 분산) — Auto Scaling min 2, max 10
- 데이터베이스: Amazon RDS Aurora MySQL (provisioned) — db.r5.large 또는 db.t3.medium (비용/성능 고려)
  - 스토리지: gp3 100–500 GB, IOPS: 3k–10k (워크로드에 따라)
  - Multi-AZ 복제, 자동 백업(주기적 스냅샷)
- 캐시/브로커: ElastiCache Redis cluster (replication, 2 nodes) or Redis Cluster
  - 메모리: 4–8 GB per node
- 스토리지: S3 + CloudFront, S3 버전관리 & 수명주기 규칙(보존 정책)
- 오브젝트 처리: Celery workers on Fargate or EC2 (worker tasks 2–4)
- 로깅/모니터링: Prometheus + Grafana (self-hosted or managed), CloudWatch, Sentry

C. 대규모 (고부하·고가용성)
- 트래픽/사용자: 수만 ~ 그 이상 DAU
- 컨테이너: EKS with HPA & Cluster Autoscaler, node groups across AZs
  - pod resources: 2+ vCPU, 4+ GB memory (API), use autoscaling based on CPU/RPS
  - min nodes per AZ: 2
- 데이터베이스: Aurora MySQL / Aurora Global DB, writer + reader replicas
  - instance: db.r5.xlarge+ (or Aurora serverless v2 with scaling)
  - Storage: gp3 / io2 (high IOPS) depending on OLTP needs
- 캐시/브로커: ElastiCache Redis Cluster (sharded), multi-AZ, 3+ shards
- 파일 처리: Dedicated worker pools (Spot + On-demand mix), autoscaled
- 네트워크: Private link / VPC endpoints for S3, RDS, ECR
- 모니터링: Managed Prometheus & Grafana, ELK or OpenSearch for logs, tracing (Jaeger/X-Ray)

---

## 2. 소프트웨어 스택 (권장)

- OS / Container base
  - Base image: `python:3.11-slim` (보안 업데이트 준수)
  - Host OS (if EC2): Amazon Linux 2 / Ubuntu 22.04 LTS
- Runtime
  - Python 3.11
  - Web framework: Flask (현재 코드 기반) — 권장: upgrade to latest patch
  - WSGI/ASGI: Gunicorn (with gevent) or Uvicorn + Gunicorn (ASGI) if async needed
- App server / reverse proxy
  - Nginx as reverse proxy inside container or sidecar (caching, gzip)
- Worker / Task queue
  - Celery with Redis broker (or SQS + Lambda for serverless alternative)
  - Celery beat for scheduled jobs (or EventBridge)
- Data storage
  - RDS Aurora MySQL (compatible), use InnoDB, utf8mb4 charset
  - Migrations: Alembic
- Cache / Broker
  - Redis (ElastiCache) for sessions, rate-limiting, view dedupe, Celery broker
- Object storage / CDN
  - S3 (Standard / Intelligent-Tiering) + CloudFront (signed URLs for private content)
- Container / Orchestration
  - Docker images, built with multi-stage Dockerfile
  - Registry: ECR
  - Orchestration: ECS (Fargate) or EKS (Kubernetes)
- CI/CD
  - GitHub Actions workflow: lint -> tests -> build image -> push to ECR -> deploy (ECS update / kubectl / helm)
- Secrets & Config
  - AWS Secrets Manager or Parameter Store for DB credentials and API keys
  - IAM roles for service principals (least privilege)
- Observability
  - Tracing: AWS X-Ray or Jaeger
  - Metrics: Prometheus (exporter) + Grafana
  - Error tracking: Sentry

---

## 3. 통신(네트워크) 구성 및 프로토콜

- VPC 설계
  - CIDR: `10.0.0.0/16` (조정 가능)
  - Public Subnets: 하나 이상 AZ에 각 1개 (ALB)
  - Private Subnets: App, Worker, RDS, Redis 각각 격리 (각 AZ마다)
  - NAT Gateway: 프라이빗 서브넷의 아웃바운드 연결
- 보안 그룹 / 네트워크 ACL
  - ALB: Ingress 80/443 from 0.0.0.0/0 (HTTPS enforced), Egress: App security group
  - App: Ingress from ALB on 8080 (or container port), Egress to RDS:3306, Redis:6379, S3 via VPC endpoint
  - RDS: Ingress only from App security group, port 3306
  - Redis: Ingress only from App & Worker security groups, port 6379
  - SSH: block from Internet (use Bastion/Session Manager)
- TLS / HTTPS
  - TLS termination at ALB (ACM-managed certs). Enforce HTTP->HTTPS redirect.
  - Backend TLS (optional): TLS between ALB and App for end-to-end encryption if required.
- Load Balancer & Health checks
  - ALB target health check: `/health` endpoint, 10s interval, 2 unhealthy, 2 healthy thresholds
  - Connection settings: keepalive timeout 60s, idle timeout aligned with Gunicorn
- CDN / S3
  - Use CloudFront with origin access identity / origin access control to restrict direct S3 access
  - Cache-control: static assets long TTL (e.g., 7 days) with cache-busting; upload/avatars may be shorter
- Internal communication patterns
  - HTTP/HTTPS REST for API
  - Long-running jobs: Celery with Redis (AMQP-like semantics via Redis lists) or SQS
  - Service-to-service calls: use mTLS or IAM roles if crossing accounts

---

## 4. 성능·용량 계획 지표

- 목표 지표
  - RPS: 계획에 따라 설정 (예: 중간 규모 200–1000 RPS 정상 처리 가능)
  - 평균 응답 시간: p95 < 500ms
  - DB connections: pool sizing, max_connections = (db instance mem / connection mem) 약 산정

- 캐시 전략
  - Read-heavy endpoints: cache results in Redis with short TTL (30–120s)
  - Feed generation: precompute for heavy users in Redis zset and update on events

- DB scaling
  - Vertical scaling for writer, read replicas for read scaling
  - Using Aurora: reader autoscaling + global DB for cross-region

---

## 5. 백업·복구·운영(운영 정책)

- RDS
  - Automated daily snapshots + point-in-time recovery (PITR) enabled
  - Snapshot retention: 7–30 days(요건에 따름)
  - Test restore 절차 문서화(분기별)
- S3
  - Versioning ON for uploads, lifecycle rules (move to IA / Glacier after X days)
- Redis
  - Snapshot RDB / AOF 설정(관리형 ElastiCache 자동 복제 사용 권장)
- 운영 권한
  - IAM roles and least privilege per service
- 모니터링·알림
  - 알람: high error rate (>1% 5m), high latency (p95 > threshold), CPU/Memory > 80%
  - PagerDuty / Slack 연동

---

## 6. 보안 (요약)

- 네트워크 레벨: VPC, Subnet 분리, Security Groups, WAF
- 애플리케이션: 입력 검증, XSS/CSRF 방어, 파일 업로드 스캐닝(확장자/멀웨어)
- 데이터 보호: RDS encryption at-rest, S3 encryption, TLS in-transit
- 비밀관리: Secrets Manager, rotate (DB credentials rotation)
- 감사로그: CloudTrail, CloudWatch Logs

---

## 7. 운영 체크리스트(배포 전)

1. Infrastructure as Code 준비(Terraform/CloudFormation)
2. CI 파이프라인(Lint -> Tests -> Build -> Push -> Deploy) 점검
3. 모니터링/알람 룰 설정 및 테스트 알림
4. 백업 정책 및 복원 테스트 문서화
5. 보안 점검(포트, IAM, S3 권한)

---

## 8. 참고값 예시(요금·사이징 근사치)

- 중간 규모 예시 월비용(대략):
  - App (Fargate / small cluster) : $200–800
  - Aurora (db.r5.large x 1 writer + 1 reader): $600–1500
  - ElastiCache Redis (2 nodes): $200–600
  - S3 / CloudFront: 트래픽 의존
  - Monitoring / Logging: $50–300

총합: $1k–3k+/월 (트래픽/저장소에 따라 크게 변동)

---

원하시면 이 스펙을 기반으로 다음을 생성해 드립니다:
- IaC 템플릿(간단한 Terraform 예제)
- `Dockerfile`/`helm`/`ecs` 배포 템플릿 스켈레톤
- 상세 용량 산정(예: RPS 기반 수식) 및 비용 시뮬레이션

원하시는 후속 작업을 알려주세요.
