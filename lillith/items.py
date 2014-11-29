from .local import LocalObject
from .model import Field, Isomorphism
from .map import *
from .cached_property import cached_property
from .icons import IconObject
from .config import _getcf

__all__ = ['ItemType', 'Item', 'ItemContainer', 'SpaceItem']
   
class ItemType(LocalObject, IconObject):
    _table = 'invTypes'
    _icon_type = 'Type'
    
    # groupID
    name = Field('typeName')
    description = Field()
    mass = Field()
    volume = Field()
    capacity = Field()
    portion_size = Field()
    # raceID
    base_price = Field()
    published = Field(convert=Isomorphism.simple(int, bool))
    # marketGroupID
    chance_of_duplicating = Field()

    @cached_property
    def materials(self):
        mats = ItemTypeMaterial.filter(type=self)
        return dict((m.material_type, m.quantity) for m in mats)

    def get_prices(self, **kwargs):
        return ItemPrice.filter(type=self, **kwargs)
    
    def get_buy_price(self, **kwargs):
        return ItemPrice(type=self, buysell='buy', **kwargs)

    def get_sell_price(self, **kwargs):
        return ItemPrice(type=self, buysell='sell', **kwargs)

    def __repr__(self):
        return "<ItemType: {}>".format(self.name)

    def _repr_html_(self):
        return self._make_repr_html(self.name, Volume=self.volume)
    
class SpaceItem(LocalObject):
    _table = 'mapDenormalize'

    type = Field('typeID', foreign_key=ItemType)
    solar_system = Field('solarSystemID', foreign_key=SolarSystem)
    constellation = Field('constellationID', foreign_key=Constellation)
    region = Field('regionID', foreign_key=Region)
    name = Field('itemName')

    def __repr__(self):
        return "<SpaceItem {} {}>".format(self.type.name, self.name)

class ItemTypeMaterial(LocalObject):
    _table = 'invTypeMaterials'

    type = Field('typeID', foreign_key=ItemType)
    material_type = Field('materialTypeID', foreign_key=ItemType)
    quantity = Field()

    def __repr__(self):
        return "<ItemTypeMaterial: {} -> {} x {}>".format(self.type.name, self.material_type.name, self.quantity)

class ItemContainer:
    def __init__(self, data):
        self._id = data['itemID']
        self._data = data
        self.items = []
    def __repr__(self):
        return "<ItemContainer {} items: {}>".format(len(self.items), self.type.name)
    def add(self, item):
        self.items.append(item)
    @cached_property
    def type(self):
        return ItemType(id=self._data['typeID'])
    @cached_property
    def location(self):
        lid = self._data.get('locationID')
        if lid is None: 
            return None
        return get_by_id(lid)
    @property
    def total_value(self):
        return sum([x.total_value for x in self.items])


class Item:
    def __init__(self, data):
        self._id = data['itemID']
        self._data = data

    def __repr__(self):
        return "<Item: {} {}>".format(self.quantity, self.type.name)

    @property
    def total_value(self):
        return self.quantity * self.type.base_price

    @cached_property
    def location(self):
        lid = self._data.get('locationID')
        if lid is None: 
            return None
        return get_by_id(lid)

    @cached_property
    def type(self):
        return ItemType(id=self._data['typeID'])
    
    @property
    def quantity(self):
        return int(self._data['quantity'])



def get_by_id(id):
    # see http://wiki.eve-id.net/APIv2_Corp_AssetList_XML
    id = int(id)
    SolarSystemType = ItemType(id=5)

    if 66000000 <= id <= 66014933:
        return Station(id=id-6000001)
    elif 66014934 <= id <= 67999999:
        return ConquerableStation(id=id)
    elif 60014861 <= id <= 60014928:
        return ConquerableStation(id=id)
    elif 60000000 <= id <= 61000000:
        return Station(id=id)
    elif id >= 61000000:
        return ConquerableStation(id=id)
    else:
        si = SpaceItem.new_from_id(id)
        if si.type == SolarSystemType:
            return SolarSystem(name=si.name)
        else:
            raise RuntimeError("Need SpaceItem lookup for", id)

# late imports
from .market import ItemPrice
