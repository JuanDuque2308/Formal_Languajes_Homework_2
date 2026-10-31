import os
import re
import sys
from collections import deque


def parse_set(token):
    token = token.strip()
    if token == "0" or token == "{}" or not token:
        return frozenset()
    nums = re.findall(r"\d+", token)
    return frozenset(int(x) for x in nums)


def read_case(lines, pos):
    n = int(lines[pos].strip())
    initial = frozenset(int(x) for x in re.findall(r"\d+", lines[pos + 1]) if x != "0")
    alphabet = lines[pos + 2].split()
    final = frozenset(int(x) for x in re.findall(r"\d+", lines[pos + 3]) if x != "0")

    delta = {}
    for i in range(n):
        line = lines[pos + 4 + i].strip()
        tokens = re.findall(r"\{[^}]*\}|\S+", line)
        state = int(tokens[0])
        for sym, tok in zip(alphabet, tokens[1:]):
            delta[(state, sym)] = parse_set(tok)

    return (n, initial, alphabet, final, delta), pos + 4 + n


def subset_construction(initial, alphabet, final, delta):
    start = frozenset(initial)
    ids = {start: 1}
    order = [start]
    trans = {}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for sym in alphabet:
            target = set()
            for q in current:
                target |= delta.get((q, sym), frozenset())
            target = frozenset(target)

            if target not in ids:
                ids[target] = len(ids) + 1
                order.append(target)
                queue.append(target)
            trans[(current, sym)] = ids[target]

    finals = [s for s in order if (s & final)]
    return start, order, ids, trans, finals


def fmt_set(subset):
    if not subset:
        return "0"
    return "{" + " ".join(str(x) for x in sorted(subset)) + "}"


def print_dfa(alphabet, start, order, ids, trans, finals):
    finals_set = set(finals)
    header = ["mark", "state", "subset"] + alphabet
    rows = []

    for s in order:
        mark = ""
        if s == start:
            mark += "->"
        if s in finals_set:
            mark += "*"

        row = [
                  mark,
                  str(ids[s]),
                  fmt_set(s)
              ] + [str(trans[(s, a)]) for a in alphabet]
        rows.append(row)

    col_widths = [max(len(r[i]) for r in [header] + rows) for i in range(len(header))]

    for r in [header] + rows:
        print("  ".join(r[i].ljust(col_widths[i]) for i in range(len(header))).rstrip())


def get_input_text():
    # 1. Si no es interactivo (ej. tubería o redirección de archivo), leer stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()

    # 2. Si se ejecutó con botón Play, buscar 'entrada.txt' en la misma carpeta del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "entrada.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    # 3. Buscar en el directorio actual
    if os.path.exists("entrada.txt"):
        with open("entrada.txt", "r", encoding="utf-8") as f:
            return f.read()

    return sys.stdin.read()


def main():
    raw_input = get_input_text()
    if not raw_input or not raw_input.strip():
        print("Error: No se encontró contenido para procesar.")
        return

    lines = [ln.strip() for ln in raw_input.splitlines() if ln.strip()]
    c = int(lines[0])
    pos = 1

    for case_idx in range(c):
        (n, initial, alphabet, final, delta), pos = read_case(lines, pos)
        start, order, ids, trans, finals = subset_construction(
            initial, alphabet, final, delta
        )
        print_dfa(alphabet, start, order, ids, trans, finals)
        if case_idx < c - 1:
            print()


if __name__ == "__main__":
    main()