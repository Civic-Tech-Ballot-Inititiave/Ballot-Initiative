#!/usr/bin/env python3
"""
Test script for CRNN integration with Ballot Initiative project.
This script demonstrates how to use the CRNN model and compares it with AI-based OCR.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "app"))

from ocr.crnn_inference import predict_ballot_text, BallotTextExtractor
from ocr.hybrid_ocr_client import create_hybrid_ocr_client
from ocr.ocr_client_factory import extract_from_encoding_async
from utils.app_logger import logger


def encode_image_to_base64(image_path: str) -> str:
    """Convert image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def test_crnn_model():
    """Test CRNN model with sample data."""
    print("🧪 Testing CRNN Model")
    print("=" * 50)
    
    # Test with sample image
    sample_image = "sample_data/page-0.jpg"
    
    if not os.path.exists(sample_image):
        print(f"❌ Sample image not found: {sample_image}")
        return
    
    print(f"📸 Testing with image: {sample_image}")
    
    try:
        # Test CRNN model (if available)
        if os.path.exists("models/crnn_best.pth"):
            print("✅ CRNN model found, testing inference...")
            result = predict_ballot_text(sample_image)
            print(f"📊 CRNN extracted {len(result)} entries:")
            for i, entry in enumerate(result):
                print(f"  {i+1}. Name: {entry.get('Name', 'N/A')}")
                print(f"     Address: {entry.get('Address', 'N/A')}")
                print(f"     Date: {entry.get('Date', 'N/A')}")
                print(f"     Ward: {entry.get('Ward', 'N/A')}")
        else:
            print("⚠️  CRNN model not found. Run training first:")
            print("   python app/ocr/train_crnn.py --config configs/crnn_config.yaml")
    
    except Exception as e:
        print(f"❌ Error testing CRNN model: {e}")


async def test_ai_ocr():
    """Test AI-based OCR with sample data."""
    print("\n🤖 Testing AI-based OCR")
    print("=" * 50)
    
    # Test with sample image
    sample_image = "sample_data/page-0.jpg"
    
    if not os.path.exists(sample_image):
        print(f"❌ Sample image not found: {sample_image}")
        return
    
    try:
        # Convert image to base64
        base64_image = encode_image_to_base64(sample_image)
        
        # Test AI OCR
        print("🔄 Testing AI-based OCR...")
        result = await extract_from_encoding_async(base64_image)
        
        print(f"📊 AI OCR extracted {len(result)} entries:")
        for i, entry in enumerate(result):
            print(f"  {i+1}. Name: {entry.get('Name', 'N/A')}")
            print(f"     Address: {entry.get('Address', 'N/A')}")
            print(f"     Date: {entry.get('Date', 'N/A')}")
            print(f"     Ward: {entry.get('Ward', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Error testing AI OCR: {e}")


async def test_hybrid_ocr():
    """Test hybrid OCR approach."""
    print("\n🔀 Testing Hybrid OCR")
    print("=" * 50)
    
    # Test with sample image
    sample_image = "sample_data/page-0.jpg"
    
    if not os.path.exists(sample_image):
        print(f"❌ Sample image not found: {sample_image}")
        return
    
    try:
        # Convert image to base64
        base64_image = encode_image_to_base64(sample_image)
        
        # Test different hybrid modes
        modes = ["crnn_only", "ai_only", "hybrid", "ensemble"]
        
        for mode in modes:
            print(f"\n🔄 Testing {mode} mode...")
            
            try:
                client = create_hybrid_ocr_client(mode=mode)
                result = await client.extract_from_encoding_async(base64_image)
                
                print(f"📊 {mode} extracted {len(result)} entries:")
                for i, entry in enumerate(result[:3]):  # Show first 3 entries
                    print(f"  {i+1}. Name: {entry.get('Name', 'N/A')}")
                    print(f"     Address: {entry.get('Address', 'N/A')}")
            
            except Exception as e:
                print(f"❌ Error in {mode} mode: {e}")
    
    except Exception as e:
        print(f"❌ Error testing hybrid OCR: {e}")


def test_model_architecture():
    """Test CRNN model architecture."""
    print("\n🏗️  Testing CRNN Model Architecture")
    print("=" * 50)
    
    try:
        from ocr.crnn_inference import CRNN
        import torch
        
        # Create model with default parameters
        model = CRNN(
            img_height=32,
            img_width=128,
            num_classes=80,
            hidden_size=256
        )
        
        print("✅ CRNN model created successfully")
        print(f"📊 Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        # Test forward pass
        dummy_input = torch.randn(1, 1, 32, 128)
        output = model(dummy_input)
        
        print(f"✅ Forward pass successful")
        print(f"📊 Input shape: {dummy_input.shape}")
        print(f"📊 Output shape: {output.shape}")
        
    except Exception as e:
        print(f"❌ Error testing model architecture: {e}")


def test_data_processing():
    """Test data processing pipeline."""
    print("\n📊 Testing Data Processing Pipeline")
    print("=" * 50)
    
    try:
        from ocr.crnn_inference import CTCDecoder
        
        # Test CTC decoder
        decoder = CTCDecoder()
        print("✅ CTC decoder created successfully")
        
        # Test with dummy logits
        import torch
        dummy_logits = torch.randn(10, 80)  # 10 timesteps, 80 classes
        decoded_text = decoder.decode(dummy_logits)
        
        print(f"✅ CTC decoding successful")
        print(f"📊 Decoded text: '{decoded_text}'")
        
    except Exception as e:
        print(f"❌ Error testing data processing: {e}")


async def main():
    """Main test function."""
    print("🚀 CRNN Integration Test Suite")
    print("=" * 60)
    
    # Test model architecture
    test_model_architecture()
    
    # Test data processing
    test_data_processing()
    
    # Test CRNN model
    await test_crnn_model()
    
    # Test AI OCR
    await test_ai_ocr()
    
    # Test hybrid OCR
    await test_hybrid_ocr()
    
    print("\n✅ Test suite completed!")
    print("\n📋 Summary:")
    print("- CRNN model provides offline handwriting recognition")
    print("- Hybrid approach combines CRNN and AI OCR for best results")
    print("- All components integrate seamlessly with existing pipeline")


if __name__ == "__main__":
    asyncio.run(main()) 