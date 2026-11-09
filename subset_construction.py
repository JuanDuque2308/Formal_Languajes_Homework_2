"""
SI2002 Formal Languages - Assignment 2: Subset Construction (Kozen 1997, Lecture 6).

Converts a nondeterministic finite automaton N = (Q, Sigma, Delta, S, F) into an
equivalent deterministic finite automaton M whose states are the subsets of Q
reachable from S.

Two ways to run it:

  * CLI mode (used for grading). Prints only the DFA tables.
        python subset_construction.py < entrada.txt
        python subset_construction.py entrada.txt
        python subset_construction.py --cli < entrada.txt

  * Check mode. Only validates the input and lists every problem found,
    with its line number.
        python subset_construction.py --check entrada.txt

  * GUI mode (optional extra). A Tkinter window that animates the construction
    step by step. It opens when the script is started without input redirection
    and without arguments (e.g. the VS Code "Run" button), or with --gui.
        python subset_construction.py --gui [entrada.txt]

The algorithm is written once, as a generator of events
(subset_construction_steps). The CLI simply consumes every event; the GUI
replays them one at a time.

Only the Python standard library is used.
"""

import os
import re
import sys
from collections import deque

SAMPLE_INPUT = """1
5
3 5
a b
1 4
1 {1 5} 0
2 {1} 0
3 {2 4} 0
4 0 {5}
5 {1 5} {4}
"""


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

class NFA:
    """N = (Q, Sigma, Delta, S, F) with Q = {1, ..., n}."""

    def __init__(self, n, initial, alphabet, final, delta):
        self.n = n
        self.initial = frozenset(initial)
        self.alphabet = list(alphabet)
        self.final = frozenset(final)
        self.delta = delta  # dict: (state, symbol) -> frozenset of states

    def move(self, q, symbol):
        return self.delta.get((q, symbol), frozenset())


class DFA:
    """Result of the subset construction. States are renamed 1, 2, 3, ..."""

    def __init__(self, alphabet, subsets, trans, finals):
        self.alphabet = alphabet
        self.subsets = subsets  # list: index i holds the subset of state i + 1
        self.trans = trans      # dict: (state_id, symbol) -> state_id
        self.finals = finals    # set of accepting state ids
        self.start = 1

    @property
    def size(self):
        return len(self.subsets)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

class InputError(Exception):
    """Raised with every problem found in the input, one per line of the message."""

    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


SET_TOKEN = re.compile(r"\{[^{}]*\}|\S+")


def _is_nat(token):
    """True for a plain ASCII non-negative integer such as '0' or '12'."""
    return token.isascii() and token.isdigit()


def _parse_int_line(line, what, lo):
    """A line that must hold exactly one integer >= lo."""
    no, text = line
    if not _is_nat(text):
        raise InputError(f"line {no}: {what} must be a single integer, got '{text}'")
    value = int(text)
    if value < lo:
        raise InputError(f"line {no}: {what} must be at least {lo}, got {value}")
    return value


def parse_state_list(text, n, where, errors):
    """
    A set of states written as '1 4', '1, 4', '{1 4}', or '0' / '{}' for the empty set.
    Every state must lie in Q = {1..n}. Repeated states are accepted, since
    {1 1} is the same set as {1}. Problems are appended to errors.
    """
    body = text.strip()
    if body.startswith("{") and body.endswith("}"):
        body = body[1:-1]
    if "{" in body or "}" in body:
        errors.append(f"{where}: unbalanced braces in '{text}'")
        return frozenset()
    tokens = body.replace(",", " ").split()
    if not tokens or tokens == ["0"]:
        return frozenset()

    states = set()
    for t in tokens:
        if not _is_nat(t):
            errors.append(f"{where}: '{t}' is not a state number")
        elif int(t) == 0:
            errors.append(f"{where}: 0 means the empty set and cannot be mixed with states")
        elif int(t) > n:
            errors.append(f"{where}: state {t} is outside Q = {{1..{n}}}")
        else:
            states.add(int(t))  # a repeated state is harmless: {1 1} = {1}
    return frozenset(states)


def parse_set(token, n, where, errors):
    """One transition cell: '{1 5}', '{1, 5}', '{}' or '0' (empty set)."""
    if token == "0":
        return frozenset()
    if not (token.startswith("{") and token.endswith("}")):
        errors.append(f"{where}: '{token}' is not a set; write 0 or {{...}}")
        return frozenset()
    return parse_state_list(token, n, where, errors)


