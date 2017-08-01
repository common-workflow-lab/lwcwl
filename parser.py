class Matcher(object):
    def __rshift__(self, other):
        return Sequence(self, other)

    def __or__(self, other):
        return Alternate(self, other)

    def __pos__(self):
        return Repeat(self)

    def __sub__(self, other):
        return Sub(self, other)

    def match(self, p):
        return None, p

class L(Matcher):
    def __init__(self, s):
        self.s = s

    def match(self, p):
        if p and p[0] == self.s:
            return p[0], p[1:]
        else:
            return None, p

class SW(Matcher):
    def __init__(self, s):
        self.s = s

    def match(self, p):
        if p and p[0].startswith(self.s):
            return p[0], p[1:]
        else:
            return None, p

class _EOL(Matcher):
    def match(self, p):
        if p and p[0] == "\n":
            return "", p[1:]
        else:
            return None, p

class _Any(Matcher):
    def match(self, p):
        return p[0], p[1:]

EOL = _EOL()
Any = _Any()

class Repeat(Matcher):
    def __init__(self, s):
        self.s = s

    def match(self, p):
        l, c = self.s.match(p)
        if l is None:
            return None, p
        r = None
        if c:
            r, c = self.match(c)
        return (l, r), c

class Combinator(Matcher):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

class Sequence(Combinator):
    def match(self, p):
        l, c = self.lhs.match(p)
        if l is not None:
            r, c = self.rhs.match(c)
            if r is not None:
                return (l, r), c
        return None, p

class Alternate(Combinator):
    def match(self, p):
        l, c = self.lhs.match(p)
        if l is not None:
            return l, c
        r, c = self.rhs.match(p)
        if r is not None:
            return r, c
        return None, p

class Sub(Combinator):
    def match(self, p):
        l, c = self.lhs.match(p)
        if l is not None:
            r, _ = self.rhs.match(p)
            if r is None:
                return l, c
        return None, p

class Gen(Matcher):
    def __init__(self, m, fn):
        self.m = m
        self.fn = fn

    def match(self, p):
        r, c = self.m.match(p)
        if r is not None:
            return self.fn(r), c
        return None, p

def test():
    s = (L("a") >> L("b")) | (L("a") >> L("c")) | (L("a") >> L("d") >> L("e"))

    print s.match(["a", "b"]) == (('a', 'b'), [])
    print s.match(["a", "c"]) == (('a', 'c'), [])
    print s.match(["a", "d"]) == (None, ['a', 'd'])
    print s.match(["a", "d", "e"]) == ((('a', 'd'), 'e'), [])

    s = L("a") >> (Any() - L("b"))

    print s.match(["a", "b"]) == (None, ['a', 'b'])
    print s.match(["a", "c"]) == (('a', 'c'), [])

    s = L("a") >> L("a") >> L("b")

    print s.match(["a", "b"]) == (None, ['a', 'b'])
    print s.match(["a", "a", "b"]) == ((('a', 'a'), 'b'), [])
    print s.match(["a", "a", "a", "b"]) == (None, ['a', 'a', 'a', 'b'])

    s = +L("a") >> L("b")

    print s.match(["a", "b"]) == ((('a', None), 'b'), [])
    print s.match(["a", "a", "b"]) == ((('a', ('a', None)), 'b'), [])
    print s.match(["a", "a", "a", "b"]) == ((('a', ('a', ('a', None))), 'b'), [])
    print s.match(["a", "a", "a", "c"]) == (None, ['a', 'a', 'a', 'c'])

    s = Gen(L("a") >> L("b"), lambda x: [x[1], x[0]])
    print s.match(["a", "b"]) == (['b', 'a'], [])

if __name__ == "__main__":
    test()
