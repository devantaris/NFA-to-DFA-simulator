"""Powerset / Subset Construction algorithm to convert ε-NFA / NFA to equivalent DFA.

Includes:
- Step-by-step mathematical transition logs
- Configurable dead/trap state handling
- Canonical and human-readable state naming
- Full trace mapping between DFA state IDs and original NFA subsets
"""

from __future__ import annotations
from collections import deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .models import ConversionStep, ConversionResult
from .nfa import NFA
from .dfa import DFA


class NFAtoDFAConverter:
    """Converts an NFA or ε-NFA to a minimal or standard DFA via Subset Construction."""

    def __init__(
        self,
        nfa: NFA,
        state_prefix: str = "q",
        include_dead_state: bool = True,
        dead_state_name: str = "DEAD",
    ):
        self.nfa = nfa
        self.state_prefix = state_prefix
        self.include_dead_state = include_dead_state
        self.dead_state_name = dead_state_name

    def convert(self) -> ConversionResult:
        """Execute the subset construction algorithm."""
        # Step 1: Precompute ε-closure for all individual NFA states for reference
        epsilon_closures: Dict[str, List[str]] = {}
        for st in sorted(self.nfa.states):
            epsilon_closures[st] = sorted(list(self.nfa.epsilon_closure(st)))

        # Step 2: Initial DFA state is ε-closure of NFA start state
        initial_subset = self.nfa.epsilon_closure(self.nfa.start_state)

        # Mappings: frozenset(NFA states) <-> DFA state label
        subset_to_label: Dict[FrozenSet[str], str] = {}
        label_to_subset: Dict[str, List[str]] = {}

        def get_or_create_label(subset: FrozenSet[str]) -> Tuple[str, bool]:
            if not subset:
                if self.include_dead_state:
                    if frozenset() not in subset_to_label:
                        subset_to_label[frozenset()] = self.dead_state_name
                        label_to_subset[self.dead_state_name] = ["∅"]
                        return self.dead_state_name, True
                    return self.dead_state_name, False
                return "", False

            if subset in subset_to_label:
                return subset_to_label[subset], False

            idx = len(subset_to_label)
            label = f"{self.state_prefix}{idx}"
            subset_to_label[subset] = label
            label_to_subset[label] = sorted(list(subset))
            return label, True

        start_label, _ = get_or_create_label(initial_subset)

        queue = deque([initial_subset])
        visited_subsets: Set[FrozenSet[str]] = {initial_subset}

        dfa_transitions: Dict[Tuple[str, str], str] = {}
        conversion_steps: List[ConversionStep] = []
        step_counter = 1

        alphabet_symbols = sorted(list(self.nfa.alphabet))

        while queue:
            current_subset = queue.popleft()
            current_label = subset_to_label[current_subset]

            for symbol in alphabet_symbols:
                # Union of moves on current symbol
                union_set = self.nfa.move(current_subset, symbol)
                # ε-closure of union
                target_subset = self.nfa.epsilon_closure(union_set) if union_set else frozenset()

                if not target_subset:
                    if self.include_dead_state:
                        target_label, is_new = get_or_create_label(target_subset)
                        dfa_transitions[(current_label, symbol)] = target_label
                        conversion_steps.append(
                            ConversionStep(
                                step_number=step_counter,
                                dfa_state=current_label,
                                nfa_subset=current_subset,
                                symbol=symbol,
                                union_set=union_set,
                                epsilon_closure_set=target_subset,
                                target_dfa_state=target_label,
                                is_new_state=is_new,
                            )
                        )
                        step_counter += 1
                        if is_new:
                            visited_subsets.add(target_subset)
                    else:
                        # Incomplete DFA: no transition entry created
                        conversion_steps.append(
                            ConversionStep(
                                step_number=step_counter,
                                dfa_state=current_label,
                                nfa_subset=current_subset,
                                symbol=symbol,
                                union_set=union_set,
                                epsilon_closure_set=target_subset,
                                target_dfa_state="[NONE]",
                                is_new_state=False,
                            )
                        )
                        step_counter += 1
                    continue

                target_label, is_new = get_or_create_label(target_subset)
                dfa_transitions[(current_label, symbol)] = target_label

                conversion_steps.append(
                    ConversionStep(
                        step_number=step_counter,
                        dfa_state=current_label,
                        nfa_subset=current_subset,
                        symbol=symbol,
                        union_set=union_set,
                        epsilon_closure_set=target_subset,
                        target_dfa_state=target_label,
                        is_new_state=is_new,
                    )
                )
                step_counter += 1

                if target_subset not in visited_subsets:
                    visited_subsets.add(target_subset)
                    queue.append(target_subset)

        # Handle self-loop transitions for the DEAD state if present
        if self.include_dead_state and frozenset() in subset_to_label:
            dead_lbl = subset_to_label[frozenset()]
            for symbol in alphabet_symbols:
                dfa_transitions[(dead_lbl, symbol)] = dead_lbl

        # Determine DFA accepting states (any subset containing at least one NFA final state)
        dfa_states = set(subset_to_label.values())
        dfa_final_states: Set[str] = set()

        for subset, label in subset_to_label.items():
            if subset.intersection(self.nfa.final_states):
                dfa_final_states.add(label)

        converted_dfa = DFA(
            states=dfa_states,
            alphabet=set(alphabet_symbols),
            transitions=dfa_transitions,
            start_state=start_label,
            final_states=dfa_final_states,
            name=f"Converted_DFA_from_{self.nfa.name}",
            trap_state=self.dead_state_name if (self.include_dead_state and frozenset() in subset_to_label) else None,
        )

        return ConversionResult(
            dfa=converted_dfa,
            steps=conversion_steps,
            state_mapping=label_to_subset,
            epsilon_closures=epsilon_closures,
        )
