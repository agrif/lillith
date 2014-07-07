from .local import LocalObject, QueryBuilder
from .map import SolarSystem
from .cached_property import cached_property
from .icons import IconObject
from .config import _getcf

__all__ = ['ItemType', 'Item', 'ItemContainer']

class ItemTypeMaterial(LocalObject):
    _table = 'invTypeMaterials'

    @cached_property
    def type(self):
        return ItemType.new_from_id(self._data['typeID'])

    @cached_property
    def material_type(self):
        return ItemType.new_from_id(self._data['materialTypeID'])

    @property
    def quantity(self):
        return self._data['quantity']

    def __repr__(self):
        return "<ItemTypeMaterial: {} -> {} x {}>".format(self.type.name, self.material_type.name, self.quantity)

    @classmethod
    def filter(cls, type=None, material_type=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)

        if type is not None:
            if not isinstance(type, ItemType):
                type = ItemType(name=type)
            type = type.id
        if material_type is not None:
            if not isinstance(material_type, ItemType):
                material_type = ItemType(name=material_type)
            material_type = material_type.id

        qb.conditions(locals(),
                      type = 'typeID',
                      material_type = 'materialTypeID',
        )

        for data in qb.select():
            yield cls.new_from_id(data['rowid'], data=data)

class ItemType(LocalObject, IconObject):
    _table = 'invTypes'
    _icon_type = 'Type'
    
    # groupID
    
    @property
    def name(self):
        return self._data['typeName']
    
    @property
    def description(self):
        return self._data['description']

    @property
    def mass(self):
        return self._data['mass']

    @property
    def volume(self):
        return self._data['volume']

    @property
    def capacity(self):
        return self._data['capacity']

    @property
    def portion_size(self):
        return self._data['portionSize']

    # raceID

    @property
    def base_price(self):
        return self._data['basePrice']

    @property
    def published(self):
        return bool(self._data['published'])

    # marketGroupID

    @property
    def chance_of_duplicating(self):
        return self._data['chanceOfDuplicating']

    @cached_property
    def materials(self):
        mats = ItemTypeMaterial.filter(type=self)
        return dict((m.material_type, m.quantity) for m in mats)

    def get_prices(self, **kwargs):
        return ItemPrice.filter(type=self, **kwargs)

    def __repr__(self):
        return "<ItemType: {}>".format(self.name)

    def _repr_html_(self):
        return self._make_repr_html(self.name, Volume=self.volume)
    
    @classmethod
    def filter(cls, name=None, id=None, description=None, mass=None, volume=None, capacity=None, portion_size=None, base_price=None, published=None, chance_of_duplicating=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)
        
        qb.conditions(locals(),
                      name = "typeName",
                      id = "typeID",
                      description = "description",
                      mass = "mass",
                      volume = "volume",
                      capacity = "capacity",
                      portion_size = "portionSize",
                      base_price = "basePrice",
                      published = "published",
                      chance_of_duplicating = "chanceOfDuplicating",
        )
        
        for data in qb.select():
            yield cls.new_from_id(data['typeID'], data=data)

class ItemContainer:
    def __init__(self, data):
        self._id = data['itemID']
        self.data = data
        self.items = []
    def __repr__(self):
        return "<ItemContainer {} items: {}>".format(len(self.items), self.type.name)
    def add(self, item):
        self.items.append(item)
    @cached_property
    def type(self):
        return ItemType(id=self.data['typeID'])
    @cached_property
    def location(self):
        return SolarSystem(id=self.data['locationID'])
    @property
    def total_value(self):
        return sum([x.total_value for x in self.items])


class Item:
    def __init__(self, data):
        self._id = data['itemID']
        self.data = data

    def __repr__(self):
        return "<Item: {} {}>".format(self.quantity, self.type.name)

    @property
    def total_value(self):
        return self.quantity * self.type.base_price

    @cached_property
    def location(self):
        return SolarSystem(id=self.data['locationID'])

    @cached_property
    def type(self):
        return ItemType(id=self.data['typeID'])
    
    @property
    def quantity(self):
        return int(self.data['quantity'])

# late imports
from .market import ItemPrice
