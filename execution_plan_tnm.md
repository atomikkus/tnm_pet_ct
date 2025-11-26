# Multi-Agent LLM System for TNM Staging Prediction

## 1. Overview

The goal of this project is to automate the prediction of TNM (Tumor, Node, Metastasis) staging for lung cancer from the JSON output of PET-CT radiological reports. This plan outlines a multi-agent Large Language Model (LLM) architecture designed for accuracy, modularity, and interpretability. The system will take a structured JSON file (extracted via a pre-existing OCR tool) as input and produce a final TNM stage classification with supporting evidence.

## 2. Proposed Architecture: A Multi-Agent System

A multi-agent approach is recommended over a single monolithic LLM call. This breaks down the complex task of staging into specialized, manageable sub-tasks, improving reliability and making the system easier to debug and maintain. Each agent is an LLM instance with a prompt engineered for a specific purpose.

### Agent 1: T-Agent (Tumor Staging)

This agent is responsible for determining the 'T' component of the stage.

*   **Input:** The "findings" and "impression" sections of the report's JSON.
*   **Task:**
    1.  Search for descriptions of the primary tumor.
    2.  Extract its greatest dimension. For subsolid lesions, specifically extract the size of the **solid component**.
    3.  Identify any local invasion into adjacent structures as defined in the TNM 9th Edition (e.g., main bronchus, visceral pleura, chest wall, diaphragm, mediastinum).
    4.  Detect the presence and location of any "separate tumor nodules" to determine if they are in the same lobe (T3) or a different ipsilateral lobe (T4).
*   **Output:** A JSON object containing the T-stage (e.g., `T1c`, `T3`) and the evidence found (e.g., `{"stage": "T2a", "evidence": "Tumor is 3.5 cm in greatest dimension."}`).

### Agent 2: N-Agent (Node Staging)

This agent is responsible for determining the 'N' component by analyzing lymph node involvement.

*   **Input:** The "findings" and "impression" sections of the report's JSON, along with the primary tumor's laterality (left/right) determined by the T-Agent.
*   **Task:**
    1.  Scan the text for any mention of lymph nodes, specifically looking for IASLC station numbers (e.g., "station 4R", "level 7", "subcarinal") or descriptive locations (e.g., "hilar", "supraclavicular").
    2.  Note whether nodes are described as "enlarged", "pathologic", or "FDG-avid" / "metabolically active".
    3.  Classify each involved station as ipsilateral or contralateral based on the tumor's location.
    4.  Apply the TNM 9th Edition rules:
        *   Ipsilateral hilar nodes -> N1.
        *   Ipsilateral mediastinal/subcarinal nodes -> N2. Differentiate between single station (N2a) and multiple stations (N2b).
        *   Contralateral mediastinal/hilar or any supraclavicular/scalene nodes -> N3.
*   **Output:** A JSON object with the N-stage (e.g., `N0`, `N2b`) and a list of involved nodes supporting the classification.

### Agent 3: M-Agent (Metastasis Staging)

This agent searches for evidence of distant metastasis to determine the 'M' component.

*   **Input:** The entire report JSON.
*   **Task:**
    1.  Search the entire report for findings of disease outside the lungs and regional lymph nodes.
    2.  **M1a (Intrathoracic Metastasis):** Look for separate tumor nodules in the **contralateral** lung, or malignant pleural/pericardial effusion or nodules.
    3.  **M1b/M1c (Extrathoracic Metastasis):**
        *   Identify all sites of extrathoracic metastasis (e.g., "adrenal nodule", "osseous metastasis in the T5 vertebral body", "lesion in the liver").
        *   Count the number of distinct organ systems involved.
        *   If there is only **one** metastasis in a **single** organ system -> M1b.
        *   If there are **multiple** metastases in a **single** organ system -> M1c1.
        *   If there are metastases in **multiple** organ systems -> M1c2.
*   **Output:** A JSON object with the M-stage (`M0`, `M1a`, `M1b`, `M1c1`, `M1c2`) and a summary of metastatic sites.

### Agent 4: Staging Compiler

This final agent aggregates the outputs from the specialized agents and determines the final stage.

*   **Input:** The JSON outputs from the T, N, and M agents.
*   **Task:**
    1.  Combine the individual stages into a final TNM string (e.g., `T2aN1M0`).
    2.  Reference the TNM 9th Edition prognostic stage group table to map the TNM string to an overall stage (e.g., `Stage IIB`).
    3.  Assemble a final, comprehensive JSON object that includes the overall stage, the individual TNM components, and the evidence for each.
*   **Output:** The final staging result. Example:
    ```json
    {
      "overall_stage": "Stage IIB",
      "tnm_stage": "T2bN1M0",
      "tumor": {
        "stage": "T2b",
        "evidence": "Primary tumor in the right upper lobe measures 4.2 cm."
      },
      "nodes": {
        "stage": "N1",
        "evidence": "Metabolically active right hilar lymph nodes (station 10R) are present."
      },
      "metastasis": {
        "stage": "M0",
        "evidence": "No evidence of distant metastatic disease."
      }
    }
    ```

## 3. Recommended Tools and Stack

*   **Programming Language:** **Python 3.10+**
*   **LLM Orchestration Framework:** **LangChain** or **LlamaIndex** or **CrewAI**
*   **LLM Model:** **Google's Gemini 1.5 Pro** (via Vertex AI). Its large context window, advanced reasoning capabilities, and native JSON mode are well-suited for parsing dense medical reports and following complex instructions.
*   **API Framework:** **FastAPI**. It can be used to wrap the entire multi-agent system into a scalable, high-performance API endpoint.
*   **Data Validation:** **Pydantic**. For defining and validating the structure of the input and output JSON, ensuring data integrity throughout the pipeline.
