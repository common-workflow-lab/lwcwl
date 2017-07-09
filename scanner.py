class SubstitutionError(Exception):
    pass

def scan(scanstr, i=0):  # type: (Text) -> List[int]
    START = 0
    DOLLAR = 1
    PAREN = 2
    BRACE = 3
    SINGLE_QUOTE = 4
    DOUBLE_QUOTE = 5
    BACKSLASH = 6
    PLAIN = 7
    RUN = 8

    stack = [START]
    start = i
    while i < len(scanstr):
        state = stack[-1]
        c = scanstr[i]

        if state == START:
            if c == '$':
                stack.append(DOLLAR)
            elif c == '\\':
                stack.append(BACKSLASH)
            elif c == "'":
                stack.append(SINGLE_QUOTE)
            elif c == '"':
                stack.append(DOUBLE_QUOTE)
            elif c in (' ', "\n"):
                start += 1
            else:
                stack.append(RUN)
        elif state == RUN:
            if c == "'":
                stack.append(SINGLE_QUOTE)
            elif c == '"':
                stack.append(DOUBLE_QUOTE)
            elif c in (' ', '\\', '$', "\n"):
                stack.pop()
                if stack[-1] == START:
                    return [start, i]
        elif state == BACKSLASH:
            stack.pop()
            if stack[-1] == START:
                return [i - 1, i + 1]
        elif state == DOLLAR:
            if c == '(':
                start = i - 1
                stack.append(PAREN)
            elif c == '{':
                start = i - 1
                stack.append(BRACE)
            else:
                stack.pop()
        elif state == PAREN:
            if c == '(':
                stack.append(PAREN)
            elif c == ')':
                stack.pop()
                if stack[-1] == DOLLAR:
                    return [start, i + 1]
            elif c == "'":
                stack.append(SINGLE_QUOTE)
            elif c == '"':
                stack.append(DOUBLE_QUOTE)
        elif state == BRACE:
            if c == '{':
                stack.append(BRACE)
            elif c == '}':
                stack.pop()
                if stack[-1] == DOLLAR:
                    return [start, i + 1]
            elif c == "'":
                stack.append(SINGLE_QUOTE)
            elif c == '"':
                stack.append(DOUBLE_QUOTE)
        elif state == SINGLE_QUOTE:
            if c == "'":
                stack.pop()
            elif c == '\\':
                stack.append(BACKSLASH)
        elif state == DOUBLE_QUOTE:
            if c == '"':
                stack.pop()
            elif c == '\\':
                stack.append(BACKSLASH)
        i += 1

    if stack[-1] == RUN:
        return [start, i]

    if len(stack) > 1:
        raise SubstitutionError(
            "Substitution error, unfinished block starting at position {}: {}".format(start, scanstr[start:]))
    else:
        return None


def lex(cont, join=True):
    prv = 0
    pieces = []
    n = scan(cont)
    while n:
        if n[0] > prv or not pieces or not join:
            pieces.append(cont[n[0]:n[1]])
        else:
            pieces[-1] = pieces[-1] + cont[n[0]:n[1]]
        prv = n[1]
        n = scan(cont, n[1])
    return pieces
