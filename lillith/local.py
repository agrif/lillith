from .config import _getcf

__all__ = ['Equal', 'Like', 'Greater', 'GreaterEqual', 'Less', 'LessEqual']

class LocalObject:
    _table = None
    
    def __new__(cls, **kwargs):
        obj, = cls.filter(**kwargs)
        return obj
    
    def __init__(self, **kwargs):
        pass
    
    @classmethod
    def filter(cls, **kwargs):
        raise NotImplementedError("filter")
    
    @classmethod
    def new_from_id(cls, id, data=None):
        cfg = _getcf()
        try:
            return cfg.localcache[(cls, id)]
        except KeyError:
            pass
        
        obj = super().__new__(cls)
        obj.id = id
        obj._cfg = cfg

        if data:
            obj._data = data
        else:
            qb = QueryBuilder(obj)
            qb.condition("rowid", id)
            obj._data, = qb.select()

        obj.__init__()
        cfg.localcache[(cls, id)] = obj
        return obj
    
    @classmethod
    def all(cls):
        return cls.filter()

class Comparison:
    def render(self, field):
        raise NotImplementedError("render")

class SimpleComparison(Comparison):
    format = None
    def __init__(self, val):
        self.val = val
    def render(self, field):
        return (self.format.format(field), [self.val])

class Equal(SimpleComparison):
    format = "{} = ?"

class Like(SimpleComparison):
    format = "{} like ?"

class Greater(SimpleComparison):
    format = "{} > ?"

class GreaterEqual(SimpleComparison):
    format = "{} >= ?"

class Less(SimpleComparison):
    format = "{} < ?"

class LessEqual(SimpleComparison):
    format = "{} <= ?"

class QueryBuilder:
    def __init__(self, cls):
        self.table = cls._table
        self.conds = []
        self.condfields = []
    
    def condition(self, field, val):
        if val is None:
            return
        if not isinstance(val, Comparison):
            val = Equal(val)
        
        cond, condfields = val.render(field)
        self.conds.append(cond)
        self.condfields += condfields
    
    def conditions(self, locals, **kwargs):
        for k, v in kwargs.items():
            self.condition(v, locals[k])
    
    def select(self, *fields):
        if fields:
            fields = ', '.join(fields)
        else:
            fields = '*'
        
        query = "select rowid, {} from {}".format(fields, self.table)
        
        condfields = None
        if self.conds:
            conditions = " and ".join(self.conds)
            condfields = tuple(self.condfields)
            query += " where " + conditions
        
        c = _getcf().dbconn.cursor()
        if condfields:
            c.execute(query, condfields)
        else:
            c.execute(query)
        for row in c:
            yield dict(zip((i[0] for i in c.description), row))

class RemoteQueryBuilder:
    def __init__(self, cls):
        self.api = cls._api_source
        self.conds = []
        self.condfields = []
    
    def condition(self, field, val):
        if val is None:
            return
        if isinstance(val, Comparison):
            raise ValueError("RemoteQueryBuild doesn't support comparisons")
        
        self.conds.append((field, val))
    
    def conditions(self, locals, **kwargs):
        for k, v in kwargs.items():
            self.condition(v, locals[k])
    
    def select(self, **fields):
        data = self.api.get(**fields)
        for row in data:
            if self.conds:
                for field,val in self.conds:
                    if row[field] == val:
                        yield row
            else:
                yield row
class RemoteObject:
    _api_source = None
    _index = "rowid"

    def __new__(cls, **kwargs):
        obj, = cls.filter(**kwargs)
        return obj
    def __init__(self, **kwargs):
        pass

    @classmethod
    def filter(cls, **kwargs):
        raise NotImplementedError("filter")

    @classmethod
    def new_from_id(cls, id, data=None):
        obj = super().__new__(cls)
        obj._id = id
        if data:
            obj._data = data
        else:
            qb = RemoteQueryBuilder(obj)
            qb.condition(cls._index, str(id))
            obj._data, = qb.select()
        
        obj.__init__()
        return obj
    
    @classmethod
    def all(cls):
        return cls.filter()
