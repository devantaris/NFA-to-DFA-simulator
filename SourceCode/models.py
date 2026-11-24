"""Data models and abstractions for Automata Theory Simulator (NFA to DFA).

Course: CSET302 - Automata Theory and Computability
Author: Devansh Kumar
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Any, Union


class AutomatonType(Enum):
    NFA = "NFA"
    EPSILON_NFA = "EPSILON_NFA"
    DFA = "DFA"


EPSILON = "ε"
EPSILON_VARIANTS = {"ε", "eps", "epsilon", "EPSILON", ""}


def is_epsilon(symbol: str) -> bool:
    """Check if an input symbol represents an epsilon transition."""
    return symbol in EPSILON_VARIANTS


@dataclass
class SimulationStep:
    """Represents a single step during string simulation."""
    step_number: int
    current_states: Union[str, Set[str], FrozenSet[str]]
    symbol_consumed: Optional[str]
    remaining_input: str
    next_states: Union[str, Set[str], FrozenSet[str]]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        curr = list(self.current_states) if isinstance(self.current_states, (set, frozenset)) else self.current_states
        nxt = list(self.next_states) if isinstance(self.next_states, (set, frozenset)) else self.next_states
        return {
            "step_number": self.step_number,
            "current_states": curr,
            "symbol_consumed": self.symbol_consumed,
            "remaining_input": self.remaining_input,
            "next_states": nxt,
            "description": self.description,
        }


@dataclass
class SimulationResult:
    """Complete result and trace of simulating a string on an automaton."""
    accepted: bool
    input_string: str
    automaton_type: AutomatonType
    start_state: Union[str, Set[str]]
    final_states_reached: Union[str, Set[str]]
    trace: List[SimulationStep]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        st = list(self.start_state) if isinstance(self.start_state, (set, frozenset)) else self.start_state
        fn = list(self.final_states_reached) if isinstance(self.final_states_reached, (set, frozenset)) else self.final_states_reached
        return {
            "accepted": self.accepted,
            "input_string": self.input_string,
            "automaton_type": self.automaton_type.value,
            "start_state": st,
            "final_states_reached": fn,
            "trace": [s.to_dict() for s in self.trace],
            "message": self.message,
        }


@dataclass
class ConversionStep:
    """A single step in the powerset (subset) construction algorithm."""
    step_number: int
    dfa_state: str
    nfa_subset: FrozenSet[str]
    symbol: str
    union_set: Set[str]
    epsilon_closure_set: FrozenSet[str]
    target_dfa_state: str
    is_new_state: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "dfa_state": self.dfa_state,
            "nfa_subset": sorted(list(self.nfa_subset)),
            "symbol": self.symbol,
            "union_set": sorted(list(self.union_set)),
            "epsilon_closure_set": sorted(list(self.epsilon_closure_set)),
            "target_dfa_state": self.target_dfa_state,
            "is_new_state": self.is_new_state,
        }


@dataclass
class ConversionResult:
    """Outcome of NFA to DFA conversion."""
    dfa: Any  # DFA instance
    steps: List[ConversionStep]
    state_mapping: Dict[str, List[str]]  # DFA state name -> sorted list of NFA states
    epsilon_closures: Dict[str, List[str]]  # NFA state -> its epsilon closure

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dfa": self.dfa.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "state_mapping": self.state_mapping,
            "epsilon_closures": self.epsilon_closures,
        }


@dataclass
class MinimizationResult:
    """Outcome of DFA minimization via Myhill-Nerode Table-Filling."""
    minimal_dfa: Any  # DFA instance
    state_mapping: Dict[str, List[str]]  # Min DFA state -> merged original DFA states
    distinguishable_table: Dict[str, Any]  # Matrix for academic reporting
    unreachable_states: Set[str]
    partitions_history: List[List[Set[str]]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minimal_dfa": self.minimal_dfa.to_dict(),
            "state_mapping": self.state_mapping,
            "distinguishable_table": self.distinguishable_table,
            "unreachable_states": sorted(list(self.unreachable_states)),
        }
