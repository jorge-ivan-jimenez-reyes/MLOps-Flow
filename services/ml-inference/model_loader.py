"""
Model Loader - Handles loading prompts/models from MLflow.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)


class ModelLoader:
    """Loads and manages model/prompt versions from MLflow."""
    
    def __init__(self, mlflow_uri: str, model_name: str):
        self.mlflow_uri = mlflow_uri
        self.model_name = model_name
        self.current_version = "default"
        self.current_config = None
        
        # Configure MLflow
        mlflow.set_tracking_uri(mlflow_uri)
        self.client = MlflowClient(mlflow_uri)
    
    def load_latest_model(self) -> Optional[Dict[str, Any]]:
        """Load the latest registered model/prompt configuration."""
        try:
            # Try to get the latest version from Model Registry
            versions = self.client.get_latest_versions(self.model_name, stages=["Production", "Staging", "None"])
            
            if not versions:
                logger.warning(f"No versions found for model: {self.model_name}")
                return None
            
            # Get the latest version
            latest = versions[0]
            self.current_version = f"v{latest.version}"
            
            # Load the model artifact
            model_uri = f"models:/{self.model_name}/{latest.version}"
            return self._load_prompt_config(model_uri)
            
        except mlflow.exceptions.MlflowException as e:
            logger.warning(f"MLflow error loading model: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def load_model(self, model_uri: str) -> Optional[Dict[str, Any]]:
        """Load a specific model version."""
        try:
            return self._load_prompt_config(model_uri)
        except Exception as e:
            logger.error(f"Error loading model from {model_uri}: {e}")
            return None
    
    def _load_prompt_config(self, model_uri: str) -> Optional[Dict[str, Any]]:
        """Load prompt configuration from MLflow artifact."""
        try:
            # Download the artifact
            local_path = mlflow.artifacts.download_artifacts(model_uri)
            
            # Look for prompt config file
            config_path = os.path.join(local_path, "prompt_config.json")
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.current_config = config
                    logger.info(f"Loaded prompt config from {model_uri}")
                    return config
            else:
                logger.warning(f"No prompt_config.json found in {model_uri}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}")
            return None
    
    def get_current_version(self) -> str:
        """Get the current model version."""
        return self.current_version
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the current prompt configuration."""
        return self.current_config

