from pydantic import BaseModel, Field
from typing import List


class EmployeeRequestDTO(BaseModel):
    """
    Request body for POST /api/v1/run-employee-review.

    Fields
    ------
    emp_id           : Unique employee identifier. Used as the DB primary key.
    screenshot_paths : Local filesystem paths to employee screenshot images (PNG/JPG).
    transcript_path  : Local path to the Zoom recording transcript (.txt or .json).
    """

    emp_id: str = Field(..., example="EMP-001")
    screenshot_paths: List[str] = Field(..., min_length=1, example=["data/emp001_screen1.png"])
    transcript_path: str = Field(..., example="data/emp001_zoom_transcript.txt")

    class Config:
        json_schema_extra = {
            "example": {
                "emp_id": "EMP-001",
                "screenshot_paths": ["data/emp001_screen1.png", "data/emp001_screen2.png"],
                "transcript_path": "data/emp001_zoom_transcript.txt",
            }
        }