def parse_input(text):
    """
    Parse and validate the whole input; return a list of NFA objects (one per case).

    Every problem found is collected and reported together through InputError,
    each message prefixed with its line number. Checks performed:
      * the number of cases and of states are positive integers;
      * initial and final states are valid state numbers in {1..n}
        (repeated states inside a set are allowed);
      * the alphabet is non-empty, has no repeated symbols and no braces/commas;
      * there is exactly one row per state 1..n, each with one well-formed set
        per symbol, and every target state lies in {1..n};
      * nothing follows the last case.
    """
    text = text.lstrip("\ufeff")  # UTF-8 BOM (e.g. a file saved by Notepad, read via '<')
    lines = [(no, ln.strip()) for no, ln in enumerate(text.splitlines(), 1) if ln.strip()]
    if not lines:
        raise InputError("empty input")

    errors = []

    def line_at(i, expected):
        if i >= len(lines):
            last = lines[-1][0] if lines else 0
            raise InputError(errors + [f"after line {last}: unexpected end of input, "
                                       f"expected {expected}"])
        return lines[i]

    cases = _parse_int_line(line_at(0, "the number of cases"), "the number of cases", 1)

    nfas, pos = [], 1
    for case in range(1, cases + 1):
        try:
            n = _parse_int_line(line_at(pos, f"the number of states of case {case}"),
                                f"case {case}: the number of states", 1)
        except InputError as exc:
            raise InputError(errors + exc.errors)

        no, txt = line_at(pos + 1, f"the initial states of case {case}")
        initial = parse_state_list(txt, n, f"line {no} (case {case}, initial states)", errors)

        no, txt = line_at(pos + 2, f"the alphabet of case {case}")
        alphabet = txt.split()
        where = f"line {no} (case {case}, alphabet)"
        seen = set()
        for sym in alphabet:
            if any(c in sym for c in "{},"):
                errors.append(f"{where}: symbol '{sym}' may not contain braces or commas")
            if sym in seen:
                errors.append(f"{where}: symbol '{sym}' is repeated")
            seen.add(sym)

        no, txt = line_at(pos + 3, f"the final states of case {case}")
        final = parse_state_list(txt, n, f"line {no} (case {case}, final states)", errors)

        delta, rows_seen, bad_rows = {}, set(), 0
        for i in range(n):
            no, txt = line_at(pos + 4 + i, f"row {i + 1} of {n} of the transition table "
                                           f"of case {case}")
            where = f"line {no} (case {case}, transition row)"
            depth = 0
            for ch in txt:
                depth += {"{": 1, "}": -1}.get(ch, 0)
                if depth not in (0, 1):
                    break
            if depth != 0:
                errors.append(f"{where}: unbalanced or nested braces in '{txt}'")
                bad_rows += 1
                continue
            tokens = SET_TOKEN.findall(txt)
            head = tokens[0]
            if not _is_nat(head) or not 1 <= int(head) <= n:
                errors.append(f"{where}: row must start with a state in {{1..{n}}}, got '{head}'")
                bad_rows += 1
                continue
            state = int(head)
            if state in rows_seen:
                errors.append(f"{where}: state {state} already has a row")
                bad_rows += 1
                continue
            rows_seen.add(state)

            cells = tokens[1:]
            if len(cells) != len(alphabet):
                errors.append(f"{where}: state {state} has {len(cells)} sets, expected "
                              f"{len(alphabet)} (one per symbol: {' '.join(alphabet)})")
                continue
            for symbol, cell in zip(alphabet, cells):
                delta[(state, symbol)] = parse_set(
                    cell, n, f"{where[:-1]}, delta({state}, {symbol}))", errors)

        missing = sorted(set(range(1, n + 1)) - rows_seen)
        if missing and len(missing) > bad_rows:
            errors.append(f"case {case}: no row for state(s) {', '.join(map(str, missing))}")

        nfas.append(NFA(n, initial, alphabet, final, delta))
        pos += 4 + n

    if pos < len(lines):
        errors.append(f"line {lines[pos][0]}: unexpected extra content after the last case "
                      f"(the first line says {cases} case(s))")

    if errors:
        raise InputError(errors)
    return nfas


# --------------------------------------------------------------------------
# Subset construction
# --------------------------------------------------------------------------

