import os
import time

class ApiCache:
    def __init__(self, cachedir):
        self.cachedir = cachedir
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)

    def lookup(self, h):
        cacheitem = os.path.join(self.cachedir, h.replace("/","_"))
        if os.path.exists(cacheitem):
            with open(cacheitem) as fobj:
                url = fobj.readline().strip()
                expire = fobj.readline().strip()
                data = fobj.read()
            if time.time() > float(expire):
                return None
            return data

        else:
            return None

    def save(self, k, v, expire=60*60):
        cacheitem = os.path.join(self.cachedir, k.replace("/","_"))
        with open(cacheitem, "wb") as fobj:
            fobj.write(k.encode() + b"\n")
            fobj.write(str(int(time.time()) + expire).encode() + b"\n")
            fobj.write(v)
