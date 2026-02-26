GENDER_EXPAND = {
    "M": set("MHW~"),
    "F": set("FH~"),
    "N": set("NW~"),
    "H": set("MFHW~"),
    "W": set("NMWH~"),
    "~": set("NMFWH~"),
}

NUMBER_EXPAND = {
    "S": set("ST"),
    "P": set("PT"),
    "T": set("SPT")
}

import re

CASE_RE = re.compile(r"^[A-Za-z]+-[DG][MFNHW~][SPT]$")
CASE_RE_3 = re.compile(r"^V-.*-([DG])([MFNHW~])([SPT])$")

def eligible(pcode):
    if pcode is None:
        return False
    if "-" not in pcode:
        return False
    if CASE_RE.match(pcode):
        return True
    if CASE_RE_3.match(pcode):
        return True
    return False


def extract_gn(pcode):
    """
    Returns (gender, number) or (None, None) if wild or '~'.
    """
    if pcode is None or "-" not in pcode:
        return None, None

    m = CASE_RE.match(pcode)
    if m:
        g, n = pcode[-2], pcode[-1]
    else:
        m = CASE_RE_3.match(pcode)
        if m:
            g, n = m.group(2), m.group(3)
        else:
            return None, None

    return g, n

def gn_matches(pcode, g_ref, n_ref):
    g, n = extract_gn(pcode)

    # Wild words never block
    if g is None and n is None:
        return True

    if g_ref is None and n_ref is None:
        return True

    if g_ref is not None:
        if g not in GENDER_EXPAND[g_ref]:
            return False

    if n_ref is not None:
        if n not in NUMBER_EXPAND[n_ref]:
            return False

    return True

def find_sequences(rows):
    """
    rows: list of dicts with keys:
      uid (float), pcode (str), raw (str)
    returns: list of (start_idx, end_idx)
    """
    matches = []
    i = 0
    N = len(rows)

    while i < N:
        w = rows[i]
        if not eligible(w["pcode"]):
            i += 1
            continue

        g1, n1 = extract_gn(w["pcode"])
        start = i
        j = i

        # --- A+ ---
        while j < N and eligible(rows[j]["pcode"]) and gn_matches(rows[j]["pcode"], g1, n1):
            j += 1

        if j == i or j >= N:
            i += 1
            continue

        # --- B+ ---
        g2, n2 = extract_gn(rows[j]["pcode"])
        if g2 is None and n2 is None:
            i += 1
            continue

        if gn_matches(rows[j]["pcode"], g1, n1):
            i += 1
            continue

        k = j
        while k < N and eligible(rows[k]["pcode"]) and gn_matches(rows[k]["pcode"], g2, n2):
            k += 1

        if k == j or k >= N:
            i += 1
            continue

        # --- A+ again ---
        m = k
        while m < N and eligible(rows[m]["pcode"]) and gn_matches(rows[m]["pcode"], g1, n1):
            m += 1

        if m > k:
            matches.append((start, m))
            i = m   # non-overlapping; change to i += 1 if desired
        else:
            i += 1

    return matches

def print_matches(rows, matches, pre="⟦", post="⟧"):
    for start, end in matches:
        verse_ids = {int(rows[i]["uid"]) for i in range(start, end)}

        verse_words = [
            (i, rows[i])
            for i in range(len(rows))
            if int(rows[i]["uid"]) in verse_ids
        ]

        verse_words.sort(key=lambda x: x[1]["uid"])

        out = []
        for idx, w in verse_words:
            token = w["raw"]
            if idx == start:
                token = pre + token
            if idx == end - 1:
                token = token + post
            out.append(token)

        print(" ".join(out))
        print()

def load_pcodes(conn):
    cur = conn.cursor()
    cur.execute("SELECT ident, pcode FROM word_map")
    return {ident: pcode for ident, pcode in cur.fetchall()}

def load_rows(conn):
    pcode_by_ident = load_pcodes(conn)

    cur = conn.cursor()
    cur.execute("""
        SELECT uid, ident, raw
        FROM entries
        WHERE uid IS NOT NULL
        ORDER BY uid
    """)

    rows = []
    for uid, ident, raw in cur.fetchall():
        rows.append({
            "uid": uid,
            "ident": ident,
            "raw": raw,
            "pcode": pcode_by_ident.get(ident)  # may be None
        })

    return rows

from typing import List, Dict, Tuple

