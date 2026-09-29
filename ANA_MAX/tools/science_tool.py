"""
A.N.A. - Science & Research Tool
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any, Dict, Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ScienceTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="science_research",
            description="Analiza statistica, procesare de date si simulari usoare.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatie suportata",
                    type="string",
                    required=True,
                    choices=["analyze_data", "hypothesis_test", "simulate_model"],
                ),
                ToolParameter(
                    name="data_path",
                    description="Calea catre dataset CSV",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="params",
                    description="JSON string pentru optiuni",
                    type="string",
                    required=False,
                ),
            ],
            category="science",
        )

    def execute(self, operation: str, data_path: Optional[str] = None, params: Optional[str] = None) -> ToolResult:
        if operation == "analyze_data":
            return self._analyze_dataset(data_path)
        if operation == "hypothesis_test":
            return self._run_stats_test(data_path, params)
        if operation == "simulate_model":
            return self._simulate_model(params)
        return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

    def _analyze_dataset(self, path: Optional[str]) -> ToolResult:
        try:
            import pandas as pd

            if not path:
                return ToolResult(status=ToolStatus.ERROR, error="Lipseste data_path")

            df = pd.read_csv(path)
            summary = {
                "rows": int(len(df)),
                "columns": list(df.columns),
                "null_values": df.isnull().sum().to_dict(),
                "description": df.describe(include="all").fillna("").to_dict(),
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=summary, message="Analiza dataset finalizata.")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _run_stats_test(self, path: Optional[str], params: Optional[str]) -> ToolResult:
        try:
            import pandas as pd
            from scipy import stats

            if not path:
                return ToolResult(status=ToolStatus.ERROR, error="Lipseste data_path")

            options = json.loads(params) if params else {}
            column_a = options.get("column_a")
            column_b = options.get("column_b")
            if not column_a or not column_b:
                return ToolResult(status=ToolStatus.ERROR, error="Params trebuie sa contina column_a si column_b")

            df = pd.read_csv(path)
            stat, pvalue = stats.ttest_ind(df[column_a].dropna(), df[column_b].dropna(), equal_var=False)
            payload = {
                "column_a": column_a,
                "column_b": column_b,
                "statistic": float(stat),
                "pvalue": float(pvalue),
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=payload, message="Test statistic finalizat.")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _simulate_model(self, params: Optional[str]) -> ToolResult:
        try:
            options = json.loads(params) if params else {}
            samples = int(options.get("samples", 10))
            low = float(options.get("low", 0))
            high = float(options.get("high", 1))
            values = [random.uniform(low, high) for _ in range(samples)]
            payload = {
                "samples": samples,
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=payload, message="Simulare finalizata.")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
