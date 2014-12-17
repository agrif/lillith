from .cached_property import cached_property
from .html_builder import HTMLBuilder

class IconObject:
    _icon_type = None
    _icon_size = 64
    _icon_ext = 'png'

    @cached_property
    def icon(self):
        return self.get_icon()

    def get_icon(self, size=None):
        if size is None:
            size = self._icon_size
        if self._icon_type is None:
            raise RuntimeError("no icon type defined")

        return "http://image.eveonline.com/{type}/{id}_{size}.{ext}".format(type=self._icon_type, id=self.id, size=size, ext=self._icon_ext)

    def _make_repr_html(self, name, **kwargs):
        t = HTMLBuilder()
        t.leaf('img', src=self.icon, style="float: left; border-right: 1px solid gray; margin-right: 7px;")
        with t.tree('div', style="display: inline-block;"):
            with t.tree('strong'):
                t.write(name)
            for k, v in kwargs.items():
                t.leaf('br')
                k = k.replace("_", " ")
                t.write('{0}: {1}'.format(k, v))
        return t.result
