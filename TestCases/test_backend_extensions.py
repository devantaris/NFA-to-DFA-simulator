"""Comprehensive Unit and Integration Tests for Milestone 1 Backend Extensions.

Tests:
1. Regex to NFA Thompson Construction (SourceCode/regex_parser.py)
2. Automated Test String Generator (SourceCode/test_generator.py)
3. Web API Endpoints & CORS Handling (SourceCode/web/app.py)

Can be executed via:
    python -m unittest TestCases.test_backend_extensions -v
    python -m unittest discover -s TestCases -v
    python TestCases/test_backend_extensions.py
"""

from __future__ import annotations
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from SourceCode.converter import NFAtoDFAConverter
from SourceCode.dfa import DFA
from SourceCode.models import EPSILON
from SourceCode.nfa import NFA
from SourceCode.regex_parser import (
    RegexParseError,
    parse_regex_to_nfa,
    regex_to_nfa,
    regex_to_nfa_dict,
)
from SourceCode.test_generator import (
    TestStringGenerator,
    generate_test_strings,
    normalize_automaton_to_dfa,
)
from SourceCode.web.app import AutomataRequestHandler


class TestRegexParser(unittest.TestCase):
    """Unit tests for Thompson's Construction in regex_parser.py."""

    def test_single_literal(self):
        nfa = regex_to_nfa("a")
        self.assertIn("a", nfa.alphabet)
        self.assertTrue(nfa.simulate("a").accepted)
        self.assertFalse(nfa.simulate("").accepted)
        self.assertFalse(nfa.simulate("b").accepted)

    def test_concatenation(self):
        nfa = regex_to_nfa("ab")
        self.assertEqual(nfa.alphabet, {"a", "b"})
        self.assertTrue(nfa.simulate("ab").accepted)
        self.assertFalse(nfa.simulate("a").accepted)
        self.assertFalse(nfa.simulate("b").accepted)
        self.assertFalse(nfa.simulate("").accepted)

    def test_union(self):
        nfa = regex_to_nfa("a|b")
        self.assertTrue(nfa.simulate("a").accepted)
        self.assertTrue(nfa.simulate("b").accepted)
        self.assertFalse(nfa.simulate("ab").accepted)
        self.assertFalse(nfa.simulate("").accepted)

    def test_kleene_star(self):
        nfa = regex_to_nfa("a*")
        self.assertTrue(nfa.simulate("").accepted)
        self.assertTrue(nfa.simulate("a").accepted)
        self.assertTrue(nfa.simulate("aaa").accepted)
        self.assertFalse(nfa.simulate("b").accepted)

    def test_positive_closure(self):
        nfa = regex_to_nfa("a+")
        self.assertFalse(nfa.simulate("").accepted)
        self.assertTrue(nfa.simulate("a").accepted)
        self.assertTrue(nfa.simulate("aaaa").accepted)
        self.assertFalse(nfa.simulate("b").accepted)

    def test_optional_operator(self):
        nfa = regex_to_nfa("a?b")
        self.assertTrue(nfa.simulate("b").accepted)
        self.assertTrue(nfa.simulate("ab").accepted)
        self.assertFalse(nfa.simulate("").accepted)
        self.assertFalse(nfa.simulate("aab").accepted)

    def test_operator_precedence(self):
        # * has higher precedence than concat, concat higher than |
        nfa1 = regex_to_nfa("ab*")
        self.assertTrue(nfa1.simulate("a").accepted)
        self.assertTrue(nfa1.simulate("abbb").accepted)
        self.assertFalse(nfa1.simulate("abab").accepted)

        nfa2 = regex_to_nfa("ab|c")
        self.assertTrue(nfa2.simulate("ab").accepted)
        self.assertTrue(nfa2.simulate("c").accepted)
        self.assertFalse(nfa2.simulate("a").accepted)

    def test_textbook_regex_conversion_and_dfa_pipeline(self):
        # Standard textbook expression: (a|b)*abb
        nfa = regex_to_nfa("(a|b)*abb")
        self.assertTrue(nfa.simulate("abb").accepted)
        self.assertTrue(nfa.simulate("aabb").accepted)
        self.assertTrue(nfa.simulate("babb").accepted)
        self.assertTrue(nfa.simulate("ababb").accepted)
        self.assertFalse(nfa.simulate("").accepted)
        self.assertFalse(nfa.simulate("ab").accepted)
        self.assertFalse(nfa.simulate("abba").accepted)

        # Convert to DFA via powerset construction
        conv = NFAtoDFAConverter(nfa).convert()
        self.assertTrue(conv.dfa.simulate("abb").accepted)
        self.assertTrue(conv.dfa.simulate("babb").accepted)
        self.assertFalse(conv.dfa.simulate("ab").accepted)

    def test_escaped_operators(self):
        nfa = regex_to_nfa(r"a\*b")
        self.assertIn("*", nfa.alphabet)
        self.assertTrue(nfa.simulate("a*b").accepted)
        self.assertFalse(nfa.simulate("ab").accepted)

    def test_empty_regex_and_epsilon(self):
        nfa_empty = regex_to_nfa("")
        self.assertTrue(nfa_empty.simulate("").accepted)
        self.assertFalse(nfa_empty.simulate("a").accepted)

        nfa_eps = regex_to_nfa("ε")
        self.assertTrue(nfa_eps.simulate("").accepted)

    def test_regex_to_nfa_dict(self):
        d = regex_to_nfa_dict("0|1")
        self.assertIn("states", d)
        self.assertIn("alphabet", d)
        self.assertIn("transitions", d)
        self.assertIn("start_state", d)
        self.assertIn("final_states", d)
        self.assertEqual(set(d["alphabet"]), {"0", "1"})

    def test_invalid_syntax_raises_error(self):
        invalid_patterns = [
            "((a|b)",
            "(a|b))",
            "a|",
            "|a",
            "*a",
            "+a",
            "?a",
            "a||b",
            "()",
            "\\",
        ]
        for pat in invalid_patterns:
            with self.subTest(pat=pat):
                with self.assertRaises(ValueError):
                    regex_to_nfa(pat)

    def test_regex_with_ascii_e_and_E(self):
        # Defect 1 regression: ASCII 'e' and 'E' should be treated as literal alphabet symbols, not epsilon
        # Dispatch expression 1: (((a|b)*c)+|(d?e)*)*
        nfa1 = regex_to_nfa("(((a|b)*c)+|(d?e)*)*")
        self.assertIn("e", nfa1.alphabet)
        self.assertTrue(nfa1.simulate("e").accepted)
        self.assertTrue(nfa1.simulate("de").accepted)
        self.assertFalse(nfa1.simulate("d").accepted)

        # Dispatch expression 2: a|b*c+d?|e
        nfa2 = regex_to_nfa("a|b*c+d?|e")
        self.assertIn("e", nfa2.alphabet)
        self.assertTrue(nfa2.simulate("e").accepted)
        self.assertFalse(nfa2.simulate("").accepted)

        # English words with 'e' and 'E'
        nfa_hello = regex_to_nfa("hello")
        self.assertIn("e", nfa_hello.alphabet)
        self.assertTrue(nfa_hello.simulate("hello").accepted)
        self.assertFalse(nfa_hello.simulate("hllo").accepted)

        nfa_test = regex_to_nfa("TEST")
        self.assertIn("E", nfa_test.alphabet)
        self.assertTrue(nfa_test.simulate("TEST").accepted)
        self.assertFalse(nfa_test.simulate("TST").accepted)


