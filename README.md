# Automata Theory Simulator: NFA to DFA Engine (Group ID: Milestone-II)

**Course:** CSET302 – Automata Theory and Computability  
**School:** School of Computer Science Engineering and Technology (SCSET), Bennett University  
**Project:** Milestone-II Final Simulator Demonstration & Evaluation (23–27 November 2026)  
**Author:** Devansh Kumar  
**Repository:** [https://github.com/devantaris/NFA-to-DFA-simulator.git](https://github.com/devantaris/NFA-to-DFA-simulator.git)

---

## Overview: What does the simulator do?

The **NFA to DFA Simulator** is a Python-based academic software engine and interactive demonstration system developed for **CSET302: Automata Theory and Computability**. It takes any arbitrary Non-Deterministic Finite Automaton (NFA)—including machines with $\varepsilon$-transitions ($\varepsilon$-NFAs)—and deterministically performs:
1. **$\varepsilon$-Closure computation** using cycle-safe Breadth-First Search (BFS).
2. **Subset / Powerset Construction** to generate an equivalent Deterministic Finite Automaton (DFA) with step-by-step transition tracking.
3. **DFA Minimization** via the **Myhill-Nerode Table-Filling Algorithm**, generating the formal triangular equivalence matrix.
4. **Dual String Simulation & Equivalence Verification**, executing input strings simultaneously on both the NFA (tracking branching active subsets) and the Minimal DFA (tracking deterministic state sequences) to prove computational equivalence.
5. **Interactive Visualization**, providing both an ANSI/Markdown terminal CLI and a zero-dependency interactive browser GUI with real-time SVG state transition graph rendering.

---

## Supported features: list implemented operations

- **5-Tuple Formal Definition Parsing & Validation:** Supports standard JSON schemas for $(Q, \Sigma, \delta, q_0, F)$ with defensive error checking for missing states, invalid symbols, and malformed inputs.
- **$\varepsilon$-Transition Support:** Handles arbitrary $\varepsilon$-transitions (accepting representations: `ε`, `e`, `eps`, or empty string `""`), with cycle detection.
- **Powerset / Subset Construction:**
  - Initial state computation: $q_{0,D} = \varepsilon\text{-closure}(q_0)$.
  - Iterative subset transitions: $\delta_D(S, a) = \varepsilon\text{-closure}\left(\bigcup_{s \in S} \delta(s, a)\right)$.
  - Dynamic discovery of reachable subsets with canonical renaming ($\{q_0, q_1\} \to q_1$ or $S_0, S_1$).
  - Configurable handling of incomplete DFAs and explicit `DEAD` / `TRAP` states.
- **Myhill-Nerode State Minimization:**
  - BFS unreachable state elimination.
  - Triangular table generation $(p, q)$ marking 0-distinguishable base pairs and iterative $k$-distinguishable transitions.
  - Merging of equivalent states into canonical minimal states.
- **Step-by-Step Simulation & Trace Generation:**
  - Full trace recording each consumed symbol, remaining input, active states, and mathematical operation.
  - Exact equivalence checking: $w \in L(\text{NFA}) \iff w \in L(\text{DFA})$.
- **Multi-Modal Visual Interfaces:**
  - Rich CLI formatting with ASCII/Markdown tables.
  - Graphviz `.dot` specification generation.
  - Interactive Browser GUI (`http://localhost:8000`) for live demonstrations during viva.

---

## Technology stack and dependencies: versions

- **Language:** Python 3.10+ (Tested on Python 3.14.3)
- **Frontend / Visualization:** HTML5, CSS3, JavaScript (ES6+), Viz.js (SVG graph layout)
- **Standard Library Modules:** `json`, `argparse`, `http.server`, `collections`, `pathlib`, `typing`, `dataclasses`
- **Optional Dependencies:**
  - `pytest>=7.0.0` (Automated test runner)
  - `tabulate>=0.9.0` (Enhanced CLI table formatting)

---

## Installation: numbered setup commands

1. **Clone the repository:**
   ```bash
   git clone https://github.com/devantaris/NFA-to-DFA-simulator.git
   cd "NFA-to-DFA-simulator"
   ```

2. **(Optional) Create and activate a Python virtual environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux / macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## How to run: exact command and entry point

### Option A: Launch Interactive Web GUI (Recommended for Demonstration)
```bash
python -m SourceCode.cli --web
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

### Option B: Interactive Terminal Mode
```bash
python -m SourceCode.cli --interactive
```

### Option C: Command-Line Conversion and Simulation
```bash
# Convert NFA to DFA, minimize it, and simulate a string:
python -m SourceCode.cli --file TestCases/definitions/01_ends_with_01.json --convert --minimize --simulate 10101

# Export Graphviz DOT files:
python -m SourceCode.cli --file TestCases/definitions/01_ends_with_01.json --export-dot Screenshots/dot
```

---

## Example: sample automaton definition, input and output

### Sample Definition (`TestCases/definitions/01_ends_with_01.json`)
```json
{
  "name": "Ends_With_01",
  "states": ["q0", "q1", "q2"],
  "alphabet": ["0", "1"],
  "start_state": "q0",
  "final_states": ["q2"],
  "transitions": [
    { "from": "q0", "symbol": "0", "to": ["q0", "q1"] },
    { "from": "q0", "symbol": "1", "to": ["q0"] },
    { "from": "q1", "symbol": "1", "to": ["q2"] }
  ]
}
```

### Sample Command
```bash
python -m SourceCode.cli --file TestCases/definitions/01_ends_with_01.json --convert --minimize --simulate 10101
```

### Sample Output Trace
```
--- Original NFA Transition Table ---
| State | 0        | 1    |
| ----- | -------- | ---- |
| → q0  | {q0, q1} | {q0} |
| q1    | ∅        | {q2} |
| * q2  | ∅        | ∅    |

--- Subset Construction Step-by-Step Log ---
| Step | DFA State | NFA Subset | Input | Move(S, a) | ε-Closure / Next Subset | Target State | New? |
| ---- | --------- | ---------- | ----- | ---------- | ----------------------- | ------------ | ---- |
| 1    | q0        | {q0}       | 0     | {q0, q1}   | {q0, q1}                | q1           | Yes  |
| 2    | q0        | {q0}       | 1     | {q0}       | {q0}                    | q0           | No   |
| 3    | q1        | {q0, q1}   | 0     | {q0, q1}   | {q0, q1}                | q1           | No   |
| 4    | q1        | {q0, q1}   | 1     | {q0, q2}   | {q0, q2}                | q2           | Yes  |
| 5    | q2        | {q0, q2}   | 0     | {q0, q1}   | {q0, q1}                | q1           | No   |
| 6    | q2        | {q0, q2}   | 1     | {q0}       | {q0}                    | q0           | No   |

================ String Simulation: '10101' ================
[1] NFA Execution Trace:
    Step 5: Consumed '1' -> Active states: {q0, q2}
    Verdict: ACCEPTED (Contains accepting state 'q2')

[2] Minimal DFA Execution Trace:
    Step 5: Consumed '1' -> Ended in state 'm2'
    Verdict: ACCEPTED

[3] Equivalence Verification: PASS (NFA and DFA agree)
```

---

## Project structure: modules and responsibilities

```
GroupID_Topic_Milestone2/
├── .gitignore                          # Standard git exclusion rules
├── README.md                            # Comprehensive project guide (this file)
├── requirements.txt                     # Python package dependencies
├── SourceCode/
│   ├── __init__.py                      # Package entrypoint & symbol exports
│   ├── models.py                        # Dataclasses (SimulationStep, ConversionResult, etc.)
│   ├── nfa.py                           # NFA class, validation, cycle-safe ε-closure
│   ├── dfa.py                           # DFA class, deterministic step-by-step simulator
│   ├── converter.py                     # Powerset / subset construction algorithm
│   ├── minimizer.py                     # Myhill-Nerode table-filling minimization engine
│   ├── visualizer.py                    # ASCII / Markdown tables, Graphviz DOT generator
│   ├── cli.py                           # Full-featured command-line interface
│   └── web/                             # Browser GUI for viva demonstrations
│       ├── app.py                       # Zero-dependency Python HTTP server
│       └── static/
│           ├── index.html               # Modern interactive UI
│           ├── app.js                   # Client controller and Viz.js rendering
│           └── styles.css               # Clean styling
├── TestCases/
│   ├── definitions/                     # Benchmark automaton JSON files
│   │   ├── 01_ends_with_01.json         # Standard binary NFA
│   │   ├── 02_contains_00_epsilon.json  # Multi-branch ε-NFA
│   │   ├── 03_cyclic_epsilon.json       # Cyclic ε-transition loop
│   │   ├── 04_redundant_dfa.json        # Minimization candidate with redundant states
│   │   └── 05_incomplete_automaton.json # Incomplete transition verification
│   ├── test_cases.json                  # Formal rubric test specifications (T01 - T10)
│   └── test_runner.py                   # Automated verification harness
├── Report/
│   ├── CSET302_Milestone2_Project_Report.md # Full 9-section academic project report
│   └── references.md                    # Standard textbook & paper citations
└── Screenshots/                         # Visual evidence for report & evaluation
    └── dot/                             # Exported Graphviz .dot files
```

---

## Testing: command, test data and expected behavior

Run the automated test suite implementing test cases **T01 through T10** matching Section 5 of the evaluation guide:

```bash
# Direct runner:
python -m TestCases.test_runner

# Or using Pytest:
python -m pytest TestCases/test_runner.py -v
```

### Milestone-II Verification Matrix
| Test ID | Feature / Input Scenario | Test Vector | Expected Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| **T01** | DFA simulation: accepted string | `10101` on Ends_With_01 | Accept | **PASS** |
| **T02** | DFA simulation: rejected string | `1010` on Ends_With_01 | Reject | **PASS** |
| **T03** | Unknown symbol in input | `10201` (symbol '2' $\notin \Sigma$) | Validation error | **PASS** |
| **T04** | Empty string $\varepsilon$ handling | `""` on non-accepting start state | Reject | **PASS** |
| **T05** | Missing transition / incomplete DFA | Symbol '1' on missing transition | Handled per documented rules | **PASS** |
| **T06** | $\varepsilon$-Closure with cyclic transitions | Cycle $A \xrightarrow{\varepsilon} B \xrightarrow{\varepsilon} C \xrightarrow{\varepsilon} A$ | Safe termination & Accept | **PASS** |
| **T07** | Powerset subset construction correctness | `00` on Contains_00_or_11_Epsilon | Accept | **PASS** |
| **T08** | DFA Minimization: Equivalence merging | Redundant states merged ($5 \to 4$) | Accept | **PASS** |
| **T09** | Dual NFA vs DFA equivalence verification | 10+ randomized and boundary strings | Identical verdict | **PASS** |
| **T10** | Malformed NFA schema rejection | Undefined start state identifier | Validation error | **PASS** |

---

## Known limitations and troubleshooting

1. **State Space Explosion:** In theoretical worst-case scenarios, powerset construction can generate up to $2^{|Q|}$ states. The simulator discovers states dynamically on-demand, pruning unreachable subsets to minimize overhead.
2. **Graphviz Rendering:** When running in terminal mode, Graphviz `.dot` files are exported to disk. For interactive live diagram previews without installing Graphviz system binaries, run the web interface (`python -m SourceCode.cli --web`), which renders graphs in-browser via JavaScript.
3. **Incomplete Automata Policy:** In accordance with Section 4 of the guidelines, incomplete DFAs report missing transitions during string evaluation unless the `--dead-state` flag is used to explicitly route missing edges to a dedicated `DEAD` trap state.

---

## Team contributions and acknowledgements

- **Devansh Kumar:**
  - Designed the core mathematical models (`models.py`, `nfa.py`, `dfa.py`).
  - Implemented the $\varepsilon$-closure algorithm and Powerset Subset Construction engine (`converter.py`).
  - Implemented the Myhill-Nerode Table-Filling DFA Minimization engine (`minimizer.py`).
  - Developed the automated verification harness and test cases (`TestCases/`).
  - Designed the interactive CLI and browser-based demonstration UI (`SourceCode/web/`).
  - Authored the technical project report and documentation.

### References
1. Hopcroft, J. E., Motwani, R., & Ullman, J. D. (2006). *Introduction to Automata Theory, Languages, and Computation* (3rd ed.). Pearson.
2. Sipser, M. (2012). *Introduction to the Theory of Computation* (3rd ed.). Cengage Learning.
3. Bennett University SCSET *CSET302 Milestone-II Technical Project Report and Source Code Documentation Guide*.
