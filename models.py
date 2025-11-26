from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TStageResult(BaseModel):
    """Result from T-Agent (Tumor staging)."""
    stage: str = Field(
        ..., 
        description="T-stage classification (e.g., T1a, T1b, T1c, T2a, T2b, T3, T4, Tis, T1mi)"
    )
    tumor_size_mm: Optional[float] = Field(
        None, 
        description="Primary tumor size in millimeters (solid component for subsolid lesions)"
    )
    location: Optional[str] = Field(None, description="Tumor location (lobe, side)")
    laterality: Optional[Literal["left", "right"]] = Field(
        None, 
        description="Tumor laterality (left or right lung)"
    )
    invasion: Optional[List[str]] = Field(
        default_factory=list,
        description="List of invaded structures (e.g., chest wall, diaphragm, mediastinum)"
    )
    separate_nodules: Optional[List[str]] = Field(
        default_factory=list,
        description="Locations of separate tumor nodules"
    )
    evidence: str = Field(..., description="Evidence from report supporting this T-stage")
    confidence: Optional[str] = Field(
        None, 
        description="Confidence level in staging (high, medium, low)"
    )


class LymphNodeInvolvement(BaseModel):
    """Details of lymph node involvement."""
    station: str = Field(..., description="IASLC station number (e.g., 4R, 7, 10L)")
    laterality: Literal["ipsilateral", "contralateral", "midline"] = Field(
        ..., 
        description="Node laterality relative to primary tumor"
    )
    description: str = Field(
        ..., 
        description="Description from report (e.g., enlarged, FDG-avid, metabolically active)"
    )


class NStageResult(BaseModel):
    """Result from N-Agent (Lymph Node staging)."""
    stage: str = Field(
        ..., 
        description="N-stage classification (N0, N1, N2a, N2b, N3)"
    )
    involved_nodes: List[LymphNodeInvolvement] = Field(
        default_factory=list,
        description="List of involved lymph node stations"
    )
    evidence: str = Field(..., description="Evidence from report supporting this N-stage")
    confidence: Optional[str] = Field(
        None, 
        description="Confidence level in staging (high, medium, low)"
    )


class MetastasisSite(BaseModel):
    """Details of metastatic site."""
    organ_system: str = Field(
        ..., 
        description="Organ system involved (e.g., bone, liver, adrenal, brain, contralateral lung)"
    )
    location: str = Field(..., description="Specific location of metastasis")
    description: str = Field(..., description="Description from report")


class MStageResult(BaseModel):
    """Result from M-Agent (Metastasis staging)."""
    stage: str = Field(
        ..., 
        description="M-stage classification (M0, M1a, M1b, M1c1, M1c2)"
    )
    metastasis_sites: List[MetastasisSite] = Field(
        default_factory=list,
        description="List of metastatic sites identified"
    )
    organ_systems_count: int = Field(
        default=0,
        description="Number of distinct organ systems involved (for M1b/M1c classification)"
    )
    evidence: str = Field(..., description="Evidence from report supporting this M-stage")
    confidence: Optional[str] = Field(
        None, 
        description="Confidence level in staging (high, medium, low)"
    )


class TNMStaging(BaseModel):
    """Final TNM staging result combining all components."""
    tnm_stage: str = Field(
        ..., 
        description="Combined TNM stage string (e.g., T2aN1M0)"
    )
    overall_stage: str = Field(
        ..., 
        description="Overall prognostic stage group (e.g., Stage IIB, Stage IIIA)"
    )
    tumor: TStageResult = Field(..., description="T-stage component with evidence")
    nodes: NStageResult = Field(..., description="N-stage component with evidence")
    metastasis: MStageResult = Field(..., description="M-stage component with evidence")
    summary: str = Field(
        ..., 
        description="Executive summary of staging rationale"
    )
    clinical_stage_prefix: str = Field(
        default="c", 
        description="Staging prefix (c=clinical, p=pathologic, yc=post-treatment)"
    )


class ReportInput(BaseModel):
    """Input schema for radiology report."""
    markdown_text: str = Field(..., description="Markdown text from PDF OCR conversion")
    report_id: Optional[str] = Field(None, description="Optional report identifier")
    patient_id: Optional[str] = Field(None, description="Optional patient identifier")
