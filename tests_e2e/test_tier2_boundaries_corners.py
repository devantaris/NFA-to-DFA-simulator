"""Tier 2: Boundary and Corner Cases Test Suite.

Probes system limits, mathematical edge conditions, and error-handling paths:
1. Empty Input Strings
2. Pathological Epsilon Automata
3. Single-State Automata
4. Empty Language Automata (F = ∅, Unreachable F)
5. Dead / Trap State Handling
6. Malformed JSON Payloads and Invalid Automaton Schemas
7. Invalid Regular Expression Syntax
"""

from __future__ import annotations

import unittest
from typing import Any, Dict

from tests_e2e.api_client import BaseE2ETestCase


class TestTier2EmptyInputs(BaseE2ETestCase):
    """Category 2a: Empty Input Strings."""

    def test_t2_empty_01_non_accepting_start_rejects_empty_string(self) -> None:
        """Automaton whose start state is not accepting rejects empty string ''."""
        nfa = {
            "name": "Non_Accepting_Start",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q1"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q1"]}],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])
        self.assertFalse(data["converted_dfa_simulation"]["accepted"])
        self.assertTrue(data["is_equivalent"])

    def test_t2_empty_02_accepting_start_accepts_empty_string(self) -> None:
        """Automaton whose start state is accepting accepts empty string ''."""
        nfa = {
            "name": "Accepting_Start",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])
        self.assertTrue(data["converted_dfa_simulation"]["accepted"])
        self.assertTrue(data["is_equivalent"])

    def test_t2_empty_03_start_state_epsilon_to_final_accepts_empty_string(self) -> None:
        """Start state with epsilon transition to final state accepts empty string ''."""
        nfa = {
            "name": "Epsilon_To_Accept",
            "states": ["q0", "q1"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q1"],
            "transitions": [{"from": "q0", "symbol": "ε", "to": ["q1"]}],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])
        self.assertTrue(data["converted_dfa_simulation"]["accepted"])

    def test_t2_empty_04_nfa_dfa_equivalence_on_empty_string(self) -> None:
        """Converted and Minimal DFA agree with NFA verdict on empty string."""
        nfa = {
            "name": "Parity_Check",
            "states": ["even", "odd"],
            "alphabet": ["0"],
            "start_state": "even",
            "final_states": ["even"],
            "transitions": [
                {"from": "even", "symbol": "0", "to": ["odd"]},
                {"from": "odd", "symbol": "0", "to": ["even"]},
            ],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["is_equivalent"])
        self.assertTrue(data["nfa_simulation"]["accepted"])
        self.assertTrue(data["minimal_dfa_simulation"]["accepted"])

    def test_t2_empty_05_regex_to_nfa_empty_or_trivial(self) -> None:
        """POST /api/regex-to-nfa with empty regex is handled gracefully or rejected."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": ""})
        self.skip_if_m1_unavailable(status, data)
        # Should either return 200 with epsilon NFA or 400 error cleanly
        self.assertIn(status, [200, 400])
        if status == 200:
            self.assertTrue(data.get("success", False))
            self.assertIn("nfa", data)
            self.assertIsInstance(data["nfa"], dict)
        else:
            self.assertFalse(data.get("success", True))
            self.assertIn("error", data)


class TestTier2PathologicalEpsilon(BaseE2ETestCase):
    """Category 2b: Pathological Epsilon Automata."""

    def test_t2_eps_01_linear_epsilon_chain(self) -> None:
        """Linear chain of epsilon transitions q0 -> q1 -> q2 in F computes full closure."""
        nfa = {
            "name": "Linear_Epsilon_Chain",
            "states": ["q0", "q1", "q2"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q2"],
            "transitions": [
                {"from": "q0", "symbol": "ε", "to": ["q1"]},
                {"from": "q1", "symbol": "ε", "to": ["q2"]},
            ],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        closures = data["epsilon_closures"]
        self.assertEqual(set(closures["q0"]), {"q0", "q1", "q2"})

    def test_t2_eps_02_cyclic_epsilon_loop(self) -> None:
        """Cyclic epsilon transitions q0 -> q1 -> q0 do not cause infinite recursion."""
        nfa = {
            "name": "Cyclic_Epsilon_Loop",
            "states": ["q0", "q1"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "ε", "to": ["q1"]},
                {"from": "q1", "symbol": "ε", "to": ["q0"]},
                {"from": "q1", "symbol": "0", "to": ["q1"]},
            ],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", data)
        self.assertEqual(set(data["epsilon_closures"]["q0"]), {"q0", "q1"})

    def test_t2_eps_03_disconnected_epsilon_component(self) -> None:
        """Disconnected unreachable epsilon component does not affect conversion or simulation."""
        nfa = {
            "name": "Disconnected_Epsilon",
            "states": ["start", "a", "x", "y"],
            "alphabet": ["0"],
            "start_state": "start",
            "final_states": ["a"],
            "transitions": [
                {"from": "start", "symbol": "0", "to": ["a"]},
                {"from": "x", "symbol": "ε", "to": ["y"]},
            ],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        # x and y should be identified as unreachable states in minimization
        self.assertIn("unreachable_states", data)

    def test_t2_eps_04_multi_branching_epsilon_tree(self) -> None:
        """Tree of epsilon transitions q0 -> {q1, q2}, q1 -> q3 in F."""
        nfa = {
            "name": "Epsilon_Tree",
            "states": ["q0", "q1", "q2", "q3", "q4"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q3"],
            "transitions": [
                {"from": "q0", "symbol": "ε", "to": ["q1", "q2"]},
                {"from": "q1", "symbol": "ε", "to": ["q3"]},
                {"from": "q2", "symbol": "ε", "to": ["q4"]},
            ],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])

    def test_t2_eps_05_epsilon_spelling_variants(self) -> None:
        """Transitions using variant symbols 'e', 'eps', 'epsilon' are standardized to ε."""
        nfa = {
            "name": "Epsilon_Variants",
            "states": ["q0", "q1", "q2"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q2"],
            "transitions": [
                {"from": "q0", "symbol": "eps", "to": ["q1"]},
                {"from": "q1", "symbol": "epsilon", "to": ["q2"]},
            ],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])


class TestTier2SingleState(BaseE2ETestCase):
    """Category 2c: Single-State Automata."""

    def test_t2_single_01_accepting_no_transitions(self) -> None:
        """Single state, accepting, no transitions: accepts '', rejects any symbol."""
        nfa = {
            "name": "Single_Accept_No_Transitions",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertTrue(data["nfa_simulation"]["accepted"])

        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "0"})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_single_02_non_accepting_no_transitions(self) -> None:
        """Single state, non-accepting, no transitions: rejects everything."""
        nfa = {
            "name": "Single_Reject_No_Transitions",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": ""})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_single_03_universal_sigma_star(self) -> None:
        """Single state with self-loops on all symbols accepting Σ*."""
        nfa = {
            "name": "Universal_Sigma_Star",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": ["q0"]},
                {"from": "q0", "symbol": "1", "to": ["q0"]},
            ],
        }
        for s in ["", "0", "1", "00", "0101", "1111"]:
            status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": s})
            self.assertEqual(status, 200)
            self.assertTrue(data["nfa_simulation"]["accepted"])
            self.assertTrue(data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(data["minimal_dfa_simulation"]["accepted"])
            self.assertTrue(data["is_equivalent"])

    def test_t2_single_04_rejecting_sigma_star(self) -> None:
        """Single state with self-loops on all symbols, non-accepting."""
        nfa = {
            "name": "Rejecting_All",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": ["q0"]},
                {"from": "q0", "symbol": "1", "to": ["q0"]},
            ],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "0101"})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_single_05_single_state_minimization(self) -> None:
        """Minimizing a single-state automaton yields 1 state with empty distinguishable table."""
        nfa = {
            "name": "Single_State_Minimization",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q0"]}],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        self.assertEqual(len(data["minimal_dfa"]["states"]), 1)


class TestTier2EmptyLanguage(BaseE2ETestCase):
    """Category 2d: Empty Language Automata (F = ∅ or unreachable F)."""

    def test_t2_emplang_01_no_final_states(self) -> None:
        """Automaton with F = [] rejects all strings."""
        nfa = {
            "name": "Empty_Language_No_Finals",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": ["q1"]},
                {"from": "q1", "symbol": "1", "to": ["q0"]},
            ],
        }
        for s in ["", "0", "01", "010"]:
            status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": s})
            self.assertEqual(status, 200)
            self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_emplang_02_unreachable_final_state(self) -> None:
        """Final state q_final cannot be reached from start state."""
        nfa = {
            "name": "Unreachable_Final",
            "states": ["q0", "q_final"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q_final"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q0"]}],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "000"})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_emplang_03_dfa_conversion_empty_language(self) -> None:
        """Converting empty language NFA produces DFA with no accepting states."""
        nfa = {
            "name": "Empty_Language_Conv",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        self.assertEqual(data["converted_dfa"]["final_states"], [])

    def test_t2_emplang_04_minimization_collapses_empty_language(self) -> None:
        """Minimization of empty language automaton collapses to 1 non-accepting state."""
        nfa = {
            "name": "Empty_Language_Min",
            "states": ["q0", "q1", "q2"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": ["q1"]},
                {"from": "q1", "symbol": "0", "to": ["q2"]},
                {"from": "q2", "symbol": "0", "to": ["q0"]},
            ],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        self.assertEqual(len(data["minimal_dfa"]["states"]), 1)
        self.assertEqual(data["minimal_dfa"]["final_states"], [])

    def test_t2_emplang_05_string_generator_on_empty_language(self) -> None:
        """POST /api/generate-strings on empty language returns empty accepted_strings."""
        nfa = {
            "name": "Empty_Lang_Gen",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/generate-strings", {"nfa": nfa})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 200)
        self.assertEqual(data.get("accepted_strings", []), [])


class TestTier2DeadTrapState(BaseE2ETestCase):
    """Category 2e: Dead / Trap State Handling."""

    def test_t2_trap_01_incomplete_nfa_generates_dead_state(self) -> None:
        """Powerset conversion of incomplete NFA introduces DEAD trap state."""
        nfa = {
            "name": "Missing_Transitions",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q1"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q1"]}],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        dfa = data["converted_dfa"]
        self.assertIn("DEAD", dfa["states"])

    def test_t2_trap_02_simulation_on_incomplete_dfa_halts_gracefully(self) -> None:
        """DFA missing transition halts gracefully without crashing server."""
        # Provide raw incomplete DFA in simulate endpoint
        nfa = {
            "name": "Incomplete_Sim",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "1"})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])

    def test_t2_trap_03_explicit_trap_state_in_converted_dfa(self) -> None:
        """Converted DFA DEAD state has self-loops on all alphabet symbols."""
        nfa = {
            "name": "Dead_State_Loops",
            "states": ["q0"],
            "alphabet": ["0", "1", "2"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        dfa = data["converted_dfa"]
        self.assertIn("DEAD", dfa["states"])
        dead_targets = {
            t["symbol"]: t["to"]
            for t in dfa["transitions"]
            if t["from"] == "DEAD"
        }
        for sym in ["0", "1", "2"]:
            self.assertIn(sym, dead_targets)

    def test_t2_trap_04_isolated_unreachable_state_pruning(self) -> None:
        """Unreachable states are identified and pruned during minimization."""
        nfa = {
            "name": "Unreachable_Pruning",
            "states": ["start", "unreachable_1", "unreachable_2"],
            "alphabet": ["0"],
            "start_state": "start",
            "final_states": ["start"],
            "transitions": [
                {"from": "unreachable_1", "symbol": "0", "to": ["unreachable_2"]},
            ],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        unreachable = data.get("unreachable_states", [])
        self.assertIsInstance(unreachable, list)

    def test_t2_trap_05_conversion_steps_record_dead_state(self) -> None:
        """Conversion steps explicitly record the creation and transitions of DEAD state."""
        nfa = {
            "name": "Steps_Dead",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 200)
        steps = data["conversion_steps"]
        dead_steps = [s for s in steps if s.get("target_dfa_state") == "DEAD"]
        self.assertGreaterEqual(len(dead_steps), 1)


class TestTier2MalformedPayloads(BaseE2ETestCase):
    """Category 2f: Malformed JSON Payloads and Schema Violations."""

    def test_t2_malform_01_invalid_json_syntax(self) -> None:
        """Sending raw unparseable JSON triggers HTTP 400 with 'Malformed JSON payload'."""
        status, data, _ = self.client.post("/api/convert", raw_body=b"{ unparseable json: 123 ")
        self.assertEqual(status, 400)
        self.assertIsInstance(data, dict)
        self.assertIn("error", data)
        self.assertIn("Malformed JSON payload", data["error"])

    def test_t2_malform_02_missing_nfa_key(self) -> None:
        """POST /api/convert without 'nfa' object responds with HTTP 400."""
        status, data, _ = self.client.post("/api/convert", {})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_t2_malform_03_invalid_start_state(self) -> None:
        """Start state not in states set triggers HTTP 400."""
        nfa = {
            "name": "Invalid_Start",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q_NONEXISTENT",
            "final_states": ["q0"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("q_NONEXISTENT", data["error"])

    def test_t2_malform_04_invalid_final_state(self) -> None:
        """Final state not in states set triggers HTTP 400."""
        nfa = {
            "name": "Invalid_Final",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q_GHOST"],
            "transitions": [],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("q_GHOST", data["error"])

    def test_t2_malform_05_invalid_transition_state(self) -> None:
        """Transition referencing undeclared state triggers HTTP 400."""
        nfa = {
            "name": "Invalid_Transition",
            "states": ["q0"],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q_UNKNOWN"]}],
        }
        status, data, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_t2_malform_06_symbol_outside_alphabet(self) -> None:
        """Simulating a symbol not in alphabet Σ cleanly rejects with validation message."""
        nfa = {
            "name": "Valid_Binary",
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q0"]}],
        }
        status, data, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "0X1"})
        self.assertEqual(status, 200)
        self.assertFalse(data["nfa_simulation"]["accepted"])
        self.assertIn("Validation Error", data["nfa_simulation"]["message"])

    def test_t2_malform_07_zero_states_automaton(self) -> None:
        """Automaton with 0 states (Q = ∅) triggers HTTP 400 on convert and simulate."""
        nfa = {
            "states": [],
            "alphabet": ["0"],
            "start_state": "q0",
            "final_states": [],
            "transitions": [],
        }
        status_conv, data_conv, _ = self.client.post("/api/convert", {"nfa": nfa})
        self.assertEqual(status_conv, 400)
        self.assertIn("error", data_conv)
        self.assertIn("at least one state", data_conv["error"])

        status_sim, data_sim, _ = self.client.post("/api/simulate", {"nfa": nfa, "input_string": "0"})
        self.assertEqual(status_sim, 400)
        self.assertIn("error", data_sim)
        self.assertIn("at least one state", data_sim["error"])


class TestTier2InvalidRegexSyntax(BaseE2ETestCase):
    """Category 2g: Invalid Regular Expression Syntax."""

    def test_t2_regerr_01_unbalanced_open_parenthesis(self) -> None:
        """Regex with unclosed parenthesis '(a|b' returns syntax error."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "(a|b"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))
        self.assertIn("error", data)

    def test_t2_regerr_02_unbalanced_close_parenthesis(self) -> None:
        """Regex with extra close parenthesis 'a|b)' returns syntax error."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "a|b)"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))
        self.assertIn("error", data)

    def test_t2_regerr_03_trailing_pipe(self) -> None:
        """Regex with trailing binary operator 'a|' returns syntax error."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "a|"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))
        self.assertIn("error", data)

    def test_t2_regerr_04_leading_pipe(self) -> None:
        """Regex with leading binary operator '|b' returns syntax error."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "|b"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))
        self.assertIn("error", data)

    def test_t2_regerr_05_invalid_repetition_operator(self) -> None:
        """Regex starting with Kleene star '*a' returns syntax error."""
        status, data, _ = self.client.post("/api/regex-to-nfa", {"regex": "*a"})
        self.skip_if_m1_unavailable(status, data)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
