from pydantic import BaseModel, Field
from typing import List, Optional


class EmployeeRequestDTO(BaseModel):
    """
    Request body for POST /api/v1/run-employee-review.

    Fields
    ------
    emp_id           : Unique employee identifier. Used as the DB primary key.
    emp_name         : Employee name (optional, used for record creation).
    department       : Employee department (optional, used for record creation).
    screenshot_paths : Local filesystem paths to employee screenshot images (PNG/JPG).
    transcript_path  : Local path to the Zoom recording transcript (.txt or .json).
    """

    emp_id: str = Field(..., example="EMP-001")
    emp_name: Optional[str] = Field(None, example="John Doe")
    department: Optional[str] = Field(None, example="Engineering")
    screenshot_paths: List[str] = Field(..., min_length=1, example=["data/emp001_screen1.png"])
    transcript_path: str = Field(..., example="data/emp001_zoom_transcript.txt")

    class Config:# shows an example in the OpenAPI docs like swagger
        json_schema_extra = {
            "example": {
                "emp_id": "EMP-001",
                "emp_name": "John Doe",
                "department": "Engineering",
                "screenshot_paths": ["data/emp001_screen1.png", "data/emp001_screen2.png"],
                "transcript_path": "data/emp001_zoom_transcript.txt",
            }
        }
