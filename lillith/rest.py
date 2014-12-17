from flask import Blueprint, url_for, request, abort
from jinja2 import escape as html_escape

__all__ = ['lillith_blueprint']

# absolute imports to please the flask reloader
import lillith
from lillith.model import Underscores, CamelCase, Or
from lillith.map import Region, Constellation, SolarSystem, Station
from lillith.items import SpaceItem, ItemType

models = [Region, Constellation, SolarSystem, Station, SpaceItem, ItemType]

python_cls_convention = CamelCase()
url_convention = Underscores(underscore='-')
js_convention = CamelCase()

class ModelUrls:
    all = {}
    
    def __init__(self, bp, model):
        self.all[model] = self
        
        self.bp = bp
        self.model = model
        
        words = python_cls_convention.backward(model.__name__)
        self.url = '/' + url_convention.forward(words) + 's'
        self.endpoint = model._backend.python_convention.forward(words)
        
        self.route('/')(self.index)
        self.route('/<int:id>')(self.view)
    
    def url_for(self, endpoint, *args, **kwargs):
        return url_for('.' + self.endpoint + '_' + endpoint, *args, **kwargs)

    @classmethod
    def repr_link(cls, m, url=None):
        if url is None and type(m) in cls.all:
            url = cls.all[type(m)].url_for('view', id=m.id)
        
        try:
            inside = m._repr_html_()
        except AttributeError:
            if isinstance(m, tuple):
                inside = html_escape(repr(m))
            elif isinstance(m, dict):
                inside = "<ul>"
                keys = list(m.keys())
                keys.sort()
                for k in keys:
                    v = m[k]
                    if not isinstance(k, str):
                        k = cls.repr_link(k)
                    v = cls.repr_link(v)
                    inside += "<li><strong>{0}</strong>: {1}</li>".format(k, v)
                inside += "</ul>"
            elif isinstance(m, str):
                inside = html_escape(repr(m))
            elif '__iter__' in dir(m):
                inside = "<ul>"
                dat = list(m)
                try:
                    dat.sort()
                except TypeError:
                    pass
                for i in dat:
                    inside += "<li>{0}</li>".format(cls.repr_link(i))
                inside += "</ul>"
            else:
                inside = html_escape(repr(m))
        
        if not url:
            return str(inside)
        return '<a href="{0}">{1}</a>'.format(url, inside)
    
    @classmethod
    def all_index(cls):
        s = ""
        for model, urls in cls.all.items():
            s += '<li><a href="{url}">{model}</a></li>'.format(url=urls.url_for('index'), model=html_escape(repr(model)))
        return '<ul>' + s + '</ul>'
    
    def route(self, url_leaf):
        def inner(f):
            endpoint = self.endpoint + '_' + f.__name__
            return self.bp.route(self.url + url_leaf, endpoint=endpoint)(f)
        return inner
    
    def index(self):
        PAGE_SIZE = 50
        page = request.args.get('page', 0)
        try:
            page = int(page)
        except ValueError:
            abort(400)
        
        navlinks = ""
        if page > 0:
            prev_url = self.url_for('index') + '?page=' + str(page - 1)
            navlinks += "<a href=\"{0}\">&lt; prev</a>".format(prev_url)
        navlinks += " <strong>page {0}</strong> ".format(page)
        
        kwargs = {k: v for k, v in request.args.items() if k != 'page'}
        print(kwargs)
        
        s = ""
        try:
            dat = self.model.filter(**kwargs)
            for i, m in enumerate(dat):
                if i < page * PAGE_SIZE:
                    continue
                if i >= (page + 1) * PAGE_SIZE:
                    break
                s += "<li>" + self.repr_link(m) + "</li>"
        except ValueError:
            abort(400)
        
        try:
            next(dat)
            next_url = self.url_for('index') + '?page=' + str(page + 1)
            navlinks += "<a href=\"{0}\">next &gt;</a>".format(next_url)
        except StopIteration:
            pass
        
        return navlinks + "<br><ul>" + s + "</ul><br>" + navlinks
        
    def view(self, id):
        m = self.model.new_from_id(id)

        res = self.repr_link(m) + "<br>"
        res += self.repr_link({name: getattr(m, name) for name in m._fields if name != "self"})
        
        rel = {name: getattr(m, name) for name, val in vars(type(m)).items() if not name in m._fields and isinstance(val, property)}
        if rel:
            res += "<h2>Related:</h2>" + self.repr_link(rel)
        
        return res

lillith_blueprint = Blueprint('lillith', __name__)
for model in models:
    ModelUrls(lillith_blueprint, model)
lillith_blueprint.route('/', endpoint='index')(ModelUrls.all_index)

if __name__ == '__main__':
    from flask import Flask
    from lillith.config import add_arguments
    import argparse

    parse = argparse.ArgumentParser(description="a REST interface to lillith")
    parse.add_argument('--host', default="localhost")
    parse.add_argument('--debug', action="store_true", default=False)
    parse.add_argument('--port', default=5000, type=int)
    add_arguments(parse)
    p = parse.parse_args()
    
    app = Flask(__name__)
    app.register_blueprint(lillith_blueprint)
    app.run(host=p.host, debug=p.debug, port=p.port)
