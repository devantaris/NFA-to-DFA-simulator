"""Visualization utilities for Automata Theory Simulator.

Generates:
- ASCII / Markdown transition tables
- Graphviz DOT specifications for NFA, DFA, and Minimal DFA
- Step-by-step subset construction tables
- Minimization triangular equivalence matrices
- Trace logs for string simulation
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple, Any

from .models import (
    EPSILON,
    ConversionResult,
    MinimizationResult,
    SimulationResult,
)
from .nfa import NFA
from .dfa import DFA


class Visualizer:
    """Helper to render textual, tabular, and graphical representations of automata."""

    @staticmethod
    def nfa_transition_table(nfa: NFA) -> str:
        """Format an NFA transition table in Markdown format."""
        symbols = sorted(list(nfa.alphabet))
        if nfa.has_epsilon:
            symbols.append(EPSILON)

        headers = ["State"] + symbols
        rows = []

        for st in sorted(list(nfa.states)):
            prefix = ""
            if st == nfa.start_state:
                prefix += "→ "
            if st in nfa.final_states:
                prefix += "* "
            state_label = f"{prefix}{st}".strip()

            row = [state_label]
            for sym in symbols:
                targets = nfa.get_transitions(st, sym)
                if targets:
                    row.append("{" + ", ".join(sorted(list(targets))) + "}")
                else:
                    row.append("∅")
            rows.append(row)

        return Visualizer._format_markdown_table(headers, rows)

    @staticmethod
    def dfa_transition_table(dfa: DFA) -> str:
        """Format a DFA transition table in Markdown format."""
        symbols = sorted(list(dfa.alphabet))
        headers = ["State"] + symbols
        rows = []

        for st in sorted(list(dfa.states)):
            prefix = ""
            if st == dfa.start_state:
                prefix += "→ "
            if st in dfa.final_states:
                prefix += "* "
            state_label = f"{prefix}{st}".strip()

            row = [state_label]
            for sym in symbols:
                target = dfa.get_transition(st, sym)
                row.append(target if target else "—")
            rows.append(row)

        return Visualizer._format_markdown_table(headers, rows)

    @staticmethod
    def subset_construction_table(conversion: ConversionResult) -> str:
        """Format the step-by-step subset construction table."""
        headers = ["Step", "DFA State", "NFA Subset", "Input", "Move(S, a)", "ε-Closure / Next Subset", "Target State", "New?"]
        rows = []

        for step in conversion.steps:
            subset_str = "{" + ", ".join(sorted(list(step.nfa_subset))) + "}"
            move_str = "{" + ", ".join(sorted(list(step.union_set))) + "}" if step.union_set else "∅"
            target_sub_str = "{" + ", ".join(sorted(list(step.epsilon_closure_set))) + "}" if step.epsilon_closure_set else "∅"
            is_new_str = "Yes" if step.is_new_state else "No"

            rows.append([
                str(step.step_number),
                step.dfa_state,
                subset_str,
                step.symbol,
                move_str,
                target_sub_str,
                step.target_dfa_state,
                is_new_str,
            ])

        return Visualizer._format_markdown_table(headers, rows)

    @staticmethod
    def minimization_table(result: MinimizationResult) -> str:
        """Format the Myhill-Nerode triangular table for distinguishable state pairs."""
        dist_data = result.distinguishable_table
        if not dist_data or "ordered_states" not in dist_data:
            return "Automaton has ≤ 1 state (already minimal)."

        ordered = dist_data["ordered_states"]
        pairs = dist_data["pairs"]
        n = len(ordered)

        lines = ["### Triangular Equivalence Table (X = Distinguishable, = = Equivalent)\n"]
        header = "| State | " + " | ".join(ordered[:-1]) + " |"
        sep = "| :---: | " + " | ".join([":---:"] * (n - 1)) + " |"
        lines.append(header)
        lines.append(sep)

        for i in range(1, n):
            row_state = ordered[i]
            row_cells = [row_state]
            for j in range(i):
                col_state = ordered[j]
                pair_key = f"{col_state},{row_state}"
                entry = pairs.get(pair_key)
                if entry and entry["distinguishable"]:
                    row_cells.append("**X**")
                else:
                    row_cells.append("==")
            # pad remaining columns
            row_cells.extend(["—"] * (n - 1 - i))
            lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines)

    @staticmethod
    def simulation_trace_table(sim: SimulationResult) -> str:
        """Format a simulation trace into a readable Markdown table."""
        headers = ["Step", "Current State(s)", "Consumed", "Remaining Input", "Next State(s)", "Operation"]
        rows = []

        for step in sim.trace:
            curr = "{" + ", ".join(sorted(list(step.current_states))) + "}" if isinstance(step.current_states, (set, frozenset)) else str(step.current_states)
            nxt = "{" + ", ".join(sorted(list(step.next_states))) + "}" if isinstance(step.next_states, (set, frozenset)) else str(step.next_states)
            consumed = step.symbol_consumed if step.symbol_consumed is not None else "—"
            rem = step.remaining_input if step.remaining_input else "ε (empty)"

            rows.append([
                str(step.step_number),
                curr,
                consumed,
                rem,
                nxt,
                step.description,
            ])

        table_md = Visualizer._format_markdown_table(headers, rows)
        status_box = f"\n**Verdict:** `{sim.message}`"
        return table_md + "\n" + status_box

    @staticmethod
    def to_dot(automaton: Any, title: Optional[str] = None) -> str:
        """Generate Graphviz DOT script for an NFA or DFA."""
        dot_lines = [
            'digraph Automaton {',
            '  rankdir=LR;',
            '  node [fontname="Helvetica", fontsize=11];',
            '  edge [fontname="Helvetica", fontsize=10];',
            f'  label="{title or automaton.name}";',
            '  labelloc="t";',
            '  fontsize=13;',
            '',
            '  // Start state arrow',
            '  __start__ [shape=none, label="", width=0, height=0];',
            f'  __start__ -> "{automaton.start_state}";',
            '',
        ]

        # Final states (doublecircle)
        final_states = sorted(list(automaton.final_states))
        if final_states:
            dot_lines.append(f'  node [shape=doublecircle, style=filled, fillcolor="#E8F5E9"]; {" ".join([f"\"{s}\"" for s in final_states])};')

        # Non-final states (circle)
        non_final = sorted(list(automaton.states - automaton.final_states))
        if non_final:
            dot_lines.append(f'  node [shape=circle, style=filled, fillcolor="#F5F5F5"]; {" ".join([f"\"{s}\"" for s in non_final])};')

        dot_lines.append('')
        dot_lines.append('  // Transitions')

        # Group transitions by (from, to) to combine multiple symbols on one edge
        edge_symbols: Dict[Tuple[str, str], List[str]] = {}

        if isinstance(automaton, NFA):
            for (st, sym), targets in sorted(automaton.transitions.items()):
                for tgt in sorted(list(targets)):
                    edge_symbols.setdefault((st, tgt), []).append(sym)
        elif isinstance(automaton, DFA):
            for (st, sym), tgt in sorted(automaton.transitions.items()):
                edge_symbols.setdefault((st, tgt), []).append(sym)

        for (st, tgt), syms in sorted(edge_symbols.items()):
            label = ", ".join(syms)
            dot_lines.append(f'  "{st}" -> "{tgt}" [label="{label}"];')

        dot_lines.append('}')
        return "\n".join(dot_lines)

    @staticmethod
    def _format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
        """Helper to create clean markdown tables."""
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(cell))

        header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
        sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"

        row_lines = []
        for row in rows:
            formatted_cells = [cell.ljust(col_widths[i]) for i, cell in enumerate(row)]
            row_lines.append("| " + " | ".join(formatted_cells) + " |")

        return "\n".join([header_line, sep_line] + row_lines)
