from .config import _getcf


import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

__all__ = ["CharacterList", "AccountBalance"]

class Api:
    _base_url = 'https://api.eveonline.com/'
    keyID = None
    vCode = None

    @classmethod
    def initialize(self, keyID, vCode):
        self.keyID = keyID
        self.vCode = vCode
        self.cfg = _getcf()
        self.cache = self.cfg.apicache
    @classmethod
    def fetch(self, data={}, expire=60*60, cacheOnly=False):
        url = self._base_url + self._method
        data.update({"keyID": self.keyID, "vCode": self.vCode})
        keys = list(data.keys())
        keys.sort()
        data = urllib.parse.urlencode([(x, data[x]) for x in keys])
        
        val = self.cache.lookup(url + data)
        if val is not None:
            return val
        if cacheOnly:
            return None
        req = urllib.request.urlopen(url, data.encode("UTF-8"))
        val = req.read()
        self.cache.save(url + data, val, expire)

        return val.decode("UTF-8")

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
        d = ET.fromstring(data)
        return self.handle(d)


class CharacterList(Api):
    _method = "/account/Characters.xml.aspx"
    _params = []
    _cachetime = 60*60
    @classmethod
    def handle(self, data):
        return [r.attrib for r in data[1][0]]

class AccountBalance(Api):
    _method = "/char/AccountBalance.xml.aspx"
    _params = ["characterID"]
    _cachetime = 60*60
    @classmethod
    def handle(self, data):
        return [r.attrib for r in data[1][0]]

class AssetList(Api):
    _method = "/char/AssetList.xml.aspx"
    _params = ["characterID"]
    _cachetime = 60*60*24
    @classmethod
    def handle(self, data):
        def handle_assets(char, rowset):
            for row in rowset:
                if len(row) > 0: # container
                    thing = {"type": "container", "items": [], "item": row.attrib}
                    handle_contents(thing, row[0])
                    char['items'].append(thing)
                else:
                    char['items'].append({"type": "item", "item": row.attrib})
                    
        def handle_contents(container, rowset):
            for row in rowset:
                container['items'].append({"type": "item", "item": row.attrib})

        me={"items": [], "type": "assets"}
        for rowset in data[1]:
            if rowset.get("name") == "assets":
                handle_assets(me, rowset)
            elif rowset.get("name") == "contents":
                handle_contents(me, rowset)
        return me

class Standings(Api):
    _method = "/char/Standings.xml.aspx"
    _params = ["characterID"]
    _cachetime = 60*60
    @classmethod
    def handle(self, data):
        pass

class CharacterID(Api):
    "ID to Name conversion"
    _method = "/eve/CharacterID.xml.aspx"
    _params = ["names"]
    _cachetime = 60*60*24
    @classmethod
    def handle(self, data):
        return [x.attrib for x in data[1][0]]

class CharacterInfo(Api):
    _method = "/eve/CharacterInfo.xml.aspx"
    _params = ['characterID']
    _cachetime = 60*60
    @classmethod
    def handle(self, data):
        d = {}
        for x in data[1]:
            d[x.tag] = x.text
        return d
