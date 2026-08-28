from __future__ import annotations

import unittest

from elyne_benchmark.common import ROOT, sha256_file
from elyne_benchmark.verify import verify_reference_run, verify_release_manifest
from evals.harness.toolchain_matcher import normalized_exact_target


class FrozenArtifactTests(unittest.TestCase):
    def test_reference_runs_reverify(self) -> None:
        expected = {
            "justesse": "05be9255c66542c35d784eea1eda092153d2378c23f4f53bd2edf812a1b59f84",
            "orchestration": "c98be9d4dc5062cab66ddbf165ce2d3d23519616264fd1d0603edb540e907bba",
            "toolchain": "14931ee92528780b2436ce530c8d43094d098a9d37e1e8a8064400d107bffb96",
        }
        for family, report_hash in expected.items():
            with self.subTest(family=family):
                result = verify_reference_run(family)
                self.assertEqual(result["report_sha256"], report_hash)

    def test_matcher_is_the_frozen_file(self) -> None:
        matcher = ROOT / "evals" / "harness" / "toolchain_matcher.py"
        self.assertEqual(
            sha256_file(matcher),
            "56736f207a207dc04b5262996160c54d367be4e99f0d670adc700a3d61317260",
        )

    def test_toolchain_final_match_is_strict(self) -> None:
        self.assertTrue(normalized_exact_target('{"target":"TARGET-ABC"}', "TARGET-ABC"))
        self.assertFalse(normalized_exact_target('Result: TARGET-ABC', "TARGET-ABC"))
        self.assertFalse(normalized_exact_target('{"target":"TARGET-ABC-extra"}', "TARGET-ABC"))
        self.assertFalse(normalized_exact_target('{"target":"TARGET-ABC","note":"ok"}', "TARGET-ABC"))
        self.assertFalse(normalized_exact_target('{"target":"bad","target":"TARGET-ABC"}', "TARGET-ABC"))

    def test_orchestration_v2_contains_only_opaque_tool_chains(self) -> None:
        from elyne_benchmark.common import load_battery

        battery, _ = load_battery("orchestration")
        self.assertEqual(2, battery["revision"])
        cases = [case for case in battery["cases"] if case["case_type"] == "tool"]
        self.assertEqual(
            {"orch-toolchain-list-read", "orch-toolchain-search-read"},
            {case["id"] for case in cases},
        )
        for case in cases:
            self.assertEqual(2, len(case["toolchain"]["expected_calls"]))
            self.assertNotIn(case["toolchain"]["final_token"], case["prompt"])

    def test_release_manifest_covers_every_public_file(self) -> None:
        result = verify_release_manifest()
        self.assertGreater(result["files"], 100)


if __name__ == "__main__":
    unittest.main()
