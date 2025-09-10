PodML Project Overview
🎯 Goal
You are building PodML, a web platform where users can:
Authenticate with AWS Cognito.
Upload datasets (CSV).
Create configurations (select dataset, X and Y columns, choose a model).
Schedule training jobs linked to configurations.
(Later) Run ML training inside Kubernetes pods, with proper isolation and scalable resource requests.
The platform should be structured, modular, and scalable, with OOP-style backend services for AWS/Cognito, database, storage, and Kubernetes scheduling.
⚙️ Stack
Frontend
Next.js (App Router) with client components.
Amplify Auth for login/register/verification.
Custom hooks (useAmplifyUser) for user context (username, sub, email, display name).
UI system:
Button (variants: primary, ghost).
Input with labels and hints.
Card components.
Spinner.
Unified styles in globals.css (calm white/grey theme, green accents, responsive layout).
Backend
FastAPI with:
auth_router for Cognito auth check (email existence).
database_router for configurations and training jobs.
Future jobs_router for Kubernetes scheduling.
DatabaseService: SQLite (later Aurora/RDS), handles schema creation and CRUD for configurations and jobs.
CognitoService: wraps AWS Cognito IDP client for server-side lookups.
CognitoJWTVerifier: verifies ID tokens via Cognito JWKS.
StorageService: for file uploads (local dev, S3 later).
Kubernetes: template Job YAMLs to run training inside pods, using environment variables for dataset, output URIs, and params.
🗄 Database Schema (SQLite MVP)
Configurations
id (UUID PK)
owner_sub (Cognito user sub)
name
dataset_uri
x_column, y_column
model_type (default: linear_regression)
hyperparams_json
created_at, updated_at
Training Jobs
id (UUID PK)
owner_sub
configuration_id (FK → configurations)
status (queued | running | succeeded | failed)
k8s_job_name
model_uri
metrics_json
resources_json
created_at, updated_at
Indexes exist on owner_sub and configuration_id.
🔐 Auth Flow
Frontend
Uses Amplify Auth for register/login/verify flows.
After login, gets Cognito ID token with fetchAuthSession().
Sends this as Authorization: Bearer <idToken> when calling backend APIs.
For dev, can use X-Debug-Sub.
Backend
router_auth.get_current_sub checks:
X-Debug-Sub if allow_debug_sub=true.
Otherwise verifies JWT with CognitoJWTVerifier (using JWKS URL).
Returns the user sub, used to scope DB queries.
📑 Example Flows
Create Config
Frontend (CreateJobPage):
Form with name, dataset URI (CSV path), X col, Y col.
Calls createConfiguration API with JWT.
Backend:
database_router.create_configuration validates and inserts record.
Returns saved config (scoped to owner_sub).
List Configurations
Dashboard fetches /api/database/configurations with JWT.
Backend returns only rows for current user (WHERE owner_sub = ?).
Training Job (planned)
User clicks “Start Training” from dashboard.
Backend:
Inserts row in training_jobs.
Creates a Kubernetes Job manifest from template:
apiVersion: batch/v1
kind: Job
metadata:
  name: train-<job_id>
  labels:
    podml/user: <sub>
    podml/job_id: <job_id>
    podml/config_id: <config_id>
spec:
  template:
    spec:
      containers:
      - name: trainer
        image: podml-trainer:latest
        env:
          - name: DATASET_URL
            value: <presigned_get>
          - name: OUTPUT_MODEL_URL
            value: <presigned_put_model>
          - name: OUTPUT_METRICS_URL
            value: <presigned_put_metrics>
          - name: X_COLUMN
            value: <x_col>
          - name: Y_COLUMN
            value: <y_col>
          - name: FIT_INTERCEPT
            value: "true"
        resources:
          requests: { cpu: "100m", memory: "256Mi" }
          limits: { cpu: "1", memory: "1Gi" }
Kubernetes schedules job, updates status, backend polls/updates training_jobs.
🚀 Deployment Roadmap
MVP
Local SQLite DB.
Local file storage for CSV.
Linear regression only (scikit-learn).
Debug auth with X-Debug-Sub.
Next
Replace file storage with S3.
Replace SQLite with Aurora or RDS.
Implement Kubernetes Job scheduling with Python SDK (kubernetes).
Add more models (logistic regression, trees, neural nets).
Add dynamic resource requests.
Future
Multi-tenant scalability (thousands of jobs/day).
RBAC and per-user quotas.
Proper job monitoring and metrics dashboards.
CI/CD pipeline with CDK.
🐞 Current Issues / Fixes
JWT verification: needed proper cognito_jwks_url in settings; fixed by adding property.
Invalid audience: backend must check against correct client_id.
CORS: updated FastAPI middleware with allow_origins=settings.cors_origins.
DB empty results: confirmed owner_sub matches inserted records.