def validate_brackets(rows: List[Dict]):
    """
    rows: list of dicts with keys: uid, raw, pcode
    Returns a list of violations or suggested nestings
    """
    bracket_stack = []  # Each element: dict(type, start_idx, g, n, words)
    violations = []

    for i, w in enumerate(rows):
        text = w["raw"]
        g, n = extract_gn(w["pcode"])

        # Detect opening bracket
        if "to{" in text or "of{" in text or "To{" in text or "Of{" in text:
            if "}" in text:
                continue
            bracket_type = "to" if text.startswith("to{") else "of"
            bracket_stack.append({
                "type": bracket_type,
                "start": i,
                "g": g,
                "n": n,
                "words": [w]
            })
            continue

        # Detect closing bracket
        if "}" in text:
            if not bracket_stack:
                # stray closing bracket, can log as warning
                violations.append(("stray_close", i, text))
                continue

            bracket = bracket_stack.pop()
            bracket["words"].append(w)

            # Validate words inside bracket
            for bw in bracket["words"]:
                if not gn_matches(bw["pcode"], bracket["g"], bracket["n"]):
                    violations.append(("mismatch", bracket["start"], i, bracket["type"]))
            
            # Check if nested brackets exist improperly
            if bracket_stack:
                # Current bracket was nested; validate if nesting is allowed
                parent = bracket_stack[-1]
                if bracket["g"] is not None and bracket["n"] is not None:
                    # If inner bracket has different g/n from parent → flag
                    if not gn_matches(bracket["g"] + bracket["n"], parent["g"], parent["n"]):
                        violations.append(("invalid_nesting", parent["start"], i, parent["type"], bracket["type"]))
            if "}}" in text:
                if not bracket_stack:
                    # stray closing bracket, can log as warning
                    violations.append(("stray_close", i, text))
                    continue

                bracket = bracket_stack.pop()
                bracket["words"].append(w)

                # Validate words inside bracket
                for bw in bracket["words"]:
                    if not gn_matches(bw["pcode"], bracket["g"], bracket["n"]):
                        violations.append(("mismatch", bracket["start"], i, bracket["type"]))
                
                # Check if nested brackets exist improperly
                if bracket_stack:
                    # Current bracket was nested; validate if nesting is allowed
                    parent = bracket_stack[-1]
                    if bracket["g"] is not None and bracket["n"] is not None:
                        # If inner bracket has different g/n from parent → flag
                        if not gn_matches(bracket["g"] + bracket["n"], parent["g"], parent["n"]):
                            violations.append(("invalid_nesting", parent["start"], i, parent["type"], bracket["type"]))

            continue

        # Normal word inside a bracket
        if bracket_stack:
            bracket_stack[-1]["words"].append(w)

    # Check if any unclosed brackets remain
    for unclosed in bracket_stack:
        violations.append(("unclosed", unclosed["start"], unclosed["type"]))

    return violations


def report_violations(rows: List[Dict], violations: List[Tuple]):
    """
    Print violations with context
    """
    for v in violations:
        if v[0] == "mismatch":
            start, end, btype = v[1], v[2], v[3]
            words = " ".join(rows[i]["raw"] for i in range(start, end + 1))
            print(f"Gender/number mismatch in {btype} bracket [{start}-{end}]: {words}")
        elif v[0] == "invalid_nesting":
            pstart, end, ptype, ctype = v[1], v[2], v[3], v[4]
            words = " ".join(rows[i]["raw"] for i in range(pstart, end + 1))
            print(f"Invalid nested {ctype} inside {ptype} bracket [{pstart}-{end}]: {words}")
        elif v[0] == "stray_close":
            idx, text = v[1], v[2]
            print(f"Stray closing bracket at {idx}: {text}")
        elif v[0] == "unclosed":
            start, btype = v[1], v[2]
            print(f"Unclosed {btype} bracket starting at {start}: {rows[start]['raw']}")


import string

def is_only_punct_or_space(s):
    return all(c.isspace() or c in string.punctuation for c in s)

def extract_cgn(pcode):
    """
    Returns (case, gender, number) or (None, None, None)
    """

    if pcode is None or "-" not in pcode:
        return None, None, None

    m = CASE_RE.match(pcode)
    if m:
        return pcode[-3], pcode[-2], pcode[-1]

    m = CASE_RE_3.match(pcode)
    if m:
        return m.group(1), m.group(2), m.group(3)

    return None, None, None


