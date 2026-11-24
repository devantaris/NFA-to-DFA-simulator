"""DFA Minimization via Myhill-Nerode Theorem / Table-Filling Algorithm.

Features:
- Unreachable state elimination
- Step-by-step table filling with triangular matrix generation
- Equivalence class aggregation into canonical minimal states
- Full trace mapping between minimal DFA states and original DFA states
"""

from __future__ import annotations
from collections import deque, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .models import MinimizationResult
from .dfa import DFA


class DFAMinimizer:
    """Implements the Table-Filling (Myhill-Nerode) algorithm for DFA state minimization."""

    def __init__(self, dfa: DFA):
        self.dfa = dfa

    def find_reachable_states(self) -> Set[str]:
        """Find all states reachable from the start state using BFS."""
        visited: Set[str] = {self.dfa.start_state}
        queue = deque([self.dfa.start_state])

        while queue:
            current = queue.popleft()
            for sym in self.dfa.alphabet:
                nxt = self.dfa.get_transition(current, sym)
                if nxt and nxt not in visited and nxt in self.dfa.states:
                    visited.add(nxt)
                    queue.append(nxt)

        return visited

    def minimize(self) -> MinimizationResult:
        """Execute the table-filling minimization algorithm."""
        # Step 1: Remove unreachable states
        reachable_states = self.find_reachable_states()
        unreachable = self.dfa.states - reachable_states
        ordered_states = sorted(list(reachable_states))
        n = len(ordered_states)

        if n <= 1:
            # Already minimal
            mapping = {s: [s] for s in ordered_states}
            return MinimizationResult(
                minimal_dfa=self.dfa,
                state_mapping=mapping,
                distinguishable_table={},
                unreachable_states=unreachable,
                partitions_history=[],
            )

        # Distinguishable pairs table: True if states are distinguishable
        table: Dict[Tuple[str, str], bool] = {}
        reason: Dict[Tuple[str, str], str] = {}

        for i in range(n):
            for j in range(i + 1, n):
                pair = (ordered_states[i], ordered_states[j])
                table[pair] = False

        # Step 2: Base case - Separate accepting from non-accepting states
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = ordered_states[i], ordered_states[j]
                is_s1_final = s1 in self.dfa.final_states
                is_s2_final = s2 in self.dfa.final_states

                if is_s1_final != is_s2_final:
                    table[(s1, s2)] = True
                    reason[(s1, s2)] = "Base: One state is final, the other is non-final (0-distinguishable)"

        # Step 3: Inductive marking
        changed = True
        iteration = 1
        alphabet = sorted(list(self.dfa.alphabet))

        while changed:
            changed = False
            for i in range(n):
                for j in range(i + 1, n):
                    s1, s2 = ordered_states[i], ordered_states[j]
                    if table[(s1, s2)]:
                        continue

                    # Check transitions for all symbols
                    for sym in alphabet:
                        t1 = self.dfa.get_transition(s1, sym)
                        t2 = self.dfa.get_transition(s2, sym)

                        if t1 is None and t2 is None:
                            continue
                        if (t1 is None) != (t2 is None):
                            table[(s1, s2)] = True
                            reason[(s1, s2)] = f"Iter {iteration}: Transition on '{sym}' differs (defined vs undefined)"
                            changed = True
                            break

                        if t1 == t2:
                            continue

                        norm_pair = (min(t1, t2), max(t1, t2))
                        if table.get(norm_pair, False):
                            table[(s1, s2)] = True
                            reason[(s1, s2)] = f"Iter {iteration}: On '{sym}', δ({s1},{sym})={t1} and δ({s2},{sym})={t2} are distinguishable"
                            changed = True
                            break

            iteration += 1

        # Step 4: Group equivalent states into partitions using disjoint sets / BFS
        adj: Dict[str, Set[str]] = {s: set() for s in ordered_states}
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = ordered_states[i], ordered_states[j]
                if not table[(s1, s2)]:
                    adj[s1].add(s2)
                    adj[s2].add(s1)

        visited_group: Set[str] = set()
        equivalence_classes: List[List[str]] = []

        for st in ordered_states:
            if st not in visited_group:
                group = []
                q = deque([st])
                visited_group.add(st)
                while q:
                    curr = q.popleft()
                    group.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited_group:
                            visited_group.add(neighbor)
                            q.append(neighbor)
                equivalence_classes.append(sorted(group))

        # Step 5: Construct the new minimal DFA
        # State label for each equivalence class: e.g. "M0", "M1" or representative name
        min_state_labels: Dict[int, str] = {}
        old_to_min_state: Dict[str, str] = {}
        state_mapping: Dict[str, List[str]] = {}

        for idx, eq_class in enumerate(equivalence_classes):
            label = f"m{idx}"
            min_state_labels[idx] = label
            state_mapping[label] = eq_class
            for old_st in eq_class:
                old_to_min_state[old_st] = label

        min_start_state = old_to_min_state[self.dfa.start_state]
        min_final_states: Set[str] = set()

        for idx, eq_class in enumerate(equivalence_classes):
            # If any state in the equivalence class was accepting, the merged state is accepting
            if any(st in self.dfa.final_states for st in eq_class):
                min_final_states.add(min_state_labels[idx])

        min_transitions: Dict[Tuple[str, str], str] = {}
        for idx, eq_class in enumerate(equivalence_classes):
            from_min = min_state_labels[idx]
            rep_state = eq_class[0]  # representative state
            for sym in alphabet:
                target = self.dfa.get_transition(rep_state, sym)
                if target and target in old_to_min_state:
                    min_transitions[(from_min, sym)] = old_to_min_state[target]

        min_trap_state = old_to_min_state.get(self.dfa.trap_state) if self.dfa.trap_state else None

        min_dfa = DFA(
            states=set(min_state_labels.values()),
            alphabet=set(alphabet),
            transitions=min_transitions,
            start_state=min_start_state,
            final_states=min_final_states,
            name=f"Min_{self.dfa.name}",
            trap_state=min_trap_state,
        )

        # Distinguishable table matrix format for report output
        dist_table_report: Dict[str, Any] = {
            "ordered_states": ordered_states,
            "pairs": {
                f"{p[0]},{p[1]}": {
                    "distinguishable": table[p],
                    "reason": reason.get(p, "Equivalent (Unmarked)"),
                }
                for p in table
            },
        }

        return MinimizationResult(
            minimal_dfa=min_dfa,
            state_mapping=state_mapping,
            distinguishable_table=dist_table_report,
            unreachable_states=unreachable,
            partitions_history=[],
        )
