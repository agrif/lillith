from .config import _getcf
from .cached_property import cached_property
from .map import Region, SolarSystem
from .items import ItemType

import urllib.parse
import urllib.request
import json

__all__ = ['ItemPrice']

class MarketObject:
    _url = None
    
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("market data objects cannot be created directly")
    
    def __init__(self):
        pass
    
    @classmethod
    def filter(cls, **kwargs):
        raise NotImplementedError("filter")
    
    @classmethod
    def _fetch(cls, **kwargs):
        cfg = _getcf()

        params = {}
        for k, v in kwargs.items():
            if not isinstance(v, list):
                v = [v]
            params[k] = ','.join(str(i) for i in v)
        params['char_name'] = cfg.charname
        
        url = cls._url + '?' + urllib.parse.urlencode(params)
        
        try:
            return cfg.marketcache[url]
        except KeyError:
            pass
        
        with urllib.request.urlopen(url) as f:
            rstr = f.read().decode()
            try:
                result = json.loads(rstr)
            except ValueError as e:
                raise RuntimeError(rstr) from e
        
        results = []
        for datarow in result['emd']['result']:
            data = datarow['row']
            
            obj = super().__new__(cls)
            obj._cfg = cfg
            obj._data = data
            obj.__init__()
            
            results.append(obj)
        
        cfg.marketcache[url] = results
        return results

class ItemPrice(MarketObject):
    _url = "http://api.eve-marketdata.com/api/item_prices2.json"
    
    @cached_property
    def type(self):
        return ItemType.new_from_id(int(self._data['typeID']))
    
    @cached_property
    def region(self):
        if 'regionID' in self._data:
            return Region.new_from_id(int(self._data['regionID']))
        if self.solar_system is not None:
            return self.solar_system.region
        return None

    @cached_property
    def solar_system(self):
        if 'solarsystemID' in self._data:
            return SolarSystem.new_from_id(int(self._data['solarsystemID']))
        return None
    
    @cached_property
    def location(self):
        if self.solar_system is not None:
            return self.solar_system
        return self.region
    
    @cached_property
    def buysell(self):
        c = self._data['buysell']
        if c == 'b':
            return 'buy'
        elif c == 's':
            return 'sell'
        else:
            raise RuntimeError("unexpected value for buysell")
    
    @property
    def price(self):
        return float(self._data['price'])
    
    def __repr__(self):
        return "<ItemPrice: {} {} at {:.2f}>".format(self.buysell, self.type.name, self.price)
    
    # FIXME marketgroup_ids, station_ids
    # FIXME minmax
    @classmethod
    def filter(cls, type=None, region=None, solar_system=None, buysell=None):
        if all([type is None, region is None, solar_system is None]):
            raise ValueError("must provide one of type, region, solar_system")
        
        if all([region is not None, solar_system is not None]):
            raise ValueError("cannot specify both region and solar system")
        
        params = {}
        
        if type is not None:
            if not isinstance(type, list):
                type = [type]
            type = [t if isinstance(t, ItemType) else ItemType(name=t) for t in type]
            params['type_ids'] = [t.id for t in type]
        
        if region is not None:
            if not isinstance(region, list):
                region = [region]
            region = [r if isinstance(r, Region) else Region(name=r) for r in region]
            params['region_ids'] = [r.id for r in region]
        
        if solar_system is not None:
            if not isinstance(solar_system, list):
                solar_system = [solar_system]
            solar_system = [s if isinstance(s, SolarSystem) else SolarSystem(name=s) for s in solar_system]
            params['solarsystem_ids'] = [s.id for s in solar_system]
        
        params['buysell'] = 'a'
        if buysell is not None:
            buysell = buysell.lower()
            if not buysell in ['buy', 'sell']:
                raise ValueError("invalid value for buysell: {}".format(buysell))
            if buysell == 'buy':
                params['buysell'] = 'b'
            else:
                params['buysell'] = 's'
        
        return [p for p in cls._fetch(**params) if p.price > 0]
