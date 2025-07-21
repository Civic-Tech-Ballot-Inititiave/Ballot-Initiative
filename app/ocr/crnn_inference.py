"""
CRNN (CNN + BiLSTM + CTC) inference module for handwriting recognition.
This module provides a drop-in replacement for the current AI-based OCR.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as transforms
import numpy as np
from typing import List, Dict, Optional
import json
import os
from pathlib import Path

from utils.app_logger import logger


class CRNN(nn.Module):
    """
    CNN + BiLSTM + CTC model for handwriting recognition.
    
    Architecture:
    - CNN layers for feature extraction
    - BiLSTM layers for sequence modeling
    - CTC loss for sequence alignment
    """
    
    def __init__(self, img_height: int = 32, img_width: int = 128, 
                 num_classes: int = 80, hidden_size: int = 256, 
                 num_layers: int = 2, dropout: float = 0.5):
        super(CRNN, self).__init__()
        
        self.img_height = img_height
        self.img_width = img_width
        self.num_classes = num_classes
        self.hidden_size = hidden_size
        
        # CNN layers for feature extraction
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(64)
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(256)
        self.conv4 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        
        # Max pooling
        self.pool = nn.MaxPool2d(2, 2)
        
        # Calculate feature map size after CNN
        # Assuming input size: (1, img_height, img_width)
        # After 4 conv layers with max pooling: (256, img_height//16, img_width//16)
        feature_height = img_height // 16
        feature_width = img_width // 16
        
        # BiLSTM layers
        self.lstm = nn.LSTM(
            input_size=256 * feature_height,
            hidden_size=hidden_size,
            num_layers=num_layers,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Output layer
        self.fc = nn.Linear(hidden_size * 2, 80)  # Fixed to match trained model
        
        # CTC loss
        self.ctc_loss = nn.CTCLoss(blank=0, zero_infinity=True)
        
    def forward(self, x):
        # CNN feature extraction
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.pool(x)
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool(x)
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.pool(x)
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.pool(x)
        
        # Reshape for LSTM: (batch, seq_len, features)
        batch_size, channels, height, width = x.size()
        x = x.permute(0, 3, 1, 2)  # (batch, width, channels, height)
        x = x.reshape(batch_size, width, channels * height)
        
        # BiLSTM
        lstm_out, _ = self.lstm(x)
        
        # Output layer
        output = self.fc(lstm_out)
        
        return output
    
    def load_from_checkpoint(self, checkpoint_path: str):
        """Load model from checkpoint file."""
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        self.load_state_dict(checkpoint['model_state_dict'])
        return self


class CTCDecoder:
    """CTC decoder for converting model outputs to text."""
    
    def __init__(self, charset_path: Optional[str] = None):
        """
        Initialize CTC decoder.
        
        Args:
            charset_path: Path to charset file. If None, uses default charset.
        """
        if charset_path and os.path.exists(charset_path):
            with open(charset_path, 'r') as f:
                self.charset = f.read().strip()
        else:
            # Default charset for English text
            self.charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,'-"
        
        self.char_to_idx = {char: idx for idx, char in enumerate(self.charset)}
        self.idx_to_char = {idx: char for char, idx in self.char_to_idx.items()}
    
    def decode(self, logits: torch.Tensor, method: str = 'greedy') -> str:
        """
        Decode CTC logits to text.
        
        Args:
            logits: Model output logits (seq_len, num_classes)
            method: Decoding method ('greedy' or 'beam_search')
            
        Returns:
            Decoded text string
        """
        if method == 'greedy':
            return self._greedy_decode(logits)
        elif method == 'beam_search':
            return self._beam_search_decode(logits)
        else:
            raise ValueError(f"Unknown decoding method: {method}")
    
    def _greedy_decode(self, logits: torch.Tensor) -> str:
        """Greedy decoding for CTC."""
        # Get most likely characters
        _, indices = torch.max(logits, dim=1)
        
        # Convert to text
        text = ""
        prev_idx = None
        for idx in indices:
            if idx != prev_idx and idx != 0:  # Skip blank and repeated characters
                text += self.idx_to_char[idx.item()]
            prev_idx = idx
        
        return text.strip()
    
    def _beam_search_decode(self, logits: torch.Tensor, beam_width: int = 10) -> str:
        """Beam search decoding for CTC."""
        # Simplified beam search implementation
        # In practice, you might want to use a more sophisticated beam search
        return self._greedy_decode(logits)


class BallotTextExtractor:
    """Main class for extracting text from ballot images using CRNN."""
    
    def __init__(self, model_path: str, charset_path: Optional[str] = None,
                 img_height: int = 32, img_width: int = 128):
        """
        Initialize the ballot text extractor.
        
        Args:
            model_path: Path to trained CRNN model checkpoint
            charset_path: Path to charset file
            img_height: Input image height
            img_width: Input image width
        """
        self.img_height = img_height
        self.img_width = img_width
        
        # Initialize model
        self.model = CRNN(
            img_height=img_height,
            img_width=img_width,
            num_classes=len(self._get_charset(charset_path))
        )
        
        # Load trained model
        self.model.load_from_checkpoint(model_path)
        self.model.eval()
        
        # Initialize decoder
        self.decoder = CTCDecoder(charset_path)
        
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((img_height, img_width)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5])
        ])
    
    def _get_charset(self, charset_path: Optional[str]) -> str:
        """Get charset for model initialization."""
        if charset_path and os.path.exists(charset_path):
            with open(charset_path, 'r') as f:
                return f.read().strip()
        else:
            return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,'-"
    
    def extract_text(self, image_path: str) -> str:
        """
        Extract text from a single image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text string
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('L')  # Convert to grayscale
            image_tensor = self.transform(image).unsqueeze(0)
            
            # Inference
            with torch.no_grad():
                logits = self.model(image_tensor)
                # Remove batch dimension and transpose for decoder
                logits = logits.squeeze(0).transpose(0, 1)
                text = self.decoder.decode(logits)
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {str(e)}")
            return ""
    
    def extract_structured_data(self, image_path: str) -> List[Dict[str, str]]:
        """
        Extract structured data from ballot image.
        This is the main interface that replaces the current AI-based OCR.
        
        Args:
            image_path: Path to ballot image
            
        Returns:
            List of dictionaries with Name, Address, Date, Ward fields
        """
        try:
            # Extract raw text
            raw_text = self.extract_text(image_path)
            
            # Parse structured data from raw text
            # This is a simplified parser - you might want to implement
            # more sophisticated parsing logic based on your ballot format
            structured_data = self._parse_ballot_text(raw_text)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data from {image_path}: {str(e)}")
            return []
    
    def _parse_ballot_text(self, text: str) -> List[Dict[str, str]]:
        """
        Parse raw text into structured ballot data.
        This is a placeholder implementation - you'll need to customize
        this based on your specific ballot format.
        
        Args:
            text: Raw extracted text
            
        Returns:
            List of dictionaries with structured data
        """
        # This is a simplified parser
        # In practice, you'll need to implement more sophisticated parsing
        # based on your specific ballot layout and format
        
        lines = text.split('\n')
        entries = []
        
        for line in lines:
            if line.strip():
                # Simple parsing - split by common delimiters
                parts = line.split(',')
                if len(parts) >= 2:
                    entry = {
                        "Name": parts[0].strip(),
                        "Address": parts[1].strip() if len(parts) > 1 else "",
                        "Date": parts[2].strip() if len(parts) > 2 else "",
                        "Ward": parts[3].strip() if len(parts) > 3 else ""
                    }
                    entries.append(entry)
        
        return entries


def predict_ballot_text(image_path: str, model_path: str = "models/crnn_best.pth",
                       charset_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Main function to extract structured data from ballot image.
    This replaces the current extract_signature_info function.
    
    Args:
        image_path: Path to ballot image
        model_path: Path to trained CRNN model
        charset_path: Path to charset file
        
    Returns:
        List of dictionaries with Name, Address, Date, Ward fields
    """
    try:
        extractor = BallotTextExtractor(
            model_path=model_path,
            charset_path=charset_path
        )
        
        return extractor.extract_structured_data(image_path)
        
    except Exception as e:
        logger.error(f"Error in predict_ballot_text: {str(e)}")
        return []


# For backward compatibility with existing code
def extract_signature_info(image_path: str) -> List[Dict[str, str]]:
    """
    Legacy function for backward compatibility.
    This replaces the original extract_signature_info function.
    
    Args:
        image_path: Path to ballot image
        
    Returns:
        List of dictionaries with Name, Address, Date, Ward fields
    """
    return predict_ballot_text(image_path) 