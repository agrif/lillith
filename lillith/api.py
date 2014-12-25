from .config import config, cache

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import datetime

def xml_to_dict(s):
    root = ET.fromstring(s)
    if not root.tag == 'eveapi' or not root.attrib.get('version') in ['1', '2']:
        raise ValueError("not valid EVE API data")

    def parse_row(elems, base):
        for rowset in elems:
            # tags that are not rowsets are stuck in directly
            if not rowset.tag == 'rowset':
                base[rowset.tag] = rowset.text
                continue

            # it must be a rowset
            if 'key' not in rowset.attrib or \
               'name' not in rowset.attrib:
                raise ValueError("badly formed EVE API data")

            # collect all rows in this rowset
            name = rowset.attrib['name']
            key = rowset.attrib['key']
            rows = []
            for row in rowset:
                if not row.tag == 'row' or key not in row.attrib:
                    raise ValueError("badly formed EVE API data")
                rowproto = row.attrib.copy()
                # if the row has text, instead of subtags, use it
                if row.text:
                    rowproto['text'] = row.text
                # parse subtags of this row, and add it to our gathered rows
                rows.append(parse_row(row, rowproto))
            # insert this row
            base[name] = rows
        return base

    currenttime = None
    cacheduntil = None
    cachetime = None
    result = None
    for child in root:
        if child.tag == 'currentTime':
            currenttime = datetime.datetime.strptime(child.text, "%Y-%m-%d %H:%M:%S")
        elif child.tag == 'cachedUntil':
            cacheduntil = datetime.datetime.strptime(child.text, "%Y-%m-%d %H:%M:%S")
        elif child.tag == 'result':
            result = parse_row(child, {})
        else:
            raise ValueError("badly formed EVE API data")
    if currenttime and cacheduntil:
        cachetime = (cacheduntil - currenttime).total_seconds()
    return cachetime, result

class Api:
    _base_url = 'https://api.eveonline.com/'

    @classmethod
    def fetch(cls, method, **data):
        data = data.copy()
        data.update({"keyID": config.api_key_id, "vCode": config.api_key_vcode})
        return cls.fetch_nokey(method, **data)
    
    @classmethod
    def fetch_nokey(cls, method, **data):
        url = cls._base_url + method
        keys = list(data.keys())
        keys.sort()
        data = urllib.parse.urlencode([(x, data[x]) for x in keys])
        
        d = cache.get(url + '?' + data)
        if d is not None:
            return d
        req = urllib.request.urlopen(url, data.encode("UTF-8"))
        val = req.read()

        expire, d = xml_to_dict(val.decode("UTF-8"))
        cache.set(url + '?' + data, d, expire)
        return d

class RemoteQueryBuilder:
    def __init__(self, cls):
        self.api = cls._api_source
        self.conds = []
        self.condfields = []
    
    def condition(self, field, val):
        if val is None:
            return
        #if isinstance(val, Comparison):
        #    raise ValueError("RemoteQueryBuild doesn't support comparisons")
        
        self.conds.append((field, val))
    
    def conditions(self, locals, **kwargs):
        for k, v in kwargs.items():
            self.condition(v, locals[k])
    
    def select(self, **fields):
        data = Api.fetch(self.api, **fields)['outposts']
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


