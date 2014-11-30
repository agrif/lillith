import weakref
from .cached_property import cached_property

__all__ = []

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

class Underscores(Isomorphism):
    def forward(self, l):
        return '_'.join(w.lower() for w in l)
    def backward(self, s):
        return [w.lower() for w in s.split('_')]

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

class Backend:
    python_convention = Underscores()
    name_convention = Underscores()

    def verify(self, name, attrs):
        pass

    def get_id_key(self, model):
        return None

    def fetch_single(self, model, i):
        raise NotImplementedError("Backend.fetch_single")

    def fetch(self, model, constraints):
        raise NotImplementedError("Backend.fetch")

constraint_types = {}
class ConstraintMeta(type):
    def __new__(cls, name, bases, attrs):
        nameiso = CamelCase(capitalize_first=True).reverse().compose(Underscores())
        attrs['name'] = nameiso.forward(name)
        ty = super().__new__(cls, name, bases, attrs)
        if ty.name != "constraint":
            constraint_types[ty.name] = ty
            for n in ty.alternates:
                constraint_types[n] = ty
            __all__.append(name)
        return ty

class Constraint(metaclass=ConstraintMeta):
    compound = False
    alternates = []
    def __init__(self, v):
        self.value = v
        if self.compound:
            self.value = []
            for i in v:
                if isinstance(i, Constraint):
                    self.value.append(i)
                else:
                    self.value.append(Equal(i))
    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, self.value)
    def map(self, f):
        if self.compound:
            return type(self)([v.map(f) for v in self.value])
        return type(self)(f(self.value))

class And(Constraint):
    compound = True
    alternates = ['all']
class Or(Constraint):
    compound = True
    alternates = ['any']
class Equal(Constraint):
    alternates = ['eq']
class Like(Constraint):
    pass
class Less(Constraint):
    alternates = ['lt']
class LessEqual(Constraint):
    alternates = ['le', 'lte']
class Greater(Constraint):
    alternates = ['gt']
class GreaterEqual(Constraint):
    alternates = ['ge', 'gte']

class ConstraintVisitor:
    def visit(self, c):
        f = getattr(self, 'visit_' + c.name, None)
        if f:
            return f(c.value)
        name = 'visit_compound' if c.compound else 'visit_simple'
        f = getattr(self, name, None)
        if f:
            return f(type(c), c.value)
        raise RuntimeError('constraint ' + c.name + ' not supported')

class Converter(Bifunction):
    """A bifunction where forward() modifies a condition tree to be used
    by a model backend, and backward() converts the data provided by
    the backend into something nicer in python.
    
    simple() is overridden to easily create converters that operate on
    all leaf nodes in the condition tree the same way.

    """
    @classmethod
    def new(cls, forward, backward):
        return Converter(forward, backward)

    @classmethod
    def simple(cls, forward, backward):
        def f(c):
            return c.map(forward)
        return cls.new(f, backward)

class ForeignKey(Converter, ConstraintVisitor):
    def __init__(self, model):
        self.model = model
    def forward(self, v):
        return self.visit(v)
    def backward(self, i):
        return self.model.new_from_id(i)
    def visit_compound(self, c, v):
        return c([self.visit(i) for i in v])
    def visit_simple(self, c, v):
        if isinstance(v, self.model):
            return c(v.id)
        ids = []
        nominals = []
        for k, f in self.model._fields.items():
            if not f.nominal:
                continue
            nominals.append(k)
            for i in self.model.filter(**{k: c(v)}):
                ids.append(i.id)
        if not nominals:
            raise ValueError("must provide " + repr(self.model) + " or one of fields " + repr(nominals))
        return Or(ids)
        
