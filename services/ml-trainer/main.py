"""
ML Trainer Service - FHIR Automapper
Handles feedback collection and model retraining with DSPy optimization.
"""

import os
import json
import logging
import time
from datetime import datetime
from concurrent import futures
from typing import List, Dict, Any

import grpc
import mlflow
import boto3
from prometheus_client import Counter, Gauge, start_http_server

from generated import mapper_pb2, mapper_pb2_grpc

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
GRPC_PORT = int(os.getenv("GRPC_PORT", "50052"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
S3_BUCKET = os.getenv("S3_BUCKET", "fhir-automapper-dev-mlflow-artifacts")
FEEDBACK_TABLE = os.getenv("FEEDBACK_TABLE", "feedback_data")
MIN_FEEDBACK_FOR_TRAINING = int(os.getenv("MIN_FEEDBACK_FOR_TRAINING", "10"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Database config (for feedback storage)
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mlflow")
DB_USER = os.getenv("DB_USER", "mlflow")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

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
FEEDBACK_RECEIVED = Counter(
    "trainer_feedback_received_total",
    "Total feedback samples received"
)
TRAINING_RUNS = Counter(
    "trainer_training_runs_total",
    "Total training runs executed",
    ["status"]
)
FEEDBACK_QUEUE_SIZE = Gauge(
    "trainer_feedback_queue_size",
    "Current size of feedback queue"
)
MODEL_VERSION = Gauge(
    "trainer_current_model_version",
    "Current model version number"
)

# -----------------------------------------------------------------------------
# Feedback Storage (In-Memory for demo, use DB in production)
# -----------------------------------------------------------------------------
class FeedbackStore:
    """Simple in-memory feedback store. In production, use PostgreSQL or S3."""
    
    def __init__(self):
        self.feedback_data: List[Dict[str, Any]] = []
        self.s3_client = None
        self._init_s3()
    
    def _init_s3(self):
        """Initialize S3 client for persistent storage."""
        try:
            self.s3_client = boto3.client('s3')
            logger.info("S3 client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize S3: {e}")
    
    def add_feedback(self, raw_data: dict, correct_fhir: dict, target_resource: str) -> bool:
        """Add feedback sample to the store."""
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": raw_data,
            "correct_fhir": correct_fhir,
            "target_resource": target_resource
        }
        
        self.feedback_data.append(feedback_entry)
        FEEDBACK_RECEIVED.inc()
        FEEDBACK_QUEUE_SIZE.set(len(self.feedback_data))
        
        # Persist to S3
        self._persist_to_s3(feedback_entry)
        
        logger.info(f"Feedback added. Total samples: {len(self.feedback_data)}")
        return True
    
    def _persist_to_s3(self, feedback_entry: dict):
        """Persist feedback to S3 for durability."""
        if not self.s3_client:
            return
        
        try:
            key = f"feedback/{feedback_entry['target_resource']}/{feedback_entry['timestamp']}.json"
            self.s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=json.dumps(feedback_entry),
                ContentType='application/json'
            )
            logger.debug(f"Feedback persisted to S3: {key}")
        except Exception as e:
            logger.warning(f"Could not persist to S3: {e}")
    
    def get_training_data(self) -> List[Dict[str, Any]]:
        """Get all feedback data for training."""
        return self.feedback_data.copy()
    
    def clear(self):
        """Clear feedback after training."""
        self.feedback_data = []
        FEEDBACK_QUEUE_SIZE.set(0)
    
    def size(self) -> int:
        """Get current feedback count."""
        return len(self.feedback_data)


# -----------------------------------------------------------------------------
# DSPy Trainer (Mock for demo)
# -----------------------------------------------------------------------------
class DSPyTrainer:
    """
    Handles DSPy prompt optimization based on feedback.
    In production, this would use actual DSPy optimization.
    """
    
    def __init__(self):
        self.current_version = 1
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
    def train(self, feedback_data: List[Dict[str, Any]]) -> dict:
        """
        Train/optimize the DSPy model with feedback data.
        
        Returns:
            dict with training results
        """
        logger.info(f"Starting training with {len(feedback_data)} samples")
        
        try:
            # Start MLflow run
            with mlflow.start_run(run_name=f"training_v{self.current_version + 1}"):
                
                # Log parameters
                mlflow.log_param("num_samples", len(feedback_data))
                mlflow.log_param("training_type", "dspy_optimization")
                
                # Simulate training (in production, use DSPy teleprompter)
                if OPENAI_API_KEY:
                    # Real DSPy training would go here
                    # from dspy.teleprompt import BootstrapFewShot
                    # teleprompter = BootstrapFewShot(metric=your_metric)
                    # optimized_program = teleprompter.compile(your_program, trainset=feedback_data)
                    pass
                
                # Mock training metrics
                metrics = {
                    "accuracy": 0.85 + (len(feedback_data) * 0.001),  # Improves with more data
                    "loss": 0.15 - (len(feedback_data) * 0.001),
                    "samples_used": len(feedback_data)
                }
                
                # Log metrics
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                
                # Create and log model artifact
                model_info = {
                    "version": self.current_version + 1,
                    "trained_at": datetime.utcnow().isoformat(),
                    "samples": len(feedback_data),
                    "metrics": metrics,
                    "prompt_template": self._generate_optimized_prompt(feedback_data)
                }
                
                # Save model artifact
                artifact_path = "/tmp/model_info.json"
                with open(artifact_path, 'w') as f:
                    json.dump(model_info, f, indent=2)
                mlflow.log_artifact(artifact_path)
                
                # Register model
                mlflow.register_model(
                    f"runs:/{mlflow.active_run().info.run_id}/model_info.json",
                    "fhir-automapper"
                )
                
                self.current_version += 1
                MODEL_VERSION.set(self.current_version)
                TRAINING_RUNS.labels(status="success").inc()
                
                logger.info(f"Training completed. New version: {self.current_version}")
                
                return {
                    "success": True,
                    "version": self.current_version,
                    "metrics": metrics
                }
                
        except Exception as e:
            TRAINING_RUNS.labels(status="error").inc()
            logger.error(f"Training failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_optimized_prompt(self, feedback_data: List[Dict[str, Any]]) -> str:
        """Generate an optimized prompt based on feedback examples."""
        # In production, DSPy would optimize this automatically
        examples = []
        for sample in feedback_data[:5]:  # Use first 5 as examples
            examples.append(f"Input: {json.dumps(sample['raw_data'])[:100]}...")
            examples.append(f"Output: {json.dumps(sample['correct_fhir'])[:100]}...")
        
        return f"""You are a FHIR mapping expert. Transform the input data to valid FHIR format.

Examples from user feedback:
{chr(10).join(examples)}

Now transform the following input to FHIR format:"""


# -----------------------------------------------------------------------------
# gRPC Service Implementation
# -----------------------------------------------------------------------------
class TrainerServicer(mapper_pb2_grpc.TrainerServiceServicer):
    """gRPC service for training operations."""
    
    def __init__(self):
        self.feedback_store = FeedbackStore()
        self.trainer = DSPyTrainer()
    
    def SubmitFeedback(self, request, context):
        """Receive and store feedback."""
        try:
            raw_data = json.loads(request.raw_data_json)
            correct_fhir = json.loads(request.correct_fhir_json)
            
            success = self.feedback_store.add_feedback(
                raw_data=raw_data,
                correct_fhir=correct_fhir,
                target_resource=request.target_resource
            )
            
            # Check if we should trigger training
            message = "Feedback received"
            if self.feedback_store.size() >= MIN_FEEDBACK_FOR_TRAINING:
                message = f"Feedback received. {self.feedback_store.size()} samples ready for training."
            
            return mapper_pb2.FeedbackResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return mapper_pb2.FeedbackResponse(
                success=False,
                message=str(e)
            )
    
    def TriggerTraining(self, request, context):
        """Manually trigger model training."""
        feedback_data = self.feedback_store.get_training_data()
        
        if len(feedback_data) < MIN_FEEDBACK_FOR_TRAINING:
            return mapper_pb2.TrainingResponse(
                success=False,
                message=f"Not enough feedback. Have {len(feedback_data)}, need {MIN_FEEDBACK_FOR_TRAINING}",
                model_version=""
            )
        
        result = self.trainer.train(feedback_data)
        
        if result["success"]:
            self.feedback_store.clear()
            return mapper_pb2.TrainingResponse(
                success=True,
                message=f"Training completed with metrics: {result['metrics']}",
                model_version=f"v{result['version']}"
            )
        else:
            return mapper_pb2.TrainingResponse(
                success=False,
                message=result.get("error", "Training failed"),
                model_version=""
            )
    
    def GetTrainingStatus(self, request, context):
        """Get current training status."""
        return mapper_pb2.TrainingStatusResponse(
            feedback_count=self.feedback_store.size(),
            min_feedback_required=MIN_FEEDBACK_FOR_TRAINING,
            current_model_version=f"v{self.trainer.current_version}",
            ready_for_training=self.feedback_store.size() >= MIN_FEEDBACK_FOR_TRAINING
        )


# Also implement MapperService for feedback endpoint compatibility
class MapperServicer(mapper_pb2_grpc.MapperServiceServicer):
    """Implements feedback endpoint for MapperService."""
    
    def __init__(self, trainer_servicer: TrainerServicer):
        self.trainer_servicer = trainer_servicer
    
    def SubmitFeedback(self, request, context):
        """Forward to trainer servicer."""
        return self.trainer_servicer.SubmitFeedback(request, context)


# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------
def serve():
    """Start the gRPC server."""
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    trainer_servicer = TrainerServicer()
    mapper_pb2_grpc.add_TrainerServiceServicer_to_server(trainer_servicer, server)
    mapper_pb2_grpc.add_MapperServiceServicer_to_server(
        MapperServicer(trainer_servicer), server
    )
    
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    
    logger.info(f"ML Trainer gRPC server started on port {GRPC_PORT}")
    logger.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    logger.info(f"Min feedback for training: {MIN_FEEDBACK_FOR_TRAINING}")
    
    try:
        while True:
            time.sleep(86400)  # Keep server running
    except KeyboardInterrupt:
        server.stop(0)
        logger.info("Server stopped")


if __name__ == "__main__":
    serve()




