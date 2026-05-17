from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.employee_model import EmployeeTable


class EmployeeRepository:
    """
    Administrative CRUD repository for EmployeeTable.
    Use VectorRepository for similarity-search operations.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_emp_id(self, emp_id: str) -> List[EmployeeTable]:
        """Return all chunk rows belonging to an employee."""
        return (
            self.db.query(EmployeeTable)
            .filter(EmployeeTable.emp_id == emp_id)
            .all()
        )

    def exists(self, emp_id: str) -> bool:
        """True if any chunks are stored for this emp_id."""
        return (
            self.db.query(EmployeeTable.emp_id)
            .filter(EmployeeTable.emp_id == emp_id)
            .first()
        ) is not None

    def delete_by_emp_id(self, emp_id: str) -> int:
        """Delete all rows for an employee and return the count removed."""
        n = (
            self.db.query(EmployeeTable)
            .filter(EmployeeTable.emp_id == emp_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return n
