# =============================================================================
# FHIR Automapper - Makefile
# =============================================================================

AWS_ACCOUNT_ID := 177061867771
AWS_REGION := us-east-1
ECR_REGISTRY := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------
.PHONY: docker-login
docker-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)

.PHONY: build-gateway
build-gateway:
	docker build -t fhir-automapper/gateway-api:latest ./services/gateway-api

.PHONY: build-inference
build-inference:
	docker build -t fhir-automapper/ml-inference:latest ./services/ml-inference

.PHONY: build-all
build-all: build-gateway build-inference

.PHONY: push-gateway
push-gateway:
	docker tag fhir-automapper/gateway-api:latest $(ECR_REGISTRY)/fhir-automapper/gateway-api:latest
	docker push $(ECR_REGISTRY)/fhir-automapper/gateway-api:latest

.PHONY: push-inference
push-inference:
	docker tag fhir-automapper/ml-inference:latest $(ECR_REGISTRY)/fhir-automapper/ml-inference:latest
	docker push $(ECR_REGISTRY)/fhir-automapper/ml-inference:latest

.PHONY: push-all
push-all: push-gateway push-inference

.PHONY: deploy-images
deploy-images: docker-login build-all push-all

# -----------------------------------------------------------------------------
# Kubernetes
# -----------------------------------------------------------------------------
.PHONY: deploy-platform
deploy-platform:
	kubectl apply -f k8s-manifests/platform/namespace.yaml
	kubectl apply -f k8s-manifests/platform/mlflow-secret.yaml
	kubectl apply -f k8s-manifests/platform/mlflow.yaml
	kubectl apply -f k8s-manifests/platform/prometheus.yaml
	kubectl apply -f k8s-manifests/platform/grafana.yaml

.PHONY: deploy-apps
deploy-apps:
	kubectl apply -f k8s-manifests/apps/

.PHONY: deploy-all
deploy-all: deploy-platform deploy-apps

# -----------------------------------------------------------------------------
# Local Development
# -----------------------------------------------------------------------------
.PHONY: run-gateway-local
run-gateway-local:
	cd services/gateway-api && uvicorn main:app --reload --port 8000

.PHONY: run-inference-local
run-inference-local:
	cd services/ml-inference && python main.py

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
.PHONY: port-forward-mlflow
port-forward-mlflow:
	kubectl port-forward svc/mlflow -n mlops 5000:5000

.PHONY: port-forward-grafana
port-forward-grafana:
	kubectl port-forward svc/grafana -n monitoring 3000:3000

.PHONY: logs-gateway
logs-gateway:
	kubectl logs -n mlops -l app=gateway-api -f

.PHONY: logs-inference
logs-inference:
	kubectl logs -n mlops -l app=ml-inference -f

