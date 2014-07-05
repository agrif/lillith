import time

__all__ = ['TimedDict']

monotonic = getattr(time, 'monotonic', time.time)

class TimedDict(dict):
    def __init__(self, dict={}, time=60, monotonic=monotonic, missing=None):
        self.expires = {}
        self.missing = missing
        self.time = time
        self.monotonic = monotonic
        super().__init__(dict)
    
    def _expire_items(self):
        current = self.monotonic()
        for k, v in list(self.expires.items()):
            if current > v:
                super().__delitem__(k)
                del self.expires[k]
    
    def __missing__(self, key):
        if not self.missing:
            raise KeyError(key)
        return self.missing(key)
    
    def __getitem__(self, key):
        self._expire_items()
        return super().__getitem__(key)
    
    def __setitem__(self, key, item):
        self._expire_items()
        super().__setitem__(key, item)
        self.expires[key] = self.monotonic() + self.time
    
    def __delitem__(self, key):
        self._expire_items()
        super().__delitem__(key)
        del self.expires[key]

