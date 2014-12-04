from . import config
import sys
import subprocess
import argparse

class Interact:
    def p(self, *args, **kwargs):
        print(*args, **kwargs)

    def i(self, prompt, help=None, convert=lambda x: x, verify=lambda x: True, fail=None, default=None):
        if default and not help:
            help = default
        if help:
            prompt = "{0} [{1}]".format(prompt, help)
        while True:
            try:
                v = input(prompt + ' ')
            except EOFError:
                self.p()
                sys.exit(1)
            if not v:
                if default is not None:
                    return default
                continue
            
            try:
                v = convert(v)
                if verify(v):
                    return v
            except Exception:
                pass
            if fail:
                self.p(fail)

    def path(self, prompt):
        return self.i(prompt)

    def yesno(self, prompt, default=True):
        help = 'y/N'
        if default:
            help = 'Y/n'
        def convert(v):
            if v.lower() in ['y', 'yes']:
                return True
            if v.lower() in ['n', 'no']:
                return False
            raise ValueError()

        return self.i(prompt, help=help, convert=convert, fail="Please enter `y' or `n'.", default=default)

    def choice(self, header, choices, other=None):
        rets = [(c, c) for c in choices]
        if other:
            rets.append((other, None))
        l = len(rets)

        self.p(header)
        for i, (s, _) in enumerate(rets):
            self.p("({0}) {1}".format(i, s))
        i = self.i("Choice:", help="0-{0}, default 0".format(l - 1), convert=int, verify=lambda x: 0 <= x < l, fail="Please enter a number between 0 and {0}.".format(l - 1), default=0)
        return rets[i][1]

class Dialog(Interact):
    def __init__(self):
        self.backlog = []
    
    @classmethod
    def useable(cls):
        try:
            subprocess.check_call(['dialog'])
            return True
        except Exception:
            return False

    def _call(self, *args):
        p = subprocess.Popen(['dialog'] + [str(s) for s in args], stderr=subprocess.PIPE)
        dat = p.communicate()
        print()
        if p.returncode == 255:
            sys.exit(1)
        txt = dat[1]
        if txt:
            txt = txt.decode()
        return (p.returncode, txt)

    def p(self, *args):
        if not args:
            if self.backlog:
                msg = '\n\n'.join(self.backlog)
                self.backlog = []
                self._call('--msgbox', msg, 0, 0)
        else:
            self.backlog.append(' '.join(str(i) for i in args))

    def _combine(self, s):
        s = '\n\n'.join(self.backlog + [s])
        self.backlog = []
        return s

    def i(self, prompt, help=None, convert=lambda x: x, verify=lambda x: True, fail=None, default=None):
        while True:
            s = self._combine(prompt)
            if default:
                i, v = self._call('--inputbox', s, 0, 0, default)
            else:
                i, v = self._call('--inputbox', s, 0, 0)
            if i != 0:
                sys.exit(1)
            try:
                v = convert(v)
                if verify(v):
                    return v
            except Exception:
                pass
            if fail:
                self.p(fail)

    def yesno(self, prompt, default=True):
        prompt = self._combine(prompt)
        return not bool(self._call('--yesno', prompt, 0, 0)[0])

    def choice(self, header, choices, other=None):
        tags_items = []
        for i, v in enumerate(choices):
            tags_items.append(str(i))
            tags_items.append(str(v))
        if other:
            tags_items.append(str(len(choices)))
            tags_items.append(other)

        _, v = self._call('--menu', self._combine(header), 0, 0, 0, *tags_items)
        if not v:
            sys.exit(1)
        v = int(v)
        if v < len(choices):
            return choices[v]
        return None

def wizard(text_only):
    if not text_only and Dialog.useable():
        w = Dialog()
    else:
        w = Interact()
    actions = []
    
    w.p("Welcome to the lillith configuration wizard.")
    w.p()

    def choose_store(stores, prompt, mode=None):
        c = w.choice(prompt, stores, other="Other...")
        if c is None:
            p = w.path('Enter path:')
            c = config.Storage(p, mode=mode)
        if not c.writeable:
            w.p('This location does not appear to be writeable.')
            if not w.yesno('Are you sure you want to continue?', default=False):
                sys.exit(1)
        return c

    cfgstore = choose_store(config.config.stores, "Which location do you want to configure?", mode=config.Configuration.store_mode)

    c = config.config
    def get_def(attr):
        try:
            return getattr(c, attr)
        except RuntimeError:
            return None
    def unset(k):
        p = c._profile_data
        if k in p:
            del p[k]

    w.p()
    w.p('The Market API requires a character name for tracking purposes.')
    if w.yesno('Do you wish to provide one?'):
        cn = w.i('Character Name:', default=get_def('character_name'))
        config.character_namep(cn)
        actions.append('set Character Name to {0}'.format(cn))
    else:
        unset(c.character_config_key)
        actions.append('unset Character Name')
        w.p('Ok. The Market API will not be useable until you provide one.')

    w.p()
    w.p('The official API requires an API key to function.')
    if w.yesno('Do you wish to provide a default?'):
        kid = w.i('Key ID:', default=get_def('api_key_id'))
        vcode = w.i('Verification Code:', default=get_def('api_key_vcode'))
        config.api_keyp((kid, vcode))
        actions.append('set API Key to {0}'.format(kid))
    else:
        unset(c.api_id_config_key)
        unset(c.api_vcode_config_key)
        actions.append('unset API Key')
        w.p('Ok. The official API will not be useable until you provide one.')

    download = False
    datastore = False
    if config.data.needs_update:
        w.p()
        w.p('Lillith requires an updated local copy of the Static Data Export, about 300MB uncompressed.')
        w.p('One can be downloaded for you from ' + config.SDE_BASE_URL + ' (about 100MB, compressed).')
        download = w.yesno('Do you want to download it now?')
        if download:
            datastore = choose_store(config.data.stores, "Where do you want to store the SDE?")
            actions.append('download Static Data Export to ' + repr(datastore))
        else:
            w.p('Ok. Large parts of lillith will not work until you do.')
            actions.append('DO NOT download Static Data Export')

    w.p()
    w.p('Ok, the following actions will be taken:')
    for act in actions:
        w.p(" *", act)
    if not w.yesno('Do you wish to continue?'):
        sys.exit(1)

    print()
    print("Saving configuration...")
    c.save(store=cfgstore, force=True)
    if download:
        print('Downloading Static Data Export...')
        config.data.update(store=datastore)
    print()
    print('Done.')

if __name__ == "__main__":
    parse = argparse.ArgumentParser(description="lillith config wizard")
    parse.add_argument('--text-only', action='store_true', default=False, help='force the text-only wizard')
    config.add_arguments(parse)
    p = parse.parse_args()
    wizard(p.text_only)
