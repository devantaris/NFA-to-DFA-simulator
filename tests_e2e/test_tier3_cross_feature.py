"""Tier 3: Cross-Feature Integration and Pipeline Workflows Test Suite.

Executes end-to-end multi-step scenarios combining multiple system components:
- Workflow A: Full Pipeline (Regex -> NFA -> DFA -> MinDFA -> StringGen -> SimDual)
- Workflow B: Preset Automata Roundtrip & Cross-Model Equivalence
- Workflow C: Fault Injection, Error Isolation, and Resilient Recovery
- Workflow D: Minimization Reduction & Distinguishability Matrix Validation
- Workflow E: Interactive Client Session Simulation
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

from tests_e2e.api_client import BaseE2ETestCase


SAMPLE_REDUNDANT_DFA: Dict[str, Any] = {
    "name": "Redundant_DFA_Minimization_Candidate",
    "description": "DFA containing equivalent states C and D that can be merged",
    "states": ["A", "B", "C", "D", "E"],
    "alphabet": ["0", "1"],
    "start_state": "A",
    "final_states": ["C", "D"],
    "transitions": [
        {"from": "A", "symbol": "0", "to": ["B"]},
        {"from": "A", "symbol": "1", "to": ["A"]},
        {"from": "B", "symbol": "0", "to": ["C"]},
        {"from": "B", "symbol": "1", "to": ["D"]},
        {"from": "C", "symbol": "0", "to": ["E"]},
        {"from": "C", "symbol": "1", "to": ["A"]},
        {"from": "D", "symbol": "0", "to": ["E"]},
        {"from": "D", "symbol": "1", "to": ["A"]},
        {"from": "E", "symbol": "0", "to": ["E"]},
        {"from": "E", "symbol": "1", "to": ["E"]},
    ],
}


class TestTier3CrossFeature(BaseE2ETestCase):
    """Tier 3 Multi-Step Pipeline Workflows."""

    def test_t3_workflow_a_full_pipeline(self) -> None:
        """Workflow A: Regex -> NFA -> DFA -> MinDFA -> StringGen -> SimDual."""
        regex_input = "(0|1)*001(0|1)*"

        # Step 1: Regex to NFA
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": regex_input})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        nfa = data["nfa"]

        # Step 2: Convert NFA to DFA & MinDFA
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", conv_data)
        self.assertIn("minimal_dfa", conv_data)

        # Step 3: Generate accepted and rejected test strings
        status, gen_data, _ = self.client.post(
            "/api/generate-strings",
            {"nfa": nfa, "max_accepted": 3, "max_rejected": 3},
        )
        self.assertEqual(status, 200)
        accepted_strings = gen_data.get("accepted_strings", [])
        rejected_strings = gen_data.get("rejected_strings", [])

        # Step 4: Simulate accepted strings on both NFA and DFA
        for s in accepted_strings:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertTrue(
                sim_data["nfa_simulation"]["accepted"],
                f"Generated accepted string '{s}' failed NFA simulation",
            )
            self.assertTrue(
                sim_data["converted_dfa_simulation"]["accepted"],
                f"Generated accepted string '{s}' failed DFA simulation",
            )
            self.assertTrue(sim_data["is_equivalent"])

        # Step 5: Simulate rejected strings on both NFA and DFA
        for s in rejected_strings:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertFalse(
                sim_data["nfa_simulation"]["accepted"],
                f"Generated rejected string '{s}' was accepted by NFA",
            )
            self.assertFalse(
                sim_data["converted_dfa_simulation"]["accepted"],
                f"Generated rejected string '{s}' was accepted by DFA",
            )
            self.assertTrue(sim_data["is_equivalent"])

    def test_t3_workflow_b_preset_automata_roundtrip(self) -> None:
        """Workflow B: Fetch sample preset, convert to DFA, verify dual equivalence."""
        # Step 1: Fetch presets
        status, data, _ = self.client.get("/api/samples")
        self.assertEqual(status, 200)
        samples = data.get("samples", [])
        self.assertGreaterEqual(len(samples), 1)

        ends_with_01 = next(
            (s for s in samples if "ends_with_01" in s.get("name", "").lower()),
            samples[0],
        )

        # Step 2: Convert to DFA
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": ends_with_01})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", conv_data)
        self.assertIn("minimal_dfa", conv_data)

        # Step 3: Run comprehensive positive & negative test vectors
        positive_vectors = ["01", "101", "001", "11101", "000001", "10101"]
        negative_vectors = ["", "0", "1", "10", "1010", "00", "1111"]

        for s in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": ends_with_01, "input_string": s}
            )
            self.assertEqual(status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"], f"Expected '{s}' to accept")
            self.assertTrue(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["minimal_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

        for s in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": ends_with_01, "input_string": s}
            )
            self.assertEqual(status, 200)
            self.assertFalse(sim_data["nfa_simulation"]["accepted"], f"Expected '{s}' to reject")
            self.assertFalse(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertFalse(sim_data["minimal_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

    def test_t3_workflow_c_fault_injection_and_recovery(self) -> None:
        """Workflow C: Send malformed requests, assert 400, verify server stability."""
        # Fault 1: Malformed raw bytes
        status, err_data, _ = self.client.post(
            "/api/convert", raw_body=b"{ malformed json content"
        )
        self.assertEqual(status, 400)
        self.assertIn("Malformed JSON payload", str(err_data))

        # Fault 2: Invalid start state
        bad_nfa = {
            "name": "Bad_State",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q_NOT_PRESENT",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, err_data, _ = self.client.post("/api/convert", {"nfa": bad_nfa})
        self.assertEqual(status, 400)

        # Recovery 1: GET /api/samples operates normally
        status, samples_data, _ = self.client.get("/api/samples")
        self.assertEqual(status, 200)
        self.assertIn("samples", samples_data)

        # Recovery 2: POST /api/convert with valid NFA succeeds
        valid_nfa = {
            "name": "Valid_NFA",
            "states": ["s0", "s1"],
            "alphabet": ["0", "1"],
            "start_state": "s0",
            "final_states": ["s1"],
            "transitions": [{"from": "s0", "symbol": "0", "to": ["s1"]}],
        }
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": valid_nfa})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", conv_data)

    def test_t3_workflow_d_minimization_reduction(self) -> None:
        """Workflow D: Verify state reduction and distinguishability table on redundant DFA."""
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_REDUNDANT_DFA})
        self.assertEqual(status, 200)

        converted_dfa = conv_data["converted_dfa"]
        minimal_dfa = conv_data["minimal_dfa"]
        dist_table = conv_data["distinguishable_table"]

        # 5 original states (A, B, C, D, E) reduce to 4 states (merging C and D)
        self.assertLess(
            len(minimal_dfa["states"]),
            len(SAMPLE_REDUNDANT_DFA["states"]),
            "Expected minimization to reduce state count",
        )
        self.assertEqual(len(minimal_dfa["states"]), 4)
        self.assertIsInstance(dist_table, dict)

        # Equivalence test on vectors
        test_strings = ["", "0", "1", "00", "01", "000", "010", "001"]
        for s in test_strings:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": SAMPLE_REDUNDANT_DFA, "input_string": s}
            )
            self.assertEqual(status, 200)
            self.assertTrue(sim_data["is_equivalent"])

    def test_t3_workflow_e_client_session_simulation(self) -> None:
        """Workflow E: Full interactive client session simulation."""
        # 1. Page load
        status, _, _ = self.client.get("/")
        self.assertEqual(status, 200)
        status, _, _ = self.client.get("/static/styles.css")
        self.assertEqual(status, 200)
        status, _, _ = self.client.get("/static/app.js")
        self.assertEqual(status, 200)

        # 2. Retrieve samples
        status, samples_data, _ = self.client.get("/api/samples")
        self.assertEqual(status, 200)
        samples = samples_data["samples"]
        self.assertGreaterEqual(len(samples), 2)
        sample = samples[1]  # Contains 00 or 11 with epsilon

        # 3. Convert sample
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": sample})
        self.assertEqual(status, 200)

        # 4. Simulation step checks
        # Accepted string "00"
        status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": sample, "input_string": "00"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(sim_data["nfa_simulation"]["accepted"])
        trace = sim_data["nfa_simulation"]["trace"]
        self.assertGreaterEqual(len(trace), 2)

        # Accepted string "11"
        status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": sample, "input_string": "11"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        # Rejected string "0101"
        status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": sample, "input_string": "0101"}
        )
        self.assertEqual(status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])

        # 5. Out of alphabet validation error
        status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": sample, "input_string": "002"}
        )
        self.assertEqual(status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])
        self.assertIn("Validation Error", sim_data["nfa_simulation"]["message"])


if __name__ == "__main__":
    unittest.main()
