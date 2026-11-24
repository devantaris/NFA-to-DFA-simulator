"""Tier 5: Adversarial Stress, Security & Robustness Test Suite.

Combines white-box algorithmic adversarial probes from challenger_adv1
(regex parsing, generator edge cases, powerset explosion, cyclic epsilon networks)
and web server security/concurrency adversarial probes from challenger_adv2
(directory traversal, non-UTF8 payloads, invalid headers, rapid concurrency bursts).
"""

from __future__ import annotations

import concurrent.futures
import json
import socket
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from SourceCode.converter import NFAtoDFAConverter
from SourceCode.dfa import DFA
from SourceCode.minimizer import DFAMinimizer
from SourceCode.models import EPSILON
from SourceCode.nfa import NFA
from SourceCode.regex_parser import RegexParseError, parse_regex_to_nfa
from SourceCode.test_generator import TestStringGenerator
from tests_e2e.api_client import BaseE2ETestCase


# ==============================================================================
# Category A: Algorithmic Adversarial Probes (challenger_adv1)
# ==============================================================================


class TestTier5AdversarialRegex(unittest.TestCase):
    """Adversarial stress tests for regex_parser.py."""

    def test_t5_regex_01_deeply_nested_parentheses_iterative(self) -> None:
        """Depth 500 nested parentheses parse and simulate iteratively without RecursionError."""
        depth = 500
        expr = ("(" * depth) + "a" + (")" * depth)
        nfa = parse_regex_to_nfa(expr)
        self.assertTrue(nfa.simulate("a").accepted)
        self.assertFalse(nfa.simulate("b").accepted)

    def test_t5_regex_02_nested_kleene_stars_and_repetition(self) -> None:
        """Deeply nested stars ((a*)*)* and complex repetitions simulate correctly."""
        exprs = [
            ("((a*)*)*", ["", "a", "aaaa"], ["b", "ab"]),
            ("(((a+)?)*)?", ["", "a", "aaaa"], ["b", "ab"]),
            ("((a|b)*c*)*", ["", "a", "b", "c", "abc", "bbaacc"], ["d"]),
            ("((((a)*)*)*)*", ["", "a", "aaaa"], ["b"]),
        ]
        for expr, should_acc, should_rej in exprs:
            nfa = parse_regex_to_nfa(expr)
            for s in should_acc:
                self.assertTrue(nfa.simulate(s).accepted, f"Failed accept on '{s}' for '{expr}'")
            for s in should_rej:
                self.assertFalse(nfa.simulate(s).accepted, f"Failed reject on '{s}' for '{expr}'")

    def test_t5_regex_03_malformed_syntax_rejection(self) -> None:
        """Malformed repetition, empty alternatives, and trailing operators raise RegexParseError."""
        invalid_patterns = [
            "a**", "a*+", "a++", "a?*", "a+*", "a??",
            "*a", "+a", "?a", "*", "+", "?",
            "(a|)", "(|a)", "(|)", "()", "a|", "|a", "a||b", "(a||b)",
            "((a)", "(a))", "\\", "a\\", "((a|b)*", "(a|b))*"
        ]
        for pat in invalid_patterns:
            with self.assertRaises(RegexParseError, msg=f"Failed to reject invalid regex '{pat}'"):
                parse_regex_to_nfa(pat)

    def test_t5_regex_04_escaped_metacharacters(self) -> None:
        """Escaped operators are treated as literals, not structural syntax."""
        nfa = parse_regex_to_nfa(r"\(\*\+\?\)")
        self.assertTrue(nfa.simulate("(*+?)").accepted)
        self.assertFalse(nfa.simulate("*").accepted)

        # Escaped pipe means literal '|', not union
        nfa_pipe = parse_regex_to_nfa(r"a\|b")
        self.assertTrue(nfa_pipe.simulate("a|b").accepted)
        self.assertFalse(nfa_pipe.simulate("a").accepted)
        self.assertFalse(nfa_pipe.simulate("b").accepted)

    def test_t5_regex_05_unicode_alphabet_support(self) -> None:
        """Unicode characters (Greek, CJK, Emoji) are handled seamlessly as literals."""
        nfa_greek = parse_regex_to_nfa("(α|β)*γ+")
        self.assertTrue(nfa_greek.simulate("βαβγ").accepted)
        self.assertFalse(nfa_greek.simulate("βαβ").accepted)

        nfa_emoji = parse_regex_to_nfa("(🚀|⭐)*✨+")
        self.assertTrue(nfa_emoji.simulate("⭐🚀✨✨").accepted)
        self.assertFalse(nfa_emoji.simulate("🎉").accepted)

    def test_t5_regex_06_catastrophic_backtracking_immunity(self) -> None:
        """Thompson construction guarantees linear time simulation without catastrophic backtracking."""
        nfa = parse_regex_to_nfa("(a*)*b")
        # In PCRE engines, this pattern on 40 'a's causes catastrophic backtracking
        res = nfa.simulate("a" * 40)
        self.assertFalse(res.accepted)
        self.assertTrue(nfa.simulate(("a" * 40) + "b").accepted)