class TestTestGenerator(unittest.TestCase):
    """Unit tests for string generation in test_generator.py."""

    def setUp(self):
        def_path = ROOT_DIR / "TestCases" / "definitions" / "01_ends_with_01.json"
        with open(def_path, "r", encoding="utf-8") as f:
            self.sample_dict = json.load(f)
            self.sample_nfa = NFA.from_dict(self.sample_dict)

    def test_basic_generation_with_nfa_object(self):
        res = generate_test_strings(self.sample_nfa, max_accepted=3, max_rejected=3)
        self.assertTrue(res["success"])
        accepted = res["accepted_strings"]
        rejected = res["rejected_strings"]

        self.assertGreaterEqual(len(accepted), 2)
        self.assertGreaterEqual(len(rejected), 2)

        for s in accepted:
            sim = self.sample_nfa.simulate(s)
            self.assertTrue(sim.accepted, f"Expected '{s}' to be accepted")
            self.assertTrue(s.endswith("01"), f"Expected '{s}' to end with '01'")

        for s in rejected:
            sim = self.sample_nfa.simulate(s)
            self.assertFalse(sim.accepted, f"Expected '{s}' to be rejected")
            self.assertFalse(s.endswith("01"), f"Expected '{s}' not to end with '01'")

    def test_basic_generation_with_dict(self):
        res = generate_test_strings(self.sample_dict, max_accepted=3, max_rejected=3)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(len(res["accepted_strings"]), 2)
        self.assertGreaterEqual(len(res["rejected_strings"]), 2)

    def test_accepted_strings_length_ordering(self):
        res = generate_test_strings(self.sample_nfa, max_accepted=5, max_rejected=5)
        accepted = res["accepted_strings"]
        lengths = [len(s) for s in accepted]
        self.assertEqual(lengths, sorted(lengths), "Accepted strings should be ordered by length")

    def test_empty_string_accepted(self):
        # Automaton that accepts epsilon (start state is final)
        nfa_dict = {
            "states": ["q0"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "final_states": ["q0"],
            "transitions": [{"from": "q0", "symbol": "0", "to": ["q0"]}],
        }
        res = generate_test_strings(nfa_dict, max_accepted=3, max_rejected=3)
        self.assertIn("", res["accepted_strings"])

    def test_empty_language(self):
        # Automaton with no final states (empty language)
        nfa = NFA(
            states={"q0"},
            alphabet={"0", "1"},
            start_state="q0",
            final_states=set(),
            transitions={},
        )
        res = generate_test_strings(nfa, max_accepted=3, max_rejected=3)
        self.assertTrue(res["is_empty_language"])
        self.assertEqual(res["accepted_strings"], [])
        self.assertGreater(len(res["rejected_strings"]), 0)

    def test_universal_language(self):
        # Universal language over alphabet {0, 1}
        univ_nfa = regex_to_nfa("(0|1)*")
        res = generate_test_strings(univ_nfa, max_accepted=3, max_rejected=3)
        self.assertTrue(res["is_universal_language"])
        self.assertEqual(res["rejected_strings"], [])
        self.assertGreater(len(res["accepted_strings"]), 0)

    def test_incomplete_dfa_rejection(self):
        # DFA with missing transition on symbol '1'
        def_path = ROOT_DIR / "TestCases" / "definitions" / "05_incomplete_automaton.json"
        with open(def_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        res = generate_test_strings(d, max_accepted=2, max_rejected=2)
        self.assertTrue(res["success"])
        self.assertIn("1", res["rejected_strings"])

    def test_zero_max_counts(self):
        res = generate_test_strings(self.sample_nfa, max_accepted=0, max_rejected=0)
        self.assertEqual(res["accepted_strings"], [])
        self.assertEqual(res["rejected_strings"], [])

    def test_shortlex_order_on_incomplete_dfa(self):
        # Defect 2 regression: Shortlex ordering on incomplete DFAs with missing transitions
        # Length Inversion DFA
        dfa_len = DFA(
            states={"q0", "q1", "q2"},
            alphabet={"a", "b"},
            transitions={
                ("q0", "a"): "q1",
                ("q0", "b"): "q2",
                ("q1", "b"): "q1",  # (q1, 'a') is missing/undefined
                ("q2", "a"): "q2",
                ("q2", "b"): "q2",
            },
            start_state="q0",
            final_states={"q0", "q1"},
            name="LengthInversionDFA",
        )
        gen_len = TestStringGenerator(dfa_len, minimize=False)
        rej_len = gen_len.generate_rejected(5)
        self.assertEqual(rej_len, ["b", "aa", "ba", "bb", "aba"])
        # Verify strict Shortlex: length non-decreasing, and lexicographical for equal length
        for i in range(len(rej_len) - 1):
            s1, s2 = rej_len[i], rej_len[i + 1]
            if len(s1) == len(s2):
                self.assertLess(s1, s2, f"Lexicographical ordering violated: {s1} not < {s2}")
            else:
                self.assertLess(len(s1), len(s2), f"Length ordering violated: |{s1}| not < |{s2}|")

        # Lexicographical Inversion DFA
        dfa_lex = DFA(
            states={"q0", "q1"},
            alphabet={"a", "b"},
            transitions={("q0", "a"): "q1"},  # (q0, 'b') is missing/undefined
            start_state="q0",
            final_states={"q0"},
            name="IncompleteDFA",
        )
        gen_lex = TestStringGenerator(dfa_lex, minimize=False)
        rej_lex = gen_lex.generate_rejected(4)
        self.assertEqual(rej_lex, ["a", "b", "aa", "ab"])
        for i in range(len(rej_lex) - 1):
            s1, s2 = rej_lex[i], rej_lex[i + 1]
            if len(s1) == len(s2):
                self.assertLess(s1, s2, f"Lexicographical ordering violated: {s1} not < {s2}")
            else:
                self.assertLess(len(s1), len(s2), f"Length ordering violated: |{s1}| not < |{s2}|")


class TestWebAppEndpoints(unittest.TestCase):
    """End-to-end integration tests for HTTP API endpoints in app.py."""

    server: HTTPServer
    port: int
    thread: threading.Thread

    @classmethod
    def setUpClass(cls):
        # Bind ephemeral port (port 0) on localhost
        cls.server = HTTPServer(("127.0.0.1", 0), AutomataRequestHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def make_request(
        self,
        path: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                resp_headers = dict(resp.headers)
                return resp.status, json.loads(body) if body else {}, resp_headers
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            resp_headers = dict(e.headers)
            e.close()
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"raw": body}
            return e.code, parsed, resp_headers

    def test_api_samples_get(self):
        status, data, _ = self.make_request("/api/samples")
        self.assertEqual(status, 200)
        self.assertIn("samples", data)
        self.assertGreaterEqual(len(data["samples"]), 5)

    def test_api_regex_to_nfa_success(self):
        status, data, _ = self.make_request(
            "/api/regex-to-nfa",
            method="POST",
            payload={"regex": "(a|b)*abb"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        nfa_dict = data.get("nfa")
        self.assertIsNotNone(nfa_dict)
        self.assertIn("states", nfa_dict)
        self.assertEqual(set(nfa_dict["alphabet"]), {"a", "b"})

    def test_api_regex_to_nfa_missing_field(self):
        status, data, _ = self.make_request(
            "/api/regex-to-nfa",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_api_regex_to_nfa_invalid_syntax(self):
        status, data, _ = self.make_request(
            "/api/regex-to-nfa",
            method="POST",
            payload={"regex": "((a|b)"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_api_generate_strings_success(self):
        sample_path = ROOT_DIR / "TestCases" / "definitions" / "01_ends_with_01.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            nfa_dict = json.load(f)

        status, data, _ = self.make_request(
            "/api/generate-strings",
            method="POST",
            payload={"nfa": nfa_dict, "max_accepted": 3, "max_rejected": 3},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("accepted_strings", data)
        self.assertIn("rejected_strings", data)
        self.assertGreaterEqual(len(data["accepted_strings"]), 2)
        self.assertGreaterEqual(len(data["rejected_strings"]), 2)

    def test_api_generate_strings_missing_nfa(self):
        status, data, _ = self.make_request(
            "/api/generate-strings",
            method="POST",
            payload={"max_accepted": 3},
        )
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))

    def test_api_generate_strings_invalid_params(self):
        sample_path = ROOT_DIR / "TestCases" / "definitions" / "01_ends_with_01.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            nfa_dict = json.load(f)

        status, data, _ = self.make_request(
            "/api/generate-strings",
            method="POST",
            payload={"nfa": nfa_dict, "max_accepted": -1},
        )
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))

    def test_api_options_preflight(self):
        url = f"http://127.0.0.1:{self.port}/api/regex-to-nfa"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)
            headers = dict(resp.headers)
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))

    def test_api_convert_backward_compatibility(self):
        sample_path = ROOT_DIR / "TestCases" / "definitions" / "01_ends_with_01.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            nfa_dict = json.load(f)

        status, data, _ = self.make_request(
            "/api/convert",
            method="POST",
            payload={"nfa": nfa_dict},
        )
        self.assertEqual(status, 200)
        self.assertIn("converted_dfa", data)
        self.assertIn("minimal_dfa", data)

    def test_api_simulate_backward_compatibility(self):
        sample_path = ROOT_DIR / "TestCases" / "definitions" / "01_ends_with_01.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            nfa_dict = json.load(f)

        status, data, _ = self.make_request(
            "/api/simulate",
            method="POST",
            payload={"nfa": nfa_dict, "input_string": "10101"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("is_equivalent"))


if __name__ == "__main__":
    unittest.main()