class Field:
    def __init__(self, name=None, convert=None, foreign_key=None, optional=False, default=None, nominal=False, extra={}):
        self.name = name
        
        self.cached = True
        if convert is None and foreign_key is None:
            self.cached = False
        
        self.extra = extra
        self.optional = optional
        self.default = default
        self.nominal = nominal
        if convert is None:
            convert = Converter.identity()
        else:
            if not isinstance(convert, Converter):
                raise ValueError("convert must be a Converter")
        self.foreign_key = None
        if foreign_key:
            self.foreign_key = foreign_key
            convert = convert.compose(ForeignKey(foreign_key))
        self.convert = convert
    def __repr__(self):
        return "<Field: {0}>".format(repr(self.name))
    def make_property(self):
        dec = property
        if self.cached:
            dec = cached_property
        @dec
        def prop(inner_self):
            if self.name in inner_self._data:
                return self.convert.backward(inner_self._data[self.name])
            return self.default
        return prop

class ModelMeta(type):
    def __new__(cls, name, bases, attrs, backend=None):
        fields = {}
        if backend is None:
            for o in bases:
                nb = getattr(o, '_backend', None)
                fields = getattr(o, '_fields', {}).copy()
                if backend and nb:
                    raise ValueError("cannot inherit from two models")
                if nb:
                    backend = nb
        if backend is None:
            raise ValueError("no backend found for " + name)
        
        attrs['_backend'] = backend
        nameiso = backend.python_convention.reverse().compose(backend.name_convention)
        for k, v in attrs.items():
            if not isinstance(v, Field):
                continue
            fields[k] = v
            if v.name is None:
                v.name = nameiso.forward(k)
        rfields = {}
        for k, v in fields.items():
            if k == 'self':
                continue
            attrs[k] = v.make_property()
            rfields[v.name] = v
        attrs['_fields'] = fields
        attrs['_cache'] = weakref.WeakValueDictionary()

        if fields:
            backend.verify(name, attrs)
        model = super().__new__(cls, name, bases, attrs)
        idk = backend.get_id_key(model)
        if idk:
            model._fields['self'] = Field(idk, foreign_key=model)
        return model

    def __init__(self, name, bases, attrs, **kwargs):
        return super().__init__(name, bases, attrs)

def parse_constraints(model, raw):
    cs = {}
    for k, v in raw.items():
        ctype = None
        if '__' in k:
            k, ctype = k.split('__', 1)
        
        if not k in model._fields:
            raise ValueError('invalid field: ' + k)
        if ctype:
            if not ctype in constraint_types:
                raise ValueError('invalid constraint type: ' + ctype)
            cclass = constraint_types[ctype]
            v = cclass(v)
        else:
            if not isinstance(v, Constraint):
                v = Equal(v)

        f = model._fields[k]
        v = f.convert.forward(v)
        cs.setdefault(f, []).append(v)
    final = {}
    for k, v in cs.items():
        if len(v) == 0:
            continue
        elif len(v) == 1:
            final[k] = v[0]
        else:
            final[k] = And(v)
    return final

class Model(metaclass=ModelMeta, backend=Backend()):
    def __new__(cls, **kwargs):
        obj, = cls.filter(**kwargs)
        return obj

    @property
    def id(self):
        k = self._backend.get_id_key(self.__class__)
        if k is None:
            raise NotImplementedError("backend does not support ids")
        return self._data[k]

    @classmethod
    def all(cls):
        return cls.filter()
    
    @classmethod
    def filter(cls, **kwargs):
        constraints = parse_constraints(cls, kwargs)
        k = cls._backend.get_id_key(cls)
        for d in cls._backend.fetch(cls, constraints):
            i = None
            if k:
                i = d[k]
            yield cls.new_from_id(i, data=d)

    @classmethod
    def new_from_id(cls, i, data=None):
        if i is not None and cls._backend.get_id_key(cls) is None:
            raise NotImplementedError("backend does not support ids")
        if i is None and data is None:
            raise ValueError("must provide one of id or data")
        
        if i is not None:
            try:
                return cls._cache[i]
            except KeyError:
                pass

        if not data:
            data = cls._backend.fetch_single(cls, i)

        for k, v in cls._fields.items():
            if not v.optional and not v.name in data:
                raise RuntimeError("backend did not provide " + v.name)
        o = super().__new__(cls)
        o._data = data
        if i is not None:
            cls._cache[i] = o
        return o
