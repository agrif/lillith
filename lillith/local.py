from .config import _getcf
from .model import ConstraintVisitor, Backend, CamelCase, Model

class SqlConstraintVisitor(ConstraintVisitor):
    def __init__(self, field):
        self.field = field

    def visit_compound(self, c, l):
        op = {
            'and': "and",
            'or': "or",
        }[c.name]
        cs = []
        binds = []
        for o in l:
            c, bind = self.visit(o)
            cs.append(c)
            binds += bind
        return ('(' + (') ' + op + ' (').join(cs) + ')', binds)

    def visit_simple(self, c, v):
        op = {
            'equal': '=',
            'like': 'like',
            'less': '<',
            'less_equal': '<=',
            'greater': '>',
            'greater_equal': '>=',
        }[c.name]
        return (self.field + ' ' + op + ' ?', [v])

class SqliteBackend(Backend):
    name_convention = CamelCase()
    
    def __init__(self, dbcallback):
        self.dbc = dbcallback

    def get_id_key(self, model):
        return 'rowid'

    def _iter_data(self, c):
        for row in c:
            d = dict(zip((i[0] for i in c.description), row))
            d['rowid'] = row[0]
            yield d
    
    def fetch_single(self, model, i):
        if not '_table' in dir(model):
            raise ValueError('Sqlite models must have _table attribute')
        
        query = "select rowid, * from " + model._table + " where rowid = ?"
        #print(query, [i])
        c = self.dbc().cursor()
        c.execute(query, (i,))
        for d in self._iter_data(c):
            return d
        raise ValueError("invalid id")
    
    def fetch(self, model, constraints):
        if not '_table' in dir(model):
            raise ValueError('Sqlite models must have _table attribute')
        
        cons = []
        binds = []
        for k, v in constraints.items():
            cv = SqlConstraintVisitor(k.name)
            cs, bind = cv.visit(v)
            cons.append(cs)
            binds += bind
        if cons:
            cons = ' where (' + ') and ('.join(cons) + ')'
        else:
            cons = ''
        query = "select rowid, * from " + model._table + cons
        #print(query, binds)
        c = self.dbc().cursor()
        c.execute(query, binds)
        return self._iter_data(c)

class LocalObject(Model, backend=SqliteBackend(lambda: _getcf().dbconn)):
    pass

