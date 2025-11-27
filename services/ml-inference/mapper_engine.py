"""
FHIR Mapper Engine - DSPy-based mapping logic.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

import dspy

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# DSPy Signatures
# -----------------------------------------------------------------------------
class FHIRMappingSignature(dspy.Signature):
    """Map raw healthcare data to FHIR format."""
    
    raw_data = dspy.InputField(desc="Raw healthcare data as JSON string")
    target_resource = dspy.InputField(desc="Target FHIR resource type (e.g., Patient, Observation)")
    schema_guide = dspy.InputField(desc="FHIR schema guide and mapping rules")
    
    fhir_json = dspy.OutputField(desc="Valid FHIR resource as JSON string")
    confidence = dspy.OutputField(desc="Confidence score between 0 and 1")


# -----------------------------------------------------------------------------
# Default Prompts
# -----------------------------------------------------------------------------
DEFAULT_SCHEMA_GUIDE = """
You are a healthcare data transformation expert. Your task is to map raw healthcare data to FHIR R4 format.

Target FHIR Resource: {target_resource}

FHIR Patient Schema (simplified):
{{
    "resourceType": "Patient",
    "id": "string",
    "name": [{{ "family": "string", "given": ["string"] }}],
    "gender": "male|female|other|unknown",
    "birthDate": "YYYY-MM-DD",
    "telecom": [{{ "system": "phone|email", "value": "string" }}],
    "address": [{{ "line": ["string"], "city": "string", "state": "string", "postalCode": "string" }}]
}}

Rules:
1. Map field names intelligently (e.g., "Nom" -> name, "Fecha_Nac" -> birthDate)
2. Normalize date formats to YYYY-MM-DD
3. Split full names into family and given names
4. Return valid JSON only
5. Include only fields that have data
"""


# -----------------------------------------------------------------------------
# Mapper Engine
# -----------------------------------------------------------------------------
class FHIRMapperEngine:
    """Engine for mapping raw data to FHIR using DSPy."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.schema_guide = DEFAULT_SCHEMA_GUIDE
        
        # Configure DSPy with OpenAI
        if api_key:
            self.lm = dspy.LM(
                model=f"openai/{model}",
                api_key=api_key,
                max_tokens=2000,
                temperature=0.1
            )
            dspy.configure(lm=self.lm)
            logger.info(f"DSPy configured with model: {model}")
        else:
            logger.warning("No OpenAI API key provided. Using mock responses.")
            self.lm = None
        
        # Create the mapper module
        self.mapper = dspy.Predict(FHIRMappingSignature)
    
    def update_prompt(self, config: Dict[str, Any]):
        """Update the schema guide from MLflow config."""
        if "schema_guide" in config:
            self.schema_guide = config["schema_guide"]
            logger.info("Updated schema guide from MLflow config")
        
        if "examples" in config:
            # Could be used for few-shot learning
            logger.info(f"Loaded {len(config['examples'])} examples for few-shot")
    
    def map_to_fhir(self, raw_data: Dict[str, Any], target_resource: str = "Patient") -> Dict[str, Any]:
        """
        Map raw data to FHIR format.
        
        Args:
            raw_data: Dictionary containing raw healthcare data
            target_resource: Target FHIR resource type
            
        Returns:
            Dictionary with 'fhir' (the result) and 'confidence' score
        """
        try:
            # If no LLM configured, use mock response
            if not self.lm:
                return self._mock_mapping(raw_data, target_resource)
            
            # Prepare inputs
            raw_json = json.dumps(raw_data, ensure_ascii=False)
            schema_guide = self.schema_guide.format(target_resource=target_resource)
            
            # Call DSPy
            result = self.mapper(
                raw_data=raw_json,
                target_resource=target_resource,
                schema_guide=schema_guide
            )
            
            # Parse result
            fhir_json = self._parse_fhir_response(result.fhir_json)
            confidence = self._parse_confidence(result.confidence)
            
            return {
                "fhir": fhir_json,
                "confidence": confidence,
                "jsonata": ""  # Could generate JSONata expression if needed
            }
            
        except Exception as e:
            logger.error(f"Mapping error: {e}")
            # Return a basic FHIR structure on error
            return self._fallback_mapping(raw_data, target_resource)
    
    def _parse_fhir_response(self, response: str) -> Dict[str, Any]:
        """Parse FHIR JSON from LLM response."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse FHIR response: {response[:100]}...")
            return {"resourceType": "Patient", "error": "Parse error"}
    
    def _parse_confidence(self, confidence: str) -> float:
        """Parse confidence score from LLM response."""
        try:
            # Extract number from response
            import re
            numbers = re.findall(r"[\d.]+", str(confidence))
            if numbers:
                score = float(numbers[0])
                return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
            return 0.8
        except:
            return 0.8
    
    def _mock_mapping(self, raw_data: Dict[str, Any], target_resource: str) -> Dict[str, Any]:
        """Generate mock FHIR response when no LLM is available."""
        logger.info("Using mock mapping (no LLM configured)")
        
        # Simple field mapping
        fhir = {"resourceType": target_resource}
        
        if target_resource == "Patient":
            # Try to extract patient fields
            name_fields = ["name", "nombre", "nom", "fullName", "full_name"]
            for field in name_fields:
                if field in raw_data:
                    name = raw_data[field]
                    if isinstance(name, str):
                        parts = name.split()
                        fhir["name"] = [{
                            "given": parts[:-1] if len(parts) > 1 else parts,
                            "family": parts[-1] if len(parts) > 1 else ""
                        }]
                    break
            
            # Birth date
            date_fields = ["birthDate", "birth_date", "fecha_nac", "dob", "fechaNacimiento"]
            for field in date_fields:
                if field in raw_data and raw_data[field]:
                    fhir["birthDate"] = str(raw_data[field])
                    break
            
            # Gender
            gender_fields = ["gender", "sexo", "sex"]
            for field in gender_fields:
                if field in raw_data:
                    gender = str(raw_data[field]).lower()
                    if gender in ["m", "male", "masculino", "hombre"]:
                        fhir["gender"] = "male"
                    elif gender in ["f", "female", "femenino", "mujer"]:
                        fhir["gender"] = "female"
                    else:
                        fhir["gender"] = "unknown"
                    break
        
        return {
            "fhir": fhir,
            "confidence": 0.7,
            "jsonata": ""
        }
    
    def _fallback_mapping(self, raw_data: Dict[str, Any], target_resource: str) -> Dict[str, Any]:
        """Fallback mapping when LLM fails."""
        return {
            "fhir": {
                "resourceType": target_resource,
                "extension": [{
                    "url": "http://example.org/raw-data",
                    "valueString": json.dumps(raw_data)
                }]
            },
            "confidence": 0.3,
            "jsonata": ""
        }



