import sys
import os


QUOTE_CHARS = {'"', "'"}


def is_apostrophe_in_word(text, i):
    """
    A single quote surrounded by letters is an apostrophe, not a quotation mark.

    Examples:
        don't  -> ignored
        can't  -> ignored
        Jesus' -> NOT ignored; treated as a possible closing quote
    """
    if text[i] != "'":
        return False

    prev_char = text[i - 1] if i > 0 else ""
    next_char = text[i + 1] if i + 1 < len(text) else ""

    return prev_char.isalpha() and next_char.isalpha()


def get_significant_before(text, i):
    """
    Return the character immediately before i, ignoring the bracket wrapper
    in the special ["] case.

    For:
        foo["]
    the quote is treated as if it followed 'o'.

    For:
        ["]word
    the quote is treated as if it were immediately before 'w'.
    """
    if i >= 2 and text[i - 1] == "[" and text[i + 1:i + 2] == "]":
        return text[i - 2]

    return text[i - 1] if i > 0 else ""


def get_significant_after(text, i):
    """
    Return the character immediately after i, ignoring the bracket wrapper
    in the special ["] case.
    """
    if i >= 1 and i + 2 < len(text):
        if text[i - 1] == "[" and text[i + 1] == "]":
            return text[i + 2]

    return text[i + 1] if i + 1 < len(text) else ""


def classify_quote(text, i):
    """
    Classify a quotation mark as OPEN or CLOSE.

    Rules:

    - Quotes after whitespace are OPEN.
    - Quotes after '(' or '[' are OPEN.
    - Quotes before ')' or ']' are CLOSE.
    - Quotes before punctuation are CLOSE.
    - Quotes before whitespace/end are CLOSE.
    - Quotes between [ and ] are treated as though the brackets aren't there.
    - Adjacent quotes of different types are handled according to context.
    - Adjacent same-type quotes are marked as ADJACENT.
    """
    ch = text[i]

    if ch not in QUOTE_CHARS:
        return "NONE"

    if ch == "'" and is_apostrophe_in_word(text, i):
        return "NONE"

    # Special handling for ["] / [']
    bracketed = (
        i >= 1
        and i + 1 < len(text)
        and text[i - 1] == "["
        and text[i + 1] == "]"
    )

    if bracketed:
        prev_char = text[i - 2] if i >= 2 else ""
        next_char = text[i + 2] if i + 2 < len(text) else ""
    else:
        prev_char = text[i - 1] if i > 0 else ""
        next_char = text[i + 1] if i + 1 < len(text) else ""

    # Adjacent quotation marks require special treatment.
    if prev_char in QUOTE_CHARS or next_char in QUOTE_CHARS:
        return "ADJACENT"

    # Opening context.
    if prev_char.isspace() or prev_char in "([":
        return "OPEN"

    # Closing context.
    if (
        not next_char
        or next_char.isspace()
        or next_char in ")]"
        or not next_char.isalnum()
    ):
        return "CLOSE"

    # Otherwise this is not clearly an opening or closing quote.
    return "NONE"


def add_error(errors, kind, text, pos, extra=""):
    """
    Add an error with surrounding context.
    """
    start = max(0, pos - 30)
    end = min(len(text), pos + 31)
    context = text[start:end]

    errors.append({
        "kind": kind,
        "position": pos,
        "context": context,
        "extra": extra,
    })


