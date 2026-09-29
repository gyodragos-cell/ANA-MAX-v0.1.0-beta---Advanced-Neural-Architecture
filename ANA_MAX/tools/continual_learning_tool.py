"""
ANA MAX - continual_learning_tool.py
======================================
Continual Learning fara Catastrophic Forgetting.

Problema:
  Modelele AI uita totul dupa fiecare sesiune (Catastrophic Forgetting).
  Chiar si cu memory_cortex, Qwen/Ollama nu incorporeaza niciodata
  corectiile in ponderile proprii — ele raman externe, injectate la prompt.

Solutia (LoRA-style feedback loop local):
  1. Colecteaza perechile (prompt_gresit, corectie_utilizator) din memory_cortex.
  2. Le formateaza ca date de antrenament JSONL (format Ollama fine-tune).
  3. Genereaza un fisier de configuratie pentru fine-tuning LoRA local.
  4. (Optional) Lanseaza un job de fine-tune prin Ollama daca e disponibil.

Pana cand Ollama suporta complet fine-tuning local automat (in curs de dezvoltare),
acest tool pregateste si pastreaza datele in formatul corect, gata de import.

Chiar si fara fine-tuning, acest tool are valoare imediata:
- Exporta datele de antrenament in format compatibil cu orice framework
- Analizeaza calitatea corectiilor pentru a detecta pattern-uri de invatare
- Poate alimenta un RAG (Retrieval-Augmented Generation) local cu exemple reale
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.ContinualLearning")

ANA_ROOT = Path(__file__).parent.parent
MEMORY_DB = ANA_ROOT / "ana_memory.db"
TRAINING_DIR = ANA_ROOT / "training"
TRAINING_DIR.mkdir(exist_ok=True)


def _load_corrections_from_db() -> list[dict]:
    """Incarca toate corectiile din memory_cortex SQLite."""
    if not MEMORY_DB.exists():
        return []
    try:
        with sqlite3.connect(str(MEMORY_DB)) as conn:
            rows = conn.execute(
                """SELECT prompt_context, bad_response, correct_response, error_type, times_repeated
                   FROM cortex_errors
                   WHERE correct_response IS NOT NULL AND correct_response != ''
                   ORDER BY times_repeated DESC, timestamp DESC"""
            ).fetchall()
        return [
            {
                "prompt": r[0] or "",
                "bad_response": r[1] or "",
                "correct_response": r[2] or "",
                "error_type": r[3] or "general",
                "times_repeated": r[4] or 1,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"Nu s-au putut incarca corectiile: {e}")
        return []


def _corrections_to_training_data(corrections: list[dict]) -> list[dict]:
    """Converteste corectiile in format JSONL pentru fine-tuning."""
    training = []
    for c in corrections:
        if not c["prompt"] or not c["correct_response"]:
            continue
        # Formatul standard pentru fine-tuning conversational (OpenAI/Ollama compatible)
        entry = {
            "messages": [
                {
                    "role": "system",
                    "content": "Esti ANA MAX, un asistent AI expert in pentest, Android reverse engineering si automatizare desktop. Raspunzi concis, tehnic si complet."
                },
                {
                    "role": "user",
                    "content": c["prompt"][:500]
                },
                {
                    "role": "assistant",
                    "content": c["correct_response"][:1000]
                }
            ],
            "metadata": {
                "error_type": c["error_type"],
                "times_repeated": c["times_repeated"],
                "source": "memory_cortex_correction"
            }
        }
        # Tool-urile mai repetate primesc mai multe exemple (data augmentation)
        for _ in range(min(c["times_repeated"], 3)):
            training.append(entry)
    return training


def _analyze_learning_quality(corrections: list[dict]) -> dict:
    """Analizeaza calitatea datelor de antrenament."""
    if not corrections:
        return {"total": 0, "quality": "no_data"}

    error_types: dict[str, int] = {}
    for c in corrections:
        et = c.get("error_type", "unknown")
        error_types[et] = error_types.get(et, 0) + 1

    avg_repetitions = sum(c["times_repeated"] for c in corrections) / len(corrections)
    high_value = [c for c in corrections if c["times_repeated"] >= 3]

    return {
        "total_corrections": len(corrections),
        "high_value_corrections": len(high_value),
        "error_type_distribution": error_types,
        "avg_times_llm_repeated_mistake": round(avg_repetitions, 1),
        "quality": "excellent" if len(high_value) > 5 else "good" if len(corrections) > 10 else "building",
    }


class ContinualLearningTool(Tool):
    """Continual Learning fara Catastrophic Forgetting."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="continual_learning",
            description=(
                "Colecteaza corectiile utilizatorului si le transforma in date de antrenament "
                "pentru fine-tuning local al modelului AI (LoRA format). "
                "Actiuni: 'analyze' (analizeaza datele), 'export' (exporta JSONL), 'stats' (statistici)."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="'analyze', 'export', 'stats'",
                    type="string",
                    required=True,
                    choices=["analyze", "export", "stats"],
                ),
                ToolParameter(
                    name="min_repetitions",
                    description="Numarul minim de repetari pentru a include o corectie in training data (default: 1)",
                    type="integer",
                    required=False,
                ),
            ],
            category="ai",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        min_rep = int(kwargs.get("min_repetitions", 1))

        corrections = _load_corrections_from_db()
        corrections = [c for c in corrections if c["times_repeated"] >= min_rep]

        if action == "analyze":
            analysis = _analyze_learning_quality(corrections)
            training_data = _corrections_to_training_data(corrections)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "analysis": analysis,
                    "training_samples": len(training_data),
                    "ready_for_export": len(training_data) > 0,
                },
                message=(
                    f"Analiza Continual Learning: {len(corrections)} corectii disponibile, "
                    f"{len(training_data)} sample-uri de antrenament generate."
                )
            )

        elif action == "export":
            if not corrections:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Nu exista corectii in memory_cortex inca. Corecteaza mai intai cateva raspunsuri gresite ale modelului."
                )

            training_data = _corrections_to_training_data(corrections)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = TRAINING_DIR / f"continual_train_{timestamp}.jsonl"

            with open(output_file, "w", encoding="utf-8") as f:
                for entry in training_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Genereaza si un script de fine-tune pentru Ollama (cand va fi suportat)
            finetune_config = {
                "model": "qwen2.5-coder:7b",
                "training_file": str(output_file),
                "lora_rank": 16,
                "lora_alpha": 32,
                "epochs": 3,
                "learning_rate": 2e-4,
                "batch_size": 4,
                "note": "Generated by ANA ContinualLearning. Use with Ollama fine-tune when available."
            }
            config_file = TRAINING_DIR / f"finetune_config_{timestamp}.json"
            config_file.write_text(json.dumps(finetune_config, indent=2))

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "training_file": str(output_file),
                    "config_file": str(config_file),
                    "samples_exported": len(training_data),
                    "analysis": _analyze_learning_quality(corrections),
                },
                message=(
                    f"Exportat {len(training_data)} sample-uri in {output_file.name}. "
                    f"Config LoRA generat in {config_file.name}."
                )
            )

        elif action == "stats":
            analysis = _analyze_learning_quality(corrections)
            # Verifica daca exista fisiere de antrenament generate anterior
            existing_files = list(TRAINING_DIR.glob("continual_train_*.jsonl"))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "analysis": analysis,
                    "previous_exports": len(existing_files),
                    "latest_export": str(existing_files[-1].name) if existing_files else None,
                    "training_dir": str(TRAINING_DIR),
                },
                message=f"Continual Learning: {analysis['total_corrections']} corectii, calitate: {analysis['quality']}."
            )

        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
