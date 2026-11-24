"""Non-Deterministic Finite Automaton (NFA / ε-NFA) representation and simulation.

Supports:
- ε-transitions (representations: ε, e, eps, empty string)
- Cycle-safe ε-closure computation via BFS
- String simulation tracking full active subset branches
- JSON serialization / deserialization with strict validation
"""

from __future__ import annotations
import json
from collections import deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Any, Union

from .models import (
    AutomatonType,
    EPSILON,
    EPSILON_VARIANTS,
    is_epsilon,
    SimulationStep,
    SimulationResult,
)


class NFA:
    """Represents an NFA / ε-NFA: 5-tuple (Q, Σ, δ, q0, F)."""

    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        transitions: Dict[Tuple[str, str], Set[str]],
        start_state: str,
        final_states: Set[str],
        name: str = "NFA",
    ):
        self.name = name
        self.states = set(str(s) for s in states)
        # Filter epsilon variants out of regular alphabet
        self.alphabet = set(str(a) for a in alphabet if not is_epsilon(a))
        self.start_state = str(start_state)
        self.final_states = set(str(f) for f in final_states)

        # Standardize transitions: map (state, canonical_symbol) -> set of target states
        self.transitions: Dict[Tuple[str, str], Set[str]] = {}
        for (st, sym), targets in transitions.items():
            canonical_sym = EPSILON if is_epsilon(sym) else str(sym)
            key = (str(st), canonical_sym)
            self.transitions.setdefault(key, set()).update(str(t) for t in targets)

        self._validate()

    @property
    def has_epsilon(self) -> bool:
        """Return True if any transition uses an epsilon symbol."""
        return any(sym == EPSILON for (_, sym) in self.transitions.keys())

    @property
    def automaton_type(self) -> AutomatonType:
        return AutomatonType.EPSILON_NFA if self.has_epsilon else AutomatonType.NFA

    def _validate(self) -> None:
        """Validate the 5-tuple consistency and raise ValueError on malformed machines."""
        if not self.states:
            raise ValueError("Automaton must contain at least one state (Q cannot be empty).")

        if self.start_state not in self.states:
            raise ValueError(
                f"Start state '{self.start_state}' is not defined in states set Q: {sorted(list(self.states))}"
            )

        invalid_finals = self.final_states - self.states
        if invalid_finals:
            raise ValueError(
                f"Final states {sorted(list(invalid_finals))} are not members of states set Q."
            )

        for (st, sym), targets in self.transitions.items():
            if st not in self.states:
                raise ValueError(f"Transition references undefined source state '{st}'.")
            if sym != EPSILON and sym not in self.alphabet:
                raise ValueError(
                    f"Transition symbol '{sym}' is not in alphabet Σ: {sorted(list(self.alphabet))}"
                )
            invalid_targets = targets - self.states
            if invalid_targets:
                raise ValueError(
                    f"Transition from '{st}' on '{sym}' references undefined target state(s): {sorted(list(invalid_targets))}"
                )

    def get_transitions(self, state: str, symbol: str) -> Set[str]:
        """Return set of target states from state on symbol (empty set if none)."""
        canonical_sym = EPSILON if is_epsilon(symbol) else str(symbol)
        return self.transitions.get((state, canonical_sym), set()).copy()

    def epsilon_closure(self, states: Union[str, Set[str], FrozenSet[str]]) -> FrozenSet[str]:
        """Compute the ε-closure of a state or set of states using BFS.
        
        Guaranteed to terminate even in the presence of cyclic ε-transitions.
        """
        if isinstance(states, str):
            initial_set = {states}
        else:
            initial_set = set(states)

        closure: Set[str] = set(initial_set)
        queue = deque(initial_set)

        while queue:
            current = queue.popleft()
            epsilon_targets = self.get_transitions(current, EPSILON)
            for target in epsilon_targets:
                if target not in closure:
                    closure.add(target)
                    queue.append(target)

        return frozenset(closure)

    def move(self, states: Union[Set[str], FrozenSet[str]], symbol: str) -> Set[str]:
        """Compute set of states reached from any state in `states` on `symbol` without ε-closure."""
        reached: Set[str] = set()
        for s in states:
            reached.update(self.get_transitions(s, symbol))
        return reached

    def simulate(self, input_string: str) -> SimulationResult:
        """Simulate an input string on the NFA.
        
        Returns full trace of active state subsets per consumed symbol.
        """
        # Step 0: Initial states are the ε-closure of start state
        current_active = self.epsilon_closure(self.start_state)
        trace: List[SimulationStep] = []

        step_num = 0
        trace.append(
            SimulationStep(
                step_number=step_num,
                current_states=current_active,
                symbol_consumed=None,
                remaining_input=input_string,
                next_states=current_active,
                description=f"Initial state: ε-closure({{{self.start_state}}}) = {sorted(list(current_active))}",
            )
        )

        for i, char in enumerate(input_string):
            step_num += 1
            if char not in self.alphabet:
                return SimulationResult(
                    accepted=False,
                    input_string=input_string,
                    automaton_type=self.automaton_type,
                    start_state=self.start_state,
                    final_states_reached=current_active,
                    trace=trace,
                    message=f"Validation Error: Symbol '{char}' at index {i} is not in alphabet Σ={sorted(list(self.alphabet))}.",
                )

            # Move on char, then take ε-closure
            reached_raw = self.move(current_active, char)
            next_active = self.epsilon_closure(reached_raw)

            trace.append(
                SimulationStep(
                    step_number=step_num,
                    current_states=current_active,
                    symbol_consumed=char,
                    remaining_input=input_string[i + 1:],
                    next_states=next_active,
                    description=f"Consumed '{char}': move={sorted(list(reached_raw))}, ε-closure={sorted(list(next_active))}",
                )
            )
            current_active = next_active

            # If no states are active (dead end branch), early check
            if not current_active:
                break

        # Check acceptance: does active states contain at least one final state?
        accepting_reached = current_active.intersection(self.final_states)
        is_accepted = len(accepting_reached) > 0

        verdict_msg = (
            f"ACCEPTED: Reached accepting state(s) {sorted(list(accepting_reached))} at end of input."
            if is_accepted
            else f"REJECTED: Final active states {sorted(list(current_active))} contain no accepting state."
        )

        return SimulationResult(
            accepted=is_accepted,
            input_string=input_string,
            automaton_type=self.automaton_type,
            start_state=self.start_state,
            final_states_reached=current_active,
            trace=trace,
            message=verdict_msg,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert NFA to standard dictionary representation."""
        transitions_serialized: List[Dict[str, Any]] = []
        for (st, sym), targets in sorted(self.transitions.items()):
            transitions_serialized.append(
                {"from": st, "symbol": sym, "to": sorted(list(targets))}
            )

        return {
            "name": self.name,
            "type": self.automaton_type.value,
            "states": sorted(list(self.states)),
            "alphabet": sorted(list(self.alphabet)),
            "start_state": self.start_state,
            "final_states": sorted(list(self.final_states)),
            "transitions": transitions_serialized,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NFA":
        """Construct NFA from dictionary."""
        states = set(data.get("states", []))
        alphabet = set(data.get("alphabet", []))
        start_state = str(data.get("start_state", ""))
        final_states = set(data.get("final_states", []))
        name = data.get("name", "NFA")

        transitions: Dict[Tuple[str, str], Set[str]] = {}
        raw_trans = data.get("transitions", [])

        # Support both list of dicts: [{"from": "q0", "symbol": "0", "to": ["q1"]}]
        # and dict format: {"q0": {"0": ["q1"]}}
        if isinstance(raw_trans, list):
            for t in raw_trans:
                f = str(t["from"])
                sym = str(t["symbol"])
                to_val = t["to"]
                to_set = set(to_val) if isinstance(to_val, list) else {str(to_val)}
                transitions.setdefault((f, sym), set()).update(to_set)
        elif isinstance(raw_trans, dict):
            for f, sym_map in raw_trans.items():
                for sym, to_val in sym_map.items():
                    to_set = set(to_val) if isinstance(to_val, list) else {str(to_val)}
                    transitions.setdefault((str(f), str(sym)), set()).update(to_set)

        return cls(
            states=states,
            alphabet=alphabet,
            transitions=transitions,
            start_state=start_state,
            final_states=final_states,
            name=name,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "NFA":
        data = json.loads(json_str)
        return cls.from_dict(data)