class TestTier5AdversarialGenerator(unittest.TestCase):
    """Adversarial stress tests for test_generator.py."""

    def test_t5_gen_01_universal_and_empty_languages(self) -> None:
        """Universal language yields 0 rejected strings; empty language yields 0 accepted strings."""
        univ_dfa = DFA(
            states={"q0"}, alphabet={"a", "b"},
            transitions={("q0", "a"): "q0", ("q0", "b"): "q0"},
            start_state="q0", final_states={"q0"}, name="Universal"
        )
        gen_u = TestStringGenerator(univ_dfa)
        self.assertTrue(gen_u.is_universal_language())
        res_u = gen_u.generate(max_accepted=5, max_rejected=5)
        self.assertEqual(len(res_u["accepted_strings"]), 5)
        self.assertEqual(len(res_u["rejected_strings"]), 0)

        empty_dfa = DFA(
            states={"q0", "q1"}, alphabet={"a", "b"},
            transitions={("q0", "a"): "q1", ("q1", "b"): "q0"},
            start_state="q0", final_states=set(), name="Empty"
        )
        gen_e = TestStringGenerator(empty_dfa)
        self.assertTrue(gen_e.is_empty_language())
        res_e = gen_e.generate(max_accepted=5, max_rejected=5)
        self.assertEqual(len(res_e["accepted_strings"]), 0)
        self.assertEqual(len(res_e["rejected_strings"]), 5)

    def test_t5_gen_02_pathological_empty_alphabet(self) -> None:
        """Empty alphabet (Σ = ∅) handles accepting and rejecting single-state automata cleanly."""
        ea_acc = NFA(states={"q0"}, alphabet=set(), transitions={}, start_state="q0", final_states={"q0"})
        res_acc = TestStringGenerator(ea_acc).generate(max_accepted=3, max_rejected=3)
        self.assertEqual(res_acc["accepted_strings"], [""])
        self.assertEqual(res_acc["rejected_strings"], [])

        ea_rej = NFA(states={"q0"}, alphabet=set(), transitions={}, start_state="q0", final_states=set())
        res_rej = TestStringGenerator(ea_rej).generate(max_accepted=3, max_rejected=3)
        self.assertEqual(res_rej["accepted_strings"], [])
        self.assertEqual(res_rej["rejected_strings"], [""])

    def test_t5_gen_03_massive_count_shortlex_order(self) -> None:
        """Requesting 100 accepted and 100 rejected strings produces strictly unique Shortlex strings."""
        mod3_dfa = DFA(
            states={"q0", "q1", "q2"}, alphabet={"0", "1"},
            transitions={
                ("q0", "0"): "q0", ("q0", "1"): "q1",
                ("q1", "0"): "q2", ("q1", "1"): "q0",
                ("q2", "0"): "q1", ("q2", "1"): "q2",
            },
            start_state="q0", final_states={"q0"}, name="Mod3"
        )
        gen = TestStringGenerator(mod3_dfa)
        res = gen.generate(max_accepted=100, max_rejected=100)
        acc = res["accepted_strings"]
        rej = res["rejected_strings"]

        self.assertEqual(len(acc), 100)
        self.assertEqual(len(set(acc)), 100)
        self.assertTrue(all((len(acc[i]), acc[i]) <= (len(acc[i+1]), acc[i+1]) for i in range(len(acc)-1)))

        self.assertEqual(len(rej), 100)
        self.assertEqual(len(set(rej)), 100)
        self.assertTrue(all((len(rej[i]), rej[i]) <= (len(rej[i+1]), rej[i+1]) for i in range(len(rej)-1)))


