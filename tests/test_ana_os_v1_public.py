"""Public tests for the ANA MAX OS v1 package."""

import importlib
import json
from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "ana_os_v1"


class TestAnaOSV1PublicPackage(TestCase):
    def test_public_package_imports(self):
        modules = [
            "agent_manager",
            "cluster_manager",
            "cognitive_runtime",
            "debug_manager",
            "devtools_manager",
            "distributed_memory",
            "event_bus",
            "federation_manager",
            "fs_sync",
            "inference_dispatcher",
            "kernel_summary",
            "lock_manager",
            "metrics_manager",
            "model_loader",
            "model_registry",
            "model_router",
            "packaging_manager",
            "pipeline_manager",
            "placement_manager",
            "profiler_manager",
            "recovery_manager",
            "routing_manager",
            "service_manager",
            "task_manager",
            "transport",
            "vector_memory",
        ]
        for name in modules:
            importlib.import_module(f"ana_os_v1.{name}")

    def test_public_package_excludes_test_and_fake_scaffolding(self):
        forbidden = ("FakeTransport", "FakeTransportMulti", "test_", "stub")
        for path in PACKAGE_ROOT.rglob("*"):
            self.assertFalse(any(token in path.name for token in forbidden), path.name)

    def test_manifest_matches_public_package(self):
        manifest = json.loads((PROJECT_ROOT / "ANA_OS_V1_MANIFEST.json").read_text(encoding="utf-8"))
        actual = sorted(path.stem for path in PACKAGE_ROOT.glob("*.py") if path.name != "__init__.py")
        self.assertEqual(sorted(manifest["modules"]), actual)
