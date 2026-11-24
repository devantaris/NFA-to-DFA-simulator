"""Tier 1: Comprehensive Happy-Path Feature Coverage Test Suite.

Validates core functional requirements across all REST endpoints and static assets:
1. Static Web Assets & UI Entrypoint
2. Sample Automata Retrieval (/api/samples)
3. NFA to DFA Conversion (/api/convert)
4. Step-by-Step Simulation (/api/simulate)
5. Thompson Regex-to-NFA Conversion (/api/regex-to-nfa)
6. Automated Test String Generator (/api/generate-strings)
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

from SourceCode.nfa import NFA
from tests_e2e.api_client import BaseE2ETestCase


SAMPLE_ENDS_WITH_01: Dict[str, Any] = {
    "name": "Ends_With_01",
    "description": "Recognizes binary strings ending with 01",
    "states": ["q0", "q1", "q2"],
    "alphabet": ["0", "1"],
    "start_state": "q0",
    "final_states": ["q2"],
    "transitions": [
        {"from": "q0", "symbol": "0", "to": ["q0", "q1"]},
        {"from": "q0", "symbol": "1", "to": ["q0"]},
        {"from": "q1", "symbol": "1", "to": ["q2"]},
    ],
}

SAMPLE_CONTAINS_00_OR_11_EPSILON: Dict[str, Any] = {
    "name": "Contains_00_or_11_Epsilon",
    "description": "Uses epsilon transitions to branch to 00 detector or 11 detector",
    "states": ["q0", "q1", "q2", "q3", "q4", "q5", "q6"],
    "alphabet": ["0", "1"],
    "start_state": "q0",
    "final_states": ["q6"],
    "transitions": [
        {"from": "q0", "symbol": "ε", "to": ["q1", "q3"]},
        {"from": "q1", "symbol": "0", "to": ["q2"]},
        {"from": "q2", "symbol": "0", "to": ["q6"]},
        {"from": "q3", "symbol": "1", "to": ["q4"]},
        {"from": "q4", "symbol": "1", "to": ["q6"]},
        {"from": "q6", "symbol": "0", "to": ["q6"]},
        {"from": "q6", "symbol": "1", "to": ["q6"]},
    ],
}

SAMPLE_CYCLIC_EPSILON: Dict[str, Any] = {
    "name": "Cyclic_Epsilon_NFA",
    "description": "NFA with a directed cycle of epsilon transitions: A -> B -> C -> A",
    "states": ["A", "B", "C", "D"],
    "alphabet": ["0", "1"],
    "start_state": "A",
    "final_states": ["D"],
    "transitions": [
        {"from": "A", "symbol": "ε", "to": ["B"]},
        {"from": "B", "symbol": "ε", "to": ["C"]},
        {"from": "C", "symbol": "ε", "to": ["A"]},
        {"from": "B", "symbol": "0", "to": ["D"]},
        {"from": "C", "symbol": "1", "to": ["D"]},
    ],
}

SAMPLE_INCOMPLETE: Dict[str, Any] = {
    "name": "Incomplete_DFA_Test",
    "description": "Automaton with missing transitions to test trap/dead state logic",
    "states": ["q0", "q1"],
    "alphabet": ["0", "1"],
    "start_state": "q0",
    "final_states": ["q1"],
    "transitions": [
        {"from": "q0", "symbol": "0", "to": ["q1"]},
    ],
}

SAMPLE_ALREADY_DFA: Dict[str, Any] = {
    "name": "Already_DFA",
    "states": ["s0", "s1"],
    "alphabet": ["0", "1"],
    "start_state": "s0",
    "final_states": ["s1"],
    "transitions": [
        {"from": "s0", "symbol": "0", "to": ["s1"]},
        {"from": "s0", "symbol": "1", "to": ["s0"]},
        {"from": "s1", "symbol": "0", "to": ["s1"]},
        {"from": "s1", "symbol": "1", "to": ["s0"]},
    ],
}


class TestTier1StaticAssets(BaseE2ETestCase):
    """Feature 1: Static Web Assets & UI Entrypoint."""

    def test_t1_asset_01_root_returns_html(self) -> None:
        """GET / returns HTTP 200 with text/html content type and document structure."""
        status, data, headers = self.client.get("/")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
        self.assertIn("text/html", content_type)
        self.assertIsInstance(data, str)
        self.assertIn("<!DOCTYPE html>", data)
        self.assertIn("<html", data)

    def test_t1_asset_02_index_html_identical_to_root(self) -> None:
        """GET /index.html returns HTTP 200 identical to GET /."""
        status_root, data_root, _ = self.client.get("/")
        status_idx, data_idx, _ = self.client.get("/index.html")
        self.assertEqual(status_idx, 200)
        self.assertEqual(status_root, status_idx)
        self.assertEqual(data_root, data_idx)

    def test_t1_asset_03_styles_css_returns_css_tokens(self) -> None:
        """GET /static/styles.css returns HTTP 200 with text/css."""
        status, data, headers = self.client.get("/static/styles.css")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
        self.assertIn("text/css", content_type)
        self.assertIsInstance(data, str)
        self.assertGreater(len(data), 50)

    def test_t1_asset_04_app_js_returns_javascript(self) -> None:
        """GET /static/app.js returns HTTP 200 with javascript content type."""
        status, data, headers = self.client.get("/static/app.js")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
        self.assertTrue(
            "javascript" in content_type or "text/plain" in content_type,
            f"Unexpected Content-Type: {content_type}",
        )
        self.assertIsInstance(data, str)
        self.assertGreater(len(data), 100)

    def test_t1_asset_05_graph_manager_or_static_asset(self) -> None:
        """GET /static/graph_manager.js returns HTTP 200 if present or 404 before M3."""
        status, data, headers = self.client.get("/static/graph_manager.js")
        self.assertIn(status, [200, 404])
        if status == 200:
            content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
            self.assertTrue("javascript" in content_type or "text/plain" in content_type)

    def test_t1_asset_06_nonexistent_asset_returns_404(self) -> None:
        """GET /static/nonexistent_xyz_123.css cleanly returns HTTP 404."""
        status, data, _ = self.client.get("/static/nonexistent_xyz_123.css")
        self.assertEqual(status, 404)


class TestTier1SampleRetrieval(BaseE2ETestCase):
    """Feature 2: Sample Automata Retrieval (/api/samples)."""

    def test_t1_sample_01_samples_endpoint_status_and_count(self) -> None:
        """GET /api/samples returns HTTP 200 with samples list length >= 5."""
        status, data, headers = self.client.get("/api/samples")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
        self.assertIn("application/json", content_type)
        self.assertIsInstance(data, dict)
        self.assertIn("samples", data)
        self.assertIsInstance(data["samples"], list)
        self.assertGreaterEqual(len(data["samples"]), 5)

    def test_t1_sample_02_sample_ends_with_01(self) -> None:
        """GET /api/samples includes sample 'Ends_With_01' matching specification."""
        _, data, _ = self.client.get("/api/samples")
        samples = data["samples"]
        matching = [s for s in samples if "ends_with_01" in s.get("name", "").lower()]
        self.assertGreaterEqual(len(matching), 1, "Ends_With_01 sample not found in samples list")
        sample = matching[0]
        self.assertIn("0", sample["alphabet"])
        self.assertIn("1", sample["alphabet"])
        self.assertEqual(sample["start_state"], "q0")
        self.assertEqual(sample["final_states"], ["q2"])

    def test_t1_sample_03_sample_contains_00_epsilon(self) -> None:
        """GET /api/samples includes sample with epsilon transitions."""
        _, data, _ = self.client.get("/api/samples")
        samples = data["samples"]
        matching = [
            s for s in samples
            if any(t.get("symbol") in ("ε", "e", "E", "eps", "epsilon") for t in s.get("transitions", []))
        ]
        self.assertGreaterEqual(len(matching), 1, "Epsilon sample not found in samples list")

    def test_t1_sample_04_sample_cyclic_epsilon(self) -> None:
        """GET /api/samples includes cyclic epsilon sample."""
        _, data, _ = self.client.get("/api/samples")
        samples = data["samples"]
        matching = [s for s in samples if "cyclic" in s.get("name", "").lower()]
        self.assertGreaterEqual(len(matching), 1, "Cyclic epsilon sample not found in samples list")
        cyclic_sample = matching[0]
        self.assertIn("A", cyclic_sample["states"])
        self.assertIn("B", cyclic_sample["states"])
        self.assertIn("C", cyclic_sample["states"])

    def test_t1_sample_05_all_samples_deserializable_as_nfa(self) -> None:
        """Every sample returned by /api/samples can be deserialized via NFA.from_dict()."""
        _, data, _ = self.client.get("/api/samples")
        for sample in data["samples"]:
            nfa = NFA.from_dict(sample)
            self.assertIsNotNone(nfa)
            self.assertEqual(nfa.start_state, sample["start_state"])
            self.assertEqual(nfa.final_states, set(sample["final_states"]))


class TestTier1Conversion(BaseE2ETestCase):
    """Feature 3: NFA to DFA Conversion (/api/convert)."""

    def test_t1_conv_01_ends_with_01(self) -> None:
        """POST /api/convert on Ends_With_01 returns valid DFA and conversion steps."""
        status, data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_ENDS_WITH_01})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", data)
        self.assertIn("minimal_dfa", data)
        self.assertIn("conversion_steps", data)
        self.assertIn("state_mapping", data)
        self.assertIn("distinguishable_table", data)

        dfa = data["converted_dfa"]
        self.assertIsInstance(dfa["states"], list)
        self.assertIn("start_state", dfa)
        self.assertIsInstance(dfa["final_states"], list)
        self.assertGreater(len(data["conversion_steps"]), 0)

    def test_t1_conv_02_branching_epsilon(self) -> None:
        """POST /api/convert on branching epsilon NFA computes start state closure."""
        status, data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_CONTAINS_00_OR_11_EPSILON})
        self.assertEqual(status, 200)
        self.assertIn("epsilon_closures", data)
        closures = data["epsilon_closures"]
        self.assertIn("q0", closures)
        q0_closure = closures["q0"]
        self.assertIn("q0", q0_closure)
        self.assertIn("q1", q0_closure)
        self.assertIn("q3", q0_closure)

    def test_t1_conv_03_cyclic_epsilon(self) -> None:
        """POST /api/convert on cyclic epsilon NFA terminates without infinite loop."""
        status, data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_CYCLIC_EPSILON})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", data)
        closures = data["epsilon_closures"]
        self.assertIn("A", closures)
        # Cycle A -> B -> C -> A means closure of A is {A, B, C}
        self.assertEqual(set(closures["A"]), {"A", "B", "C"})

    def test_t1_conv_04_incomplete_nfa_creates_dead_state(self) -> None:
        """POST /api/convert on incomplete NFA introduces DEAD trap state."""
        status, data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_INCOMPLETE})
        self.assertEqual(status, 200)
        dfa = data["converted_dfa"]
        self.assertIn("DEAD", dfa["states"])
        # DEAD state has transitions to DEAD on all symbols
        dead_transitions = [
            t for t in dfa["transitions"]
            if t["from"] == "DEAD"
        ]
        symbols_covered = {t["symbol"] for t in dead_transitions}
        self.assertEqual(symbols_covered, set(SAMPLE_INCOMPLETE["alphabet"]))

    def test_t1_conv_05_already_deterministic_dfa(self) -> None:
        """POST /api/convert on already-deterministic DFA preserves language idempotently."""
        status, data, _ = self.client.post("/api/convert", {"nfa": SAMPLE_ALREADY_DFA})
        self.assertEqual(status, 200)
        min_dfa = data["minimal_dfa"]
        self.assertLessEqual(len(min_dfa["states"]), len(SAMPLE_ALREADY_DFA["states"]))


class TestTier1Simulation(BaseE2ETestCase):
    """Feature 4: Step-by-Step Automaton Simulation (/api/simulate)."""

    def test_t1_sim_01_accepted_string(self) -> None:
        """POST /api/simulate with '10101' on Ends_With_01 accepts on all 3 models."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "input_string": "10101"}
        status, data, _ = self.client.post("/api/simulate", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])
        self.assertTrue(data["converted_dfa_simulation"]["accepted"])
        self.assertTrue(data["minimal_dfa_simulation"]["accepted"])
        self.assertTrue(data["is_equivalent"])

    def test_t1_sim_02_rejected_string(self) -> None:
        """POST /api/simulate with '1010' on Ends_With_01 rejects on all 3 models."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "input_string": "1010"}
        status, data, _ = self.client.post("/api/simulate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])
        self.assertFalse(data["converted_dfa_simulation"]["accepted"])
        self.assertFalse(data["minimal_dfa_simulation"]["accepted"])
        self.assertTrue(data["is_equivalent"])

    def test_t1_sim_03_epsilon_branch_simulation(self) -> None:
        """POST /api/simulate on epsilon branching NFA with '11' evaluates accepted."""
        payload = {"nfa": SAMPLE_CONTAINS_00_OR_11_EPSILON, "input_string": "11"}
        status, data, _ = self.client.post("/api/simulate", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])
        trace = data["nfa_simulation"]["trace"]
        self.assertGreaterEqual(len(trace), 1)

    def test_t1_sim_04_trace_step_schema_compliance(self) -> None:
        """Verify that trace steps adhere to the documented SimulationStep schema."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "input_string": "01"}
        status, data, _ = self.client.post("/api/simulate", payload)
        self.assertEqual(status, 200)
        trace = data["converted_dfa_simulation"]["trace"]
        for step in trace:
            self.assertIn("step_number", step)
            self.assertIn("current_states", step)
            self.assertIn("symbol_consumed", step)
            self.assertIn("remaining_input", step)
            self.assertIn("next_states", step)
            self.assertIn("description", step)
            self.assertIsInstance(step["step_number"], int)
            self.assertIsInstance(step["description"], str)

    def test_t1_sim_05_multi_symbol_alternating_string(self) -> None:
        """Simulate alternating string '010101' verifying multi-step equivalence."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "input_string": "010101"}
        status, data, _ = self.client.post("/api/simulate", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])
        self.assertTrue(data["converted_dfa_simulation"]["accepted"])
        self.assertTrue(data["is_equivalent"])


class TestTier1RegexToNFA(BaseE2ETestCase):
    """Feature 5: Thompson Regex-to-NFA Conversion (/api/regex-to-nfa)."""

    def test_t1_regex_01_concatenation(self) -> None:
        """POST /api/regex-to-nfa with 'ab' creates NFA accepting 'ab'."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "ab"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("nfa", data)
        nfa_dict = data["nfa"]
        self.assertIn("a", nfa_dict["alphabet"])
        self.assertIn("b", nfa_dict["alphabet"])

        # String simulations: 'ab' accepted, 'ba' rejected
        sim_status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": nfa_dict, "input_string": "ab"}
        )
        self.assertEqual(sim_status, 200)
        self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        sim_status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": nfa_dict, "input_string": "ba"}
        )
        self.assertEqual(sim_status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])

    def test_t1_regex_02_union(self) -> None:
        """POST /api/regex-to-nfa with 'a|b' creates NFA accepting 'a' and 'b'."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "a|b"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("nfa", data)
        nfa_dict = data["nfa"]

        # String simulations: 'a', 'b' accepted, 'ab' rejected
        for s in ["a", "b"]:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa_dict, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        sim_status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": nfa_dict, "input_string": "ab"}
        )
        self.assertEqual(sim_status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])

    def test_t1_regex_03_kleene_star(self) -> None:
        """POST /api/regex-to-nfa with 'a*' creates NFA accepting '', 'a', 'aaa'."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "a*"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("nfa", data)
        nfa_dict = data["nfa"]

        # String simulations: '', 'a', 'aaa' accepted, 'b' rejected
        for s in ["", "a", "aaa"]:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa_dict, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        sim_status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": nfa_dict, "input_string": "b"}
        )
        self.assertEqual(sim_status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])

    def test_t1_regex_04_grouping_and_kleene(self) -> None:
        """POST /api/regex-to-nfa with '(a|b)*c' creates valid NFA."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "(a|b)*c"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("nfa", data)
        nfa_dict = data["nfa"]

        # String simulations: 'c', 'ac', 'bc', 'ababc' accepted, 'a' rejected
        for s in ["c", "ac", "bc", "ababc"]:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa_dict, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        sim_status, sim_data, _ = self.client.post(
            "/api/simulate", {"nfa": nfa_dict, "input_string": "a"}
        )
        self.assertEqual(sim_status, 200)
        self.assertFalse(sim_data["nfa_simulation"]["accepted"])

    def test_t1_regex_05_binary_language(self) -> None:
        """POST /api/regex-to-nfa with '(0|1)*01' creates valid binary NFA."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "(0|1)*01"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("nfa", data)
        self.assertEqual(set(data["nfa"]["alphabet"]), {"0", "1"})
        nfa_dict = data["nfa"]

        # String simulations: '01', '101', '1101' accepted, '0', '10', '100' rejected
        for s in ["01", "101", "1101"]:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa_dict, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"])

        for s in ["0", "10", "100"]:
            sim_status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": nfa_dict, "input_string": s}
            )
            self.assertEqual(sim_status, 200)
            self.assertFalse(sim_data["nfa_simulation"]["accepted"])


