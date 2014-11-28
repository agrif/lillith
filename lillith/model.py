import weakref

__all__ = []

# in the loosest sense...
class Isomorphism:
    @classmethod
    def simple(cls, forward, backward):
        iso = cls()
        iso.forward = forward
        iso.backward = backward
        return iso

    @classmethod
    def identity(cls):
        return cls.simple(lambda x: x, lambda x: x)
    
    def reverse(self):
        return Isomorphism.simple(self.backward, self.forward)

    def compose(self, other):
        def f(v):
            return other.forward(self.forward(v))
        def b(v):
            return self.backward(other.backward(v))
        return Isomorphism.simple(f, b)
    
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

    def get_id(self, model, data):
        raise NotImplementedError("Backend.get_id")

    def fetch_single(self, model, i):
        raise NotImplementedError("Backend.fetch_single")

    def fetch(self, model, constraints):
        raise NotImplementedError("Backend.fetch")

class ModelID(Isomorphism):
    def __init__(self, model):
        self.model = model
    def forward(self, o):
        return o.id
    def backward(self, i):
        return self.model.new_from_id(i)
    
class Field:
    def __init__(self, name=None, convert=Isomorphism.identity(), foreign_key=None):
        self.name = name
        if foreign_key:
            convert = convert.compose(ModelID(foreign_key))
        self.convert = convert
    def __repr__(self):
        return "<Field: {0}>".format(repr(self.name))
    def make_property(self):
        @property
        def prop(inner_self):
            return self.convert.backward(inner_self._data[self.name])
        return prop

constraint_types = {}
class ConstraintMeta(type):
    def __new__(cls, name, bases, attrs):
        convert = CamelCase(capitalize_first=True).reverse().compose(Underscores())
        attrs['name'] = convert.forward(name)
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
        convert = backend.python_convention.reverse().compose(backend.name_convention)
        for k, v in attrs.items():
            if not isinstance(v, Field):
                continue
            fields[k] = v
            if v.name is None:
                v.name = convert.forward(k)
        for k, v in fields.items():
            attrs[k] = v.make_property()
        attrs['_fields'] = fields
        attrs['_cache'] = weakref.WeakValueDictionary()

        if fields:
            backend.verify(name, attrs)
        return super().__new__(cls, name, bases, attrs)

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
        v = v.map(f.convert.forward)
        cs.setdefault(f.name, []).append(v)
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
        return self._backend.get_id(self.__class__, self._data)

    @classmethod
    def all(cls):
        return cls.filter()
    
    @classmethod
    def filter(cls, **kwargs):
        constraints = parse_constraints(cls, kwargs)
        for d in cls._backend.fetch(cls, constraints):
            i = cls._backend.get_id(cls, d)
            yield cls.new_from_id(i, data=d)

    @classmethod
    def new_from_id(cls, i, data=None):
        try:
            return cls._cache[i]
        except KeyError:
            pass

        if not data:
            data = cls._backend.fetch_single(cls, i)

        for k, v in cls._fields.items():
            if not v.name in data:
                raise RuntimeError("backend did not provide " + v.name)
        o = super().__new__(cls)
        o._data = data
        cls._cache[i] = o
        return o
