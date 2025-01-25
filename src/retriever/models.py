from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class QueryResult:
    """Structure pour les résultats de requête"""
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    doc_id: str
