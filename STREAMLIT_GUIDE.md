# TNM Staging Streamlit App - User Guide

## Overview

The TNM Staging Streamlit App provides a modern, user-friendly interface for interacting with the TNM Staging FastAPI backend. It allows users to upload PET-CT radiology reports (PDF or text) and receive AI-powered TNM staging predictions for lung cancer.

## Features

### 🎨 Modern UI
- **Gradient Background**: Beautiful purple gradient design
- **Card-Based Layout**: Clean, organized information display
- **Glassmorphism Effects**: Modern frosted-glass UI elements
- **Responsive Design**: Works on various screen sizes
- **Smooth Animations**: Hover effects and transitions

### 📊 Two Viewing Modes

#### Minimal View
The minimal view shows essential staging information at a glance:
- **TNM Stage**: Combined classification (e.g., T2aN1M0)
- **Overall Stage**: Prognostic stage group (e.g., Stage IIB)
- **Component Breakdown**: Individual T, N, and M stages with key details
- **Clinical Summary**: Executive summary of staging rationale

#### Deep Dive View
The deep dive reveals comprehensive details:
- **Tumor Details**: Size, location, laterality, invasion, evidence
- **Lymph Node Details**: All involved stations with descriptions
- **Metastasis Details**: Sites, organ systems, and descriptions
- **Complete JSON**: Full API response for advanced users

### 📤 Input Methods

1. **PDF Upload**: Upload PET-CT reports in PDF format
2. **Text Input**: Paste markdown text directly with optional report ID

## Getting Started

### Prerequisites

1. **Install Dependencies**
   ```powershell
   # Activate your virtual environment
   .\venv\Scripts\Activate.ps1
   
   # Install required packages
   pip install -r requirements.txt
   ```

2. **Start the FastAPI Backend**
   ```powershell
   # In a terminal window
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the Streamlit App**
   ```powershell
   # In another terminal window
   streamlit run streamlit_app.py
   ```

### Configuration

The app connects to the FastAPI backend at `http://localhost:8000` by default. To change this:

```powershell
# Set environment variable
$env:API_BASE_URL = "http://your-api-url:port"

# Then run Streamlit
streamlit run streamlit_app.py
```

## Usage

### Using PDF Upload

1. Select **📄 Upload PDF** in the sidebar
2. Click **Browse files** and select your PET-CT report PDF
3. Click **🚀 Analyze Report**
4. Wait for processing (typically 30-60 seconds)
5. View results in **Minimal View** or **Deep Dive** tabs

### Using Text Input

1. Select **✏️ Text Input** in the sidebar
2. Paste the report text (markdown format) into the text area
3. Optionally enter a Report ID
4. Click **🚀 Analyze Report**
5. View results in **Minimal View** or **Deep Dive** tabs

### Exporting Results

After analysis, you can export results in two formats:

1. **JSON Format**: Complete structured data including all metadata
2. **Text Summary**: Human-readable summary report

Click the respective download buttons to save the files.

## Understanding the Results

### TNM Components

- **T (Tumor)**: Describes the size and extent of the primary tumor
  - T0-T4: Progressively larger or more invasive tumors
  - Subdivisions (a, b, c): Specific size ranges
  
- **N (Nodes)**: Indicates lymph node involvement
  - N0: No lymph node involvement
  - N1: Nearby lymph nodes
  - N2: Mediastinal lymph nodes (same side)
  - N3: Contralateral or supraclavicular lymph nodes
  
- **M (Metastasis)**: Describes distant spread
  - M0: No distant metastasis
  - M1a: Same chest metastasis (pleural/pericardial)
  - M1b: Single distant metastasis
  - M1c: Multiple distant metastases

### Overall Stage

The combined TNM components map to an overall stage (0-IV):
- **Stage 0**: Carcinoma in situ
- **Stage I**: Localized tumor
- **Stage II**: Locally advanced tumor
- **Stage III**: Regional spread
- **Stage IV**: Distant metastasis

## Troubleshooting

### Cannot Connect to API

**Error**: "⚠️ Cannot connect to API at http://localhost:8000"

**Solutions**:
1. Ensure FastAPI is running: `uvicorn app:app --reload`
2. Check the API port (default: 8000)
3. Verify no firewall blocking connections
4. Set correct API_BASE_URL environment variable

### Analysis Takes Too Long

The analysis typically takes 30-90 seconds. If it's taking longer:
1. Check FastAPI logs for errors
2. Verify MISTRAL_API_KEY is set correctly
3. Check internet connection (API calls to Mistral)
4. Review the PDF quality (poor OCR can cause issues)

### PDF Upload Fails

**Common causes**:
1. File not in PDF format
2. File corrupted or password-protected
3. File too large (>10MB)

**Solutions**:
- Ensure file is a valid PDF
- Try using text input instead
- Check FastAPI logs for specific errors

### Unexpected Staging Results

If results seem incorrect:
1. Review the evidence citations in Deep Dive
2. Check the original report for clarity
3. Verify the PDF was converted correctly
4. Consider using text input for better control

## Technical Details

### Architecture

```
User → Streamlit App → FastAPI Backend → LangGraph Workflow → Mistral AI
                                        ↓
                                    T/N/M Agents
                                        ↓
                                  Staging Compiler
```

### API Endpoints Used

- `GET /health`: Health check before analysis
- `POST /api/v1/stage/pdf`: PDF report staging
- `POST /api/v1/stage/text`: Text report staging

### Data Flow

1. User provides report (PDF or text)
2. Streamlit sends request to FastAPI
3. FastAPI processes report through workflow
4. T, N, M agents analyze independently
5. Staging compiler combines results
6. Results returned to Streamlit
7. User views formatted results

## Best Practices

1. **Report Quality**: Use clear, structured reports for best results
2. **Review Evidence**: Always check the evidence citations in Deep Dive
3. **Export Results**: Save important analyses for records
4. **Multiple Runs**: If uncertain, run the analysis multiple times
5. **Clinical Validation**: Always validate AI results with clinical expertise

## Support

For issues or questions:
1. Check FastAPI logs for backend errors
2. Review Streamlit console for frontend errors
3. Verify environment variables are set correctly
4. Ensure all dependencies are installed

## Limitations

- Only supports lung cancer TNM staging
- Requires well-formatted radiology reports
- AI predictions should be validated by clinicians
- Processing time depends on report complexity
- Requires active internet connection for Mistral API

## Future Enhancements

Potential improvements:
- Batch processing of multiple reports
- Report comparison features
- Historical staging tracking
- Custom staging guidelines
- Multi-language support
- Offline mode with local models

---

**Version**: 1.0.0  
**Last Updated**: November 2025
