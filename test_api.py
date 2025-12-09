"""
Test script for FastAPI endpoints
"""

import requests
import json
from pathlib import Path

# Base URL
BASE_URL = "http://localhost:8022"

def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_pdf_upload():
    """Test PDF upload endpoint."""
    print("Testing /api/v1/stage/pdf endpoint...")
    
    # Use test PDF
    pdf_path = Path("test_data_pet_ct/test_pet_ct8.pdf")
    if not pdf_path.exists():
        print(f"Error: Test PDF not found at {pdf_path}\n")
        return False
    
    with open(pdf_path, 'rb') as f:
        files = {'file': ('test_pet_ct8.pdf', f, 'application/pdf')}
        response = requests.post(
            f"{BASE_URL}/api/v1/stage/pdf",
            files=files,
            data={'report_id': 'TEST001'}
        )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        staging = result.get('staging', {})
        print(f"TNM Stage: {staging.get('tnm_stage')}")
        print(f"Overall Stage: {staging.get('overall_stage')}")
        print(f"Summary: {staging.get('summary', '')[:100]}...\n")
        return True
    else:
        print(f"Error: {response.text}\n")
        return False

def test_text_staging():
    """Test text staging endpoint."""
    print("Testing /api/v1/stage/text endpoint...")
    
    sample_text = """
    # PET-CT Report
    
    FINDINGS:
    Right upper lobe mass measuring 4.2 cm in greatest dimension.
    FDG-avid with SUV max of 12.5.
    
    LYMPH NODES:
    Enlarged right paratracheal lymph nodes (station 4R).
    Subcarinal lymph nodes (station 7) are metabolically active.
    
    No evidence of distant metastatic disease.
    """
    
    payload = {
        "report_text": sample_text,
        "report_id": "TEXT001"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/stage/text",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        staging = result.get('staging', {})
        print(f"TNM Stage: {staging.get('tnm_stage')}")
        print(f"Overall Stage: {staging.get('overall_stage')}\n")
        return True
    else:
        print(f"Error: {response.text}\n")
        return False

def main():
    print("="*60)
    print("FastAPI TNM Staging System - API Tests")
    print("="*60)
    print("\nMake sure the FastAPI server is running:")
    print("  python app.py\n")
    print("="*60)
    print()
    
    try:
        # Test health endpoint
        if not test_health():
            print("❌ Health check failed")
            return
        
        print("✅ Health check passed")
        print()
        
        # Test PDF upload
        print("Note: PDF upload test may take 10-15 seconds...")
        if test_pdf_upload():
            print("✅ PDF upload test passed")
        else:
            print("❌ PDF upload test failed")
        
        print()
        
        # Test text staging
        print("Note: Text staging test may take 10-15 seconds...")
        if test_text_staging():
            print("✅ Text staging test passed")
        else:
            print("❌ Text staging test failed")
        
        print()
        print("="*60)
        print("All tests completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to FastAPI server")
        print("Make sure to start the server first:")
        print("  python app.py")

if __name__ == "__main__":
    main()
