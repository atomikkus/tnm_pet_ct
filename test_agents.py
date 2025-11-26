"""
Simple test script to verify the TNM staging system is set up correctly.
This tests the agents without requiring a full PDF.
"""

import logging
from agents import TAgent, NAgent, MAgent, StagingCompiler

# Configure logging
logging.basicConfig(level=logging.INFO)

# Sample mock report text for testing
SAMPLE_REPORT = """
# PET-CT Radiology Report

## Page 1
---

CLINICAL HISTORY: 65-year-old male with new lung mass.

FINDINGS:

THORAX:
There is a spiculated mass in the right upper lobe measuring 38 mm in greatest dimension. 
The mass demonstrates increased FDG uptake with SUV max of 12.5.

LYMPH NODES:
- Enlarged right paratracheal lymph nodes (station 4R) measuring up to 15 mm, FDG-avid with SUV max 8.2
- Subcarinal lymph nodes (station 7) measuring 18 mm, metabolically active with SUV max 7.8
- No left-sided mediastinal lymphadenopathy

CHEST WALL: No invasion of the chest wall identified.

ABDOMEN:
- Liver: No focal hepatic lesions
- Adrenal glands: Normal bilateral adrenal glands
- Kidneys: Normal

BONES:
No suspicious osseous lesions identified on the PET or CT images.

IMPRESSION:
1. Right upper lobe lung mass measuring 38 mm, highly FDG avid, suspicious for primary lung malignancy
2. FDG-avid right paratracheal (4R) and subcarinal (7) lymph nodes, concerning for N2b disease
3. No evidence of distant metastatic disease
"""

def test_agents():
    """Test individual agents."""
    print("="*60)
    print("Testing TNM Staging Agents")
    print("="*60)
    
    # Test T-Agent
    print("\n[1/4] Testing T-Agent...")
    try:
        t_agent = TAgent()
        t_result = t_agent.analyze(SAMPLE_REPORT)
        print(f"✓ T-Agent Success: Stage = {t_result['stage']}")
        print(f"  - Size: {t_result.get('tumor_size_mm')} mm")
        print(f"  - Location: {t_result.get('location')}")
        print(f"  - Laterality: {t_result.get('laterality')}")
    except Exception as e:
        print(f"✗ T-Agent Failed: {e}")
        return False
    
    # Test N-Agent
    print("\n[2/4] Testing N-Agent...")
    try:
        n_agent = NAgent()
        context = {"tumor_laterality": t_result.get("laterality")}
        n_result = n_agent.analyze(SAMPLE_REPORT, context=context)
        print(f"✓ N-Agent Success: Stage = {n_result['stage']}")
        print(f"  - Involved nodes: {len(n_result.get('involved_nodes', []))}")
    except Exception as e:
        print(f"✗ N-Agent Failed: {e}")
        return False
    
    # Test M-Agent
    print("\n[3/4] Testing M-Agent...")
    try:
        m_agent = MAgent()
        m_result = m_agent.analyze(SAMPLE_REPORT)
        print(f"✓ M-Agent Success: Stage = {m_result['stage']}")
        print(f"  - Metastasis sites: {len(m_result.get('metastasis_sites', []))}")
    except Exception as e:
        print(f"✗ M-Agent Failed: {e}")
        return False
    
    # Test Staging Compiler
    print("\n[4/4] Testing Staging Compiler...")
    try:
        compiler = StagingCompiler()
        final_result = compiler.compile_staging(t_result, n_result, m_result)
        print(f"✓ Compiler Success:")
        print(f"  - TNM Stage: {final_result['tnm_stage']}")
        print(f"  - Overall Stage: {final_result['overall_stage']}")
        print(f"\nSummary:")
        print(f"  {final_result['summary'][:200]}...")
    except Exception as e:
        print(f"✗ Staging Compiler Failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("✓ All tests passed successfully!")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        success = test_agents()
        if not success:
            print("\n✗ Some tests failed. Please check the errors above.")
            exit(1)
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