def subset_construction_steps(nfa):
    """
    Breadth-first subset construction, yielded one event at a time.

    Events (dicts):
      start      - the initial DFA state S was created
      expand     - a state was taken from the front of the queue
      transition - delta'(A, a) was computed for one symbol
      done       - construction finished; carries the DFA
    Every event also carries a snapshot of the queue (list of state ids).
    """
    start = frozenset(nfa.initial)
    ids = {start: 1}
    subsets = [start]
    trans = {}
    queue = deque([start])

    yield {
        "type": "start",
        "id": 1,
        "subset": start,
        "accepting": bool(start & nfa.final),
        "queue": [1],
    }

    while queue:
        current = queue.popleft()
        cid = ids[current]
        yield {"type": "expand", "id": cid, "subset": current,
               "queue": [ids[s] for s in queue]}

        for symbol in nfa.alphabet:
            parts = [(q, nfa.move(q, symbol)) for q in sorted(current)]
            target = frozenset().union(*(p for _, p in parts))

            is_new = target not in ids
            if is_new:
                ids[target] = len(subsets) + 1
                subsets.append(target)
                queue.append(target)
            trans[(cid, symbol)] = ids[target]

            yield {
                "type": "transition",
                "id": cid,
                "subset": current,
                "symbol": symbol,
                "parts": parts,
                "target": target,
                "target_id": ids[target],
                "new": is_new,
                "accepting": bool(target & nfa.final),
                "queue": [ids[s] for s in queue],
            }

    finals = {i + 1 for i, s in enumerate(subsets) if s & nfa.final}
    yield {"type": "done", "dfa": DFA(nfa.alphabet, subsets, trans, finals),
           "queue": []}


def subset_construction(nfa):
    """Run the whole construction and return the DFA."""
    for event in subset_construction_steps(nfa):
        if event["type"] == "done":
            return event["dfa"]


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def fmt_set(subset):
    """Set in the same notation as the input: {1 5}, or 0 for the empty set."""
    if not subset:
        return "0"
    return "{" + " ".join(str(x) for x in sorted(subset)) + "}"


def fmt_math(subset):
    """Set in math notation: {1, 5}, or the symbol for the empty set."""
    if not subset:
        return "∅"
    return "{" + ", ".join(str(x) for x in sorted(subset)) + "}"


def state_mark(dfa, sid):
    mark = "->" if sid == dfa.start else ""
    return mark + ("*" if sid in dfa.finals else "")


def format_dfa(dfa):
    """
    The DFA as a text table:
        mark  state  subset     a  b
        ->    1      {3 5}      2  3
        *     2      {1 2 4 5}  4  5
    """
    header = ["mark", "state", "subset"] + dfa.alphabet
    rows = []
    for sid in range(1, dfa.size + 1):
        rows.append([state_mark(dfa, sid), str(sid), fmt_set(dfa.subsets[sid - 1])]
                    + [str(dfa.trans[(sid, a)]) for a in dfa.alphabet])

    widths = [max(len(r[i]) for r in [header] + rows) for i in range(len(header))]
    return "\n".join(
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)).rstrip()
        for r in [header] + rows
    )


def describe_event(event, nfa, step):
    """Human-readable explanation of one event (used by the GUI log)."""
    kind = event["type"]
    F = fmt_math(nfa.final)

    if kind == "start":
        s = fmt_math(event["subset"])
        lines = [f"Step {step}: the initial state of M is the set of initial states of N.",
                 f"  s' = S = {s}  ->  State 1 (enqueued)."]
        if event["accepting"]:
            lines.append(f"  State 1 is ACCEPTING because {s} ∩ F = {s} ∩ {F} ≠ ∅.")
        else:
            lines.append(f"  State 1 is not accepting: {s} ∩ {F} = ∅.")
        return "\n".join(lines)

    if kind == "expand":
        return (f"Step {step}: dequeue State {event['id']} = {fmt_math(event['subset'])} "
                f"and compute its transitions.")

    if kind == "transition":
        a = event["symbol"]
        a_set = fmt_math(event["subset"])
        t_set = fmt_math(event["target"])
        lines = [f"Step {step}: evaluating State {event['id']} ({a_set}) with symbol '{a}'."]
        if event["parts"]:
            names = " ∪ ".join(f"Δ({q}, {a})" for q, _ in event["parts"])
            values = " ∪ ".join(fmt_math(p) for _, p in event["parts"])
            lines.append(f"  δ'({a_set}, {a}) = {names}")
            lines.append(f"               = {values} = {t_set}")
        else:
            lines.append(f"  δ'(∅, {a}) = ∅  (empty union: the dead state loops on itself)")

        tid = event["target_id"]
        if event["new"]:
            lines.append(f"  -> New subset: State {tid} is created and enqueued.")
            if event["accepting"]:
                lines.append(f"  -> State {tid} is ACCEPTING because {t_set} ∩ F = {F} ≠ ∅.")
            elif event["target"]:
                lines.append(f"  -> State {tid} is not accepting: {t_set} ∩ {F} = ∅.")
            else:
                lines.append(f"  -> State {tid} is the empty set: a dead (sink) state.")
        else:
            lines.append(f"  -> Subset already known: it is State {tid}.")
        return "\n".join(lines)

    dfa = event["dfa"]
    finals = ", ".join(str(s) for s in sorted(dfa.finals)) or "none"
    return (f"Step {step}: the queue is empty, so the construction is complete.\n"
            f"  M has {dfa.size} reachable states (out of 2^{nfa.n} = {2 ** nfa.n} subsets of Q).\n"
            f"  Initial state: 1.  Accepting states: {finals}.")


