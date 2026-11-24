"""Automated Test String Generator for Finite Automata.

Generates distinct accepted and rejected test strings for NFA or DFA models
using Breadth-First Search (BFS) path exploration in Shortlex order on the
minimized DFA representation with cycle control and co-reachability pruning.
"""

from __future__ import annotations
import sys
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from SourceCode.converter import NFAtoDFAConverter
    from SourceCode.dfa import DFA
    from SourceCode.minimizer import DFAMinimizer
    from SourceCode.models import is_epsilon
    from SourceCode.nfa import NFA
else:
    from .converter import NFAtoDFAConverter
    from .dfa import DFA
    from .minimizer import DFAMinimizer
    from .models import is_epsilon
    from .nfa import NFA


def normalize_automaton_to_dfa(
    automaton: Union[NFA, DFA, Dict[str, Any]],
    minimize: bool = True,
) -> DFA:
    """Normalize an NFA, DFA, or raw dictionary into a minimal (or complete) DFA."""
    if isinstance(automaton, dict):
        auto_type = automaton.get("type", "").upper()
        is_nfa = auto_type in ("NFA", "EPSILON_NFA") or auto_type != "DFA"
        if not is_nfa:
            raw_trans = automaton.get("transitions", [])
            if isinstance(raw_trans, list):
                for t in raw_trans:
                    to_val = t.get("to")
                    sym = str(t.get("symbol", ""))
                    if (isinstance(to_val, list) and len(to_val) > 1) or is_epsilon(sym):
                        is_nfa = True
                        break

        if is_nfa:
            nfa = NFA.from_dict(automaton)
            conv = NFAtoDFAConverter(nfa, include_dead_state=True).convert()
            dfa = conv.dfa
        else:
            try:
                dfa = DFA.from_dict(automaton)
            except Exception:
                nfa = NFA.from_dict(automaton)
                conv = NFAtoDFAConverter(nfa, include_dead_state=True).convert()
                dfa = conv.dfa
    elif isinstance(automaton, NFA):
        conv = NFAtoDFAConverter(automaton, include_dead_state=True).convert()
        dfa = conv.dfa
    elif isinstance(automaton, DFA):
        dfa = automaton
    else:
        raise TypeError(f"Expected NFA, DFA, or dict, got {type(automaton).__name__}")

    if minimize:
        min_res = DFAMinimizer(dfa).minimize()
        return min_res.minimal_dfa
    return dfa


def compute_live_states(dfa: DFA) -> Set[str]:
    """Find all states that have a directed path to at least one accepting state."""
    rev_adj: Dict[str, Set[str]] = {s: set() for s in dfa.states}
    for (st, sym), tgt in dfa.transitions.items():
        if tgt in rev_adj:
            rev_adj[tgt].add(st)

    live: Set[str] = set()
    queue = deque([f for f in dfa.final_states if f in dfa.states])
    live.update(queue)

    while queue:
        curr = queue.popleft()
        for pred in rev_adj.get(curr, set()):
            if pred not in live:
                live.add(pred)
                queue.append(pred)
    return live


def compute_reject_live_states(dfa: DFA) -> Set[str]:
    """Find all states that can reach a non-accepting state or undefined transition."""
    non_finals = dfa.states - dfa.final_states
    incomplete_states = {
        st for st in dfa.states
        if any((st, sym) not in dfa.transitions for sym in dfa.alphabet)
    }
    targets = non_finals | incomplete_states

    rev_adj: Dict[str, Set[str]] = {s: set() for s in dfa.states}
    for (st, sym), tgt in dfa.transitions.items():
        if tgt in rev_adj:
            rev_adj[tgt].add(st)

    reject_live: Set[str] = set()
    queue = deque([t for t in targets if t in dfa.states])
    reject_live.update(queue)

    while queue:
        curr = queue.popleft()
        for pred in rev_adj.get(curr, set()):
            if pred not in reject_live:
                reject_live.add(pred)
                queue.append(pred)
    return reject_live


