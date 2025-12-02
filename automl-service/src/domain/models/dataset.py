"""
Dataset - Aggregate Root for dataset management
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DatasetId:
    """Value Object for Dataset identifier"""
    value: UUID

    @classmethod
    def generate(cls) -> "DatasetId":
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "DatasetId":
        return cls(value=UUID(id_str))

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Dataset:
    """
    Dataset Aggregate Root
    
    Represents a registered dataset in the system.
    Datasets are stored in MinIO, this entity holds metadata.
    """
    id: DatasetId
    name: str
    minio_path: str  # e.g., "bucket/path/to/file.csv"
    user_id: str
    session_id: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    file_size_bytes: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_metadata(
        self, 
        columns: List[str], 
        row_count: int, 
        file_size_bytes: int
    ) -> None:
        """Update dataset metadata after file validation"""
        self.columns = columns
        self.row_count = row_count
        self.file_size_bytes = file_size_bytes
        self.updated_at = datetime.utcnow()

    def has_column(self, column_name: str) -> bool:
        """Check if dataset has a specific column"""
        return column_name in self.columns

    def belongs_to(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Check if dataset belongs to user/session"""
        if self.user_id != user_id:
            return False
        if session_id and self.session_id and self.session_id != session_id:
            return False
        return True
