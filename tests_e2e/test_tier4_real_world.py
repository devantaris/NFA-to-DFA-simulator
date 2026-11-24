"""Tier 4: Real-World Workload and Textbook Automata Test Suite.

Validates canonical theoretical computer science benchmarks and protocol models:
- Scenario 1: Binary Numbers Divisible by 3 (Modulo-3 DFA)
- Scenario 2: Substring '001' or Ending in '01' (Union Nondeterministic NFA)
- Scenario 3: Alternating 0s and 1s of Even Length ((01)+ | (10)+)
- Scenario 4: C-Style Identifier Lexical Tokenizer Pattern ([a-zA-Z_][a-zA-Z0-9_]*)
- Scenario 5: TCP Connection Lifecycle State Machine (CLOSED -> SYN_SENT -> ESTABLISHED -> FIN_WAIT)
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

from tests_e2e.api_client import BaseE2ETestCase


class TestTier4RealWorld(BaseE2ETestCase):
    """Tier 4 Real-World Application and Classical Automata Benchmarks."""

    def test_t4_scenario_1_binary_divisible_by_3(self) -> None:
        """Scenario 1: Modulo-3 arithmetic DFA for binary numbers divisible by 3."""
        modulo3_dfa = {
            "name": "Binary_Divisible_By_3",
            "description": "Recognizes binary numbers with remainder 0 modulo 3",
            "states": ["r0", "r1", "r2"],
            "alphabet": ["0", "1"],
            "start_state": "r0",
            "final_states": ["r0"],
            "transitions": [
                {"from": "r0", "symbol": "0", "to": ["r0"]},
                {"from": "r0", "symbol": "1", "to": ["r1"]},
                {"from": "r1", "symbol": "0", "to": ["r2"]},
                {"from": "r1", "symbol": "1", "to": ["r0"]},
                {"from": "r2", "symbol": "0", "to": ["r1"]},
                {"from": "r2", "symbol": "1", "to": ["r2"]},
            ],
        }

        # Conversion check
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": modulo3_dfa})
        self.assertEqual(status, 200)
        self.assertEqual(len(conv_data["minimal_dfa"]["states"]), 3)

        # Multiples of 3 (0, 3, 6, 9, 12, 15, 18)
        positive_vectors = ["0", "11", "110", "1001", "1100", "1111", "10010"]
        for vec in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": modulo3_dfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertTrue(
                sim_data["nfa_simulation"]["accepted"],
                f"Binary multiple of 3 '{vec}' should be accepted",
            )
            self.assertTrue(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["minimal_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

        # Non-multiples of 3 (1, 2, 4, 5, 7, 8, 10)
        negative_vectors = ["1", "10", "100", "101", "111", "1000", "1010"]
        for vec in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": modulo3_dfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertFalse(
                sim_data["nfa_simulation"]["accepted"],
                f"Binary non-multiple '{vec}' should be rejected",
            )
            self.assertFalse(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

    def test_t4_scenario_2_substring_001_or_ends_01(self) -> None:
        """Scenario 2: NFA union for strings containing '001' or ending in '01'."""
        union_nfa = {
            "name": "Contains_001_Or_Ends_01",
            "states": ["q0", "c1", "c2", "c3", "c_acc", "e1", "e2", "e_acc"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["c_acc", "e_acc"],
            "transitions": [
                {"from": "q0", "symbol": "ε", "to": ["c1", "e1"]},
                {"from": "c1", "symbol": "0", "to": ["c1", "c2"]},
                {"from": "c1", "symbol": "1", "to": ["c1"]},
                {"from": "c2", "symbol": "0", "to": ["c3"]},
                {"from": "c3", "symbol": "1", "to": ["c_acc"]},
                {"from": "c_acc", "symbol": "0", "to": ["c_acc"]},
                {"from": "c_acc", "symbol": "1", "to": ["c_acc"]},
                {"from": "e1", "symbol": "0", "to": ["e1", "e2"]},
                {"from": "e1", "symbol": "1", "to": ["e1"]},
                {"from": "e2", "symbol": "1", "to": ["e_acc"]},
            ],
        }

        status, conv_data, _ = self.client.post("/api/convert", {"nfa": union_nfa})
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", conv_data)

        positive_vectors = ["001", "01", "101", "0010", "110011", "0001", "1001", "1101"]
        for vec in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": union_nfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertTrue(
                sim_data["nfa_simulation"]["accepted"],
                f"String '{vec}' should be accepted by union NFA",
            )
            self.assertTrue(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

        negative_vectors = ["", "0", "1", "00", "10", "111", "000", "1100"]
        for vec in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": union_nfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertFalse(
                sim_data["nfa_simulation"]["accepted"],
                f"String '{vec}' should be rejected by union NFA",
            )
            self.assertFalse(sim_data["converted_dfa_simulation"]["accepted"])
            self.assertTrue(sim_data["is_equivalent"])

    def test_t4_scenario_3_alternating_even_length(self) -> None:
        """Scenario 3: Strictly alternating 0s and 1s of even length ((01)+ | (10)+)."""
        alternating_dfa = {
            "name": "Alternating_Even_Length",
            "states": ["S", "A0", "A1", "B1", "B0", "DEAD"],
            "alphabet": ["0", "1"],
            "start_state": "S",
            "final_states": ["A1", "B0"],
            "transitions": [
                {"from": "S", "symbol": "0", "to": ["A0"]},
                {"from": "S", "symbol": "1", "to": ["B1"]},
                {"from": "A0", "symbol": "1", "to": ["A1"]},
                {"from": "A0", "symbol": "0", "to": ["DEAD"]},
                {"from": "A1", "symbol": "0", "to": ["A0"]},
                {"from": "A1", "symbol": "1", "to": ["DEAD"]},
                {"from": "B1", "symbol": "0", "to": ["B0"]},
                {"from": "B1", "symbol": "1", "to": ["DEAD"]},
                {"from": "B0", "symbol": "1", "to": ["B1"]},
                {"from": "B0", "symbol": "0", "to": ["DEAD"]},
                {"from": "DEAD", "symbol": "0", "to": ["DEAD"]},
                {"from": "DEAD", "symbol": "1", "to": ["DEAD"]},
            ],
        }

        positive_vectors = ["01", "10", "0101", "1010", "010101", "101010", "01010101"]
        for vec in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": alternating_dfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"], f"Expected '{vec}' to accept")
            self.assertTrue(sim_data["is_equivalent"])

        negative_vectors = ["", "0", "1", "00", "11", "010", "101", "01011", "10100", "0010"]
        for vec in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": alternating_dfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertFalse(sim_data["nfa_simulation"]["accepted"], f"Expected '{vec}' to reject")
            self.assertTrue(sim_data["is_equivalent"])

    def test_t4_scenario_4_c_identifier_tokenizer(self) -> None:
        """Scenario 4: Lexical tokenizer pattern [a-zA-Z_][a-zA-Z0-9_]*."""
        tokenizer_nfa = {
            "name": "C_Identifier_Tokenizer",
            "states": ["q_init", "q_valid", "q_err"],
            "alphabet": ["L", "D", "_"],
            "start_state": "q_init",
            "final_states": ["q_valid"],
            "transitions": [
                {"from": "q_init", "symbol": "L", "to": ["q_valid"]},
                {"from": "q_init", "symbol": "_", "to": ["q_valid"]},
                {"from": "q_init", "symbol": "D", "to": ["q_err"]},
                {"from": "q_valid", "symbol": "L", "to": ["q_valid"]},
                {"from": "q_valid", "symbol": "D", "to": ["q_valid"]},
                {"from": "q_valid", "symbol": "_", "to": ["q_valid"]},
                {"from": "q_err", "symbol": "L", "to": ["q_err"]},
                {"from": "q_err", "symbol": "D", "to": ["q_err"]},
                {"from": "q_err", "symbol": "_", "to": ["q_err"]},
            ],
        }

        # Conversion check
        status, conv_data, _ = self.client.post("/api/convert", {"nfa": tokenizer_nfa})
        self.assertEqual(status, 200)
        self.assertEqual(len(conv_data["minimal_dfa"]["states"]), 3)

        positive_vectors = ["L", "_", "LL", "L_", "LD", "_L", "_D", "__", "L_D_L"]
        for vec in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": tokenizer_nfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"], f"Expected identifier '{vec}' to accept")
            self.assertTrue(sim_data["is_equivalent"])

        negative_vectors = ["", "D", "DL", "D_", "DDD", "D_L"]
        for vec in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": tokenizer_nfa, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertFalse(sim_data["nfa_simulation"]["accepted"], f"Expected invalid identifier '{vec}' to reject")
            self.assertTrue(sim_data["is_equivalent"])

    def test_t4_scenario_5_tcp_connection_lifecycle(self) -> None:
        """Scenario 5: TCP connection lifecycle FSM."""
        tcp_fsm = {
            "name": "TCP_Connection_FSM",
            "states": ["CLOSED", "SYN_SENT", "ESTABLISHED", "FIN_WAIT", "ERROR"],
            "alphabet": ["s", "a", "f", "k"],
            "start_state": "CLOSED",
            "final_states": ["ESTABLISHED"],
            "transitions": [
                {"from": "CLOSED", "symbol": "s", "to": ["SYN_SENT"]},
                {"from": "CLOSED", "symbol": "a", "to": ["ERROR"]},
                {"from": "CLOSED", "symbol": "f", "to": ["ERROR"]},
                {"from": "CLOSED", "symbol": "k", "to": ["ERROR"]},
                {"from": "SYN_SENT", "symbol": "a", "to": ["ESTABLISHED"]},
                {"from": "SYN_SENT", "symbol": "s", "to": ["ERROR"]},
                {"from": "SYN_SENT", "symbol": "f", "to": ["ERROR"]},
                {"from": "SYN_SENT", "symbol": "k", "to": ["ERROR"]},
                {"from": "ESTABLISHED", "symbol": "f", "to": ["FIN_WAIT"]},
                {"from": "ESTABLISHED", "symbol": "s", "to": ["ERROR"]},
                {"from": "ESTABLISHED", "symbol": "a", "to": ["ERROR"]},
                {"from": "ESTABLISHED", "symbol": "k", "to": ["ERROR"]},
                {"from": "FIN_WAIT", "symbol": "k", "to": ["CLOSED"]},
                {"from": "FIN_WAIT", "symbol": "s", "to": ["ERROR"]},
                {"from": "FIN_WAIT", "symbol": "a", "to": ["ERROR"]},
                {"from": "FIN_WAIT", "symbol": "f", "to": ["ERROR"]},
                {"from": "ERROR", "symbol": "s", "to": ["ERROR"]},
                {"from": "ERROR", "symbol": "a", "to": ["ERROR"]},
                {"from": "ERROR", "symbol": "f", "to": ["ERROR"]},
                {"from": "ERROR", "symbol": "k", "to": ["ERROR"]},
            ],
        }

        # Successful connection Handshake & Reconnect cycle
        positive_vectors = ["sa", "safksa"]
        for vec in positive_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": tcp_fsm, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertTrue(sim_data["nfa_simulation"]["accepted"], f"Protocol path '{vec}' should reach ESTABLISHED")
            self.assertTrue(sim_data["is_equivalent"])

        # Invalid, out-of-order, or incomplete protocol events
        negative_vectors = ["", "s", "a", "f", "saf", "safk", "ss", "aa"]
        for vec in negative_vectors:
            status, sim_data, _ = self.client.post(
                "/api/simulate", {"nfa": tcp_fsm, "input_string": vec}
            )
            self.assertEqual(status, 200)
            self.assertFalse(sim_data["nfa_simulation"]["accepted"], f"Protocol path '{vec}' should reject")
            self.assertTrue(sim_data["is_equivalent"])


if __name__ == "__main__":
    unittest.main()
