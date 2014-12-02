from .timed_dict import TimedDict
from .ApiCache import ApiCache

import sys
import os
import os.path
import urllib.request
import bz2
import time
import configparser
import weakref
import sqlite3
import parameterize

__all__ = ['initialize', 'data_path', 'config_path', 'character_name', 'api_key']

SDE_BASE_URL = "https://www.fuzzwork.co.uk/dump/"
SDE_SQLITE_URL = SDE_BASE_URL + 'sqlite-latest.sqlite.bz2'

_lillith_config = None
def _getcf():
    global _lillith_config
    if _lillith_config is None:
        # temporary HACK FIXME
        initialize(None, None)
    return _lillith_config

def initialize(key_id, vcode, cachetime=60*5, apicachedir=".evecache"):
    class Config:
        def __init__(self):
            self.marketcache = TimedDict(time=cachetime)
            self.api_key_id = key_id
            self.api_vcode = vcode
            self.apicache = ApiCache(apicachedir)
        
    global _lillith_config
    _lillith_config = Config()

class Storage:
    def __init__(self, path):
        self.path = os.path.abspath(path)

    def __repr__(self):
        traits = ""
        if self.exists():
            traits += ' exists'
        if self.writeable:
            traits += ' writeable'
        return "<Storage: {0}{1}>".format(self.path, traits)

    def join(self, *paths):
        return os.path.join(self.path, *paths)

    def exists(self, path=None):
        if path:
            return os.path.exists(self.join(path))
        return os.path.exists(self.path)

    @property
    def writeable(self):
        test = self.path
        while not os.path.exists(test):
            test, _ = os.path.split(test)
        return os.access(test, os.W_OK)

    def open(self, *paths, mode='r', **kwargs):
        if 'w' in mode or 'a' in mode or '+' in mode:
            if not self.exists():
                os.makedirs(self.path)
        return open(self.join(*paths), mode=mode, **kwargs)

class SearchingLoader:
    def __init__(self, paths):
        self.stores = [Storage(p) for p in paths]
        self._store = None
        self.reload()

    def _perform_on_store(self, do, store=None):
        if store:
            do(store)
            return

        if self._store:
            if not self._store.writeable:
                raise IOError("location in use is not writeable: {0}".format(self._store))
            do(self._store)
            return
        
        for store in self.stores:
            if not store.writeable:
                continue
            do(store)
            return
        
        raise IOError("none of the locations were writeable: {0}".format(self.stores))

character_namep = parameterize.Parameter(None)
api_keyp = parameterize.Parameter((None, None))

def character_name(n):
    return character_namep.parameterize(n)

def api_key(id, vcode):
    return api_keyp.parameterize((id, vcode))

class Configuration(SearchingLoader):
    cfname = 'config.ini'
    character_config_key = 'character'
    api_id_config_key = 'key_id'
    api_vcode_config_key = 'vcode'
    def reload(self):
        self._cf = {}
        self._store = None

        for store in self.stores:
            if store.exists(self.cfname):
                cfg = configparser.ConfigParser()
                with store.open(self.cfname) as f:
                    cfg.read_file(f)
                self._cf = dict(cfg['DEFAULT'])
                self._store = store
                break

    @property
    def character_name(self):
        n = character_namep()
        if n:
            return n
        n = self._cf.get(self.character_config_key)
        if n:
            return n
        raise RuntimeError('character name not configured')

    @property
    def api_key_id(self):
        k, _ = api_keyp()
        if k:
            return k
        k = self._cf.get(self.api_id_config_key)
        if k:
            return k
        raise RuntimeError('api key not configured')

    @property
    def api_key_vcode(self):
        _, v = api_keyp()
        if v:
            return v
        v = self._cf.get(self.api_vcode_config_key)
        if v:
            return v
        raise RuntimeError('api key not configured')

    def save(self, store=None):
        dat = {}
        try:
            dat[self.character_config_key] = self.character_name
        except RuntimeError:
            pass
        try:
            dat[self.api_id_config_key] = self.api_key_id
            dat[self.api_vcode_config_key] = self.api_key_vcode
        except RuntimeError:
            pass

        def do(store):
            cfg = configparser.ConfigParser()
            cfg['DEFAULT'] = dat
            with store.open(self.cfname, mode='w') as f:
                cfg.write(f)
            self.reload()

        self._perform_on_store(do, store=store)
        
class Data(SearchingLoader):
    dbname = 'data.sqlite'
    def reload(self):
        self._db = None
        self._store = None
        
        def eve_decode(b):
            return b.decode('windows-1252')
        
        for store in self.stores:
            if store.exists(self.dbname):
                self._store = store
                self._db = sqlite3.connect(store.join(self.dbname))
                self._db.text_factory = eve_decode
                break

    @property
    def database(self):
        if self._db:
            return self._db
        raise RuntimeError("static data export is not available")

    def _update_copy(self, store, url, path):
        BUFSIZE = 1024 * 16
        MESSAGE_DELAY = 1
        last_message = 0
        fullpath = store.join(path)
        def progress(s):
            nonlocal last_message
            t = time.time()
            if t > last_message + MESSAGE_DELAY:
                last_message = t
                print('Downloading {0} to {1}... ({2})'.format(url, fullpath, s))
        progress('starting')
        bytes_read = 0
        with urllib.request.urlopen(url) as i:
            total = i.length
            dc = bz2.BZ2Decompressor()
            with store.open(path, mode='wb') as o:
                while True:
                    dat = i.read(BUFSIZE)
                    if not dat:
                        break
                    r = dc.decompress(dat)
                    if r:
                        o.write(r)
                    bytes_read += len(dat)
                    progress('{0:02.01f}%'.format(100 * bytes_read / total))

    @property
    def needs_update(self):
        return True
    
    def update(self, force=False, store=None):
        if not force and not self.needs_update:
            return

        def do(store):
            if self._db:
                self._db.close()
                self._db = None
            self._update_copy(store, SDE_SQLITE_URL, self.dbname)
            self.reload()

        self._perform_on_store(do, store=store)

config_paths = []
cache_paths = []
data_paths = []

def add_env_path(k, paths):
    if k in os.environ:
        p = os.path.expandvars(os.path.expanduser(os.environ[k]))
        paths.append(p)

add_env_path('LILLITH_CONFIG', config_paths)
add_env_path('LILLITH_CACHE', cache_paths)
add_env_path('LILLITH_DATA', data_paths)

if sys.platform.startswith('linux'):
    config_paths.append(os.path.expanduser('~/.config/lillith'))
    cache_paths.append(os.path.expanduser('~/.cache/lillith'))
    data_paths.append(os.path.expanduser('~/.local/share/lillith'))
    data_paths.append(os.path.expanduser('/usr/local/share/lillith'))
    data_paths.append(os.path.expanduser('/usr/share/lillith'))
else:
    raise RuntimeError('Unknown Platform: ' + sys.platform)

datap = parameterize.Parameter(Data(data_paths))
data = datap.proxy()
configp = parameterize.Parameter(Configuration(config_paths))
config = configp.proxy()
#cachep = parameterize.Parameter(Cache(cache_paths))
#cache = cachep.proxy()

def data_path(p):
    return datap.parameterize(Data([p] + [s.path for s in data.stores]))

def config_path(p):
    return configp.parameterize(Configuration([p] + [s.path for s in config.stores]))
