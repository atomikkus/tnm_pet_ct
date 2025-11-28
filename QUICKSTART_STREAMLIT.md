# Quick Start - Streamlit App

## Running the Streamlit Application

### 1. Install Dependencies
```powershell
# Make sure you're in the project directory
cd c:\Users\satya\Downloads\tnm_pet_ct

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Start the FastAPI Backend
```powershell
# Terminal 1
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the Streamlit App
```powershell
# Terminal 2 (new terminal window)
streamlit run streamlit_app.py
```

The app will automatically open in your default browser at `http://localhost:8501`

## Features

- 📄 **PDF Upload**: Upload PET-CT reports for automatic TNM staging
- ✏️ **Text Input**: Paste markdown text directly
- 📊 **Minimal View**: Quick overview of staging results
- 🔍 **Deep Dive**: Comprehensive details with evidence
- 💾 **Export**: Download results as JSON or text summary
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

## Usage

1. Choose input method (PDF or Text)
2. Upload file or paste text
3. Click "🚀 Analyze Report"
4. View results in Minimal or Deep Dive tabs
5. Export results if needed

For detailed instructions, see [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md)
