"""Command-Line Interface (CLI) for NFA to DFA Simulator.

CSET302 - Automata Theory and Computability
Author: Devansh Kumar
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .converter import NFAtoDFAConverter
from .dfa import DFA
from .minimizer import DFAMinimizer
from .models import EPSILON
from .nfa import NFA
from .visualizer import Visualizer


def print_banner() -> None:
    banner = """
========================================================================
       CSET302: Automata Theory Simulator - NFA to DFA Engine
========================================================================
  Features: ε-Closure | Subset Construction | DFA Minimization | Trace
========================================================================
"""
    print(banner)


def handle_file(path_str: str) -> NFA:
    path = Path(path_str)
    if not path.exists():
        print(f"[Error] Specified file does not exist: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return NFA.from_json(content)


def run_interactive() -> None:
    print("\n--- Interactive Automaton Mode ---")
    print("Example JSON format:")
    example = {
        "name": "Ends_with_01",
        "states": ["q0", "q1", "q2"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "final_states": ["q2"],
        "transitions": [
            {"from": "q0", "symbol": "0", "to": ["q0", "q1"]},
            {"from": "q0", "symbol": "1", "to": ["q0"]},
            {"from": "q1", "symbol": "1", "to": ["q2"]}
        ]
    }
    print(json.dumps(example, indent=2))
    print("\nEnter path to JSON file or press Enter to load built-in sample:")
    choice = input("> ").strip()
    if choice:
        nfa = handle_file(choice)
    else:
        nfa = NFA.from_dict(example)

    print(f"\n[+] Loaded NFA: '{nfa.name}'")
    print(Visualizer.nfa_transition_table(nfa))

    print("\n[+] Converting to DFA via Powerset Construction...")
    conv = NFAtoDFAConverter(nfa).convert()
    print("\nSubset Construction Log:")
    print(Visualizer.subset_construction_table(conv))
    print("\nConverted DFA Transition Table:")
    print(Visualizer.dfa_transition_table(conv.dfa))

    print("\n[+] Minimizing DFA via Myhill-Nerode Table-Filling...")
    min_res = DFAMinimizer(conv.dfa).minimize()
    print(Visualizer.minimization_table(min_res))
    print("\nMinimal DFA Transition Table:")
    print(Visualizer.dfa_transition_table(min_res.minimal_dfa))

    while True:
        print("\nEnter a test string to simulate (or 'exit' to quit):")
        test_str = input("> ").strip()
        if test_str.lower() in ("exit", "quit", "q"):
            break

        print(f"\n--- Simulating on NFA: '{test_str}' ---")
        nfa_res = nfa.simulate(test_str)
        print(Visualizer.simulation_trace_table(nfa_res))

        print(f"\n--- Simulating on Minimal DFA: '{test_str}' ---")
        dfa_res = min_res.minimal_dfa.simulate(test_str)
        print(Visualizer.simulation_trace_table(dfa_res))

        # Check equivalence
        equiv = nfa_res.accepted == dfa_res.accepted
        print(f"\nEquivalence Check: {'PASSED (Consistent verdict)' if equiv else 'FAILED (Discrepancy detected)'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CSET302: NFA to DFA Simulator with ε-closure, minimization and step trace."
    )
    parser.add_argument("--file", "-f", type=str, help="Path to NFA definition JSON file.")
    parser.add_argument("--convert", "-c", action="store_true", help="Perform subset construction.")
    parser.add_argument("--minimize", "-m", action="store_true", help="Perform DFA minimization.")
    parser.add_argument("--simulate", "-s", type=str, help="Simulate input string on both NFA & DFA.")
    parser.add_argument("--export-dot", type=str, help="Directory to export Graphviz .dot files.")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run interactive shell.")
    parser.add_argument("--web", "-w", action="store_true", help="Start the interactive Web UI.")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default 8000).")

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.interactive:
        print_banner()
        run_interactive()
        return

    if args.web:
        from .web.app import run_web_server
        run_web_server(port=args.port)
        return

    if not args.file:
        print("[Error] Please specify an automaton JSON file with --file <path> or use --interactive.")
        sys.exit(1)

    nfa = handle_file(args.file)
    print_banner()
    print(f"Loaded: {nfa.name} (Has ε: {nfa.has_epsilon})")
    print("\n--- Original NFA Transition Table ---")
    print(Visualizer.nfa_transition_table(nfa))

    conv = NFAtoDFAConverter(nfa).convert()

    if args.convert:
        print("\n--- Subset Construction Step-by-Step Log ---")
        print(Visualizer.subset_construction_table(conv))
        print("\n--- Converted DFA Transition Table ---")
        print(Visualizer.dfa_transition_table(conv.dfa))

    min_res = DFAMinimizer(conv.dfa).minimize()
    if args.minimize:
        print("\n--- DFA Minimization (Table-Filling Algorithm) ---")
        print(Visualizer.minimization_table(min_res))
        print("\n--- Minimal DFA Transition Table ---")
        print(Visualizer.dfa_transition_table(min_res.minimal_dfa))

    if args.simulate is not None:
        test_str = args.simulate
        print(f"\n================ String Simulation: '{test_str}' ================")
        nfa_res = nfa.simulate(test_str)
        print("\n[1] NFA Execution Trace:")
        print(Visualizer.simulation_trace_table(nfa_res))

        dfa_res = min_res.minimal_dfa.simulate(test_str)
        print("\n[2] Minimal DFA Execution Trace:")
        print(Visualizer.simulation_trace_table(dfa_res))

        equiv = nfa_res.accepted == dfa_res.accepted
        print("\n[3] Equivalence Verification:")
        print(f"    NFA Verdict: {'ACCEPTED' if nfa_res.accepted else 'REJECTED'}")
        print(f"    DFA Verdict: {'ACCEPTED' if dfa_res.accepted else 'REJECTED'}")
        print(f"    Status:      {'PASS (Equivalence Confirmed)' if equiv else 'FAIL'}")

    if args.export_dot:
        out_dir = Path(args.export_dot)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "nfa.dot").write_text(Visualizer.to_dot(nfa, "Original NFA"), encoding="utf-8")
        (out_dir / "converted_dfa.dot").write_text(Visualizer.to_dot(conv.dfa, "Converted DFA"), encoding="utf-8")
        (out_dir / "minimal_dfa.dot").write_text(Visualizer.to_dot(min_res.minimal_dfa, "Minimal DFA"), encoding="utf-8")
        print(f"\n[+] Exported Graphviz DOT files to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
