import sys
import os
import os.path
import stat
import urllib.request
import bz2
import time
import configparser
import argparse
import json
import collections
import sqlite3
import threading

import appdirs
import parameterize
from .bifunction import JSON, Encode, Base64

__all__ = ['data_path', 'config_path', 'character_name', 'api_key', 'add_arguments']

SDE_BASE_URL = "https://www.fuzzwork.co.uk/dump/"
SDE_SQLITE_URL = SDE_BASE_URL + 'sqlite-latest.sqlite.bz2'

class Storage:
    def __init__(self, path, mode=None):
        self.path = os.path.abspath(path)
        self.mode = mode

    def __repr__(self):
        traits = ""
        if self.exists():
            traits += ' exists'
        if self.writeable:
            traits += ' writeable'
        return "<Storage: {0}{1}>".format(self.path, traits)

    def join(self, *paths):
        return os.path.join(self.path, *paths)

    def exists(self, *paths):
        return os.path.exists(self.join(*paths))
    
    def remove(self, *paths):
        os.remove(self.join(*paths))
    
    def listdir(self, *paths):
        try:
            return os.listdir(self.join(*paths))
        except FileNotFoundError:
            return []

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
                if self.mode:
                    os.chmod(self.path, self.mode)
        p = self.join(*paths)
        f = open(p, mode=mode, **kwargs)
        if self.mode:
            os.chmod(p, self.mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        return f

class SearchingLoader:
    store_mode = None
    def __init__(self, paths):
        self.stores = [Storage(p, mode=self.store_mode) for p in paths]
        self._store = None
        self.reload()

    def _perform_on_store(self, do, store=None):
        if store:
            return do(store)

        if self._store:
            if not self._store.writeable:
                raise IOError("location in use is not writeable: {0}".format(self._store))
            return do(self._store)
        
        for store in self.stores:
            if not store.writeable:
                continue
            return do(store)
        
        raise IOError("none of the locations were writeable: {0}".format(self.stores))

profilep = parameterize.Parameter('DEFAULT')
character_namep = parameterize.Parameter(None)
api_keyp = parameterize.Parameter((None, None))

def profile(n):
    return profilep.parameterize(n)

def character_name(n):
    return character_namep.parameterize(n)

def api_key(id, vcode):
    return api_keyp.parameterize((id, vcode))

class Configuration(SearchingLoader):
    store_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    
    cfname = 'config.ini'
    character_config_key = 'character'
    api_id_config_key = 'key_id'
    api_vcode_config_key = 'vcode'
    
    def reload(self):
        self._cf = configparser.ConfigParser()
        self._store = None

        for store in self.stores:
            if store.exists(self.cfname):
                with store.open(self.cfname) as f:
                    self._cf.read_file(f)
                self._store = store
                break

    @property
    def _profile_data(self):
        p = profilep()
        if not p in self._cf:
            raise ValueError('profile ' + repr(p) + ' does not exist')
        return self._cf[p]

    @property
    def character_name(self):
        n = character_namep()
        if n:
            return n
        n = self._profile_data.get(self.character_config_key)
        if n:
            return n
        raise RuntimeError('character name not configured')

    @property
    def api_key_id(self):
        k, _ = api_keyp()
        if k:
            return k
        k = self._profile_data.get(self.api_id_config_key)
        if k:
            return k
        raise RuntimeError('api key not configured')

    @property
    def api_key_vcode(self):
        _, v = api_keyp()
        if v:
            return v
        v = self._profile_data.get(self.api_vcode_config_key)
        if v:
            return v
        raise RuntimeError('api key not configured')

    def save(self, store=None, force=False):
        def do(store):
            needs_save = force
            p = profilep()
            if not p in self._cf:
                self._cf[p] = {}
                needs_save = True

            def set_if(v, k):
                nonlocal needs_save
                if v:
                    old = self._profile_data.get(k)
                    self._profile_data[k] = v
                    if old != v:
                        needs_save = True

            set_if(character_namep(), self.character_config_key)
            k, v = api_keyp()
            set_if(k, self.api_id_config_key)
            set_if(v, self.api_vcode_config_key)

            if needs_save:
                with store.open(self.cfname, mode='w') as f:
                    self._cf.write(f)
                self.reload()
            return needs_save
        return self._perform_on_store(do, store=store)
        
class Data(SearchingLoader):
    dbname = 'data.sqlite'
    def reload(self):
        self._dbcontainer = None
        self._store = None
        
        for store in self.stores:
            if store.exists(self.dbname):
                self._store = store
                self._dbcontainer = threading.local()
                # test that this will work later
                sqlite3.connect(store.join(self.dbname))
                break

    @property
    def database(self):
        if not 'db' in dir(self._dbcontainer):
            if not self._store:
                raise RuntimeError("static data export is not available")
            
            db = sqlite3.connect(self._store.join(self.dbname))
            db.text_factory = lambda b: b.decode('windows-1252')
            self._dbcontainer.db = db
        
        return self._dbcontainer.db

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
            if self._dbcontainer:
                self._dbcontainer = None
            self._update_copy(store, SDE_SQLITE_URL, self.dbname)
            self.reload()

        self._perform_on_store(do, store=store)

class Cache(SearchingLoader, collections.MutableMapping):
    store_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    
    _default_expire = 60 * 60
    _autoclean_interval = 60 * 60
    _key = JSON().compose(Encode().wrap(Base64(altchars=b'-_')))
    _serialize = (json.load, json.dump)
    
    def reload(self):
        self.main = self
        @self._perform_on_store
        def do(s):
            self._store = s
        self.clean()
    
    def __contains__(self, key):
        self._autoclean()
        k = self._key.forward(key)
        return self._store.exists(k)
    
    def _remove(self, k):
        try:
            self._store.remove(k)
        except Exception:
            pass
    
    def __getitem__(self, key):
        self._autoclean()
        k = self._key.forward(key)
        try:
            with self._store.open(k) as f:
                f.readline() # key
                t = float(f.readline().strip())
                if time.time() <= t:
                    return self._serialize[0](f)
        except Exception:
            pass
        
        self._remove(k)
        raise KeyError(key)
    
    def __setitem__(self, key, value, expires=None):
        self._autoclean()
        if expires is None:
            expires = self._default_expire
        k = self._key.forward(key)
        try:
            with self._store.open(k, mode='w') as f:
                f.write('{0}\n'.format(repr(key)))
                f.write('{0}\n'.format(time.time() + expires))
                self._serialize[1](value, f)
        except Exception:
            self._remove(k)
            raise
    
    def set(self, key, value, expires=None):
        self.__setitem__(key, value, expires=expires)
    
    def __delitem__(self, key):
        self._autoclean()
        k = self._key.forward(key)
        try:
            self._store.remove(k)
        except Exception:
            raise KeyError(key)

    def __iter__(self):
        self._autoclean()
        for k in self._store.listdir():
            try:
                key = self._key.backwards(k)
                yield key
            except Exception:
                pass
    
    def __len__(self):
        self._autoclean()
        return len(self._store.listdir())
    
    def _autoclean(self):
        if self._last_clean + self._autoclean_interval < time.time():
            self.clean()
    
    def clean(self):
        self._last_clean = time.time()
        for k in self._store.listdir():
            try:
                with self._store.open(k) as f:
                    f.readline() # key
                    t = float(f.readline().strip())
                    if time.time() > t:
                        self._remove(k)
            except Exception:
                self._remove(k)

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

dirs = appdirs.AppDirs('lillith', appauthor=False, multipath=True)
def add_app_path(l, key, use_site=False):
    user = getattr(dirs, 'user_' + key + '_dir')
    site = getattr(dirs, 'site_' + key + '_dir', None)
    l += user.split(os.pathsep)
    if site and use_site:
        l += site.split(os.pathsep)

add_app_path(config_paths, 'config')
add_app_path(cache_paths, 'cache')
add_app_path(data_paths, 'data', use_site=True)

datap = parameterize.Parameter(Data(data_paths))
data = datap.proxy()
configp = parameterize.Parameter(Configuration(config_paths))
config = configp.proxy()
cachep = parameterize.Parameter(Cache(cache_paths))
cache = cachep.proxy()

def data_path(p):
    return datap.parameterize(Data([p] + [s.path for s in data.stores]))

def config_path(p):
    return configp.parameterize(Configuration([p] + [s.path for s in config.stores]))

def cache_path(p):
    return cachep.parameterize(Cache([p] + [s.path for s in cache.stores]))

def add_arguments(p, prefix=''):
    def call(f):
        class CallAction(argparse.Action):
            def __init__(self, option_strings, dest, **kwargs):
                super().__init__(option_strings, '__lillith_' + dest, **kwargs)
            def __call__(self, parser, namespace, values, option_string=None):
                f(values)
        return CallAction
    
    def add(n, **kwargs):
        p.add_argument('--' + prefix + n, **kwargs)

    def add_call(**kwargs):
        def inner(f):
            n = f.__name__.replace('_', '-')
            add(n, action=call(f), **kwargs)
            return f
        return inner

    @add_call(metavar='NAME', help='select which profile to use from lillith config')
    def profile(p):
        profilep(p)
    
    @add_call(metavar='NAME', help='set character name to use for eve-marketdata.com')
    def character(c):
        character_namep(c)

    def api_key_type(s):
        if not ':' in s:
            raise argparse.ArgumentTypeError('must have form ID:vCode')
        return s
    
    @add_call(metavar='ID:VCODE', type=api_key_type, help='set API Key to use for official API')
    def api_key(t):
        k, v = t.split(':', 1)
        api_keyp((k, v))

if __name__ == "__main__":
    parse = argparse.ArgumentParser(description="lillith config utility")
    parse.add_argument('--update-data', default=False, action='store_true', help='download the static data export, if needed')
    add_arguments(parse)
    p = parse.parse_args()

    if len(sys.argv) == 1:
        parse.print_help()
    else:
        # check if we should update
        if p.update_data:
            data.update()
        
        # just save the config
        saved = config.save()
        print('Profile:', profilep())
        try:
            print('Character Name:', config.character_name)
        except Exception:
            print('Character Name unset')
        try:
            print('API Key:', config.api_key_id, ':', ''.join('*' for c in config.api_key_vcode)[:10])
        except Exception:
            print('API Key unset')
        if saved:
            print('Saved.')
        else:
            print('Already set.')
            
