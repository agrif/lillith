from .config import _getcf


import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import datetime

__all__ = ["initialize"]


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
    keyID = None
    vCode = None
    _cachetime = None # this means use the cacheexpire time from the result document 

    @classmethod
    def initialize(self, keyID, vCode):
        self.keyID = keyID
        self.vCode = vCode
        self.cfg = _getcf()
        self.cache = self.cfg.apicache
    @classmethod
    def fetch(self, data={}, expire=None, cacheOnly=False):
        url = self._base_url + self._method
        data.update({"keyID": self.keyID, "vCode": self.vCode})
        keys = list(data.keys())
        keys.sort()
        data = urllib.parse.urlencode([(x, data[x]) for x in keys])
        
        val = self.cache.lookup(url + data)
        if val is not None:
            return xml_to_dict(val)[1]
        if cacheOnly:
            return None
        req = urllib.request.urlopen(url, data.encode("UTF-8"))
        val = req.read()

        cachetime, d = xml_to_dict(val.decode("UTF-8"))
        if expire is None:
            expire = cachetime
        self.cache.save(url + data, val, expire)
        return d

    @classmethod
    def get(self, **kwargs):
        req_args = self._params
        for arg in self._params:
            if arg not in kwargs:
                raise RuntimeError("Missing parameter:", arg)
        for arg in kwargs:
            if arg not in self._params:
                del kwargs[arg]
        data = self.fetch(data=kwargs, expire=self._cachetime)
        return self.handle(data)
    @classmethod
    def handle(self, data):
        "A default implementation"
        return data 
initialize = Api.initialize

class CharacterList(Api):
    _method = "/account/Characters.xml.aspx"
    _params = []
    @classmethod
    def handle(self, data):
        return data['characters']

class AccountBalance(Api):
    _method = "/char/AccountBalance.xml.aspx"
    _params = ["characterID"]
    @classmethod
    def handle(self, data):
        return data['accounts']

class AssetList(Api):
    _method = "/char/AssetList.xml.aspx"
    _params = ["characterID"]
    @classmethod
    def handle(self, data):
        return data['assets']

class Standings(Api):
    _method = "/char/Standings.xml.aspx"
    _params = ["characterID"]

class CharacterID(Api):
    "ID to Name conversion"
    _method = "/eve/CharacterID.xml.aspx"
    _params = ["names"]
    @classmethod
    def handle(self, data):
        return data['characters']

class CharacterInfo(Api):
    _method = "/eve/CharacterInfo.xml.aspx"
    _params = ['characterID']

class ConqStationList(Api):
    _method = "/eve/ConquerableStationList.xml.aspx"
    _params = []
    @classmethod
    def handle(self, data):
        return data['outposts']