class TestStringGenerator:
    """Systematic Shortlex test string generator for finite automata."""

    def __init__(
        self,
        automaton: Union[NFA, DFA, Dict[str, Any]],
        minimize: bool = True,
        max_state_repeats: int = 3,
        max_depth: int = 25,
        max_queue_iterations: int = 50000,
    ) -> None:
        self.dfa = normalize_automaton_to_dfa(automaton, minimize=minimize)
        self.max_state_repeats = max_state_repeats
        self.max_depth = max_depth
        self.max_queue_iterations = max_queue_iterations
        self.sorted_alphabet = sorted(list(self.dfa.alphabet))
        self.live_states = compute_live_states(self.dfa)
        self.reject_live_states = compute_reject_live_states(self.dfa)

    def is_empty_language(self) -> bool:
        """Return True if no accepted string exists (start state cannot reach any final state)."""
        return self.dfa.start_state not in self.live_states

    def is_universal_language(self) -> bool:
        """Return True if all strings over the alphabet are accepted (no rejected strings exist)."""
        return self.dfa.start_state not in self.reject_live_states

    def generate_accepted(self, max_count: int = 3) -> List[str]:
        """Generate up to max_count accepted strings in Shortlex order."""
        if max_count <= 0 or self.is_empty_language():
            return []

        accepted: List[str] = []
        queue = deque([(self.dfa.start_state, "", (self.dfa.start_state,))])
        iterations = 0

        while queue and len(accepted) < max_count and iterations < self.max_queue_iterations:
            iterations += 1
            curr_state, curr_str, history = queue.popleft()

            if curr_state in self.dfa.final_states:
                if curr_str not in accepted:
                    accepted.append(curr_str)
                    if len(accepted) >= max_count:
                        break

            if len(curr_str) >= self.max_depth:
                continue

            for sym in self.sorted_alphabet:
                nxt = self.dfa.get_transition(curr_state, sym)
                if nxt and (nxt in self.live_states):
                    if history.count(nxt) <= self.max_state_repeats:
                        queue.append((nxt, curr_str + sym, history + (nxt,)))

        return accepted

    def generate_rejected(self, max_count: int = 3) -> List[str]:
        """Generate up to max_count rejected strings in Shortlex order."""
        if max_count <= 0 or self.is_universal_language():
            return []

        rejected: List[str] = []
        queue = deque([(self.dfa.start_state, "", (self.dfa.start_state,))])
        iterations = 0

        while queue and len(rejected) < max_count and iterations < self.max_queue_iterations:
            iterations += 1
            curr_state, curr_str, history = queue.popleft()

            if curr_state is None or curr_state not in self.dfa.final_states:
                if curr_str not in rejected:
                    rejected.append(curr_str)
                    if len(rejected) >= max_count:
                        break

            if curr_state is None or len(curr_str) >= self.max_depth:
                continue

            for sym in self.sorted_alphabet:
                nxt = self.dfa.get_transition(curr_state, sym)
                if nxt is None:
                    # Undefined transition causes immediate crash / rejection
                    queue.append((None, curr_str + sym, (None,)))
                elif nxt in self.reject_live_states:
                    if history.count(nxt) <= self.max_state_repeats:
                        queue.append((nxt, curr_str + sym, history + (nxt,)))

        return rejected

    def generate(self, max_accepted: int = 3, max_rejected: int = 3) -> Dict[str, Any]:
        """Generate both accepted and rejected test strings."""
        return {
            "success": True,
            "accepted_strings": self.generate_accepted(max_accepted),
            "rejected_strings": self.generate_rejected(max_rejected),
            "alphabet": self.sorted_alphabet,
            "is_empty_language": self.is_empty_language(),
            "is_universal_language": self.is_universal_language(),
        }


def generate_test_strings(
    automaton: Union[NFA, DFA, Dict[str, Any]],
    max_accepted: int = 3,
    max_rejected: int = 3,
    minimize: bool = True,
) -> Dict[str, Any]:
    """Convenience function to generate accepted and rejected test strings for an automaton."""
    try:
        generator = TestStringGenerator(automaton, minimize=minimize)
        return generator.generate(max_accepted=max_accepted, max_rejected=max_rejected)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "accepted_strings": [],
            "rejected_strings": [],
        }
