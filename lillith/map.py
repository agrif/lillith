from .local import LocalObject
from .model import Field, Isomorphism
import lillith
from .Api import RemoteObject, RemoteQueryBuilder, Api
from .cached_property import cached_property
from .html import HTMLBuilder
from .config import _getcf

__all__ = ['Region', 'Constellation', 'SolarSystem', 'Station', 'ConquerableStation']

class SimpleMapObject(LocalObject):
    x = Field()
    y = Field()
    z = Field()

    @cached_property
    def position(self):
        return tuple(self._data[k] for k in ['x', 'y', 'z'])

class MapObject(SimpleMapObject):
    x_min = Field()
    x_max = Field()
    y_min = Field()
    y_max = Field()
    z_min = Field()
    z_max = Field()

    radius = Field()

    @cached_property
    def bounding_box(self):
        mins = tuple(self._data[k+'Min'] for k in ['x', 'y', 'z'])
        maxs = tuple(self._data[k+'Max'] for k in ['x', 'y', 'z'])
        return (mins, maxs)
    
class Region(MapObject):
    _table = 'mapRegions'

    name = Field('regionName')
    
    # factionID
    
    @property
    def constellations(self):
        return Constellation.filter(region=self)

    @property
    def solar_systems(self):
        return SolarSystem.filter(region=self)
    
    def __repr__(self):
        return "<Region: {}>".format(self.name)
    
class Constellation(MapObject):
    _table = 'mapConstellations'

    name = Field('constellationName')
    region = Field('regionID', foreign_key=Region)
    # factionID
    
    @property
    def solar_systems(self):
        return SolarSystem.filter(constellation=self)
    
    def __repr__(self):
        return "<Constellation: {}/{}>".format(self.region.name, self.name)

class SolarSystem(MapObject):
    _table = 'mapSolarSystems'

    name = Field('solarSystemName')
    region = Field('regionID', foreign_key=Region)
    constellation = Field('constellationID', foreign_key=Constellation)
    luminosity = Field()
    border = Field(convert=Isomorphism.simple(int, bool))
    fringe = Field(convert=Isomorphism.simple(int, bool))
    corridor = Field(convert=Isomorphism.simple(int, bool))
    hub = Field(convert=Isomorphism.simple(int, bool))
    international = Field(convert=Isomorphism.simple(int, bool))
    regional = Field(convert=Isomorphism.simple(int, bool))
    constellational = Field('constellation', convert=Isomorphism.simple(int, bool))
    security = Field()
    
    @cached_property
    def security_color(self):
        sec = round(self.security, 1)
        if sec >= 1.0:
            return (0x2F, 0xEF, 0xEF)
        elif sec == 0.9:
            return (0x48, 0xF0, 0xC0)
        elif sec == 0.8:
            return (0x00, 0xEF, 0x47)
        elif sec == 0.7:
            return (0x00, 0xF0, 0x00)
        elif sec == 0.6:
            return (0x8F, 0xEF, 0x2F)
        elif sec == 0.5:
            return (0xEF, 0xEF, 0x00)
        elif sec == 0.4:
            return (0xD7, 0x77, 0x00)
        elif sec == 0.3:
            return (0xF0, 0x60, 0x00)
        elif sec == 0.2:
            return (0xF0, 0x48, 0x00)
        elif sec == 0.1:
            return (0xD7, 0x30, 0x00)
        elif sec <= 0.0:
            return (0xF0, 0x00, 0x00)
        
    # factionID    
    # sunTypeID
    security_class = Field()

    @cached_property
    def jumps(self):
        jumps = SolarSystemJumps.filter(from_solar_system=self)
        return [jump.to_solar_system for jump in jumps]

    @cached_property
    def stations(self):
        return Station.filter(solar_system=self)

    def __repr__(self):
        return "<SolarSystem: {}/{}/{} {:.1f}>".format(self.region.name, self.constellation.name, self.name, self.security)

    def _repr_html_(self):
        t = HTMLBuilder()
        with t.tree('strong'):
            t.write(self.name)
        with t.tree('span', style="font-weight: bold; margin-left: 0.2em; color: rgb{};".format(self.security_color)):
            t.print("{:.1f}".format(self.security))
        t.print('/', self.constellation.name, '/', self.region.name)

        return t.result

class SolarSystemJumps(LocalObject):
    _table = 'mapSolarSystemJumps'

    from_solar_system = Field('fromSolarSystemID', foreign_key=SolarSystem)
    to_solar_system = Field('toSolarSystemID', foreign_key=SolarSystem)
    
    def __repr__(self):
        return "<SolarSystemJump: {} -> {}>".format(self.from_solar_system.name, self.to_solar_system.name)
    
class Station(SimpleMapObject):
    _table = 'staStations'

    def __repr__(self):
        return "<Station {}>".format(self.name)

    name = Field('stationName')
    region = Field('regionID', foreign_key=Region)
    constellation = Field('constellationID', foreign_key=Constellation)
    solar_system = Field('solarSystemID', foreign_key=SolarSystem)
    reprocessing_efficiency = Field()
    reprocessing_stations_take = Field()
    security = Field()
    docking_cost_per_volume = Field()
    max_ship_volume_dockable = Field()
    
class ConquerableStation(RemoteObject):
    _api_source = "/eve/ConquerableStationList.xml.aspx"
    _index = "stationID"

    @property
    def id(self):
        return self._data['stationID']

    @cached_property
    def solar_system(self):
        return SolarSystem(id=self._data['solarSystemID'])
    
    @property
    def name(self):
        return self._data['stationName']
    
    @cached_property
    def type(self):
        return lillith.ItemType(id=self._data['stationTypeID'])

    def __repr__(self):
        return "<ConquerableStation {}>".format(self.name)
    
    @classmethod
    def filter(cls, id=None, name=None):
        cfg = _getcf()
        qb = RemoteQueryBuilder(cls)
        if type(id) == int:
            id = str(id)
        
        qb.conditions(locals(),
                      id = "stationID",
                      name = "stationName",
        )

        for data in qb.select():
            yield cls.new_from_id(data['stationID'], data=data)