def find_quote_errors(text):
    """
    Check quotation consistency.

    The stack contains tuples of:

        (quote_character, position)

    Double quotes are the outer quotation level.
    Single quotes are the nested quotation level.

    Thus:

        "foo 'bar'"

    is valid, while:

        'foo "bar"'

    is invalid.

    Alternating nesting is permitted:

        "foo 'bar "baz"'"

    """
    stack = []
    errors = []

    for i, ch in enumerate(text):

        if ch not in QUOTE_CHARS:
            continue

        # Ignore apostrophes occurring inside words.
        if ch == "'" and is_apostrophe_in_word(text, i):
            continue

        qtype = classify_quote(text, i)

        if qtype == "NONE":
            continue

        if qtype == "ADJACENT":
            prev_char = text[i - 1] if i > 0 else ""
            next_char = text[i + 1] if i + 1 < len(text) else ""

            # Same-type adjacent quotes are always malformed.
            if prev_char == ch or next_char == ch:
                add_error(
                    errors,
                    "Adjacent same-type quotation marks",
                    text,
                    i,
                )
                continue

            # Different-type adjacent quotes:
            #
            # They should both behave the same way—either both open
            # or both close. Determine their behavior from context.
            if prev_char in QUOTE_CHARS:
                surrounding_before = (
                    text[i - 2] if i > 1 else ""
                )

                if (
                    surrounding_before.isspace()
                    or surrounding_before in "(["
                ):
                    qtype = "OPEN"
                else:
                    qtype = "CLOSE"

            elif next_char in QUOTE_CHARS:
                surrounding_after = (
                    text[i + 2] if i + 2 < len(text) else ""
                )

                if (
                    surrounding_after.isspace()
                    or not surrounding_after
                    or surrounding_after in ")]"
                    or not surrounding_after.isalnum()
                ):
                    qtype = "CLOSE"
                else:
                    qtype = "OPEN"

        if qtype == "OPEN":

            # The outermost quotation must always be double.
            if not stack and ch != '"':
                add_error(
                    errors,
                    "Invalid outermost single quotation",
                    text,
                    i,
                    "The outermost quotation must use double quotes.",
                )
                continue

            # Nested quotations must alternate between double and single.
            if stack and stack[-1][0] == ch:
                add_error(
                    errors,
                    "Invalid nested quotation",
                    text,
                    i,
                    f"A {ch} quotation cannot open inside another {ch} quotation.",
                )
                continue

            stack.append((ch, i))

        elif qtype == "CLOSE":

            if not stack:
                add_error(
                    errors,
                    "Unmatched CLOSING quote",
                    text,
                    i,
                )
                continue

            expected_quote, opening_pos = stack[-1]

            if expected_quote != ch:
                add_error(
                    errors,
                    "Mismatched CLOSING quote",
                    text,
                    i,
                    (
                        f"Currently open quotation is {expected_quote!r} "
                        f"from position {opening_pos}, but found {ch!r}."
                    ),
                )
                continue

            stack.pop()

    # Anything remaining on the stack is an unmatched opening quote.
    for quote_char, pos in stack:
        add_error(
            errors,
            "Unmatched OPENING quote",
            text,
            pos,
        )

    return errors


def position_to_line_column(text, position):
    """
    Convert a character position to 1-based line and column.
    """
    line = text.count("\n", 0, position) + 1

    last_newline = text.rfind("\n", 0, position)

    if last_newline == -1:
        column = position + 1
    else:
        column = position - last_newline

    return line, column


def run_on_file(path):
    if not os.path.isfile(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    errors = find_quote_errors(text)

    if not errors:
        print("No quotation issues found.")
        return

    print(f"Found {len(errors)} quotation issue(s):\n")

    for number, error in enumerate(errors, 1):
        position = error["position"]
        line, column = position_to_line_column(text, position)

        print(f"{number}. {error['kind']}")
        print(f"   Position: {position}")
        print(f"   Line: {line}, Column: {column}")

        if error["extra"]:
            print(f"   {error['extra']}")

        print(f"   ...{error['context']}...")
        print()


def run_tests():
    """
    Basic sanity tests for the quotation rules.
    """

    tests = [
        ('"word"', False),
        ("'word'", False),
        ('"word \'word\'"', False),

        # Single quote cannot be outer level.
        ("'word \"word\"'", True),

        ("don't", False),

        # Terminal apostrophe is deliberately treated as a quote.
        ("Jesus'", True),

        ('"word"', False),

        # Double quotation containing single quotation containing double.
        ('"word \'word "word"\'"', False),

        # Same-type adjacent quotes.
        ('""', True),
        ("''", True),

        # Different-type adjacent quotes.
        ('"\'' , True),
        ('\'"', True),

        # Unmatched closing.
        ('word"', True),

        # Unmatched opening.
        ('"word', True),

        # Bracketed quote behaves contextually.
        ('["]word"', False),

        # This is an unresolved alternative and should produce an
        # unmatched closing quote.
        ('"word["] text["]', True),
    ]

    print("Running tests...\n")

    passed = 0

    for text, should_error in tests:
        errors = find_quote_errors(text)
        got_error = bool(errors)

        if got_error == should_error:
            result = "PASS"
            passed += 1
        else:
            result = "FAIL"

        print(f"{result}: {text!r}")

        if got_error and result == "FAIL":
            for error in errors:
                print(f"    {error['kind']} at {error['position']}")

    print(f"\n{passed}/{len(tests)} tests passed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    else:
        run_on_file("rawtext.txt")
