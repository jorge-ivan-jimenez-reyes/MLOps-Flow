# FHIR Automapper - Plataforma MLOps en AWS EKS

## Proyecto Final - Machine Learning Operations

**Autor:** Jorge Jiménez  
**Fecha:** Noviembre 2025  
**Repositorio:** MLOps-Flow  
**Cloud Provider:** Amazon Web Services (AWS)

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Infraestructura AWS (Terraform)](#3-infraestructura-aws-terraform)
4. [Cluster Kubernetes (EKS)](#4-cluster-kubernetes-eks)
5. [Microservicios](#5-microservicios)
6. [Comunicación entre Servicios (gRPC)](#6-comunicación-entre-servicios-grpc)
7. [MLOps Pipeline](#7-mlops-pipeline)
8. [Observabilidad](#8-observabilidad)
9. [Despliegue y CI/CD](#9-despliegue-y-cicd)
10. [Comandos Útiles](#10-comandos-útiles)
11. [Estructura del Proyecto](#11-estructura-del-proyecto)

---

## 1. Resumen Ejecutivo

### 1.1 Objetivo del Proyecto

Desarrollar una **plataforma MLOps completa** desplegada en **AWS EKS** para un sistema de **FHIR Automapper** - un agente de IA que transforma automáticamente datos de salud dental crudos al estándar internacional **FHIR** (Fast Healthcare Interoperability Resources).

### 1.2 Tecnologías Principales

| Categoría | Tecnología |
|-----------|------------|
| **Cloud** | AWS (EKS, S3, RDS, ECR, VPC, ALB) |
| **IaC** | Terraform v1.0+ |
| **Orquestación** | Kubernetes v1.29 (EKS) |
| **ML Framework** | DSPy + OpenAI GPT-4 |
| **Experiment Tracking** | MLflow v2.9.2 |
| **Backend** | FastAPI + gRPC (Python 3.11) |
| **Frontend** | React + Vite + Tailwind CSS |
| **Observabilidad** | Prometheus + Grafana |
| **Base de Datos** | PostgreSQL 15.5 (RDS) |
| **Almacenamiento** | S3 (Artefactos MLflow) |

### 1.3 Capacidades del Sistema

- **Inferencia en Tiempo Real:** Transformación de datos crudos a FHIR en < 2 segundos
- **Feedback Loop:** Los usuarios pueden corregir mapeos incorrectos
- **Entrenamiento Automático:** Re-optimización de prompts con DSPy cuando hay suficiente feedback
- **Model Registry:** Versionado de modelos con MLflow
- **Auto-scaling:** HPA configurado para escalar según demanda
- **Monitoreo Completo:** Métricas, logs y dashboards en tiempo real

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Arquitectura

![Arquitectura MLOps](architecture/images/mlops_architecture.png)

### 2.2 Componentes Principales

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         VPC (10.0.0.0/16)                              │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    EKS CLUSTER (v1.29)                           │  │  │
│  │  │                                                                   │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │  │
│  │  │  │   Frontend  │  │ Gateway API │  │ ML Inference│              │  │  │
│  │  │  │   (React)   │──│  (FastAPI)  │──│   (gRPC)    │              │  │  │
│  │  │  │   2 pods    │  │   2 pods    │  │   2 pods    │              │  │  │
│  │  │  └─────────────┘  └─────────────┘  └──────┬──────┘              │  │  │
│  │  │                                           │                      │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌──────┴──────┐              │  │  │
│  │  │  │   MLflow    │  │ Prometheus  │  │ ML Trainer  │              │  │  │
│  │  │  │   Server    │  │   + Grafana │  │   (gRPC)    │              │  │  │
│  │  │  │   1 pod     │  │   2 pods    │  │   1 pod     │              │  │  │
│  │  │  └──────┬──────┘  └─────────────┘  └─────────────┘              │  │  │
│  │  │         │                                                        │  │  │
│  │  └─────────┼────────────────────────────────────────────────────────┘  │  │
│  │            │                                                           │  │
│  │  ┌─────────┴─────────┐  ┌─────────────────────┐                       │  │
│  │  │   RDS PostgreSQL  │  │        S3           │                       │  │
│  │  │   (db.t3.micro)   │  │  (MLflow Artifacts) │                       │  │
│  │  │   Port: 5432      │  │                     │                       │  │
│  │  └───────────────────┘  └─────────────────────┘                       │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    Application Load Balancer (ALB)                      │  │
│  │                    Ingress: internet-facing                             │  │
│  │                    /      → Frontend                                    │  │
│  │                    /api/* → Gateway API                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Flujo de Datos

```
Usuario → ALB → Frontend (React)
                    │
                    ▼
              Gateway API (FastAPI)
                    │
                    ▼ (gRPC)
              ML Inference ──────────────┐
                    │                    │
                    ▼                    ▼
              DSPy + LLM           MLflow (Model)
                    │
                    ▼
              FHIR Output
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
    Usuario acepta      Usuario corrige
         │                     │
         ▼                     ▼
       FIN               ML Trainer
                              │
                              ▼
                     DSPy Optimization
                              │
                              ▼
                     MLflow (New Model)
```

---

## 3. Infraestructura AWS (Terraform)

### 3.1 Recursos Provisionados

| Recurso | Especificación | Propósito |
|---------|----------------|-----------|
| **VPC** | CIDR: 10.0.0.0/16 | Red aislada |
| **Subnets** | 3 públicas + 3 privadas | Alta disponibilidad |
| **Internet Gateway** | 1 | Acceso a internet |
| **NAT Gateway** | 1 | Salida para subnets privadas |
| **EKS Cluster** | v1.29 | Orquestación de contenedores |
| **Node Group** | 2x t3.medium (escalable 1-4) | Workers |
| **RDS PostgreSQL** | db.t3.micro, v15.5 | Metadata MLflow + Feedback |
| **S3 Bucket** | fhir-automapper-dev-mlflow-artifacts | Artefactos ML |
| **ECR** | 4 repositorios | Imágenes Docker |

### 3.2 Configuración Terraform

**Archivo principal (`infrastructure/main.tf`):**

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "fhir-automapper"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# Módulos
module "vpc" { ... }
module "eks" { ... }
module "s3"  { ... }
module "rds" { ... }
module "ecr" { ... }
```

### 3.3 Variables de Configuración

| Variable | Valor Default | Descripción |
|----------|---------------|-------------|
| `aws_region` | us-east-1 | Región AWS |
| `environment` | dev | Ambiente |
| `vpc_cidr` | 10.0.0.0/16 | CIDR del VPC |
| `eks_cluster_version` | 1.29 | Versión Kubernetes |
| `eks_node_instance_types` | ["t3.medium"] | Tipo de instancias |
| `eks_node_desired_size` | 2 | Nodos deseados |
| `eks_node_min_size` | 1 | Mínimo de nodos |
| `eks_node_max_size` | 4 | Máximo de nodos |
| `db_name` | mlflow | Nombre de BD |

### 3.4 Outputs de Terraform

```bash
# Después de terraform apply:
eks_cluster_name     = "fhir-automapper-dev-eks"
eks_cluster_endpoint = "https://D03921005C8B66AF6F3E4020B31D5FC9.gr7.us-east-1.eks.amazonaws.com"
mlflow_bucket_name   = "fhir-automapper-dev-mlflow-artifacts"
rds_endpoint         = "fhir-automapper-dev-db.cnis2qc4s4u0.us-east-1.rds.amazonaws.com:5432"
ecr_repository_urls  = {
  "fhir-automapper/frontend"     = "177061867771.dkr.ecr.us-east-1.amazonaws.com/fhir-automapper/frontend"
  "fhir-automapper/gateway-api"  = "177061867771.dkr.ecr.us-east-1.amazonaws.com/fhir-automapper/gateway-api"
  "fhir-automapper/ml-inference" = "177061867771.dkr.ecr.us-east-1.amazonaws.com/fhir-automapper/ml-inference"
  "fhir-automapper/ml-trainer"   = "177061867771.dkr.ecr.us-east-1.amazonaws.com/fhir-automapper/ml-trainer"
}
```

---

## 4. Cluster Kubernetes (EKS)

### 4.1 Namespaces

| Namespace | Propósito |
|-----------|-----------|
| `mlops` | Microservicios de aplicación |
| `monitoring` | Prometheus + Grafana |
| `kube-system` | Componentes del sistema (AWS Load Balancer Controller) |

### 4.2 Workloads Desplegados

#### Namespace: `mlops`

| Deployment | Réplicas | Imagen | Puertos |
|------------|----------|--------|---------|
| `frontend` | 2 | fhir-automapper/frontend | 80 (HTTP) |
| `gateway-api` | 2 | fhir-automapper/gateway-api | 8000 (HTTP) |
| `ml-inference` | 2 | fhir-automapper/ml-inference | 50051 (gRPC), 8001 (metrics) |
| `ml-trainer` | 1 | fhir-automapper/ml-trainer | 50052 (gRPC), 8000 (metrics) |
| `mlflow` | 1 | ghcr.io/mlflow/mlflow:v2.9.2 | 5000 (HTTP) |

#### Namespace: `monitoring`

| Deployment | Réplicas | Imagen | Puertos |
|------------|----------|--------|---------|
| `prometheus` | 1 | prom/prometheus:v2.47.0 | 9090 |
| `grafana` | 1 | grafana/grafana:10.2.0 | 3000 |

### 4.3 Servicios Kubernetes

```yaml
# Services en namespace mlops
frontend       ClusterIP   80/TCP
gateway-api    ClusterIP   8000/TCP
ml-inference   ClusterIP   50051/TCP, 8001/TCP
ml-trainer     ClusterIP   50052/TCP, 8000/TCP
mlflow         ClusterIP   5000/TCP

# Services en namespace monitoring
prometheus     ClusterIP   9090/TCP
grafana        ClusterIP   3000/TCP
```

### 4.4 Ingress (AWS ALB)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fhir-automapper-ingress
  namespace: mlops
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: gateway-api
                port:
                  number: 8000
```

### 4.5 Horizontal Pod Autoscaler (HPA)

```yaml
# Gateway API HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

# ML Inference HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-inference
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### 4.6 Resource Limits

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| frontend | 50m | 100m | 64Mi | 128Mi |
| gateway-api | 100m | 250m | 256Mi | 512Mi |
| ml-inference | 250m | 500m | 512Mi | 1Gi |
| ml-trainer | 100m | 500m | 256Mi | 1Gi |
| mlflow | 250m | 500m | 512Mi | 1Gi |
| prometheus | 100m | 250m | 256Mi | 512Mi |
| grafana | 100m | 250m | 256Mi | 512Mi |

---

## 5. Microservicios

### 5.1 Frontend (React)

**Tecnologías:** React 18, Vite, Tailwind CSS, Nginx

**Funcionalidades:**
- Interfaz moderna para subir datos crudos
- Visualización del resultado FHIR generado
- Editor para corregir mapeos incorrectos
- Envío de feedback al sistema

**Estructura:**
```
services/frontend/
├── Dockerfile
├── nginx.conf
├── package.json
├── vite.config.js
├── tailwind.config.js
└── src/
    ├── App.jsx
    ├── main.jsx
    └── index.css
```

### 5.2 Gateway API (FastAPI)

**Tecnologías:** FastAPI, gRPC, Prometheus Client

**Endpoints:**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Métricas Prometheus |
| POST | `/api/predict` | Transformar datos a FHIR |
| POST | `/api/predict/file` | Transformar desde archivo |
| POST | `/api/feedback` | Enviar corrección |

**Código Principal:**
```python
@app.post("/api/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Transform raw data to FHIR format."""
    grpc_request = mapper_pb2.PredictRequest(
        raw_data_json=json.dumps(request.raw_data),
        target_resource=request.target_resource
    )
    
    stub, channel = get_inference_stub()
    response = stub.PredictMapping(grpc_request, timeout=30)
    
    return PredictResponse(
        fhir_json=json.loads(response.fhir_json),
        jsonata_expression=response.jsonata_expression,
        confidence=response.confidence,
        model_version=response.model_version
    )
```

### 5.3 ML Inference (gRPC + DSPy)

**Tecnologías:** gRPC, DSPy, OpenAI, MLflow Client

**RPCs Implementados:**

| RPC | Request | Response | Descripción |
|-----|---------|----------|-------------|
| `PredictMapping` | PredictRequest | PredictResponse | Mapeo a FHIR |
| `ReloadModel` | ReloadRequest | ReloadResponse | Recargar modelo |
| `SubmitFeedback` | FeedbackRequest | FeedbackResponse | Recibir feedback |

**Flujo de Inferencia:**
```
1. Recibe raw_data_json + target_resource
2. Carga prompt optimizado desde MLflow (si existe)
3. Ejecuta DSPy con LLM (GPT-4o-mini)
4. Genera JSONata expression
5. Aplica transformación
6. Retorna FHIR JSON + metadata
```

### 5.4 ML Trainer (Feedback Loop)

**Tecnologías:** gRPC, DSPy, MLflow, S3, PostgreSQL

**RPCs Implementados:**

| RPC | Request | Response | Descripción |
|-----|---------|----------|-------------|
| `SubmitFeedback` | FeedbackRequest | FeedbackResponse | Almacenar feedback |
| `TriggerTraining` | TrainingRequest | TrainingResponse | Iniciar entrenamiento |
| `GetTrainingStatus` | TrainingStatusRequest | TrainingStatusResponse | Estado actual |

**Flujo de Entrenamiento:**
```
1. Acumula feedback (mínimo 10 samples)
2. Trigger manual o automático
3. DSPy Teleprompter optimization
4. Log métricas en MLflow
5. Registra nuevo modelo
6. Notifica a ML Inference para reload
```

---

## 6. Comunicación entre Servicios (gRPC)

### 6.1 Definición Proto

**Archivo:** `protos/mapper.proto`

```protobuf
syntax = "proto3";
package mlops.mapper;

// Servicio de Mapeo (Inferencia)
service MapperService {
  rpc PredictMapping (PredictRequest) returns (PredictResponse);
  rpc ReloadModel (ReloadRequest) returns (ReloadResponse);
  rpc SubmitFeedback (FeedbackRequest) returns (FeedbackResponse);
}

// Servicio de Entrenamiento
service TrainerService {
  rpc SubmitFeedback (FeedbackRequest) returns (FeedbackResponse);
  rpc TriggerTraining (TrainingRequest) returns (TrainingResponse);
  rpc GetTrainingStatus (TrainingStatusRequest) returns (TrainingStatusResponse);
}

// Mensajes
message PredictRequest {
  string raw_data_json = 1;
  string target_resource = 2;
}

message PredictResponse {
  string fhir_json = 1;
  string jsonata_expression = 2;
  float confidence = 3;
  string model_version = 4;
}

message FeedbackRequest {
  string raw_data_json = 1;
  string correct_fhir_json = 2;
  string target_resource = 3;
}

message FeedbackResponse {
  bool success = 1;
  string message = 2;
}
```

### 6.2 Generación de Código

```bash
# Generar código Python desde proto
python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./services/gateway-api/generated \
  --grpc_python_out=./services/gateway-api/generated \
  ./protos/mapper.proto
```

---

## 7. MLOps Pipeline

### 7.1 MLflow Configuration

**Backend Store:** PostgreSQL (RDS)
```
postgresql://mlflow_admin:****@fhir-automapper-dev-db.cnis2qc4s4u0.us-east-1.rds.amazonaws.com:5432/mlflow
```

**Artifact Store:** S3
```
s3://fhir-automapper-dev-mlflow-artifacts/artifacts
```

### 7.2 Experiment Tracking

```python
import mlflow

mlflow.set_tracking_uri("http://mlflow:5000")

with mlflow.start_run(run_name="training_v2"):
    # Log parameters
    mlflow.log_param("num_samples", len(feedback_data))
    mlflow.log_param("training_type", "dspy_optimization")
    
    # Log metrics
    mlflow.log_metric("accuracy", 0.92)
    mlflow.log_metric("loss", 0.08)
    
    # Log model artifact
    mlflow.log_artifact("model_info.json")
    
    # Register model
    mlflow.register_model(
        f"runs:/{mlflow.active_run().info.run_id}/model",
        "fhir-automapper"
    )
```

### 7.3 Model Registry

| Stage | Descripción |
|-------|-------------|
| `None` | Modelo recién registrado |
| `Staging` | En pruebas |
| `Production` | Activo en inferencia |
| `Archived` | Versión anterior |

### 7.4 Feedback Loop Completo

```
┌──────────────────────────────────────────────────────────────────┐
│                     FEEDBACK LOOP MLOPS                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐   │
│   │ Usuario │───▶│ Frontend │───▶│ Gateway  │───▶│Inference│   │
│   └─────────┘    └──────────┘    └──────────┘    └────┬────┘   │
│        │                                              │         │
│        │         ┌──────────────────────────────────┘         │
│        │         ▼                                             │
│        │    ┌─────────┐                                        │
│        │    │  FHIR   │                                        │
│        │    │ Output  │                                        │
│        │    └────┬────┘                                        │
│        │         │                                             │
│        │    ┌────┴────┐                                        │
│        │    ▼         ▼                                        │
│        │ Correcto  Incorrecto                                  │
│        │    │         │                                        │
│        │    ▼         ▼                                        │
│        │   FIN    ┌───────┐                                    │
│        │          │Feedback│                                   │
│        │          └───┬───┘                                    │
│        │              │                                        │
│        │              ▼                                        │
│        │         ┌─────────┐                                   │
│        │         │ Trainer │                                   │
│        │         └────┬────┘                                   │
│        │              │                                        │
│        │    ┌─────────┴─────────┐                             │
│        │    ▼                   ▼                              │
│        │ Almacenar         ¿≥10 samples?                      │
│        │ en S3/DB               │                              │
│        │                   ┌────┴────┐                        │
│        │                   ▼         ▼                         │
│        │                  NO        SI                         │
│        │                   │         │                         │
│        │                   ▼         ▼                         │
│        │                Esperar   DSPy Train                   │
│        │                           │                           │
│        │                           ▼                           │
│        │                      ┌─────────┐                      │
│        │                      │ MLflow  │                      │
│        │                      │Registry │                      │
│        │                      └────┬────┘                      │
│        │                           │                           │
│        │                           ▼                           │
│        │                    Reload Model                       │
│        │                    en Inference                       │
│        │                           │                           │
│        └───────────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Observabilidad

### 8.1 Prometheus

**Configuración de Scraping:**

```yaml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

**Métricas Expuestas:**

| Servicio | Métrica | Tipo | Descripción |
|----------|---------|------|-------------|
| gateway-api | `gateway_requests_total` | Counter | Total de requests |
| gateway-api | `gateway_request_latency_seconds` | Histogram | Latencia |
| ml-inference | `inference_predictions_total` | Counter | Predicciones |
| ml-inference | `inference_prediction_latency_seconds` | Histogram | Latencia |
| ml-trainer | `trainer_feedback_received_total` | Counter | Feedback recibido |
| ml-trainer | `trainer_training_runs_total` | Counter | Entrenamientos |
| ml-trainer | `trainer_feedback_queue_size` | Gauge | Cola de feedback |

### 8.2 Grafana

**Datasource:** Prometheus (auto-configurado)

**Dashboard MLOps incluye:**
- Requests por segundo (RPS)
- Latencia p50, p95, p99
- Tasa de errores
- Estado de pods
- Feedback queue size
- Training runs

### 8.3 Acceso Local

```bash
# MLflow UI
kubectl port-forward svc/mlflow -n mlops 5000:5000
# Acceder: http://localhost:5000

# Grafana
kubectl port-forward svc/grafana -n monitoring 3000:3000
# Acceder: http://localhost:3000 (admin/admin123)

# Prometheus
kubectl port-forward svc/prometheus -n monitoring 9090:9090
# Acceder: http://localhost:9090
```

---

## 9. Despliegue y CI/CD

### 9.1 Makefile Targets

```makefile
# Docker
make docker-login      # Login a ECR
make build-all         # Build todas las imágenes (linux/amd64)
make push-all          # Push a ECR

# Kubernetes
make deploy-platform   # Deploy MLflow, Prometheus, Grafana
make deploy-apps       # Deploy microservicios
make deploy-all        # Deploy todo

# Utilities
make port-forward-mlflow   # Port forward MLflow
make port-forward-grafana  # Port forward Grafana
make logs-gateway          # Ver logs gateway
make logs-inference        # Ver logs inference
make logs-trainer          # Ver logs trainer
```

### 9.2 Build Multi-Arquitectura

```bash
# Build para EKS (AMD64) desde Mac M1/M2 (ARM64)
docker buildx build --platform linux/amd64 \
  -t fhir-automapper/gateway-api:latest \
  ./services/gateway-api --load
```

### 9.3 Flujo de Despliegue

```bash
# 1. Configurar AWS CLI
aws configure

# 2. Provisionar infraestructura
cd infrastructure
terraform init
terraform plan
terraform apply

# 3. Configurar kubectl
aws eks update-kubeconfig --region us-east-1 --name fhir-automapper-dev-eks

# 4. Verificar nodos
kubectl get nodes

# 5. Instalar AWS Load Balancer Controller
eksctl create iamserviceaccount \
  --cluster=fhir-automapper-dev-eks \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::177061867771:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=fhir-automapper-dev-eks \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# 6. Build y Push imágenes
make docker-login
make build-all
make push-all

# 7. Deploy
make deploy-all

# 8. Verificar
kubectl get pods -n mlops
kubectl get pods -n monitoring
kubectl get ingress -n mlops
```

---

## 10. Comandos Útiles

### 10.1 Kubernetes

```bash
# Ver todos los pods
kubectl get pods -A

# Ver pods en mlops
kubectl get pods -n mlops

# Ver logs de un servicio
kubectl logs -n mlops -l app=gateway-api -f

# Reiniciar deployment
kubectl rollout restart deployment gateway-api -n mlops

# Ver ingress y ALB URL
kubectl get ingress -n mlops

# Ejecutar shell en un pod
kubectl exec -it -n mlops deploy/gateway-api -- /bin/sh

# Ver eventos
kubectl get events -n mlops --sort-by='.lastTimestamp'

# Escalar deployment
kubectl scale deployment ml-inference -n mlops --replicas=4
```

### 10.2 Terraform

```bash
# Inicializar
terraform init

# Ver plan
terraform plan

# Aplicar cambios
terraform apply

# Destruir infraestructura
terraform destroy

# Ver outputs
terraform output
```

### 10.3 AWS CLI

```bash
# Verificar identidad
aws sts get-caller-identity

# Actualizar kubeconfig
aws eks update-kubeconfig --region us-east-1 --name fhir-automapper-dev-eks

# Login a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 177061867771.dkr.ecr.us-east-1.amazonaws.com

# Ver password de RDS
aws ssm get-parameter --name "/dev/rds/fhir-automapper-dev-db/password" --with-decryption --query "Parameter.Value" --output text
```

---

## 11. Estructura del Proyecto

```
MLOps-Flow/
├── docs/
│   └── architecture/
│       ├── diagram.py           # Generador de diagrama
│       ├── requirements.txt     # Deps para diagrama
│       └── images/
│           └── mlops_architecture.png
│
├── infrastructure/              # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── vpc/
│       ├── eks/
│       ├── s3/
│       ├── rds/
│       └── ecr/
│
├── k8s-manifests/              # Kubernetes manifests
│   ├── platform/
│   │   ├── namespace.yaml
│   │   ├── mlflow.yaml
│   │   ├── mlflow-secret.yaml
│   │   ├── prometheus.yaml
│   │   ├── grafana.yaml
│   │   └── grafana-dashboard.yaml
│   └── apps/
│       ├── frontend.yaml
│       ├── gateway-api.yaml
│       ├── ml-inference.yaml
│       ├── ml-trainer.yaml
│       └── ingress.yaml
│
├── protos/                     # gRPC definitions
│   └── mapper.proto
│
├── services/                   # Microservicios
│   ├── frontend/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   ├── package.json
│   │   └── src/
│   │       ├── App.jsx
│   │       ├── main.jsx
│   │       └── index.css
│   │
│   ├── gateway-api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── generated/
│   │       ├── mapper_pb2.py
│   │       └── mapper_pb2_grpc.py
│   │
│   ├── ml-inference/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── model_loader.py
│   │   ├── mapper_engine.py
│   │   └── generated/
│   │
│   └── ml-trainer/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── main.py
│       └── generated/
│
├── Makefile                    # Automatización
├── LICENSE
├── .gitignore
└── README.md
```

---

## Apéndice A: Costos Estimados AWS

| Servicio | Tipo | Costo Estimado/mes |
|----------|------|-------------------|
| EKS Cluster | Control Plane | ~$72 |
| EC2 (2x t3.medium) | Node Group | ~$60 |
| RDS (db.t3.micro) | PostgreSQL | ~$15 |
| S3 | Storage | ~$1-5 |
| NAT Gateway | Networking | ~$32 |
| ALB | Load Balancer | ~$16 |
| **Total Estimado** | | **~$200/mes** |

> **Nota:** Para reducir costos en desarrollo, considerar usar `t3.small` y apagar recursos cuando no se usen.

---

## Apéndice B: Troubleshooting Común

### Error: ImagePullBackOff
```bash
# Verificar que la imagen existe en ECR
aws ecr describe-images --repository-name fhir-automapper/gateway-api

# Verificar que los nodos tienen permisos
kubectl describe pod <pod-name> -n mlops
```

### Error: DNS no resuelve EKS endpoint
```bash
# Reconectar kubeconfig
aws eks update-kubeconfig --region us-east-1 --name fhir-automapper-dev-eks
```

### Error: Ingress sin ADDRESS
```bash
# Verificar AWS Load Balancer Controller
kubectl get pods -n kube-system | grep aws-load-balancer

# Ver logs del controller
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

### Error: gRPC connection refused
```bash
# Verificar que el servicio de inferencia está corriendo
kubectl get svc ml-inference -n mlops
kubectl get endpoints ml-inference -n mlops
```

---

## Apéndice C: Referencias

- [FHIR Standard](https://www.hl7.org/fhir/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [AWS EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [gRPC Python](https://grpc.io/docs/languages/python/)

---

**Documento generado para el Proyecto Final de MLOps - Universidad Panamericana**



