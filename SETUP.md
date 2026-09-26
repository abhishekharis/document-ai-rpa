# Setup Guide

## Python Version Requirements

**CRITICAL**: This project requires Python 3.10-3.13. Python 3.14 is NOT currently supported due to PaddleOCR compatibility issues.

### Check Python Version
```bash
python3 --version
```

If you have Python 3.14, you need to install a compatible version:

### Install Python 3.12 (Recommended)

#### Using Homebrew (macOS)
```bash
brew install python@3.12
```

#### Using pyenv (Cross-platform)
```bash
# Install pyenv if not already installed
brew install pyenv  # macOS
# or
curl https://pyenv.run | bash  # Linux/Unix

# Install Python 3.12
pyenv install 3.12.0
pyenv global 3.12.0
```

#### Verify Installation
```bash
python3.12 --version
```

## Fresh Setup Instructions

### 1. Clean Environment Setup

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa

# Copy environment file
cp .env.example .env

# Edit .env if needed (defaults should work for local development)
# nano .env  # or use your preferred editor
```

### 2. Start MongoDB

#### Option A: Docker (Recommended)
```bash
docker-compose up -d
```

#### Option B: Local MongoDB Installation
```bash
# Install MongoDB via Homebrew
brew tap mongodb/brew
brew trust mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community
```

#### Verify MongoDB is Running
```bash
# If using Docker
docker ps

# If using local installation
brew services list  # Look for mongodb-community

# Test connection
mongosh mongodb://localhost:27017
```

### 3. Backend Setup

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa/backend

# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies (this will take 10-20 minutes due to PaddleOCR)
pip install -r requirements.txt
```

#### If PaddleOCR Installation Fails
```bash
# Install PaddlePaddle first (CPU version)
pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Then install PaddleOCR
pip install paddleocr==2.7.0.3
```

### 4. Run Backend

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa/backend
source venv/bin/activate
python -m app.main
```

The backend should start on `http://127.0.0.1:8000`

### 5. Verify Backend is Running

```bash
# Test health endpoint
curl http://127.0.0.1:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "mongodb_connected": true,
#   "timestamp": "2024-01-01T00:00:00"
# }
```

### 6. Frontend Setup (Optional)

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa/frontend

# Install Node.js dependencies
npm install

# Run frontend development server
npm run dev
```

The frontend should start on `http://localhost:3000`

### 7. Simulated Accounting App Setup (Optional)

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa/simulated-accounting-app

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the accounting app
python app.py
```

The accounting app should start on `http://localhost:3001`

## Troubleshooting

### Python Version Issues
```bash
# Check current Python version
python3 --version

# If wrong version, use specific version
python3.12 -m venv venv
```

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
docker ps  # if using Docker
brew services list  # if using local installation

# Check MongoDB logs
docker logs document-ai-rpa-mongodb

# Restart MongoDB
docker-compose restart
# or
brew services restart mongodb-community
```

### Dependency Installation Issues
```bash
# Clear pip cache
pip cache purge

# Upgrade pip
pip install --upgrade pip

# Try installing packages individually
pip install fastapi uvicorn pydantic pymongo motor
pip install pymupdf Pillow opencv-python
pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install paddleocr
```

### PaddleOCR Model Download Issues
PaddleOCR downloads models on first run. This requires internet connection and may take time.

### Port Conflicts
If ports are already in use, modify the `.env` file:
```bash
API_PORT=8001  # Change backend port
ACCOUNTING_APP_URL=http://localhost:3002  # Change accounting app port
```

## Verification Checklist

- [ ] Python 3.10-3.13 installed
- [ ] MongoDB running on port 27017
- [ ] Backend dependencies installed successfully
- [ ] Backend server running on port 8000
- [ ] Health endpoint returns `{"status": "healthy", "mongodb_connected": true}`
- [ ] Frontend dependencies installed (optional)
- [ ] Frontend running on port 3000 (optional)
- [ ] Accounting app running on port 3001 (optional)

## Known Limitations

1. **Python 3.14 Not Supported**: PaddleOCR doesn't support Python 3.14 yet. Use Python 3.10-3.13.
2. **PaddleOCR Initial Run**: First run downloads models (~200MB) and may take several minutes.
3. **Docker Resource Limits**: MongoDB container needs sufficient memory (512MB+ recommended).
4. **macOS Apple Silicon**: All dependencies are compatible with Apple Silicon (M1/M2/M3).

## Compatibility Matrix

| Component | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 | Python 3.14 |
|-----------|-------------|-------------|-------------|-------------|-------------|
| FastAPI   | ✅          | ✅          | ✅          | ✅          | ✅          |
| PyMongo   | ✅          | ✅          | ✅          | ✅          | ✅          |
| PaddleOCR | ✅          | ✅          | ✅          | ✅          | ❌          |
| Pillow    | ✅          | ✅          | ✅          | ✅          | ✅ (12.2+)  |
| OpenCV    | ✅          | ✅          | ✅          | ✅          | ✅          |
| PyMuPDF   | ✅          | ✅          | ✅          | ✅          | ✅          |

## Next Steps

Once setup is complete:
1. Upload a test invoice via the frontend or API
2. Monitor the processing pipeline
3. Review extracted data and confidence scores
4. Test the approval/rejection workflow
5. (Optional) Set up UiPath RPA workflow