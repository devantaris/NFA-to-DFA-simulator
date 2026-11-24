"""Deterministic Finite Automaton (DFA) representation and deterministic simulation.

Adheres strictly to the CSET302 specification:
- Incomplete DFAs: explicit missing transition reporting or trap state support
- Alphabet validation
- Step-by-step deterministic execution trace
"""

from __future__ import annotations
import json
from typing import Dict, List, Optional, Set, Tuple, Any

from .models import (
    AutomatonType,
    SimulationStep,
    SimulationResult,
)


class DFA:
    """Represents a Deterministic Finite Automaton: 5-tuple (Q, Σ, δ, q0, F)."""

    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        transitions: Dict[Tuple[str, str], str],
        start_state: str,
        final_states: Set[str],
        name: str = "DFA",
        trap_state: Optional[str] = None,
    ):
        self.name = name
        self.states = set(str(s) for s in states)
        self.alphabet = set(str(a) for a in alphabet)
        self.start_state = str(start_state)
        self.final_states = set(str(f) for f in final_states)
        self.trap_state = str(trap_state) if trap_state else None

        # transitions map: (state, symbol) -> next_state
        self.transitions: Dict[Tuple[str, str], str] = {
            (str(st), str(sym)): str(tgt) for (st, sym), tgt in transitions.items()
        }

        self._validate()

    @property
    def automaton_type(self) -> AutomatonType:
        return AutomatonType.DFA

    def _validate(self) -> None:
        """Validate DFA formal properties."""
        if not self.states:
            raise ValueError("DFA must contain at least one state (Q cannot be empty).")

        if self.start_state not in self.states:
            raise ValueError(
                f"Start state '{self.start_state}' is not in states Q: {sorted(list(self.states))}"
            )

        invalid_finals = self.final_states - self.states
        if invalid_finals:
            raise ValueError(
                f"Final states {sorted(list(invalid_finals))} are not members of states Q."
            )

        for (st, sym), target in self.transitions.items():
            if st not in self.states:
                raise ValueError(f"Transition references undefined source state '{st}'.")
            if sym not in self.alphabet:
                raise ValueError(
                    f"Transition symbol '{sym}' is not in alphabet Σ: {sorted(list(self.alphabet))}"
                )
            if target not in self.states:
                raise ValueError(
                    f"Transition from '{st}' on '{sym}' references undefined target '{target}'."
                )

    def is_complete(self) -> bool:
        """Check whether δ is total (defined for every (state, symbol) pair)."""
        for st in self.states:
            for sym in self.alphabet:
                if (st, sym) not in self.transitions:
                    return False
        return True

    def get_transition(self, state: str, symbol: str) -> Optional[str]:
        """Return the next state from state on symbol, or None if undefined."""
        return self.transitions.get((state, symbol))

    def simulate(self, input_string: str) -> SimulationResult:
        """Simulate an input string on the DFA step by step."""
        current = self.start_state
        trace: List[SimulationStep] = []

        trace.append(
            SimulationStep(
                step_number=0,
                current_states=current,
                symbol_consumed=None,
                remaining_input=input_string,
                next_states=current,
                description=f"Initial state: {current}",
            )
        )

        for i, char in enumerate(input_string):
            if char not in self.alphabet:
                return SimulationResult(
                    accepted=False,
                    input_string=input_string,
                    automaton_type=self.automaton_type,
                    start_state=self.start_state,
                    final_states_reached=current,
                    trace=trace,
                    message=f"Validation Error: Unknown symbol '{char}' at index {i} not in alphabet Σ={sorted(list(self.alphabet))}.",
                )

            next_state = self.get_transition(current, char)

            if next_state is None:
                # Incomplete transition encountered
                if self.trap_state and (self.trap_state in self.states):
                    next_state = self.trap_state
                    desc = f"Consumed '{char}': Undefined transition from '{current}'. Redirected to Trap state '{self.trap_state}'."
                else:
                    trace.append(
                        SimulationStep(
                            step_number=i + 1,
                            current_states=current,
                            symbol_consumed=char,
                            remaining_input=input_string[i + 1:],
                            next_states="UNDEFINED (CRASH)",
                            description=f"Halted: Missing transition from state '{current}' on symbol '{char}'.",
                        )
                    )
                    return SimulationResult(
                        accepted=False,
                        input_string=input_string,
                        automaton_type=self.automaton_type,
                        start_state=self.start_state,
                        final_states_reached=current,
                        trace=trace,
                        message=f"REJECTED: Automaton crashed due to undefined transition: δ({current}, {char}) is not defined.",
                    )
            else:
                desc = f"Consumed '{char}': δ({current}, {char}) -> {next_state}"

            trace.append(
                SimulationStep(
                    step_number=i + 1,
                    current_states=current,
                    symbol_consumed=char,
                    remaining_input=input_string[i + 1:],
                    next_states=next_state,
                    description=desc,
                )
            )
            current = next_state

        is_accepted = current in self.final_states
        verdict = (
            f"ACCEPTED: Ended in final state '{current}'."
            if is_accepted
            else f"REJECTED: Ended in non-final state '{current}'."
        )

        return SimulationResult(
            accepted=is_accepted,
            input_string=input_string,
            automaton_type=self.automaton_type,
            start_state=self.start_state,
            final_states_reached=current,
            trace=trace,
            message=verdict,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert DFA to dictionary representation."""
        transitions_serialized: List[Dict[str, Any]] = []
        for (st, sym), target in sorted(self.transitions.items()):
            transitions_serialized.append({"from": st, "symbol": sym, "to": target})

        return {
            "name": self.name,
            "type": self.automaton_type.value,
            "states": sorted(list(self.states)),
            "alphabet": sorted(list(self.alphabet)),
            "start_state": self.start_state,
            "final_states": sorted(list(self.final_states)),
            "trap_state": self.trap_state,
            "transitions": transitions_serialized,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DFA":
        """Construct DFA from dictionary."""
        states = set(data.get("states", []))
        alphabet = set(data.get("alphabet", []))
        start_state = str(data.get("start_state", ""))
        final_states = set(data.get("final_states", []))
        name = data.get("name", "DFA")
        trap_state = data.get("trap_state")

        transitions: Dict[Tuple[str, str], str] = {}
        raw_trans = data.get("transitions", [])

        if isinstance(raw_trans, list):
            for t in raw_trans:
                to_val = t["to"]
                target = str(to_val[0]) if isinstance(to_val, list) else str(to_val)
                transitions[(str(t["from"]), str(t["symbol"]))] = target
        elif isinstance(raw_trans, dict):
            for f, sym_map in raw_trans.items():
                for sym, to_val in sym_map.items():
                    target = str(to_val[0]) if isinstance(to_val, list) else str(to_val)
                    transitions[(str(f), str(sym))] = target

        return cls(
            states=states,
            alphabet=alphabet,
            transitions=transitions,
            start_state=start_state,
            final_states=final_states,
            name=name,
            trap_state=trap_state,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DFA":
        data = json.loads(json_str)
        return cls.from_dict(data)
