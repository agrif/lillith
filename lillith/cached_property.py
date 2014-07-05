import functools

# http://code.activestate.com/recipes/576563-cached-property/

def cached_property(f):
    """returns a cached property that is calculated by function f"""
    @functools.wraps(f)
    def get(self):
        try:
            return self._property_cache[f]
        except AttributeError:
            self._property_cache = {}
        except KeyError:
            pass
        x = self._property_cache[f] = f(self)
        return x
        
    return property(get)