def detect_redundant_splits(rows, context=8):
    stack = []
    last_closed = None
    violations = []

    for i, w in enumerate(rows):
        text = w["raw"]
        t = text.lower()
        c, g, n = extract_cgn(w["pcode"])

        # Break adjacency ONLY if outside brackets
        if not stack and last_closed:
            if breaks_adjacency(w, t):
                last_closed = None

        # OPEN
        if "of{" in t or "to{" in t:
            if "}" in t:
                continue

            if last_closed:
                lc = last_closed
                if (
                    lc["case"] == c and
                    g in GENDER_EXPAND.get(lc["g"], {g}) and
                    n in NUMBER_EXPAND.get(lc["n"], {n})
                ):
                    start = max(0, lc["index"] - context)
                    end = min(len(rows), i + context + 1)
                    snippet = " ".join(r["raw"] for r in rows[start:end])

                    violations.append((
                        "redundant_split",
                        lc["index"],
                        i,
                        (c, g, n),
                        snippet
                    ))

            stack.append({
                "start": i,
                "case": c,
                "g": g,
                "n": n
            })
            continue

        # CLOSE
        if "}" in text:
            if not stack:
                continue

            closed = stack.pop()
            last_closed = {
                "case": closed["case"],
                "g": closed["g"],
                "n": closed["n"],
                "index": i
            }
            if "}}" in text:
                if not stack:
                    continue

                closed = stack.pop()
                last_closed = {
                    "case": closed["case"],
                    "g": closed["g"],
                    "n": closed["n"],
                    "index": i
                }
            continue

    return violations


def breaks_adjacency(w, t):
    if is_only_punct_or_space(w["raw"]):
        return False
    if "of{" in t or "to{" in t or "}" in t:
        return False
    if w["pcode"] and "-" in w["pcode"]:
        c, _, _ = extract_cgn(w["pcode"])
        return c not in {"D", "G"}
    return False

def detect_missing_nests(rows, context=8):
    stack = []
    closed_history = []
    violations = []

    for i, w in enumerate(rows):
        text = w["raw"]
        t = text.lower()
        c, g, n = extract_cgn(w["pcode"])

        # Break adjacency only if OUTSIDE all brackets
        if not stack and closed_history:
            if breaks_adjacency(w, t):
                closed_history.clear()

        # OPEN
        if "of{" in t or "to{" in t:
            if "}" in t:
                continue

            # scan back through all recent closes
            for prev in reversed(closed_history):
                if prev["case"] != c:
                    break

                if (
                    g in GENDER_EXPAND.get(prev["g"], {g}) and
                    n in NUMBER_EXPAND.get(prev["n"], {n})
                ):
                    start = max(0, prev["index"] - context)
                    end = min(len(rows), i + context + 1)
                    snippet = " ".join(r["raw"] for r in rows[start:end])

                    violations.append((
                        "missing_nest",
                        prev["index"],
                        i,
                        (c, g, n),
                        snippet
                    ))
                    break  # only report nearest

            stack.append({"case": c, "g": g, "n": n, "start": i})
            continue

        # CLOSE
        if "}" in text:
            if not stack:
                continue

            closed = stack.pop()
            closed_history.append({
                "case": closed["case"],
                "g": closed["g"],
                "n": closed["n"],
                "index": i
            })
            if "}}" in text:
                if not stack:
                    continue

                closed = stack.pop()
                closed_history.append({
                    "case": closed["case"],
                    "g": closed["g"],
                    "n": closed["n"],
                    "index": i
                })

    return violations

def merge_violations(*violation_lists):
    merged = {}

    for violations in violation_lists:
        for kind, close_i, open_i, gn, snippet in violations:
            key = (close_i, open_i)

            if key not in merged:
                merged[key] = {
                    "kinds": {kind},
                    "close_i": close_i,
                    "open_i": open_i,
                    "gn": gn,
                    "snippet": snippet
                }
            else:
                merged[key]["kinds"].add(kind)

    # flatten to list
    results = []
    for v in merged.values():
        results.append((
            "+".join(sorted(v["kinds"])),   # e.g. "redundant_split+missing_nest"
            v["close_i"],
            v["open_i"],
            v["gn"],
            v["snippet"]
        ))

    # sort by close index for nice output
    results.sort(key=lambda x: (x[1], x[2]))

    return results

# Example usage
import sqlite3

conn = sqlite3.connect("concordance.db")
rows = load_rows(conn)  # Use your existing load_rows function
conn.close()

violations = validate_brackets(rows)
report_violations(rows, violations)

violations = merge_violations(
    detect_redundant_splits(rows),
    detect_missing_nests(rows)
)

for kind, close_i, open_i, gn, snippet in violations:
    print(f"{kind}  close@{close_i} → open@{open_i}  GN={gn}")
    print(snippet)
    print()