class TestTier5AdversarialConverterAndMinimizer(unittest.TestCase):
    """Adversarial stress tests for converter.py and minimizer.py."""

    def test_t5_powerset_state_explosion(self) -> None:
        """Language with n-th bit from end equal to '1' produces exact 2^n DFA states."""
        for n in [4, 5]:
            expected = 2 ** n
            states = {f"q{i}" for i in range(n + 1)}
            transitions = {("q0", "0"): {"q0"}, ("q0", "1"): {"q0", "q1"}}
            for i in range(1, n):
                transitions[(f"q{i}", "0")] = {f"q{i+1}"}
                transitions[(f"q{i}", "1")] = {f"q{i+1}"}
            nfa = NFA(states=states, alphabet={"0", "1"}, transitions=transitions, start_state="q0", final_states={f"q{n}"})
            conv = NFAtoDFAConverter(nfa, include_dead_state=False).convert()
            min_res = DFAMinimizer(conv.dfa).minimize()

            self.assertEqual(len(conv.dfa.states), expected)
            self.assertEqual(len(min_res.minimal_dfa.states), expected)

    def test_t5_dense_cyclic_epsilon_networks(self) -> None:
        """Epsilon ring of 50 states computes closure in linear time without recursion spike."""
        states = {f"q{i}" for i in range(50)}
        transitions = {(f"q{i}", EPSILON): {f"q{(i+1)%50}"} for i in range(50)}
        nfa = NFA(states=states, alphabet=set(), transitions=transitions, start_state="q0", final_states={"q25"})
        closure = nfa.epsilon_closure("q0")
        self.assertEqual(len(closure), 50)

    def test_t5_disconnected_components_elimination(self) -> None:
        """Minimizer identifies and purges unreachable islands and disconnected cycles."""
        dfa = DFA(
            states={"q0", "q1", "q_island1", "q_island2"},
            alphabet={"a", "b"},
            transitions={
                ("q0", "a"): "q1", ("q0", "b"): "q0",
                ("q1", "a"): "q0", ("q1", "b"): "q1",
                ("q_island1", "a"): "q_island2", ("q_island2", "b"): "q_island1"
            },
            start_state="q0", final_states={"q1", "q_island2"}, name="Disconnected_DFA"
        )
        min_res = DFAMinimizer(dfa).minimize()
        self.assertEqual(min_res.unreachable_states, {"q_island1", "q_island2"})
        self.assertEqual(len(min_res.minimal_dfa.states), 2)


# ==============================================================================
# Category B: Web Server Security, Payload & Concurrency Probes (challenger_adv2)
# ==============================================================================


class TestTier5AdversarialSecurity(BaseE2ETestCase):
    """Tier 5 Category A: Static Asset Security & Directory Traversal."""

    def _raw_get(self, path: str) -> tuple[int, bytes]:
        assert self.harness is not None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.harness.host, self.harness.port))
        try:
            req = f"GET {path} HTTP/1.0\r\nHost: {self.harness.host}:{self.harness.port}\r\n\r\n"
            sock.sendall(req.encode("latin-1"))
            resp = bytearray()
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp.extend(chunk)
            resp_bytes = bytes(resp)
            status_line = resp_bytes.split(b"\r\n", 1)[0].decode("latin-1")
            code = int(status_line.split(" ")[1])
            body = resp_bytes.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in resp_bytes else b""
            return code, body
        finally:
            sock.close()

    def test_t5_traversal_01_escape_static_dir_blocked(self) -> None:
        """GET /static/../app.py must be blocked with HTTP 403 or 404, never 200."""
        code, body = self._raw_get("/static/../app.py")
        self.assertIn(code, (400, 403, 404))
        self.assertNotIn(b"AutomataRequestHandler", body)

    def test_t5_traversal_02_escape_models_py_blocked(self) -> None:
        """GET /static/../../models.py must be blocked with HTTP 403 or 404."""
        code, body = self._raw_get("/static/../../models.py")
        self.assertIn(code, (400, 403, 404))
        self.assertNotIn(b"class Automaton", body)

    def test_t5_traversal_03_windows_backslash_blocked(self) -> None:
        """GET /static/..\\..\\SourceCode\\models.py must be blocked."""
        code, body = self._raw_get("/static/..\\..\\SourceCode\\models.py")
        self.assertIn(code, (400, 403, 404))
        self.assertNotIn(b"class Automaton", body)

    def test_t5_traversal_04_url_encoded_traversal_blocked(self) -> None:
        """GET /static/%2e%2e/app.py must be blocked with HTTP 403 or 400."""
        code, body = self._raw_get("/static/%2e%2e/app.py")
        self.assertIn(code, (400, 403, 404))
        self.assertNotIn(b"AutomataRequestHandler", body)


