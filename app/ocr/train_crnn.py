"""
Training script for CRNN (CNN + BiLSTM + CTC) model for handwriting recognition.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import os
import json
import yaml
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple, Optional
import argparse
from pathlib import Path
import logging

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from crnn_inference import CRNN, CTCDecoder
except ImportError:
    from app.ocr.crnn_inference import CRNN, CTCDecoder
from utils.app_logger import logger


class BallotDataset(Dataset):
    """Dataset for ballot signature images and their corresponding text."""
    
    def __init__(self, data_dir: str, charset_path: str, 
                 img_height: int = 32, img_width: int = 128,
                 transform=None):
        """
        Initialize dataset.
        
        Args:
            data_dir: Directory containing images and labels
            charset_path: Path to charset file
            img_height: Input image height
            img_width: Input image width
            transform: Image transformations
        """
        self.data_dir = data_dir
        self.img_height = img_height
        self.img_width = img_width
        
        # Load charset
        with open(charset_path, 'r') as f:
            self.charset = f.read().strip()
        self.char_to_idx = {char: idx for idx, char in enumerate(self.charset)}
        
        # Load data pairs
        self.data_pairs = self._load_data_pairs()
        
        # Image transformations
        if transform is None:
            self.transform = transforms.Compose([
                transforms.Resize((img_height, img_width)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5], std=[0.5])
            ])
        else:
            self.transform = transform
    
    def _load_data_pairs(self) -> List[Tuple[str, str]]:
        """Load image-text pairs from data directory."""
        pairs = []
        
        # Look for image files and corresponding label files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        
        for img_file in os.listdir(self.data_dir):
            if any(img_file.lower().endswith(ext) for ext in image_extensions):
                # Look for corresponding label file
                base_name = os.path.splitext(img_file)[0]
                label_file = os.path.join(self.data_dir, f"{base_name}.txt")
                
                if os.path.exists(label_file):
                    with open(label_file, 'r') as f:
                        text = f.read().strip()
                    pairs.append((os.path.join(self.data_dir, img_file), text))
        
        return pairs
    
    def __len__(self):
        return len(self.data_pairs)
    
    def __getitem__(self, idx):
        img_path, text = self.data_pairs[idx]
        
        # Load and preprocess image
        image = Image.open(img_path).convert('L')
        image_tensor = self.transform(image)
        
        # Convert text to indices
        text_indices = [self.char_to_idx.get(char, 0) for char in text]
        
        # Pad or truncate text to fixed length
        max_length = 20  # Maximum text length
        if len(text_indices) > max_length:
            text_indices = text_indices[:max_length]
        else:
            text_indices = text_indices + [0] * (max_length - len(text_indices))
        
        return {
            'image': image_tensor,
            'text': text,
            'text_indices': torch.tensor(text_indices, dtype=torch.long),
            'text_length': min(len(text), max_length)
        }


class CRNNTrainer:
    """Trainer class for CRNN model."""
    
    def __init__(self, config_path: str):
        """
        Initialize trainer.
        
        Args:
            config_path: Path to training configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Set up device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = CRNN(
            img_height=self.config['model']['img_height'],
            img_width=self.config['model']['img_width'],
            num_classes=self.config['model']['num_classes'],
            hidden_size=self.config['model']['hidden_size']
        ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.config['training']['learning_rate']
        )
        
        # Initialize CTC loss
        self.criterion = nn.CTCLoss(blank=0, zero_infinity=True)
        
        # Initialize decoder for evaluation
        self.decoder = CTCDecoder(self.config['data']['charset_path'])
        
        # Training state
        self.current_epoch = 0
        self.best_loss = float('inf')
        
    def train_epoch(self, train_loader: DataLoader) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch in train_loader:
            images = batch['image'].to(self.device)
            text_indices = batch['text_indices'].to(self.device)
            text_lengths = batch['text_length']
            
            # Forward pass
            logits = self.model(images)
            
            # Prepare CTC loss inputs
            batch_size = logits.size(0)
            seq_length = logits.size(1)
            
            # Reshape logits for CTC: (seq_len, batch, num_classes)
            logits = logits.permute(1, 0, 2)
            
            # All targets are now the same length (20)
            targets = torch.stack([item for item in text_indices])
            target_lengths = torch.tensor([text_lengths[i] for i in range(batch_size)])
            
            # Calculate loss
            loss = self.criterion(logits, targets, 
                                torch.full((batch_size,), seq_length, dtype=torch.long),
                                target_lengths)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / num_batches
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """Validate model."""
        self.model.eval()
        total_loss = 0.0
        total_accuracy = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in val_loader:
                images = batch['image'].to(self.device)
                text_indices = batch['text_indices'].to(self.device)
                text_lengths = batch['text_length']
                original_texts = batch['text']
                
                # Forward pass
                logits = self.model(images)
                
                # Calculate loss
                batch_size = logits.size(0)
                seq_length = logits.size(1)
                logits = logits.permute(1, 0, 2)
                
                # All targets are now the same length (20)
                targets = torch.stack([item for item in text_indices])
                target_lengths = torch.tensor([text_lengths[i] for i in range(batch_size)])
                
                loss = self.criterion(logits, targets,
                                    torch.full((batch_size,), seq_length, dtype=torch.long),
                                    target_lengths)
                
                # Calculate accuracy
                predicted_texts = []
                for i in range(batch_size):
                    logit = logits[:, i, :]
                    predicted_text = self.decoder.decode(logit)
                    predicted_texts.append(predicted_text)
                
                # Calculate character accuracy
                batch_accuracy = 0.0
                for pred, true in zip(predicted_texts, original_texts):
                    if pred == true:
                        batch_accuracy += 1.0
                batch_accuracy /= len(predicted_texts)
                
                total_loss += loss.item()
                total_accuracy += batch_accuracy
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        avg_accuracy = total_accuracy / num_batches
        
        return avg_loss, avg_accuracy
    
    def save_checkpoint(self, epoch: int, loss: float, accuracy: float, 
                       is_best: bool = False):
        """Save model checkpoint."""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'loss': loss,
            'accuracy': accuracy,
            'config': self.config
        }
        
        # Get base directory for correct paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        checkpoint_dir = os.path.join(base_dir, self.config['training']['checkpoint_dir'])
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Save regular checkpoint
        checkpoint_path = os.path.join(
            checkpoint_dir,
            f'crnn_epoch_{epoch}.pth'
        )
        torch.save(checkpoint, checkpoint_path)
        
        # Save best model
        if is_best:
            best_path = os.path.join(
                checkpoint_dir,
                'crnn_best.pth'
            )
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best model with loss: {loss:.4f}, accuracy: {accuracy:.4f}")
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader):
        """Main training loop."""
        logger.info("Starting training...")
        
        for epoch in range(self.config['training']['epochs']):
            # Train
            train_loss = self.train_epoch(train_loader)
            
            # Validate
            val_loss, val_accuracy = self.validate(val_loader)
            
            # Log progress
            logger.info(f"Epoch {epoch+1}/{self.config['training']['epochs']}")
            logger.info(f"Train Loss: {train_loss:.4f}")
            logger.info(f"Val Loss: {val_loss:.4f}, Val Accuracy: {val_accuracy:.4f}")
            
            # Save checkpoint
            is_best = val_loss < self.best_loss
            if is_best:
                self.best_loss = val_loss
            
            self.save_checkpoint(epoch + 1, val_loss, val_accuracy, is_best)
            
            self.current_epoch = epoch + 1


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train CRNN model for handwriting recognition')
    parser.add_argument('--config', type=str, required=True,
                       help='Path to training configuration file')
    args = parser.parse_args()
    
    # Create trainer
    trainer = CRNNTrainer(args.config)
    
    # Create datasets with correct paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    train_dataset = BallotDataset(
        data_dir=os.path.join(base_dir, trainer.config['data']['train_dir']),
        charset_path=os.path.join(base_dir, trainer.config['data']['charset_path']),
        img_height=trainer.config['model']['img_height'],
        img_width=trainer.config['model']['img_width']
    )
    
    val_dataset = BallotDataset(
        data_dir=os.path.join(base_dir, trainer.config['data']['val_dir']),
        charset_path=os.path.join(base_dir, trainer.config['data']['charset_path']),
        img_height=trainer.config['model']['img_height'],
        img_width=trainer.config['model']['img_width']
    )
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=trainer.config['training']['batch_size'],
        shuffle=True,
        num_workers=4
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=trainer.config['training']['batch_size'],
        shuffle=False,
        num_workers=4
    )
    
    # Start training
    trainer.train(train_loader, val_loader)
    
    logger.info("Training completed!")


if __name__ == '__main__':
    main() 