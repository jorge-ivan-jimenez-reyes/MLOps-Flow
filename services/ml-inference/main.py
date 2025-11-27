"""
ML Inference Service - FHIR Automapper
gRPC service that executes DSPy-based mapping from raw data to FHIR.
"""

import os
import json
import logging
from concurrent import futures
from datetime import datetime

import grpc
from prometheus_client import Counter, Histogram, start_http_server

# These will be generated from the proto file
from generated import mapper_pb2, mapper_pb2_grpc

from model_loader import ModelLoader
from mapper_engine import FHIRMapperEngine

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlops.svc.cluster.local:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "fhir-automapper")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------
PREDICTION_COUNT = Counter(
    "inference_predictions_total",
    "Total number of predictions",
    ["resource_type", "status"]
)
PREDICTION_LATENCY = Histogram(
    "inference_prediction_latency_seconds",
    "Prediction latency in seconds",
    ["resource_type"]
)

# -----------------------------------------------------------------------------
# gRPC Service Implementation
# -----------------------------------------------------------------------------
class MapperServicer(mapper_pb2_grpc.MapperServiceServicer):
    """gRPC service for FHIR mapping."""
    
    def __init__(self):
        self.model_loader = ModelLoader(
            mlflow_uri=MLFLOW_TRACKING_URI,
            model_name=MODEL_NAME
        )
        self.mapper_engine = FHIRMapperEngine(
            api_key=OPENAI_API_KEY,
            model=LLM_MODEL
        )
        self.current_model_version = "v1.0.0"
        
        # Try to load the latest model/prompt from MLflow
        try:
            prompt_config = self.model_loader.load_latest_model()
            if prompt_config:
                self.mapper_engine.update_prompt(prompt_config)
                self.current_model_version = self.model_loader.get_current_version()
                logger.info(f"Loaded model version: {self.current_model_version}")
        except Exception as e:
            logger.warning(f"Could not load model from MLflow: {e}. Using default prompts.")
    
    def PredictMapping(self, request, context):
        """Transform raw data to FHIR format."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Received prediction request for: {request.target_resource}")
            
            # Parse input
            raw_data = json.loads(request.raw_data_json)
            
            # Execute mapping
            result = self.mapper_engine.map_to_fhir(
                raw_data=raw_data,
                target_resource=request.target_resource
            )
            
            # Calculate latency
            latency = (datetime.utcnow() - start_time).total_seconds()
            
            # Update metrics
            PREDICTION_COUNT.labels(
                resource_type=request.target_resource,
                status="success"
            ).inc()
            PREDICTION_LATENCY.labels(
                resource_type=request.target_resource
            ).observe(latency)
            
            logger.info(f"Prediction completed in {latency:.3f}s")
            
            return mapper_pb2.PredictResponse(
                fhir_json=json.dumps(result["fhir"]),
                jsonata_expression=result.get("jsonata", ""),
                confidence=result.get("confidence", 0.95),
                model_version=self.current_model_version
            )
            
        except json.JSONDecodeError as e:
            PREDICTION_COUNT.labels(
                resource_type=request.target_resource,
                status="error"
            ).inc()
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid JSON: {str(e)}")
            return mapper_pb2.PredictResponse()
            
        except Exception as e:
            PREDICTION_COUNT.labels(
                resource_type=request.target_resource,
                status="error"
            ).inc()
            logger.error(f"Prediction error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return mapper_pb2.PredictResponse()
    
    def ReloadModel(self, request, context):
        """Reload model from MLflow."""
        try:
            logger.info(f"Reloading model: {request.model_uri}")
            
            if request.model_uri:
                prompt_config = self.model_loader.load_model(request.model_uri)
            else:
                prompt_config = self.model_loader.load_latest_model()
            
            if prompt_config:
                self.mapper_engine.update_prompt(prompt_config)
                self.current_model_version = self.model_loader.get_current_version()
                
                return mapper_pb2.ReloadResponse(
                    success=True,
                    active_version=self.current_model_version
                )
            else:
                return mapper_pb2.ReloadResponse(
                    success=False,
                    active_version=self.current_model_version
                )
                
        except Exception as e:
            logger.error(f"Model reload error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return mapper_pb2.ReloadResponse(success=False)
    
    def SubmitFeedback(self, request, context):
        """Forward feedback to trainer service (or store locally)."""
        try:
            logger.info(f"Received feedback for: {request.target_resource}")
            
            # For now, just acknowledge - in production, forward to ml-trainer
            # or store in a queue/database
            raw_data = json.loads(request.raw_data_json)
            correct_fhir = json.loads(request.correct_fhir_json)
            
            logger.info(f"Feedback stored: {len(request.raw_data_json)} bytes")
            
            return mapper_pb2.FeedbackResponse(
                success=True,
                message=f"Feedback received for {request.target_resource}"
            )
            
        except Exception as e:
            logger.error(f"Feedback error: {str(e)}")
            return mapper_pb2.FeedbackResponse(
                success=False,
                message=str(e)
            )

# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------
def serve():
    """Start the gRPC server."""
    # Start metrics server
    start_http_server(METRICS_PORT)
    logger.info(f"Metrics server started on port {METRICS_PORT}")
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    mapper_pb2_grpc.add_MapperServiceServicer_to_server(MapperServicer(), server)
    
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    
    logger.info(f"gRPC server started on port {GRPC_PORT}")
    logger.info(f"MLflow tracking: {MLFLOW_TRACKING_URI}")
    
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

