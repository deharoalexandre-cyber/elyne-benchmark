from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from elyne.contracts.hashing import InvalidInput
from elyne_benchmark.common import ROOT, load_json
from elyne_benchmark.runner import run_campaign


class PublicRunnerTests(unittest.TestCase):
    def test_mock_adapter_exercises_all_three_families(self) -> None:
        expected = {
            "justesse": {"core_origin": 15, "gemma_info": 15, "gemma_nu": 0},
            "orchestration": {"core_origin": 14, "gemma_info": 12, "gemma_nu": 0},
            "toolchain": {"core_origin": 15, "gemma_info": 0, "gemma_nu": 0},
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for index, (family, successes) in enumerate(expected.items(), start=1):
                with self.subTest(family=family):
                    report_path = run_campaign(
                        family=family,
                        adapter_config=ROOT / "adapters" / "mock.config.json",
                        output_root=output,
                        campaign_id=f"{index:032x}",
                    )
                    report = load_json(report_path)
                    self.assertEqual(report["status"], "completed")
                    self.assertEqual(report["overall"]["successes"], successes)
                    self.assertTrue(all(report["fairness"].values()))
                    if family == "orchestration":
                        chains = [
                            item for item in report["items"]
                            if item["scoring"] == "tool"
                        ]
                        self.assertEqual(2, len(chains))
                        for item in chains:
                            self.assertTrue(all(item["core_origin"]["dimensions"].values()))
                            self.assertFalse(item["gemma_info"]["dimensions"]["causal_order"])

    def test_existing_campaign_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            arguments = {
                "family": "toolchain",
                "adapter_config": ROOT / "adapters" / "mock.config.json",
                "output_root": output,
                "campaign_id": "f" * 32,
            }
            run_campaign(**arguments)
            with self.assertRaises(InvalidInput):
                run_campaign(**arguments)


if __name__ == "__main__":
    unittest.main()
