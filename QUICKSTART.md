# Quick Start Guide - TNM Staging System

Get started with the TNM staging system in 5 minutes!

## Prerequisites

- Python 3.10+
- Mistral API key ([Get one here](https://console.mistral.ai/))

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
```

## Usage Options

### Option 1: Command Line (CLI)

Process a single PET-CT PDF:

```bash
python main.py --input test_data_pet_ct/test_pet_ct8.pdf
```

**Output:**
- `test_pet_ct8_staging.json` - Structured results
- `test_pet_ct8_staging_report.md` - Human-readable report

### Option 2: FastAPI Web Service

Start the API server:

```bash
python app.py
```

The API will be available at `http://localhost:8000`

**Interactive API docs:** `http://localhost:8000/docs`

#### Upload PDF via API:

```bash
curl -X POST "http://localhost:8000/api/v1/stage/pdf" \
  -F "file=@test_data_pet_ct/test_pet_ct8.pdf"
```

#### Send text via API:

```bash
curl -X POST "http://localhost:8000/api/v1/stage/text" \
  -H "Content-Type: application/json" \
  -d '{
    "report_text": "Your markdown report text here...",
    "report_id": "report123"
  }'
```

## Example Output

```json
{
  "success": true,
  "staging": {
    "tnm_stage": "T2aN2bM0",
    "overall_stage": "Stage IIIB",
    "tumor": {
      "stage": "T2a",
      "tumor_size_mm": 38,
      "location": "right upper lobe",
      "laterality": "right"
    },
    "nodes": {
      "stage": "N2b",
      "involved_nodes": [...]
    },
    "metastasis": {
      "stage": "M0"
    }
  }
}
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--input`, `-i` | Input PDF file (required) |
| `--output`, `-o` | Output directory (default: same as input) |
| `--no-json` | Skip JSON output |
| `--no-markdown` | Skip markdown report |
| `--verbose`, `-v` | Enable detailed logging |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/api/v1/stage/pdf` | POST | Stage from PDF upload |
| `/api/v1/stage/text` | POST | Stage from markdown text |

## Common Commands

### Process multiple PDFs in a directory:

```bash
for file in test_data_pet_ct/*.pdf; do
    python main.py --input "$file"
done
```

### Run with detailed logging:

```bash
python main.py --input report.pdf --verbose
```

### Start API in production mode:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

Run the test script to verify everything works:

```bash
python test_agents.py
```

Expected output:
```
[1/4] Testing T-Agent...
✓ T-Agent Success: Stage = T2a
[2/4] Testing N-Agent...
✓ N-Agent Success: Stage = N2b
[3/4] Testing M-Agent...
✓ M-Agent Success: Stage = M0
[4/4] Testing Staging Compiler...
✓ Compiler Success
```

## Troubleshooting

### "MISTRAL_API_KEY not found"
→ Check your `.env` file exists and contains the API key

### Import errors
→ Run `pip install -r requirements.txt`

### Port already in use (FastAPI)
→ Change port: `python app.py --port 8080`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [walkthrough.md](walkthrough.md) for architecture details
- Review TNM 9th Edition rules in [tnm_staging_howto.md](tnm_staging_howto.md)

## Support

For issues or questions, check the logs with `--verbose` flag or review the system documentation.

---

**That's it!** You're ready to start staging PET-CT reports! 🎉
