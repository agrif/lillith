from .timed_dict import TimedDict

import weakref
import sqlite3

__all__ = ['initialize']

_lillith_config = None
def _getcf():
    global _lillith_config
    if _lillith_config is None:
        raise RuntimeError("lillith was not initialized")
    return _lillith_config

def initialize(dbpath, charname, cachetime=60*5):
    class Config:
        def __init__(self, dbpath, charname):
            self.dbpath = dbpath
            self.charname = charname
            self.dbconn = sqlite3.connect(dbpath)
            self.db = self.dbconn.cursor()
            
            # fix encoding issues
            def eve_decode(b):
                return b.decode("windows-1252")
            self.dbconn.text_factory = eve_decode
            
            self.localcache = weakref.WeakValueDictionary()
            self.marketcache = TimedDict(time=cachetime)
        
    global _lillith_config
    _lillith_config = Config(dbpath, charname)
