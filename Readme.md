# SI2002 Formal Languages - Assignment 2: Subset Construction

- **Students' full names:** Juan José Duque Marín, Juan Lucas Ramírez Romero and Samuel Pulgarin
- **Class number:** S2666-0509

## Environment

- Operating system: Windows 11 (build 10.0.26200)
- Programming language: Python 3.12
- Tools: no external tools or packages. Only the Python standard library is used:
  `os`, `sys`, `re`, `collections` and, for the optional visual mode, `tkinter`
  (included with the standard Python installer for Windows).

## How to run

The program reads the input described in the assignment and prints, for each case,
the transition table of the equivalent DFA.

**Command Prompt (cmd) or bash** (on Linux/macOS use `python3`):

```
python subset_construction.py < entrada.txt
```

**PowerShell** (it does not support `<` redirection):

```
Get-Content entrada.txt | python subset_construction.py
```

**Any terminal**, passing the file as an argument:

```
python subset_construction.py entrada.txt
```

All three commands print exactly the same output. Use `--cli` to force text mode
in any situation.

### Checking an input file

```
python subset_construction.py --check entrada.txt
```

This only validates the input (it does not build the DFA) and lists every problem
found, each with its line number. The same validation runs before every
construction: if the input is invalid, nothing is printed to standard output, all
problems are written to standard error and the program exits with code 1.

### Optional: step-by-step visual mode

```
python subset_construction.py --gui entrada.txt
```

The visual mode also opens automatically when the script is started with no
arguments and no input redirection (for example, with the VS Code "Run" button).
In that case it loads `entrada.txt` from the script folder or the current folder,
or a built-in sample if neither exists.

The window shows:

- the DFA diagram as it is discovered: accepting states are drawn as double circles,
  the initial state has an incoming arrow and edges are labelled with their symbols;
- the transition table of the DFA, filled one cell at a time;
- the BFS queue of states waiting to be expanded;
- a log that explains every step formally, for example
  `δ'({3, 5}, a) = Δ(3, a) ∪ Δ(5, a) = {2, 4} ∪ {1, 5} = {1, 2, 4, 5}`.

Controls: Step, Back, Play/Pause with an adjustable delay (100 to 2000 ms),
Run to end, Load/Reset, case selector, Open file and Edit input.

If Tkinter or a display is not available, the program prints the tables instead.

## Input format

```
c          number of cases
n          number of states (the states are 1..n)
S          initial states, separated by spaces
Sigma      alphabet symbols, separated by spaces
F          final states, separated by spaces
n lines    row i: "i set_1 set_2 ..." (one set per symbol, in alphabet order)
```

Sets are written with braces, e.g. `{1 5}` (`{1, 5}` and `{}` are also accepted);
the empty set is written `0`. A repeated state inside a set is allowed and counted
once, since `{1 1}` is the same set as `{1}`.

## Output format

For each case, the program prints one table; the tables of consecutive cases are
separated by a single blank line:

| Column    | Meaning                                                                 |
|-----------|-------------------------------------------------------------------------|
| `mark`    | `->` initial state, `*` accepting state, `->*` both                     |
| `state`   | new name of the DFA state (1, 2, 3, ... in order of discovery)          |
| `subset`  | set of NFA states that the DFA state represents (`0` is the empty set)  |
| one column per symbol | the DFA state reached with that symbol                      |

Example: for the input given in the assignment (file `entrada.txt`) the output is

```
mark  state  subset     a  b
->    1      {3 5}      2  3
*     2      {1 2 4 5}  4  5
*     3      {4}        6  7
*     4      {1 5}      4  3
*     5      {4 5}      4  5
      6      0          6  6
      7      {5}        4  3
```

The input is validated before the construction: the numbers of cases and states
must be positive integers, every state must lie in {1..n}, the alphabet may not
repeat symbols, there must be exactly one row per state with one well-formed set
per symbol, and nothing may follow the last case. Error messages go to standard
error, never to standard output.

## Explanation of the algorithm

Let N = (Q, Σ, Δ, S, F) be an NFA, where Δ : Q × Σ → P(Q) and S ⊆ Q is a set of
initial states. Following Kozen (1997, Lecture 6), the subset construction defines
the DFA

    M = (P(Q), Σ, δ', s', F')

where

- **States:** subsets A ⊆ Q of states of N.
- **Initial state:** s' = S, the set of all initial states of N.
- **Transition function:** δ'(A, a) = ⋃ { Δ(q, a) : q ∈ A }, i.e. every state that
  N can reach from some state of A by reading a. In particular δ'(∅, a) = ∅.
- **Accepting states:** F' = { A ⊆ Q : A ∩ F ≠ ∅ }, the subsets that contain at
  least one accepting state of N.

**Why it works.** By induction on the length of a string x, the state reached by M
after reading x is exactly the set of states that N can be in after reading x:
δ̂'(S, x) = Δ̂(S, x). Hence x is accepted by M if and only if that set contains an
accepting state of N, that is, if and only if N accepts x. So L(M) = L(N).

**Only reachable subsets.** P(Q) has 2^n elements, but most of them usually cannot
be reached from S. Removing unreachable states does not change the language,
because no string ever leads to them. The program therefore builds only the
reachable part of M with a breadth-first search:

1. Create state 1 = S and put it in a queue.
2. Take the next subset A from the queue. For each symbol a ∈ Σ (in input order),
   compute B = δ'(A, a). If B has not been seen before, give it the next number and
   add it to the queue. Record the transition A --a--> B.
3. Repeat step 2 until the queue is empty.
4. Mark as accepting every discovered subset A with A ∩ F ≠ ∅.

If the empty set is reached, it becomes an ordinary dead (sink) state that goes to
itself on every symbol, so M is a complete DFA. For the example above, M has 7
reachable states instead of 2^5 = 32.

**Complexity.** Each discovered subset is expanded once, and each expansion does
|Σ| unions over at most n states, so the time is O(k · |Σ| · n) set operations,
where k ≤ 2^n is the number of reachable subsets.

**Implementation note.** The construction is a single generator,
`subset_construction_steps`, that yields one event per step (start, expand,
transition, done). The text mode consumes all events and prints the final table;
the visual mode replays the same events one by one, so both modes always use
exactly the same algorithm.

## Reference

Kozen, Dexter C. (1997). *Automata and Computability*. Springer-Verlag.
https://doi.org/10.1007/978-1-4612-1844-9
