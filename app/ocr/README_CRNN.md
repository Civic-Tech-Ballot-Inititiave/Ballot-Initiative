# CRNN (CNN + BiLSTM + CTC) Integration for Ballot Initiative

This module provides a CNN + BiLSTM + CTC (CRNN) model for handwriting recognition as an alternative to the current AI-based OCR system. The CRNN model offers several advantages:

## 🚀 Benefits

- **Offline Operation**: No external API dependencies
- **Cost-Effective**: No per-request API costs
- **Customizable**: Can be trained specifically for ballot signatures
- **Fast Inference**: Optimized for real-time processing
- **Privacy**: All processing happens locally

## 📁 File Structure

```
app/ocr/
├── crnn_inference.py      # CRNN model and inference code
├── train_crnn.py         # Training script
├── hybrid_ocr_client.py  # Hybrid client combining CRNN + AI OCR
└── README_CRNN.md        # This file

configs/
└── crnn_config.yaml      # Training configuration

models/                   # Trained model checkpoints
└── crnn_best.pth        # Best trained model

data/
├── charset.txt           # Character set for training
├── processed/
│   ├── train/           # Training data
│   └── val/             # Validation data
```

## 🏗️ Architecture

### CRNN Model Components

1. **CNN Layers**: Extract spatial features from images
   - 4 convolutional layers with batch normalization
   - Max pooling for dimension reduction
   - ReLU activation functions

2. **BiLSTM Layers**: Process sequential information
   - Bidirectional LSTM for context awareness
   - 2 layers with dropout for regularization
   - Hidden size: 256 units

3. **CTC Loss**: Handle sequence alignment
   - Connectionist Temporal Classification
   - Handles variable-length sequences
   - No need for explicit alignment

### Integration Points

The CRNN model integrates seamlessly with the existing Ballot Initiative pipeline:

```
PDF → Image Conversion → CRNN Model → Structured Data → Fuzzy Matching
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# PyTorch and related packages are already in requirements.txt
pip install -r requirements.txt
```

### 2. Train the Model

```bash
# Create training data directory structure
mkdir -p data/processed/train data/processed/val models

# Train the model
python app/ocr/train_crnn.py --config configs/crnn_config.yaml
```

### 3. Use CRNN for Inference

```python
from app.ocr.crnn_inference import predict_ballot_text

# Extract structured data from ballot image
result = predict_ballot_text("sample_data/page-0.jpg")
print(result)
```

### 4. Use Hybrid OCR Client

```python
from app.ocr.hybrid_ocr_client import create_hybrid_ocr_client

# Create hybrid client
client = create_hybrid_ocr_client(mode="hybrid")

# Use in existing pipeline
result = await client.extract_from_encoding_async(base64_image)
```

## 🔧 Configuration

### Training Configuration (`configs/crnn_config.yaml`)

```yaml
model:
  img_height: 32
  img_width: 128
  num_classes: 80
  hidden_size: 256

training:
  batch_size: 32
  epochs: 50
  learning_rate: 0.001

data:
  train_dir: "data/processed/train"
  val_dir: "data/processed/val"
  charset_path: "data/charset.txt"
```

### OCR Modes

1. **`crnn_only`**: Use only CRNN model (offline, fast)
2. **`ai_only`**: Use only AI-based OCR (online, potentially more accurate)
3. **`hybrid`**: Use both and select best result based on confidence
4. **`ensemble`**: Use both and combine results

## 📊 Performance Comparison

| Metric | CRNN Only | AI Only | Hybrid |
|--------|-----------|---------|--------|
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Accuracy | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Cost | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| Privacy | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

## 🎯 Training Data Requirements

### Data Format

Training data should be organized as follows:

```
data/processed/train/
├── image1.jpg
├── image1.txt      # Corresponding text label
├── image2.jpg
├── image2.txt
└── ...

data/processed/val/
├── val_image1.jpg
├── val_image1.txt
└── ...
```

### Data Sources

1. **IAM Dataset**: Standard handwriting recognition dataset
2. **EMNIST**: Extended MNIST for handwritten characters
3. **Custom Ballot Data**: Real ballot signatures (recommended)
4. **Synthetic Data**: Generated using the fake data notebooks

### Character Set

Create `data/charset.txt` with all characters that appear in your training data:

```
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,'-
```

## 🔄 Integration with Existing Pipeline

### Option 1: Replace AI OCR Completely

```python
# In app/ocr/ocr_client_factory.py
from .crnn_inference import predict_ballot_text

async def extract_from_encoding_async(base64_image: str):
    # Save base64 to temp file
    temp_path = save_base64_to_temp(base64_image)
    
    # Use CRNN model
    result = predict_ballot_text(temp_path)
    
    # Clean up
    os.remove(temp_path)
    
    return result
```

### Option 2: Use Hybrid Approach

```python
# In app/ocr/ocr_client_factory.py
from .hybrid_ocr_client import create_hybrid_ocr_client

# Create hybrid client
hybrid_client = create_hybrid_ocr_client(mode="hybrid")

async def extract_from_encoding_async(base64_image: str):
    return await hybrid_client.extract_from_encoding_async(base64_image)
```

## 🧪 Testing

### Test CRNN Model

```python
from app.ocr.crnn_inference import predict_ballot_text

# Test with sample data
result = predict_ballot_text("sample_data/page-0.jpg")
print("Extracted entries:", len(result))
for entry in result:
    print(f"Name: {entry['Name']}, Address: {entry['Address']}")
```

### Compare with AI OCR

```python
from app.ocr.hybrid_ocr_client import create_hybrid_ocr_client

client = create_hybrid_ocr_client(mode="hybrid")

# Test hybrid approach
result = await client.extract_from_encoding_async(base64_image)
print("Hybrid result:", result)
```

## 🚨 Troubleshooting

### Common Issues

1. **Model not found**: Ensure `models/crnn_best.pth` exists
2. **CUDA out of memory**: Reduce batch size in config
3. **Poor accuracy**: 
   - Increase training data
   - Adjust model architecture
   - Fine-tune hyperparameters

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed inference logs
result = predict_ballot_text("test_image.jpg")
```

## 📈 Future Improvements

1. **Attention Mechanism**: Add attention to improve accuracy
2. **Data Augmentation**: Implement more robust augmentation
3. **Ensemble Methods**: Combine multiple CRNN models
4. **Layout Analysis**: Add form structure understanding
5. **Multi-language Support**: Extend to other languages

## 🤝 Contributing

To contribute to the CRNN integration:

1. **Improve Model Architecture**: Experiment with different CNN/LSTM configurations
2. **Better Training Data**: Collect more diverse ballot signatures
3. **Enhanced Parsing**: Improve text-to-structured-data conversion
4. **Performance Optimization**: Optimize inference speed
5. **Testing**: Add comprehensive test coverage

## 📚 References

- [CRNN Paper](https://arxiv.org/abs/1507.05717)
- [CTC Loss](https://distill.pub/2017/ctc/)
- [PyTorch Tutorials](https://pytorch.org/tutorials/)
- [Ballot Initiative Project](https://github.com/civictechdc/Ballot-Initiative)

## 📄 License

This CRNN integration follows the same MIT license as the main Ballot Initiative project. 