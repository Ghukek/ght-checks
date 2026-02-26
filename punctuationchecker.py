import re

def load_abbreviations(abbrev_file_path):
    with open(abbrev_file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def find_uncapitalized_after_punctuation(text_file, abbrev_file):
    # Load abbreviations
    abbreviations = load_abbreviations(abbrev_file)
    mask_map = {}

    # Read input text
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Mask abbreviations to avoid false matches
    for i, abbr in enumerate(abbreviations):
        safe_key = f'__MASK{i}__'
        text = text.replace(abbr, safe_key)
        mask_map[safe_key] = abbr

    # Find sentence-ending punctuation followed by non-alpha and then a lowercase letter
    pattern = r'([.!?])([\s\d:\[\]"\'”’“‘\)\]\}]*)([a-z])'
    matches = list(re.finditer(pattern, text))

    for match in matches:
        punct = match.group(1)
        between = match.group(2)
        letter = match.group(3)
        context_start = max(0, match.start() - 30)
        context_end = min(len(text), match.end() + 30)
        context = text[context_start:context_end]

        # Restore any masked abbreviations in context
        for key, abbr in mask_map.items():
            context = context.replace(key, abbr)

        print(f"Issue after '{punct}': ...{context}...")


def load_proper_nouns(proper_nouns_file):
    with open(proper_nouns_file, 'r', encoding='utf-8') as f:
        return set(word.strip() for word in f if word.strip())

def is_after_special_format(text, index):
    """
    Returns True if the capital letter at `index` immediately follows the pattern:

    two newlines + [alphanumeric+space+number] + [optional colon + number]

    Example pattern: \n\n[2Cor 6][:1]
    """
    # Look behind slice length enough for pattern (e.g., 30 chars)
    start = max(0, index - 40)
    snippet = text[start:index]

    # Pattern explanation:
    # \n\n - two newlines
    # \[ - opening bracket
    # [\w\s]+ - alphanumeric + spaces (for * part)
    # \d+ - number (# part)
    # \] - closing bracket
    # \[ - next bracket
    # :?\d+ - optional colon + number
    # \] - closing bracket

    pattern = re.compile(
        r'[.!?]'                    # sentence-ending punctuation
        r'(?:["\'”’])?'             # optional quote character
        r'\s*\n\n'                  # optional space, then two newlines
        r'\[[\w\s]+\d+\]'           # [alphanumeric + spaces + digits]
        r'\[:?\d+\]'                # [:number] or [number]
        r'\s$'                      # space at the end (right before capital)
    )

    return bool(pattern.search(snippet))

def find_unexpected_capitals(file_path, proper_nouns_file):
    proper_nouns = load_proper_nouns(proper_nouns_file)

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    listwords = []

    # Find each capital letter (start of word)
    for match in re.finditer(r'\b([A-Z][a-z]*)', text):
        word = match.group(1)
        index = match.start()

        # Skip if it's a known proper noun
        if word in proper_nouns:
            continue

        # Look back ~10 characters for recent punctuation
        lookback = text[max(0, index - 50):index]

        # Check if capital is immediately following sentence punctuation
        if re.search(r'''
    [.!?]                          # sentence-ending punctuation
    [\s\n\r]*                      # optional whitespace
    (?:["'”’()\[\]{}]*)            # optional mixed brackets/quotes (open & close)
    [\s\n\r]*                      # optional whitespace
    (?:\[\:?[^\]]*\])*             # optional bracketed formatting like [:14] or [It:]
    [\s\n\r]*                     # trailing space before capital
    (?:\[)*$
''', lookback, re.VERBOSE):
            continue  # valid sentence start

        if index > 0 and text[index - 1] in ['"', '“', '\'']:
            continue

        if index > 0 and text[index - 2:index] in ['"[', '\'[']:

            continue

        if is_after_special_format(text, index):
            # Skip this capital since it follows the special format
            continue

        # Otherwise, report it
        context_start = max(0, index - 30)
        context_end = min(len(text), index + len(word) + 30)
        context = text[context_start:context_end]
        print("\nUnexpected capital at center:")
        print(context)

text_file = "rawtext.txt"
abbrev_file = "abbreviations.txt"
proper_nouns_file = "propernouns.txt"
find_uncapitalized_after_punctuation(text_file, abbrev_file)
find_unexpected_capitals(text_file, proper_nouns_file)