class TestTier5AdversarialPayloads(BaseE2ETestCase):
    """Tier 5 Category B: Malformed Payloads and Exception Safety."""

    def test_t5_payload_01_non_utf8_post_body(self) -> None:
        """Submitting non-UTF8 bytes in POST body must return HTTP 400 without crashing."""
        assert self.harness is not None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.harness.host, self.harness.port))
        try:
            bad_bytes = b'{"regex": "' + b"\xff\xfe\xaa" + b'"}'
            head = (
                f"POST /api/regex-to-nfa HTTP/1.0\r\n"
                f"Host: {self.harness.host}:{self.harness.port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(bad_bytes)}\r\n\r\n"
            )
            sock.sendall(head.encode("latin-1") + bad_bytes)
            resp = sock.recv(4096).decode("latin-1", errors="replace")
            self.assertTrue(resp.startswith("HTTP/1.0 400") or resp.startswith("HTTP/1.1 400"))
        finally:
            sock.close()

    def test_t5_payload_02_invalid_content_length_header(self) -> None:
        """POST with non-numeric Content-Length header returns HTTP 400."""
        assert self.harness is not None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.harness.host, self.harness.port))
        try:
            head = (
                f"POST /api/convert HTTP/1.0\r\n"
                f"Host: {self.harness.host}:{self.harness.port}\r\n"
                f"Content-Length: not_a_number\r\n\r\n"
            )
            sock.sendall(head.encode("latin-1"))
            resp = sock.recv(4096).decode("latin-1", errors="replace")
            self.assertTrue(resp.startswith("HTTP/1.0 400") or resp.startswith("HTTP/1.1 400"))
        finally:
            sock.close()

    def test_t5_payload_03_negative_content_length_header(self) -> None:
        """POST with negative Content-Length header returns HTTP 400."""
        assert self.harness is not None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.harness.host, self.harness.port))
        try:
            head = (
                f"POST /api/convert HTTP/1.0\r\n"
                f"Host: {self.harness.host}:{self.harness.port}\r\n"
                f"Content-Length: -10\r\n\r\n"
            )
            sock.sendall(head.encode("latin-1"))
            resp = sock.recv(4096).decode("latin-1", errors="replace")
            self.assertTrue(resp.startswith("HTTP/1.0 400") or resp.startswith("HTTP/1.1 400"))
        finally:
            sock.close()


class TestTier5ConcurrencyBursts(BaseE2ETestCase):
    """Tier 5 Category C: Concurrent Request Bursts."""

    def test_t5_burst_50_concurrent_requests(self) -> None:
        """Burst of 50 concurrent requests across endpoints all return HTTP 200."""
        sample_nfa = {
            "name": "Ends_With_01",
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

        def make_req(idx: int) -> int:
            assert self.client is not None
            if idx % 3 == 0:
                s, _, _ = self.client.get("/api/samples")
            elif idx % 3 == 1:
                s, _, _ = self.client.post("/api/regex-to-nfa", {"regex": "(a|b)*abb"})
            else:
                s, _, _ = self.client.post("/api/simulate", {"nfa": sample_nfa, "input_string": "10101"})
            return s

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(make_req, range(50)))
        self.assertEqual(codes.count(200), 50)


if __name__ == "__main__":
    unittest.main()
