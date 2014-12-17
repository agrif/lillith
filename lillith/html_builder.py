import contextlib
import html

class HTMLBuilder:
    def __init__(self):
        self._result = ""

    @property
    def result(self):
        begin = '<div style="border: 1px solid black; overflow: auto; display: inline-block; padding: 7px; background-color: #111; color: #eee; font-family: \'EveSans\', \'Tahoma\', sans-serif;">'
        end = '</div>'
        return begin + self._result + end

    def _render_tag(self, atom, name, **kwargs):
        self._result += "<{0}".format(name)
        attrs = [' {0}="{1}"'.format(k, str(v)) for k, v in kwargs.items()]
        self._result += ''.join(attrs)
        if atom:
            self._result += '/>'
        else:
            self._result += '>'

    def leaf(self, name, **kwargs):
        self._render_tag(True, name, **kwargs)

    @contextlib.contextmanager
    def tree(self, name, **kwargs):
        self._render_tag(False, name, **kwargs)
        try:
            yield
        finally:
            self._result += "</{0}>".format(name)

    def write(self, s):
        self.write_raw(html.escape(s))

    def write_raw(self, s):
        self._result += s

    def print(self, *args, **kwargs):
        nkw = kwargs.copy()
        nkw['file'] = self
        print(*args, **nkw)
