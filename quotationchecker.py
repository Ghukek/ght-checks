import string
import sys
import os

def classify_quote(text, i):
    """
    Classify a quote at position i as OPEN, CLOSE, or NONE.
    OPEN = previous char is space only
    CLOSE = next char is whitespace, punctuation, or end of line
    """
    prev_char = text[i-1] if i > 0 else '\n'
    next_char = text[i+1] if i+1 < len(text) else '\n'

    # Opening quote rule: ONLY if previous char is exactly a space
    if prev_char.isspace() or prev_char in ["(","["]:
        if next_char in ["]"]:
            return "CLOSE"
        return "OPEN"

    if prev_char in ["'", '"']:
        prevv_char = text[i-2] if i > 1 else '\n'
        if prevv_char.isspace():
            return "OPEN"
        else:
            return "CLOSE"

    # Closing quote rule: next char is whitespace, punctuation, or end-of-text
    if next_char.isspace() or next_char in string.punctuation:
        return "CLOSE"

    return "NONE"

def is_apostrophe_in_word(text, i):
    """Return True if text[i] is a single quote surrounded by letters."""
    prev_char = text[i-1] if i > 0 else ''
    next_char = text[i+1] if i+1 < len(text) else ''
    return prev_char.isalpha() and next_char.isalpha()

def find_quote_errors(text):
    stack = []        # opening quote positions
    errors = []

    for i, ch in enumerate(text):
        # Skip apostrophes used in contractions or possessives
        if ch == "'" and is_apostrophe_in_word(text, i):
            continue

        # Only process real quotes: double quotes and single quotes NOT inside words
        if ch not in ['"', "'"]:
            continue

        qtype = classify_quote(text, i)

        if qtype == "OPEN":
            #print("open")
            stack.append(i)

        elif qtype == "CLOSE":
            #print("close")
            if stack:
                #input(stack)
                stack.pop()
            else:
                # Closing quote with no opening match
                start = max(0, i-20)
                end = min(len(text), i+20)
                context = text[start:end]
                errors.append(("Unmatched CLOSING quote", i, context))

    # Any leftovers are unmatched opening quotes
    for pos in stack:
        start = max(0, pos-20)
        end = min(len(text), pos+20)
        context = text[start:end]
        errors.append(("Unmatched OPENING quote", pos, context))

    return errors


def run_on_file(path):
    if not os.path.isfile(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    errors = find_quote_errors(text)

    if not errors:
        print("No unmatched quotes found.")
        return

    print(f"Found {len(errors)} quotation issue(s):\n")

    for kind, pos, ctx in errors:
        print(f"{kind}:")
        print(f"...{ctx}...")
        if "OPENING" in kind:
            input()
        print()


if __name__ == "__main__":


    run_on_file("rawtext.txt")