# --------------------------------------------------------------------------
# Input sources and CLI
# --------------------------------------------------------------------------

def read_file(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def find_default_input():
    """entrada.txt next to the script, then in the current directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(script_dir, "entrada.txt"), "entrada.txt"):
        if os.path.exists(path):
            return path
    return None


def load_or_report(text):
    """Parse the input; on failure print every error to stderr and return None."""
    try:
        return parse_input(text)
    except InputError as exc:
        print(f"Input error ({len(exc.errors)} problem(s)):", file=sys.stderr)
        for err in exc.errors:
            print(f"  - {err}", file=sys.stderr)
        return None


def run_check(text):
    """--check: validate only, do not run the construction."""
    nfas = load_or_report(text)
    if nfas is None:
        return 1
    print(f"Input OK: {len(nfas)} case(s).")
    for i, nfa in enumerate(nfas, 1):
        print(f"  case {i}: {nfa.n} states, alphabet {{{', '.join(nfa.alphabet)}}}, "
              f"S = {fmt_math(nfa.initial)}, F = {fmt_math(nfa.final)}")
    return 0


def run_cli(text):
    nfas = load_or_report(text)
    if nfas is None:
        return 1

    for i, nfa in enumerate(nfas):
        if i > 0:
            print()  # one blank line between the tables of consecutive cases
        print(format_dfa(subset_construction(nfa)))
    return 0


# --------------------------------------------------------------------------
# GUI (optional extra)
# --------------------------------------------------------------------------

def run_gui(text, source_name):
    import math
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    C = {
        "bg": "#f4f5f7", "panel": "#ffffff", "border": "#d9dce1", "text": "#1f2328",
        "muted": "#6b7280", "accent": "#2563eb", "active": "#f59e0b",
        "active_bg": "#fff4dc", "new": "#16a34a", "new_bg": "#e7f6ec",
        "node": "#eef2ff", "dead": "#e5e7eb", "edge": "#4b5563",
        "log_bg": "#111827", "log_fg": "#e5e7eb", "log_hl": "#fbbf24",
    }
    FONT = ("Segoe UI", 10)
    FONT_B = ("Segoe UI", 10, "bold")
    MONO = ("Consolas", 10)

    class App:
        def __init__(self, root):
            self.root = root
            self.nfas, self.case_index = [], 0
            self.events, self.pos = [], 0
            self.playing, self.after_id = False, None
            self.source_text, self.source_name = text, source_name

            root.title("Subset Construction - NFA to DFA")
            root.configure(bg=C["bg"])
            root.geometry("1280x800")
            root.minsize(980, 640)

            style = ttk.Style(root)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("TButton", font=FONT, padding=(10, 5))
            style.configure("Accent.TButton", font=FONT_B, padding=(10, 5),
                            foreground="white", background=C["accent"])
            style.map("Accent.TButton", background=[("active", "#1d4ed8")])
            style.configure("TLabel", background=C["bg"], font=FONT)
            style.configure("TScale", background=C["bg"])

            self._build_controls()
            self._build_body()
            if not self.load_text(text, source_name):
                # keep the window usable: show the built-in sample instead
                self.load_text(SAMPLE_INPUT, "sample (input had errors)")

        # ---------- layout ----------
        def _build_controls(self):
            bar = tk.Frame(self.root, bg=C["bg"], padx=10, pady=8)
            bar.pack(fill="x")

            ttk.Button(bar, text="Open file…", command=self.open_file).pack(side="left")
            ttk.Button(bar, text="Edit input…", command=self.edit_input).pack(side="left", padx=(6, 0))

            ttk.Label(bar, text="  Case:").pack(side="left")
            self.case_var = tk.StringVar()
            self.case_box = ttk.Combobox(bar, textvariable=self.case_var, width=6, state="readonly")
            self.case_box.pack(side="left", padx=(4, 12))
            self.case_box.bind("<<ComboboxSelected>>", lambda e: self.select_case(self.case_box.current()))

            ttk.Button(bar, text="↺ Load / Reset", command=self.reset).pack(side="left")
            ttk.Button(bar, text="◀ Back", command=self.step_back).pack(side="left", padx=(6, 0))
            ttk.Button(bar, text="Step ▶", style="Accent.TButton",
                       command=self.step_forward).pack(side="left", padx=(6, 0))
            self.play_btn = ttk.Button(bar, text="▶ Play", command=self.toggle_play, width=9)
            self.play_btn.pack(side="left", padx=(6, 0))
            ttk.Button(bar, text="Run to end ⏭", command=self.run_to_end).pack(side="left", padx=(6, 0))

            ttk.Label(bar, text="   Delay:").pack(side="left")
            self.speed = tk.IntVar(value=700)
            ttk.Scale(bar, from_=100, to=2000, variable=self.speed, length=100,
                      command=lambda v: self.speed_lbl.config(text=f"{int(float(v))} ms")
                      ).pack(side="left", padx=4)
            self.speed_lbl = ttk.Label(bar, text="700 ms", width=8)
            self.speed_lbl.pack(side="left")


        def _panel(self, parent, title):
            outer = tk.Frame(parent, bg=C["panel"], highlightbackground=C["border"],
                             highlightthickness=1)
            outer.header = tk.Frame(outer, bg=C["panel"])
            outer.header.pack(fill="x")
            tk.Label(outer.header, text=title, bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 9, "bold"), anchor="w", padx=10, pady=4).pack(side="left")
            return outer

        def _build_body(self):
            body = tk.PanedWindow(self.root, orient="vertical", bg=C["bg"], sashwidth=6, bd=0)
            body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            top = tk.PanedWindow(body, orient="horizontal", bg=C["bg"], sashwidth=6, bd=0)
            body.add(top, stretch="always", minsize=320)

            # left: diagram
            diag = self._panel(top, "DFA DIAGRAM (reachable subsets)")
            self.canvas = tk.Canvas(diag, bg=C["panel"], highlightthickness=0)
            self.canvas.pack(fill="both", expand=True)
            self.canvas.bind("<Configure>", lambda e: self.draw_diagram())
            top.add(diag, stretch="always", minsize=420)

            # right: nfa info, table, queue
            right = tk.Frame(top, bg=C["bg"])
            top.add(right, stretch="always", minsize=360)

            info = self._panel(right, "NFA  N = (Q, Σ, Δ, S, F)")
            info.pack(fill="x")
            self.nfa_text = tk.Label(info, bg=C["panel"], fg=C["text"], font=MONO,
                                     justify="left", anchor="w", padx=10, pady=4)
            self.nfa_text.pack(fill="x")

            # packed first at the bottom so the table never squeezes it
            q = self._panel(right, "BFS QUEUE  (front → back)")
            q.pack(side="bottom", fill="x", pady=(8, 0))
            self.queue_frame = tk.Frame(q, bg=C["panel"], padx=10, pady=8)
            self.queue_frame.pack(fill="x")

            tbl = self._panel(right, "TRANSITION TABLE OF M")
            tbl.pack(fill="both", expand=True, pady=(8, 0))
            holder = tk.Frame(tbl, bg=C["panel"])
            holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.tbl_canvas = tk.Canvas(holder, bg=C["panel"], highlightthickness=0)
            sb = ttk.Scrollbar(holder, orient="vertical", command=self.tbl_canvas.yview)
            self.tbl_canvas.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self.tbl_canvas.pack(side="left", fill="both", expand=True)
            self.table = tk.Frame(self.tbl_canvas, bg=C["panel"])
            self.tbl_canvas.create_window((0, 0), window=self.table, anchor="nw")
            self.table.bind("<Configure>", lambda e: self.tbl_canvas.configure(
                scrollregion=self.tbl_canvas.bbox("all")))

            # bottom: log
            logp = self._panel(body, "STEP-BY-STEP LOG")
            self.status = tk.Label(logp.header, text="", bg=C["panel"], fg=C["muted"],
                                   font=("Segoe UI", 9), padx=10)
            self.status.pack(side="right")
            self.log = tk.Text(logp, bg=C["log_bg"], fg=C["log_fg"], font=MONO, wrap="word",
                               padx=10, pady=8, relief="flat", insertbackground=C["log_fg"])
            self.log.pack(fill="both", expand=True)
            self.log.tag_configure("current", foreground=C["log_hl"])
            self.log.configure(state="disabled")
            body.add(logp, stretch="never", minsize=150, height=210)

        # ---------- input ----------
        def load_text(self, text, name):
            try:
                nfas = parse_input(text)
            except InputError as exc:
                listed = "\n".join(f"\u2022 {e}" for e in exc.errors)
                messagebox.showerror(
                    "Input error",
                    f"{name}: {len(exc.errors)} problem(s) found\n\n{listed}")
                return False
            self.source_text, self.source_name, self.nfas = text, name, nfas
            self.case_box["values"] = [str(i + 1) for i in range(len(nfas))]
            self.select_case(0)
            return True

        def open_file(self):
            path = filedialog.askopenfilename(
                title="Open NFA input", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            if path:
                try:
                    self.load_text(read_file(path), os.path.basename(path))
                except OSError as exc:
                    messagebox.showerror("Error", str(exc))

        def edit_input(self):
            win = tk.Toplevel(self.root)
            win.title("Edit input")
            win.geometry("460x480")
            win.configure(bg=C["bg"])
            box = tk.Text(win, font=MONO, wrap="none", padx=8, pady=8)
            box.pack(fill="both", expand=True, padx=10, pady=(10, 6))
            box.insert("1.0", self.source_text)

            def apply():
                if self.load_text(box.get("1.0", "end"), "edited input"):
                    win.destroy()

            ttk.Button(win, text="Apply", style="Accent.TButton", command=apply).pack(pady=(0, 10))

        def select_case(self, index):
            self.case_index = max(0, index)
            self.case_box.current(self.case_index)
            self.nfa = self.nfas[self.case_index]
            self.events = list(subset_construction_steps(self.nfa))
            self.dfa = self.events[-1]["dfa"]
            self._compute_layout()
            self._show_nfa()
            self._build_table()
            self.reset()

        def _show_nfa(self):
            n = self.nfa
            rows = [f"Q = {{1..{n.n}}}   Σ = {{{', '.join(n.alphabet)}}}   "
                    f"S = {fmt_math(n.initial)}   F = {fmt_math(n.final)}"]
            for q in range(1, n.n + 1):
                cells = "  ".join(f"Δ({q},{a})={fmt_math(n.move(q, a))}" for a in n.alphabet)
                rows.append(cells)
            self.nfa_text.config(text="\n".join(rows))

        # ---------- playback ----------
        def reset(self):
            self.pause()
            if not self.events:
                return
            self.pos = 1  # the 'start' event is always shown
            self.render(full_log=True)

        def step_forward(self):
            if self.pos < len(self.events):
                self.pos += 1
                self.render()
                return True
            self.pause()
            return False

        def step_back(self):
            self.pause()
            if self.events and self.pos > 1:
                self.pos -= 1
                self.render(full_log=True)

        def run_to_end(self):
            self.pause()
            if not self.events:
                return
            self.pos = len(self.events)
            self.render(full_log=True)

        def toggle_play(self):
            if self.playing:
                self.pause()
            else:
                if self.pos >= len(self.events):
                    self.reset()
                self.playing = True
                self.play_btn.config(text="⏸ Pause")
                self._tick()

        def pause(self):
            self.playing = False
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            if hasattr(self, "play_btn"):
                self.play_btn.config(text="▶ Play")

        def _tick(self):
            if self.playing and self.step_forward():
                self.after_id = self.root.after(int(self.speed.get()), self._tick)
            else:
                self.pause()

        # ---------- state derived from events[:pos] ----------
        def _model(self):
            known, cells, queue = set(), {}, []
            active, active_cell, fresh = None, None, None
            for ev in self.events[:self.pos]:
                queue = ev["queue"]
                active_cell, fresh = None, None
                if ev["type"] == "start":
                    known.add(ev["id"])
                    fresh = ev["id"]
                elif ev["type"] == "expand":
                    active = ev["id"]
                elif ev["type"] == "transition":
                    known.add(ev["target_id"])
                    cells[(ev["id"], ev["symbol"])] = ev["target_id"]
                    active_cell = (ev["id"], ev["symbol"])
                    if ev["new"]:
                        fresh = ev["target_id"]
                elif ev["type"] == "done":
                    active = None
            return known, cells, queue, active, active_cell, fresh

        def render(self, full_log=False):
            self.model = self._model()
            self.draw_diagram()
            self._update_table()
            self._update_queue()
            self._update_log(full_log)
            self.status.config(
                text=f"{self.source_name}  •  step {self.pos} / {len(self.events)}")

        # ---------- log ----------
        def _update_log(self, full):
            self.log.configure(state="normal")
            self.log.tag_remove("current", "1.0", "end")
            if full:
                self.log.delete("1.0", "end")
                for i in range(self.pos):
                    self._append_log(i, i == self.pos - 1)
            else:
                self._append_log(self.pos - 1, True)
            self.log.see("end")
            self.log.configure(state="disabled")

        def _append_log(self, i, current):
            msg = describe_event(self.events[i], self.nfa, i + 1) + "\n\n"
            start = self.log.index("end-1c")
            self.log.insert("end", msg)
            if current:
                self.log.tag_add("current", start, "end-1c")

        # ---------- queue ----------
        def _update_queue(self):
            for w in self.queue_frame.winfo_children():
                w.destroy()
            queue = self.model[2]
            if not queue:
                tk.Label(self.queue_frame, text="(empty)", bg=C["panel"], fg=C["muted"],
                         font=FONT).pack(side="left")
                return
            for k, sid in enumerate(queue):
                subset = fmt_math(self.dfa.subsets[sid - 1])
                tk.Label(self.queue_frame, text=f"{sid}  {subset}", font=FONT_B,
                         bg=C["new_bg"] if sid == self.model[5] else C["node"],
                         fg=C["text"], padx=8, pady=3, relief="solid", bd=1
                         ).pack(side="left", padx=(0, 6))

        # ---------- table ----------
        def _build_table(self):
            for w in self.table.winfo_children():
                w.destroy()
            headers = ["", "state", "subset"] + self.dfa.alphabet
            for j, h in enumerate(headers):
                tk.Label(self.table, text=h, font=FONT_B, bg=C["bg"], fg=C["text"],
                         padx=10, pady=4, bd=1, relief="solid").grid(row=0, column=j, sticky="nsew")
            self.cells = {}
            for sid in range(1, self.dfa.size + 1):
                row = []
                for j in range(len(headers)):
                    lbl = tk.Label(self.table, text="", font=MONO, bg=C["panel"], fg=C["text"],
                                   padx=10, pady=3, bd=1, relief="solid", anchor="w")
                    lbl.grid(row=sid, column=j, sticky="nsew")
                    row.append(lbl)
                self.cells[sid] = row

        def _update_table(self):
            known, cells, _, active, active_cell, fresh = self.model
            for sid, row in self.cells.items():
                if sid not in known:
                    for lbl in row:
                        lbl.grid_remove()
                    continue
                mark = ("→" if sid == 1 else "") + ("*" if sid in self.dfa.finals else "")
                values = [mark, str(sid), fmt_set(self.dfa.subsets[sid - 1])]
                values += [str(cells.get((sid, a), "")) for a in self.dfa.alphabet]
                base = C["active_bg"] if sid == active else (C["new_bg"] if sid == fresh else C["panel"])
                for j, lbl in enumerate(row):
                    lbl.grid()
                    bg = base
                    if j >= 3 and active_cell == (sid, self.dfa.alphabet[j - 3]):
                        bg = C["active"]
                    lbl.config(text=values[j], bg=bg,
                               font=FONT_B if (j >= 3 and bg == C["active"]) else MONO)

        # ---------- diagram ----------
        def _compute_layout(self):
            """BFS depth = column, order of discovery within a depth = row."""
            depth = {1: 0}
            for (src, _), dst in sorted(self.dfa.trans.items(), key=lambda kv: kv[0][0]):
                if dst not in depth:
                    depth[dst] = depth[src] + 1
            columns = {}
            for sid in range(1, self.dfa.size + 1):
                columns.setdefault(depth[sid], []).append(sid)
            self.depth = depth
            self.ncols = max(columns) + 1
            self.nrows = max(len(v) for v in columns.values())
            self.grid_pos = {}
            for d, ids in columns.items():
                for r, sid in enumerate(ids):
                    offset = (self.nrows - len(ids)) / 2
                    self.grid_pos[sid] = (d, r + offset)

        def draw_diagram(self):
            cv = self.canvas
            cv.delete("all")
            if not hasattr(self, "model"):
                return
            known, cells, _, active, _, fresh = self.model
            w, h = max(cv.winfo_width(), 200), max(cv.winfo_height(), 200)
            R = max(16, min(30, int(min(w / (self.ncols * 3.2), h / (self.nrows * 3.4)))))
            mx, my = 60 + R, 2 * R + 26
            sx = (w - 2 * mx) / max(self.ncols - 1, 1)
            sy = (h - 2 * my - 14) / max(self.nrows - 1, 1)

            def center(sid):
                c, r = self.grid_pos[sid]
                x = mx + c * sx if self.ncols > 1 else w / 2
                y = my + r * sy if self.nrows > 1 else h / 2
                return x, y

            # group revealed transitions by (src, dst)
            edges = {}
            for (src, a), dst in cells.items():
                edges.setdefault((src, dst), []).append(a)
            order = {a: i for i, a in enumerate(self.dfa.alphabet)}
            all_pairs = {(s, d) for (s, _), d in self.dfa.trans.items()}

            for (src, dst), syms in edges.items():
                label = ",".join(sorted(syms, key=order.get))
                x1, y1 = center(src)
                last_col = self.grid_pos[src][0] == self.ncols - 1
                if src == dst:
                    self._self_loop(x1, y1, R, label, right=last_col and self.ncols > 1)
                    continue
                x2, y2 = center(dst)
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy) or 1
                nx, ny = -dy / dist, dx / dist
                bend = 0
                if (dst, src) in all_pairs or self.depth[dst] <= self.depth[src] \
                        or abs(self.grid_pos[dst][0] - self.grid_pos[src][0]) > 1:
                    bend = 0.18 * dist + 14
                    same_col = self.grid_pos[dst][0] == self.grid_pos[src][0]
                    if same_col and last_col and nx > 0:
                        bend = -bend  # keep the right side free for self-loops
                cx, cy = (x1 + x2) / 2 + nx * bend, (y1 + y2) / 2 + ny * bend
                p1 = self._towards(x1, y1, cx, cy, R)
                p2 = self._towards(x2, y2, cx, cy, R + 2)
                cv.create_line(p1[0], p1[1], cx, cy, p2[0], p2[1], smooth=True,
                               arrow="last", arrowshape=(10, 12, 4), width=1.6, fill=C["edge"])
                lx, ly = 0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2
                self._edge_label(lx, ly, label)

            for sid in sorted(known):
                x, y = center(sid)
                subset = self.dfa.subsets[sid - 1]
                fill = C["dead"] if not subset else C["node"]
                outline, width = C["accent"], 2
                if sid == active:
                    fill, outline, width = C["active_bg"], C["active"], 3
                elif sid == fresh:
                    fill, outline, width = C["new_bg"], C["new"], 3
                cv.create_oval(x - R, y - R, x + R, y + R, fill=fill, outline=outline, width=width)
                if sid in self.dfa.finals:
                    r2 = R - 5
                    cv.create_oval(x - r2, y - r2, x + r2, y + r2, outline=outline, width=1.6)
                cv.create_text(x, y, text=str(sid), font=("Segoe UI", max(9, R // 2), "bold"),
                               fill=C["text"])
                cv.create_text(x, y + R + 10, text=fmt_math(subset), font=("Consolas", 9),
                               fill=C["muted"])
                if sid == 1:
                    cv.create_line(x - R - 38, y, x - R - 2, y, arrow="last", width=2,
                                   arrowshape=(10, 12, 4), fill=C["text"])

            cv.create_text(10, h - 10, anchor="sw", fill=C["muted"], font=("Segoe UI", 9),
                           text="double circle = accepting   •   orange = being expanded"
                                "   •   green = just created   •   grey = ∅ (dead)")

        def _towards(self, x, y, tx, ty, r):
            d = math.hypot(tx - x, ty - y) or 1
            return x + (tx - x) / d * r, y + (ty - y) / d * r

        def _self_loop(self, x, y, R, label, right=False):
            # drawn above the node, or rotated to its right side
            def rot(dx, dy):
                return (x - dy, y + dx) if right else (x + dx, y + dy)
            pts = [rot(-R * 0.55, -R * 0.83), rot(-R * 0.9, -R * 2.1),
                   rot(R * 0.9, -R * 2.1), rot(R * 0.55, -R * 0.83)]
            self.canvas.create_line(*[c for p in pts for c in p], smooth=True, arrow="last",
                                    arrowshape=(9, 11, 4), width=1.6, fill=C["edge"])
            lx, ly = rot(0, -R * 1.95)
            self._edge_label(lx + (8 if right else 0), ly, label)

        def _edge_label(self, x, y, text):
            item = self.canvas.create_text(x, y, text=text, font=("Segoe UI", 9, "bold"),
                                           fill=C["accent"])
            x1, y1, x2, y2 = self.canvas.bbox(item)
            bg = self.canvas.create_rectangle(x1 - 3, y1 - 1, x2 + 3, y2 + 1,
                                              fill=C["panel"], outline="")
            self.canvas.tag_lower(bg, item)

    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    files = [a for a in argv if not a.startswith("--")]

    if "--help" in flags or "-h" in argv:
        print(__doc__.strip())
        return 0

    if files:
        try:
            text, name = read_file(files[0]), os.path.basename(files[0])
        except OSError as exc:
            print(f"Cannot read '{files[0]}': {exc}", file=sys.stderr)
            return 1
    elif "--gui" in flags or ("--cli" not in flags and "--check" not in flags
                              and sys.stdin.isatty()):
        path = find_default_input()
        text, name = (read_file(path), os.path.basename(path)) if path else (SAMPLE_INPUT, "sample")
    else:
        text, name = sys.stdin.read(), "stdin"

    if "--check" in flags:
        return run_check(text)

    # GUI only when asked for, or when launched interactively with no input given.
    want_gui = "--gui" in flags or ("--cli" not in flags and not files and sys.stdin.isatty())
    if want_gui:
        try:
            return run_gui(text, name)
        except Exception as exc:  # no Tkinter or no display: fall back to text output
            print(f"GUI unavailable ({exc}); printing the tables instead.", file=sys.stderr)

    return run_cli(text)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
