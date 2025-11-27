"""
Gateway API - FHIR Automapper
FastAPI service that receives HTTP requests and forwards them to the gRPC inference service.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

import grpc
from generated import mapper_pb2, mapper_pb2_grpc

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
INFERENCE_SERVICE_HOST = os.getenv("INFERENCE_SERVICE_HOST", "ml-inference")
INFERENCE_SERVICE_PORT = os.getenv("INFERENCE_SERVICE_PORT", "50051")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="FHIR Automapper Gateway",
    description="API Gateway for the FHIR Automapper MLOps system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class PredictRequest(BaseModel):
    raw_data: dict
    target_resource: str = "Patient"

class PredictResponse(BaseModel):
    fhir_json: dict
    jsonata_expression: Optional[str] = None
    confidence: float
    model_version: str
    processing_time_ms: float

class FeedbackRequest(BaseModel):
    raw_data: dict
    correct_fhir: dict
    target_resource: str = "Patient"

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    inference_service: str

# -----------------------------------------------------------------------------
# gRPC Client
# -----------------------------------------------------------------------------
def get_inference_stub():
    """Create gRPC channel and stub for inference service."""
    channel = grpc.insecure_channel(f"{INFERENCE_SERVICE_HOST}:{INFERENCE_SERVICE_PORT}")
    stub = mapper_pb2_grpc.MapperServiceStub(channel)
    return stub, channel

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    inference_status = "unknown"
    
    try:
        stub, channel = get_inference_stub()
        # Try to connect (will fail gracefully if service is down)
        grpc.channel_ready_future(channel).result(timeout=2)
        inference_status = "connected"
        channel.close()
    except Exception as e:
        inference_status = f"disconnected: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        inference_service=inference_status
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Transform raw data to FHIR format.
    
    This endpoint receives raw healthcare data and returns the FHIR-formatted version.
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Received predict request for resource: {request.target_resource}")
        
        # Create gRPC request
        grpc_request = mapper_pb2.PredictRequest(
            raw_data_json=json.dumps(request.raw_data),
            target_resource=request.target_resource
        )
        
        # Call inference service
        stub, channel = get_inference_stub()
        try:
            response = stub.PredictMapping(grpc_request, timeout=30)
        finally:
            channel.close()
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update metrics
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="success").inc()
        REQUEST_LATENCY.labels(method="POST", endpoint="/predict").observe(processing_time / 1000)
        
        logger.info(f"Prediction completed in {processing_time:.2f}ms")
        
        return PredictResponse(
            fhir_json=json.loads(response.fhir_json),
            jsonata_expression=response.jsonata_expression,
            confidence=response.confidence,
            model_version=response.model_version,
            processing_time_ms=processing_time
        )
        
    except grpc.RpcError as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="error").inc()
        logger.error(f"gRPC error: {e.code()} - {e.details()}")
        raise HTTPException(status_code=503, detail=f"Inference service error: {e.details()}")
    except Exception as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="error").inc()
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/file")
async def predict_from_file(
    file: UploadFile = File(...),
    target_resource: str = Form(default="Patient")
):
    """
    Transform data from uploaded file to FHIR format.
    
    Accepts JSON or CSV files.
    """
    start_time = datetime.utcnow()
    
    try:
        content = await file.read()
        
        # Parse file content
        if file.filename.endswith('.json'):
            raw_data = json.loads(content.decode('utf-8'))
        elif file.filename.endswith('.csv'):
            # Simple CSV parsing (first row as headers)
            import csv
            from io import StringIO
            reader = csv.DictReader(StringIO(content.decode('utf-8')))
            raw_data = list(reader)
            if len(raw_data) == 1:
                raw_data = raw_data[0]
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use JSON or CSV.")
        
        # Create request and call predict
        request = PredictRequest(raw_data=raw_data, target_resource=target_resource)
        return await predict(request)
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback for model improvement.
    
    When a user corrects a FHIR mapping, this endpoint stores the feedback
    for future model training.
    """
    try:
        logger.info(f"Received feedback for resource: {request.target_resource}")
        
        # Create gRPC request
        grpc_request = mapper_pb2.FeedbackRequest(
            raw_data_json=json.dumps(request.raw_data),
            correct_fhir_json=json.dumps(request.correct_fhir),
            target_resource=request.target_resource
        )
        
        # Call trainer service
        stub, channel = get_inference_stub()
        try:
            # Note: In production, this would call a separate TrainerService
            response = stub.SubmitFeedback(grpc_request, timeout=10)
        finally:
            channel.close()
        
        REQUEST_COUNT.labels(method="POST", endpoint="/feedback", status="success").inc()
        
        return {"success": response.success, "message": response.message}
        
    except grpc.RpcError as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/feedback", status="error").inc()
        logger.error(f"Feedback submission error: {e.details()}")
        raise HTTPException(status_code=503, detail=f"Service error: {e.details()}")
    except Exception as e:
        REQUEST_COUNT.labels(method="POST", endpoint="/feedback", status="error").inc()
        logger.error(f"Feedback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

