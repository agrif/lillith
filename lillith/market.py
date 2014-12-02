from .config import _getcf, config
from .model import Backend, Model, Field, Converter, ConstraintVisitor
from .cached_property import cached_property
from .map import Region, SolarSystem
from .items import ItemType

import urllib.parse
import urllib.request
import json

__all__ = ['ItemPrice']

class EqualConstraintVisitor(ConstraintVisitor):
    def __init__(self, full=set()): # empty full set is ok-ish for most uses
        self.full = full

    def visit_compound(self, c, l):
        op, identity = {
            'and': (lambda a, b: a.intersection(b), self.full),
            'or': (lambda a, b: a.union(b), set()),
        }[c.name]
        if not l:
            return identity
        result = self.visit(l[0])
        for x in l[1:]:
            result = op(result, self.visit(x))
        return result
    
    def visit_equal(self, v):
        return {v}

class MarketBackend(Backend):
    def fetch(self, model, constraints):
        if not '_url' in dir(model):
            raise ValueError("Market models must have a _url attribute")
        
        cfg = _getcf()
        params = {}
        for k, v in constraints.items():
            paramname = k.extra.get('paramname', None)
            if not paramname:
                pythonname = {f: v for v, f in model._fields.items()}[k]
                raise ValueError("field " + pythonname + " cannot be filtered on")
            vals = EqualConstraintVisitor(k.extra.get('all', set())).visit(v)
            vals = k.extra.get('edit', lambda x: x)(vals)
            params[paramname] = ','.join(str(i) for i in vals)
        for f in model._fields.values():
            paramname = f.extra.get('paramname', None)
            if not paramname:
                continue
            if 'default' in f.extra and paramname not in params:
                params[paramname] = f.extra['default']
        params['char_name'] = config.character_name
        
        url = model._url + '?' + urllib.parse.urlencode(params)
        
        try:
            return cfg.marketcache[url]
        except:
            pass
        
        #print(url)
        with urllib.request.urlopen(url) as f:
            rstr = f.read().decode()
            try:
                result = json.loads(rstr)
            except ValueError as e:
                raise RuntimeError(rstr) from e
        
        results = []
        for datarow in result['emd']['result']:
            data = datarow['row']
            rect_data = {}
            # rectify terrible types from eve-marketdata.com
            for k, v in data.items():
                if isinstance(v, str):
                    try:
                        v = int(v, base=10)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                rect_data[k] = v
            results.append(rect_data)
        cfg.marketcache[url] = results
        return results

class MarketObject(Model, backend=MarketBackend()):
    pass

class ItemPrice(MarketObject):
    _url = "http://api.eve-marketdata.com/api/item_prices2.json"
    
    type = Field('typeID', foreign_key=ItemType, extra={'paramname': 'type_ids'})
    region = Field('regionID', foreign_key=Region, optional=True, extra={'paramname': 'region_ids'})
    solar_system = Field('solarsystemID', foreign_key=SolarSystem, optional=True, extra={'paramname': 'solarsystem_ids'})
    buysell = Field(convert=Converter.from_map({'buy': 'b', 'sell': 's'}), extra={'paramname': 'buysell', 'default': 'a', 'edit': lambda x: {'a'} if x == {'b', 's'} else x, 'all': {'b', 's'}})
    price = Field()
    
    @cached_property
    def location(self):
        if self.solar_system is not None:
            return self.solar_system
        return self.region
    
    def __repr__(self):
        return "<ItemPrice: {} {} at {:.2f}>".format(self.buysell, self.type.name, self.price)
    
    # FIXME marketgroup_ids, station_ids
    # FIXME minmax
