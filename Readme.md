# SI2002 Formal Languages - Assignment 2: Subset Construction

* **Student's full name:** Juan José Duque Marín, Juan Lucas Ramírez Romero, Samuel Pulgarin Giraldo
* **Student's class number:** S2666-0509

## Environment

* **Operating system:** Windows 11 (tested on Windows 10/11 x64, build 26200)


* **Programming language:** Python 3 (tested with Python 3.12 and 3.13)


* **Tools / Libraries:** Python standard library only (`os`, `re`, `sys`, `collections`). No third-party dependencies required.



## How to run

The program is designed to read from standard input (`sys.stdin`) or automatically load `entrada.txt` if executed directly.

### Running with input redirection (Standard)

On Windows (Command Prompt / PowerShell):

```cmd
python subset_construction.py < entrada.txt

```

On Linux / macOS:

```bash
python3 subset_construction.py < entrada.txt

```

### Running directly (e.g., in VS Code)

You can also run the script directly. If no standard input is piped, it will look for `entrada.txt` in the same directory:

```cmd
python subset_construction.py

```

## Input format

The input must comply with the assignment specifications:

```
c                      number of cases
n                      number of states of the NFA (states are 1, 2, ..., n)
S                      initial state(s), separated by spaces
Sigma                  alphabet symbols, separated by spaces
F                      final state(s), separated by spaces
n lines                one line per state (in order 1..n), representing rows of the transition table

```



* Sets are formatted inside `{}` with blank spaces separating the elements (e.g., `{1 5}` or `{1, 5}`).


* The empty set ($0$) is represented by `0`.



## Output format

For each test case, the program prints a formatted transition table representing the equivalent Deterministic Finite Automaton (DFA) $M$:

* `mark`: Identifies the initial state (`->`) and final/accepting states (`*`). A state can be both (`->*`).


* `state`: Identifier assigned to each DFA state ($1, 2, 3, \dots$).


* `subset`: The subset of NFA states represented by that DFA state (`0` represents the empty set).


* One column per symbol of the alphabet ($\Sigma$), showing the destination state ID.



## Explanation of the algorithm

The implementation adheres to the Subset Construction method (Kozen 1997, Lecture 6):

1. **Initial State:** The initial state of the DFA $M$ corresponds to the set $S$ containing all initial states of the NFA $N$.


2. **Subset Transitions:** For each reachable DFA macro-state $A \subseteq Q$ and each input symbol $a \in \Sigma$, the target set of states is computed as:

```math
\delta'(A, a) = \bigcup_{q \in A} \Delta(q, a)

```

3. **Reachability Exploration (BFS):** Starting from the initial set $S$, states are discovered using a queue (breadth-first search). Newly discovered target subsets are added to the queue and assigned sequential integer identifiers ($1, 2, \dots$). This ensures that only reachable states are generated in the transition table.


4. **Dead / Sink State:** If the empty set $\emptyset$ (represented as `0`) is reached, it is handled as a regular dead state that loops to itself across all symbols in $\Sigma$.


5. **Acceptance Condition:** A DFA macro-state $A$ is an accepting state if and only if it contains at least one accepting state of the original NFA:



```math
A \cap F \neq \emptyset

```
