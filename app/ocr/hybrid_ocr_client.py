"""
Hybrid OCR client that combines CRNN model with AI-based OCR for improved accuracy.
"""

import asyncio
from typing import List, Dict, Optional
import json
import os
from pathlib import Path

from .ocr_client_factory import extract_from_encoding_async
from .crnn_inference import predict_ballot_text
from utils.app_logger import logger


class HybridOCRClient:
    """
    Hybrid OCR client that combines CRNN model with AI-based OCR.
    
    This client can:
    1. Use CRNN model only (offline, fast, cost-effective)
    2. Use AI-based OCR only (online, potentially more accurate)
    3. Use both and select the best result based on confidence scores
    4. Use both and ensemble the results
    """
    
    def __init__(self, mode: str = "crnn_only", 
                 crnn_model_path: str = "models/crnn_best.pth",
                 crnn_charset_path: Optional[str] = None,
                 confidence_threshold: float = 0.8):
        """
        Initialize hybrid OCR client.
        
        Args:
            mode: OCR mode ("crnn_only", "ai_only", "hybrid", "ensemble")
            crnn_model_path: Path to trained CRNN model
            crnn_charset_path: Path to charset file for CRNN
            confidence_threshold: Threshold for confidence-based selection
        """
        self.mode = mode
        self.crnn_model_path = crnn_model_path
        self.crnn_charset_path = crnn_charset_path
        self.confidence_threshold = confidence_threshold
        
        # Check if CRNN model exists
        self.crnn_available = os.path.exists(crnn_model_path)
        if not self.crnn_available and mode in ["crnn_only", "hybrid", "ensemble"]:
            logger.warning(f"CRNN model not found at {crnn_model_path}")
            if mode == "crnn_only":
                raise FileNotFoundError(f"CRNN model required but not found: {crnn_model_path}")
    
    async def extract_from_encoding_async(self, base64_image: str) -> List[Dict[str, str]]:
        """
        Extract structured data from base64 encoded image using hybrid approach.
        
        Args:
            base64_image: Base64 encoded image
            
        Returns:
            List of dictionaries with Name, Address, Date, Ward fields
        """
        try:
            if self.mode == "crnn_only":
                return await self._extract_crnn_only(base64_image)
            elif self.mode == "ai_only":
                return await self._extract_ai_only(base64_image)
            elif self.mode == "hybrid":
                return await self._extract_hybrid(base64_image)
            elif self.mode == "ensemble":
                return await self._extract_ensemble(base64_image)
            else:
                raise ValueError(f"Unknown mode: {self.mode}")
                
        except Exception as e:
            logger.error(f"Error in hybrid OCR extraction: {str(e)}")
            raise
    
    async def _extract_crnn_only(self, base64_image: str) -> List[Dict[str, str]]:
        """Extract using CRNN model only."""
        # For CRNN, we need to save the base64 image temporarily
        # and then process it with the CRNN model
        temp_image_path = await self._save_base64_to_temp(base64_image)
        
        try:
            result = predict_ballot_text(
                image_path=temp_image_path,
                model_path=self.crnn_model_path,
                charset_path=self.crnn_charset_path
            )
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
    
    async def _extract_ai_only(self, base64_image: str) -> List[Dict[str, str]]:
        """Extract using AI-based OCR only."""
        return await extract_from_encoding_async(base64_image)
    
    async def _extract_hybrid(self, base64_image: str) -> List[Dict[str, str]]:
        """Extract using both methods and select the best result."""
        # Run both methods concurrently
        crnn_task = self._extract_crnn_only(base64_image)
        ai_task = self._extract_ai_only(base64_image)
        
        crnn_result, ai_result = await asyncio.gather(crnn_task, ai_task, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(crnn_result, Exception):
            logger.warning(f"CRNN extraction failed: {crnn_result}")
            crnn_result = []
        
        if isinstance(ai_result, Exception):
            logger.warning(f"AI extraction failed: {ai_result}")
            ai_result = []
        
        # Select the best result based on confidence
        crnn_confidence = self._calculate_confidence(crnn_result)
        ai_confidence = self._calculate_confidence(ai_result)
        
        logger.info(f"CRNN confidence: {crnn_confidence:.3f}, AI confidence: {ai_confidence:.3f}")
        
        if crnn_confidence > ai_confidence and crnn_confidence > self.confidence_threshold:
            logger.info("Selected CRNN result")
            return crnn_result
        else:
            logger.info("Selected AI result")
            return ai_result
    
    async def _extract_ensemble(self, base64_image: str) -> List[Dict[str, str]]:
        """Extract using both methods and ensemble the results."""
        # Run both methods concurrently
        crnn_task = self._extract_crnn_only(base64_image)
        ai_task = self._extract_ai_only(base64_image)
        
        crnn_result, ai_result = await asyncio.gather(crnn_task, ai_task, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(crnn_result, Exception):
            logger.warning(f"CRNN extraction failed: {crnn_result}")
            crnn_result = []
        
        if isinstance(ai_result, Exception):
            logger.warning(f"AI extraction failed: {ai_result}")
            ai_result = []
        
        # Ensemble the results
        ensemble_result = self._ensemble_results(crnn_result, ai_result)
        return ensemble_result
    
    async def _save_base64_to_temp(self, base64_image: str) -> str:
        """Save base64 image to temporary file."""
        import base64 as b64
        
        # Decode base64 image
        image_data = b64.b64decode(base64_image)
        
        # Create temporary file
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"temp_image_{hash(base64_image)}.jpg"
        
        with open(temp_path, "wb") as f:
            f.write(image_data)
        
        return str(temp_path)
    
    def _calculate_confidence(self, result: List[Dict[str, str]]) -> float:
        """
        Calculate confidence score for OCR result.
        
        Args:
            result: List of extracted entries
            
        Returns:
            Confidence score between 0 and 1
        """
        if not result:
            return 0.0
        
        # Simple confidence calculation based on:
        # 1. Number of complete entries
        # 2. Average length of names and addresses
        # 3. Presence of required fields
        
        total_entries = len(result)
        complete_entries = 0
        total_name_length = 0
        total_address_length = 0
        
        for entry in result:
            name = entry.get("Name", "").strip()
            address = entry.get("Address", "").strip()
            
            if name and address:  # Complete entry
                complete_entries += 1
                total_name_length += len(name)
                total_address_length += len(address)
        
        # Calculate confidence metrics
        completeness = complete_entries / total_entries if total_entries > 0 else 0
        avg_name_length = total_name_length / total_entries if total_entries > 0 else 0
        avg_address_length = total_address_length / total_entries if total_entries > 0 else 0
        
        # Normalize lengths (assuming reasonable ranges)
        name_score = min(avg_name_length / 20.0, 1.0)  # Normalize to 20 chars
        address_score = min(avg_address_length / 30.0, 1.0)  # Normalize to 30 chars
        
        # Combined confidence score
        confidence = (completeness * 0.5 + name_score * 0.25 + address_score * 0.25)
        
        return confidence
    
    def _ensemble_results(self, crnn_result: List[Dict[str, str]], 
                         ai_result: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Ensemble results from both CRNN and AI methods.
        
        Args:
            crnn_result: Results from CRNN model
            ai_result: Results from AI-based OCR
            
        Returns:
            Ensembled results
        """
        if not crnn_result and not ai_result:
            return []
        
        if not crnn_result:
            return ai_result
        
        if not ai_result:
            return crnn_result
        
        # Simple ensemble: combine unique entries
        # In practice, you might want more sophisticated ensemble methods
        combined_entries = []
        seen_entries = set()
        
        # Add entries from both results, avoiding duplicates
        for entry in crnn_result + ai_result:
            # Create a unique key for each entry
            entry_key = f"{entry.get('Name', '')}_{entry.get('Address', '')}"
            
            if entry_key not in seen_entries:
                combined_entries.append(entry)
                seen_entries.add(entry_key)
        
        return combined_entries


# Factory function to create hybrid OCR client
def create_hybrid_ocr_client(mode: str = "hybrid", 
                            crnn_model_path: str = "models/crnn_best.pth",
                            crnn_charset_path: Optional[str] = None) -> HybridOCRClient:
    """
    Create a hybrid OCR client with specified configuration.
    
    Args:
        mode: OCR mode ("crnn_only", "ai_only", "hybrid", "ensemble")
        crnn_model_path: Path to trained CRNN model
        crnn_charset_path: Path to charset file for CRNN
        
    Returns:
        Configured HybridOCRClient instance
    """
    return HybridOCRClient(
        mode=mode,
        crnn_model_path=crnn_model_path,
        crnn_charset_path=crnn_charset_path
    ) 