import json
import base64

class Bifunction:
    """A pair of functions (forward, backward) with a
    compose operation that flips for the second argument:
    
    (f1, b1) . (f2, b2) = (f1 . f2, b2 . b1)
    
    Note that the compose() method flips the usual composition order,
    so that `forward` always pushes data from left to right in a
    compose chain, and `backwards` always right to left:
    
    bf1.compose(bf2).forward(x) = bf2.forward(bf1.forward(x))
    bf1.compose(bf2).backward(x) = bf1.backward(bf2.backward(x))
    """
    def __init__(self, forward=None, backward=None):
        if forward:
            self.forward = forward
        if backward:
            self.backward = backward
        assert all(k in dir(self) for k in ['forward', 'backward'])
    
    @classmethod
    def new(cls, forward, backward):
        return Bifunction(forward, backward)
    
    @classmethod
    def simple(cls, forward, backward):
        return cls.new(forward, backward)

    @classmethod
    def identity(cls):
        return cls.simple(lambda x: x, lambda x: x)
    
    @classmethod
    def from_map(cls, d):
        rd = {k: v for v, k in d.items()}
        return cls.simple(lambda x: d[x], lambda x: rd[x])

    def compose(self, other):
        def f(v):
            return other.forward(self.forward(v))
        def b(v):
            return self.backward(other.backward(v))
        return self.new(f, b)

class Isomorphism(Bifunction):
    """A Bifunction with the additional restriction that
    
    forward(backward(x)) == backward(forward(x)) == x
    
    or at least, that these are morally equal.
    """
    @classmethod
    def new(self, forward, backward):
        return Isomorphism(forward, backward)

    def reverse(self):
        return self.new(self.backward, self.forward)
    
    def wrap(self, other):
        return self.compose(other).compose(self.reverse())

class Underscores(Isomorphism):
    def __init__(self, underscore='_'):
        self.underscore = underscore
    def forward(self, l):
        return self.underscore.join(w.lower() for w in l)
    def backward(self, s):
        return [w.lower() for w in s.split(self.underscore)]

class CamelCase(Isomorphism):
    def __init__(self, capitalize_first=False):
        self.capitalize_first = capitalize_first
    def forward(self, l):
        if not l:
            return ""
        first = l[0]
        if self.capitalize_first:
            first = first.title()
        else:
            first = first.lower()
        return first + ''.join(w.title() for w in l[1:])
    def backward(self, s):
        w = ""
        l = []
        for c in s:
            if c.isupper() and w:
                l.append(w.lower())
                w = ""
            w += c
        if w:
            l.append(w.lower())
        return l

class JSON(Isomorphism):
    def forward(self, l):
        return json.dumps(l)
    def backward(self, s):
        return json.loads(s)

class Encode(Isomorphism):
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
    def forward(self, s):
        return s.encode(self.encoding)
    def backward(self, b):
        return b.decode(self.encoding)

class Base64(Isomorphism):
    def __init__(self, altchars=None):
        self.altchars = altchars
    def forward(self, s):
        return base64.b64encode(s, self.altchars)
    def backward(self, s):
        return base64.b64decode(s, self.altchars)
