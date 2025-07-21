"""
Integration example showing how to modify the existing OCR pipeline to use CRNN model.
This file demonstrates different integration approaches.
"""

import os
import asyncio
from typing import List, Dict
import base64
from pathlib import Path

# Import existing OCR components
from .ocr_client_factory import extract_from_encoding_async as ai_extract
from .crnn_inference import predict_ballot_text
from .hybrid_ocr_client import create_hybrid_ocr_client
from utils.app_logger import logger


def save_base64_to_temp(base64_image: str) -> str:
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


# ============================================================================
# Integration Option 1: Replace AI OCR with CRNN
# ============================================================================

async def extract_from_encoding_async_crnn_only(base64_image: str) -> List[Dict[str, str]]:
    """
    Replace AI OCR with CRNN model only.
    
    This function has the same interface as the original extract_from_encoding_async
    but uses the CRNN model instead of AI-based OCR.
    """
    try:
        # Save base64 image to temporary file
        temp_image_path = save_base64_to_temp(base64_image)
        
        # Use CRNN model for inference
        result = predict_ballot_text(
            image_path=temp_image_path,
            model_path="models/crnn_best.pth"
        )
        
        # Clean up temporary file
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in CRNN-only extraction: {str(e)}")
        raise


# ============================================================================
# Integration Option 2: Use Hybrid Approach
# ============================================================================

async def extract_from_encoding_async_hybrid(base64_image: str) -> List[Dict[str, str]]:
    """
    Use hybrid approach combining CRNN and AI OCR.
    
    This function uses both methods and selects the best result based on confidence.
    """
    try:
        # Create hybrid client
        hybrid_client = create_hybrid_ocr_client(
            mode="hybrid",
            crnn_model_path="models/crnn_best.pth"
        )
        
        # Use hybrid approach
        result = await hybrid_client.extract_from_encoding_async(base64_image)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in hybrid extraction: {str(e)}")
        raise


# ============================================================================
# Integration Option 3: Fallback Approach
# ============================================================================

async def extract_from_encoding_async_fallback(base64_image: str) -> List[Dict[str, str]]:
    """
    Use CRNN as primary method with AI OCR as fallback.
    
    This approach tries CRNN first, and if it fails or produces poor results,
    falls back to AI-based OCR.
    """
    try:
        # Try CRNN first
        if os.path.exists("models/crnn_best.pth"):
            try:
                temp_image_path = save_base64_to_temp(base64_image)
                result = predict_ballot_text(temp_image_path)
                
                # Check if result is acceptable
                if result and len(result) > 0:
                    # Clean up and return CRNN result
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                    return result
                
                # Clean up temp file
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    
            except Exception as e:
                logger.warning(f"CRNN extraction failed, falling back to AI OCR: {e}")
        
        # Fallback to AI OCR
        logger.info("Using AI OCR as fallback")
        return await ai_extract(base64_image)
        
    except Exception as e:
        logger.error(f"Error in fallback extraction: {str(e)}")
        raise


# ============================================================================
# Integration Option 4: Configurable Approach
# ============================================================================

class ConfigurableOCRClient:
    """Configurable OCR client that can switch between different methods."""
    
    def __init__(self, mode: str = "auto"):
        """
        Initialize configurable OCR client.
        
        Args:
            mode: OCR mode ("crnn_only", "ai_only", "hybrid", "fallback", "auto")
        """
        self.mode = mode
        self.crnn_available = os.path.exists("models/crnn_best.pth")
        
        if mode == "crnn_only" and not self.crnn_available:
            raise FileNotFoundError("CRNN model not found but crnn_only mode requested")
    
    async def extract_from_encoding_async(self, base64_image: str) -> List[Dict[str, str]]:
        """Extract data using configured method."""
        if self.mode == "crnn_only":
            return await extract_from_encoding_async_crnn_only(base64_image)
        elif self.mode == "ai_only":
            return await ai_extract(base64_image)
        elif self.mode == "hybrid":
            return await extract_from_encoding_async_hybrid(base64_image)
        elif self.mode == "fallback":
            return await extract_from_encoding_async_fallback(base64_image)
        elif self.mode == "auto":
            # Auto-select based on availability
            if self.crnn_available:
                return await extract_from_encoding_async_hybrid(base64_image)
            else:
                return await ai_extract(base64_image)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