class TestTier1TestStringGenerator(BaseE2ETestCase):
    """Feature 6: Automated Test String Generator (/api/generate-strings)."""

    def test_t1_gen_01_respects_max_counts(self) -> None:
        """POST /api/generate-strings produces requested accepted & rejected counts."""
        payload = {
            "nfa": SAMPLE_ENDS_WITH_01,
            "max_accepted": 3,
            "max_rejected": 3,
        }
        status, data, _ = self.client.post("/api/generate-strings", payload)
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertIn("accepted_strings", data)
        self.assertIn("rejected_strings", data)
        self.assertGreaterEqual(len(data["accepted_strings"]), 2)
        self.assertGreaterEqual(len(data["rejected_strings"]), 2)

    def test_t1_gen_02_accepted_strings_are_valid(self) -> None:
        """Generated accepted strings must end in '01' for Ends_With_01 automaton."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "max_accepted": 3, "max_rejected": 3}
        status, data, _ = self.client.post("/api/generate-strings", payload)
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        for s in data["accepted_strings"]:
            self.assertTrue(s.endswith("01"), f"Accepted string '{s}' does not end with '01'")

    def test_t1_gen_03_rejected_strings_are_valid(self) -> None:
        """Generated rejected strings must not end in '01' for Ends_With_01 automaton."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "max_accepted": 3, "max_rejected": 3}
        status, data, _ = self.client.post("/api/generate-strings", payload)
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        for s in data["rejected_strings"]:
            self.assertFalse(s.endswith("01"), f"Rejected string '{s}' unexpectedly ends with '01'")

    def test_t1_gen_04_distinctness_of_generated_strings(self) -> None:
        """Generated accepted and rejected strings have no duplicates or overlap."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01, "max_accepted": 4, "max_rejected": 4}
        status, data, _ = self.client.post("/api/generate-strings", payload)
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        accepted = data["accepted_strings"]
        rejected = data["rejected_strings"]
        self.assertEqual(len(accepted), len(set(accepted)), "Duplicate accepted strings found")
        self.assertEqual(len(rejected), len(set(rejected)), "Duplicate rejected strings found")
        self.assertEqual(set(accepted) & set(rejected), set(), "Overlap between accepted and rejected")

    def test_t1_gen_05_default_parameters(self) -> None:
        """POST /api/generate-strings functions cleanly without explicit max counts."""
        payload = {"nfa": SAMPLE_ENDS_WITH_01}
        status, data, _ = self.client.post("/api/generate-strings", payload)
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success", False))
        self.assertGreaterEqual(len(data.get("accepted_strings", [])), 2)
        self.assertGreaterEqual(len(data.get("rejected_strings", [])), 2)


if __name__ == "__main__":
    unittest.main()
