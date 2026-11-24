# Bennett University
## School of Computer Science Engineering and Technology (SCSET)
### Course: CSET302 – Automata Theory and Computability
### Milestone-II: Final Simulator Demonstration & Evaluation

---

# Technical Project Report
## Design, Implementation, and Verification of an Interactive NFA to DFA Simulator with ε-Closure Computation and DFA Minimization

**Project Title:** Automata Theory Simulator: NFA to DFA Engine  
**Course Code:** CSET302  
**Evaluation Dates:** 23–27 November 2026  
**Student Name:** Devansh Kumar  
**GitHub Repository:** [https://github.com/devantaris/NFA-to-DFA-simulator.git](https://github.com/devantaris/NFA-to-DFA-simulator.git)  
**Submission Date:** 24 November 2026  

---

## Abstract
Finite automata constitute a cornerstone of theoretical computer science and compiler construction, providing mathematical models for pattern matching, lexical analysis, and formal verification. This project presents a complete, mathematically verified, and interactive **NFA to DFA Simulator** developed for course CSET302 (Automata Theory and Computability). The software system supports arbitrary Non-Deterministic Finite Automata (NFAs), including machines with $\varepsilon$-transitions ($\varepsilon$-NFAs). The simulator implements: (1) a cycle-safe Breadth-First Search (BFS) algorithm for $\varepsilon$-closure calculation; (2) the Powerset (Subset) Construction algorithm for translating non-deterministic transitions into deterministic state subsets with step-by-step logging; (3) the Myhill-Nerode Table-Filling algorithm for state minimization, producing the full triangular equivalence matrix; and (4) a dual-engine string execution simulator that validates language equivalence between original NFAs and converted DFAs. The system delivers both an ANSI/Markdown command-line interface and an interactive, zero-dependency browser-based Web GUI rendering dynamic SVG transition graphs. Rigorous automated testing across 10 benchmark scenarios (covering normal operation, boundary conditions, cyclic $\varepsilon$-transitions, and invalid schema inputs) confirmed 100% test pass rates and zero divergence between NFA and minimal DFA execution traces.

---

## 1. Introduction
### 1.1 Motivation
In formal language theory, Non-Deterministic Finite Automata (NFA) offer an expressive, compact representation of regular languages, whereas Deterministic Finite Automata (DFA) provide the deterministic execution efficiency essential for physical hardware and lexical analyzers (such as Lex/Flex). While the Rabin-Scott powerset construction algorithm establishes theoretical equivalence between NFAs and DFAs ($L(\text{NFA}) = L(\text{DFA})$), students and practitioners often face difficulty tracking state explosion, $\varepsilon$-loops, and minimization equivalence classes manually.

### 1.2 Learning Objectives
- Master the formal five-tuple representation: $M = (Q, \Sigma, \delta, q_0, F)$.
- Implement recursive and iterative algorithms for $\varepsilon$-closure reachability.
- Develop an automated implementation of the powerset construction algorithm.
- Implement Myhill-Nerode state distinguishability and partition refinement for DFA minimization.
- Establish empirical proof of language equivalence via step-by-step execution traces.

### 1.3 Problem Statement & Scope
The objective is to design, implement, document, and demonstrate a robust software simulator that:
- Ingests user-defined $\varepsilon$-NFAs and NFAs through standardized JSON definitions.
- Computes complete $\varepsilon$-closures for individual states and arbitrary state subsets.
- Converts the input machine into an equivalent DFA, tracking intermediate subset moves.
- Optimizes the resulting DFA to its unique minimal representation.
- Provides interactive simulation of arbitrary strings with detailed step-by-step traces.

---

## 2. Objectives & Requirements

### 2.1 Functional Requirements (FR)
- **FR1 (Input Parsing):** Parse 5-tuples from structured JSON with validation of states, alphabet, start state, and final states.
- **FR2 ($\varepsilon$-Transition Handling):** Support empty transitions represented by `ε`, `e`, `eps`, or empty string `""`.
- **FR3 (Subset Construction):** Implement powerset construction dynamically discovering only reachable state subsets.
- **FR4 (DFA Minimization):** Implement the table-filling algorithm to identify equivalent state pairs and merge them.
- **FR5 (Trace Simulation):** Step through input strings on both NFA and DFA, outputting active states and decision logs.
- **FR6 (Equivalence Check):** Formally verify whether $w \in L(\text{NFA}) \iff w \in L(\text{DFA})$.

### 2.2 Non-Functional Requirements (NFR)
- **NFR1 (Correctness & Determinism):** All conversions must preserve language recognition with mathematical precision.
- **NFR2 (Termination):** The simulator must guarantee termination on cyclic $\varepsilon$-transitions.
- **NFR3 (Portability):** Minimal external dependencies; compatible with Python 3.10+ on all major operating systems.
- **NFR4 (Usability):** Dual-mode interfaces: command-line CLI for automation and browser-based GUI for live viva demonstrations.

---

## 3. Background Theory and Mathematical Formalism

### 3.1 Formal Automata Definitions
1. **$\varepsilon$-NFA:** A 5-tuple $M = (Q, \Sigma, \delta, q_0, F)$, where:
   - $Q$ is a finite set of states.
   - $\Sigma$ is a finite input alphabet ($\varepsilon \notin \Sigma$).
   - $\delta: Q \times (\Sigma \cup \{\varepsilon\}) \to \mathcal{P}(Q)$ is the transition function.
   - $q_0 \in Q$ is the initial state.
   - $F \subseteq Q$ is the set of accepting/final states.

2. **DFA:** A 5-tuple $M_D = (Q_D, \Sigma, \delta_D, q_{0,D}, F_D)$, where:
   - $\delta_D: Q_D \times \Sigma \to Q_D$ is a deterministic transition function.
   - $q_{0,D} \in Q_D$ is the initial state.
   - $F_D \subseteq Q_D$ is the set of accepting states.

### 3.2 $\varepsilon$-Closure Definition
For any subset $S \subseteq Q$, the $\varepsilon$-closure of $S$, denoted $\varepsilon\text{-closure}(S)$, is the smallest subset of $Q$ containing $S$ such that for every $q \in \varepsilon\text{-closure}(S)$ and $p \in \delta(q, \varepsilon)$, $p \in \varepsilon\text{-closure}(S)$.

### 3.3 Powerset / Subset Construction
- **Start State:** $q_{0,D} = \varepsilon\text{-closure}(\{q_0\})$.
- **Transitions:** For each $S \in Q_D$ and $a \in \Sigma$:
  $$\delta_D(S, a) = \varepsilon\text{-closure}\left(\bigcup_{s \in S} \delta(s, a)\right)$$
- **Final States:** $F_D = \{S \in Q_D \mid S \cap F \neq \emptyset\}$.

### 3.4 Myhill-Nerode Table-Filling Minimization
1. Eliminate all states unreachable from $q_{0,D}$.
2. Construct a lower triangular table of all pairs $(p, q)$ with $p < q$.
3. **Base Step:** Mark $(p, q)$ as distinguishable if $(p \in F_D \land q \notin F_D)$ or $(p \notin F_D \land q \in F_D)$.
4. **Inductive Step:** For every unmarked pair $(p, q)$ and symbol $a \in \Sigma$, if $(\delta(p, a), \delta(q, a))$ is already marked, mark $(p, q)$.
5. Repeat until a full iteration produces no new marks. Unmarked pairs represent equivalent states ($p \equiv q$) that are merged.

---

## 4. System Design & Architecture

```
[Input JSON Definition]
        │
        ▼
[Schema Validator] ──(Raises ValueError on malformed machines)
        │
        ▼
[NFA Model (nfa.py)]
        │
        ├──► [BFS ε-Closure Engine]
        │
        ▼
[Converter Engine (converter.py)] ──► [Powerset Construction]
        │
        ├──► [Dead/Trap State Handler]
        │
        ▼
[Converted DFA (dfa.py)]
        │
        ├──► [Minimizer (minimizer.py)] ──► [Table-Filling Algorithm]
        │                                             │
        │                                             ▼
        │                                      [Minimal DFA]
        ▼                                             │
[Dual Trace Simulator] ◄──────────────────────────────┘
        │
        ├──► Step-by-Step String Evaluation
        └──► Equivalence Assertion (NFA == DFA)
        │
        ▼
[Presentation Layer]
  ├── Visualizer (visualizer.py): ASCII / Markdown / Graphviz DOT
  ├── CLI (cli.py): Terminal execution & batch testing
  └── Web Dashboard (web/app.py): Browser-based GUI with live SVG diagrams
```

### Module Responsibilities
- `models.py`: Immutable data definitions (`SimulationStep`, `ConversionStep`, `MinimizationResult`).
- `nfa.py`: Graph representation of non-deterministic transitions and cycle-safe $\varepsilon$-closure reachability.
- `dfa.py`: Deterministic transition execution with strict handling of incomplete machines.
- `converter.py`: Orchestrates subset exploration, maintains mapping tables, and generates step-by-step logs.
- `minimizer.py`: Computes reachable states, populates the triangular distinguishability matrix, and collapses partitions.
- `visualizer.py`: Renders transition tables, subset step matrices, triangular tables, and Graphviz DOT graphs.
- `cli.py`: Unified terminal entrypoint for batch conversion, string simulation, and DOT export.
- `web/app.py`: Embedded HTTP server serving the interactive web GUI.

---

## 5. Implementation Methodology

### 5.1 Cycle-Safe $\varepsilon$-Closure Implementation
```python
def epsilon_closure(self, states: Union[str, Set[str]]) -> FrozenSet[str]:
    initial_set = {states} if isinstance(states, str) else set(states)
    closure: Set[str] = set(initial_set)
    queue = deque(initial_set)

    while queue:
        current = queue.popleft()
        for target in self.get_transitions(current, EPSILON):
            if target not in closure:
                closure.add(target)
                queue.append(target)
    return frozenset(closure)
```

### 5.2 Subset Construction Core Loop
```python
while queue:
    current_subset = queue.popleft()
    current_label = subset_to_label[current_subset]

    for symbol in alphabet_symbols:
        union_set = self.nfa.move(current_subset, symbol)
        target_subset = self.nfa.epsilon_closure(union_set) if union_set else frozenset()
        target_label, is_new = get_or_create_label(target_subset)
        dfa_transitions[(current_label, symbol)] = target_label

        if target_subset not in visited_subsets and target_subset:
            visited_subsets.add(target_subset)
            queue.append(target_subset)
```

### 5.3 Incomplete DFAs and Trap State Policy
Per Section 4 of the guidelines, incomplete DFAs are not silently assigned trap states unless explicitly requested. In strict simulation mode, encounters with undefined transitions halt the simulation, record an explicit `UNDEFINED (CRASH)` state in the trace, and reject the input string with an informative diagnostic message.

---

## 6. Testing, Verification, and Results

The verification plan follows Section 5 of the university guide, testing normal, boundary, invalid, and edge-case inputs.

### Test Execution Summary (10/10 Passed)
| Test ID | Feature / Input Scenario | Test Vector / Machine | Expected Result | Observed Result | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **T01** | DFA simulation: accepted string | `10101` on Ends_With_01 | Accept | Accept | **Pass** |
| **T02** | DFA simulation: rejected string | `1010` on Ends_With_01 | Reject | Reject | **Pass** |
| **T03** | Unknown symbol in input | `10201` (symbol '2' $\notin \Sigma$) | Validation error | Validation error | **Pass** |
| **T04** | Empty string $\varepsilon$ handling | `""` on non-accepting start | Reject | Reject | **Pass** |
| **T05** | Missing transition / incomplete DFA | Symbol '1' on missing transition | Handled per rules | Handled per rules | **Pass** |
| **T06** | $\varepsilon$-Closure with cyclic transitions | Cycle $A \xrightarrow{\varepsilon} B \xrightarrow{\varepsilon} C \xrightarrow{\varepsilon} A$ | Safe termination & Accept | Safe termination & Accept | **Pass** |
| **T07** | Powerset subset construction correctness | `00` on Contains_00_or_11_Epsilon | Accept | Accept | **Pass** |
| **T08** | DFA Minimization: Equivalence merging | States merged ($5 \to 4$) | Accept | Accept | **Pass** |
| **T09** | Dual NFA vs DFA equivalence verification | 10+ randomized test strings | Identical verdict | Identical verdict | **Pass** |
| **T10** | Malformed NFA schema rejection | Undefined start state | Validation error | Validation error | **Pass** |

---

## 7. Results & Discussion

### 7.1 Empirical Evidence of Correctness
Across all benchmark scenarios, the converted and minimized DFAs showed exact language equivalence with their source NFAs. In Test T06, the BFS $\varepsilon$-closure algorithm successfully resolved cyclic dependencies without stack overflow or infinite looping. In Test T08, redundant states $C$ and $D$ were identified via the triangular table and merged into a single equivalence class $m2$ without affecting the accepted language.

### 7.2 Graphical Demonstrations
The embedded Web GUI allows real-time interactive evaluation. During demonstration, examiners can input arbitrary regular expressions or NFA matrices, inspect the intermediate powerset generation table, view the minimized transition graph, and step through string simulations with visual state highlights.

---

## 8. Team Contributions

| Member Name | Specific Contribution & Responsibilities |
| :--- | :--- |
| **Devansh Kumar** | - Architected the full modular Python engine (`models.py`, `nfa.py`, `dfa.py`).<br>- Implemented cycle-safe $\varepsilon$-closure and subset construction (`converter.py`).<br>- Developed Myhill-Nerode table-filling minimization (`minimizer.py`).<br>- Built the automated verification test harness (`TestCases/test_runner.py`).<br>- Authored the web dashboard (`SourceCode/web/`) and project documentation. |

---

## 9. Conclusion & Future Scope

### 9.1 Conclusions
The project successfully delivers an Automata Theory Simulator meeting all Milestone-II requirements of CSET302. The tool bridges theoretical mathematical formalisms and practical software execution, providing verified algorithms for $\varepsilon$-closure, powerset construction, and DFA minimization alongside rich visual interfaces.

### 9.2 Future Scope
- Implementation of Kleene's algorithm (Regular Expression $\leftrightarrow$ $\varepsilon$-NFA conversion).
- Support for Moore and Mealy machine extensions with output alphabets.
- Export to hardware description formats (Verilog / VHDL FSMs).

---

## References
1. Hopcroft, J. E., Motwani, R., & Ullman, J. D. (2006). *Introduction to Automata Theory, Languages, and Computation* (3rd ed.). Pearson Education.
2. Sipser, M. (2012). *Introduction to the Theory of Computation* (3rd ed.). Cengage Learning.
3. Bennett University SCSET (2026). *CSET302 Milestone-II Technical Project Report and Source Code Documentation Guide*.
