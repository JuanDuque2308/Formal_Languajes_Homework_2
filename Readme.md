# SI2002 Formal Languages - Assignment 2: Subset Construction

* **Student's full name:** Juan José Duque Marín, Juan Lucas Ramirez Romero y Samuel Pulgarin

* **Student's class number:** S2666-0509

## Environment

* Operating system: Windows 11 (tested on Windows 10.0.26200)

* Programming language: Python 3 (tested with Python 3.12)

* Tools: none. Only the Python standard library (`re`, `sys`, `os`, `collections`).

## How to run

The program can read from standard input using redirection:

```
python subset_construction.py < entrada.txt

```

In PowerShell or bash environments:

```
Get-Content entrada.txt | python subset_construction.py

```

Alternatively, if executed directly (e.g., via VS Code Run/Play button), the program will automatically look for and read `entrada.txt` located in the project directory.

## Input format

```
c                      number of cases
n                      number of states (states are 1..n)
S                      initial states, separated by spaces
Sigma                  alphabet, separated by spaces
F                      final states, separated by spaces
n lines                row i: "i set_a set_b ..." (one set per symbol, in alphabet order)

```

Sets are written using braces, for example `{1 5}`; the empty set is represented by `0`.

## Output format

For each case, the program prints the transition table of the deterministic finite automaton (DFA) $M$:

* `mark`: Indicates state properties:

  * `->` marks the initial state.

  * `*` marks accepting/final states.

  * `->*` marks a state that is both initial and final.

* `state`: The renamed sequential identifier (1, 2, 3, ...) assigned to each DFA macro-state.

* `subset`: The set of NFA states represented by the corresponding DFA state (`0` denotes the empty set $\emptyset$).

* Destination state columns: One column per alphabet symbol, showing the destination state ID.

## Explanation of the algorithm

The implementation adheres to the Subset Construction method (Kozen 1997, Lecture 6):

1. **Initial State:** The initial state of the DFA $M$ corresponds to the set $S$ containing all initial states of the NFA $N$.

2. **Subset Transitions:** For each reachable DFA macro-state $A \subseteq Q$ and each input symbol $a \in \Sigma$, the target set of states is computed as:
   

   $$
   \delta'(A, a) = \bigcup_{q \in A} \Delta(q, a)
   $$

3. **Reachability Exploration (BFS):** Starting from the initial set $S$, states are discovered using a queue. Newly discovered target subsets are added to the queue and assigned sequential integer identifiers ($1, 2, \dots$). This ensures that only reachable states are generated in the transition table.

4. **Dead / Sink State:** If the empty set $\emptyset$ (represented as `0`) is reached, it is handled as a regular dead state that loops to itself across all symbols in $\Sigma$.

5. **Acceptance Condition:** A DFA macro-state $A$ is an accepting state if and only if it contains at least one accepting state of the original NFA:
   

   $$
   A \cap F \neq \emptyset
   $$