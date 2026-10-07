"""Status-preserving failures from standalone native analysis."""
from __future__ import annotations
import grpc

class AnalysisError(RuntimeError):
    def __init__(self, code: grpc.StatusCode, message: str) -> None:
        self.code = code
        super().__init__(message)