# ============================================================================
# Usage Examples
# ============================================================================

async def example_usage():
    """Example usage of different integration approaches."""
    
    # Sample base64 image (you would get this from your application)
    sample_image_path = "sample_data/page-0.jpg"
    if os.path.exists(sample_image_path):
        with open(sample_image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")
    else:
        print("Sample image not found, skipping examples")
        return
    
    print("🔧 Integration Examples")
    print("=" * 50)
    
    # Example 1: CRNN only
    print("\n1️⃣ CRNN Only Approach:")
    try:
        client = ConfigurableOCRClient(mode="crnn_only")
        result = await client.extract_from_encoding_async(base64_image)
        print(f"✅ Extracted {len(result)} entries with CRNN")
    except Exception as e:
        print(f"❌ CRNN only failed: {e}")
    
    # Example 2: Hybrid approach
    print("\n2️⃣ Hybrid Approach:")
    try:
        client = ConfigurableOCRClient(mode="hybrid")
        result = await client.extract_from_encoding_async(base64_image)
        print(f"✅ Extracted {len(result)} entries with hybrid approach")
    except Exception as e:
        print(f"❌ Hybrid approach failed: {e}")
    
    # Example 3: Fallback approach
    print("\n3️⃣ Fallback Approach:")
    try:
        client = ConfigurableOCRClient(mode="fallback")
        result = await client.extract_from_encoding_async(base64_image)
        print(f"✅ Extracted {len(result)} entries with fallback approach")
    except Exception as e:
        print(f"❌ Fallback approach failed: {e}")
    
    # Example 4: Auto approach
    print("\n4️⃣ Auto Approach:")
    try:
        client = ConfigurableOCRClient(mode="auto")
        result = await client.extract_from_encoding_async(base64_image)
        print(f"✅ Extracted {len(result)} entries with auto approach")
    except Exception as e:
        print(f"❌ Auto approach failed: {e}")


# ============================================================================
# How to integrate into existing code
# ============================================================================

def integration_instructions():
    """Instructions for integrating CRNN into existing code."""
    
    print("\n📋 Integration Instructions")
    print("=" * 50)
    
    print("""
To integrate CRNN into your existing Ballot Initiative project:

1. **Option A: Replace AI OCR completely**
   - Replace the function in app/ocr/ocr_client_factory.py:
   
   ```python
   # Replace this line:
   from .ocr_client_factory import extract_from_encoding_async
   
   # With this:
   from .integration_example import extract_from_encoding_async_crnn_only as extract_from_encoding_async
   ```

2. **Option B: Use hybrid approach**
   - Replace the function in app/ocr/ocr_client_factory.py:
   
   ```python
   # Replace this line:
   from .ocr_client_factory import extract_from_encoding_async
   
   # With this:
   from .integration_example import extract_from_encoding_async_hybrid as extract_from_encoding_async
   ```

3. **Option C: Use configurable client**
   - Modify app/ocr/ocr_client_factory.py:
   
   ```python
   from .integration_example import ConfigurableOCRClient
   
   # Create client with desired mode
   ocr_client = ConfigurableOCRClient(mode="hybrid")
   
   # Use in your existing code
   result = await ocr_client.extract_from_encoding_async(base64_image)
   ```

4. **Option D: Environment-based selection**
   - Set environment variable to control OCR method:
   
   ```python
   import os
   from .integration_example import ConfigurableOCRClient
   
   ocr_mode = os.getenv("OCR_MODE", "auto")
   ocr_client = ConfigurableOCRClient(mode=ocr_mode)
   ```
    """)


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_usage())
    
    # Show integration instructions
    integration_instructions() 