from .local import LocalObject, QueryBuilder
from .cached_property import cached_property
from .html import HTMLBuilder
from .config import _getcf

__all__ = ['Region', 'Constellation', 'SolarSystem']

class MapObject(LocalObject):
    @cached_property
    def position(self):
        return tuple(self._data[k] for k in ['x', 'y', 'z'])
    
    @cached_property
    def bounding_box(self):
        mins = tuple(self._data[k+'Min'] for k in ['x', 'y', 'z'])
        maxs = tuple(self._data[k+'Max'] for k in ['x', 'y', 'z'])
        return (mins, maxs)
    
    @property
    def radius(self):
        return self._data['radius']    

class Region(MapObject):
    _table = 'mapRegions'
    
    @property
    def name(self):
        return self._data['regionName']
    
    # factionID
    
    @property
    def constellations(self):
        return Constellation.filter(region=self)

    @property
    def solar_systems(self):
        return SolarSystem.filter(region=self)
    
    def __repr__(self):
        return "<Region: {}>".format(self.name)
    
    @classmethod
    def filter(cls, name=None, id=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)
        
        qb.conditions(locals(),
                      name = "regionName",
                      id = "regionID",
        )

        for data in qb.select():
            yield cls.new_from_id(data['regionID'], data=data)

class Constellation(MapObject):
    _table = 'mapConstellations'
    
    @property
    def name(self):
        return self._data['constellationName']
    
    @cached_property
    def region(self):
        return Region.new_from_id(self._data['regionID'])
    
    # factionID
    
    @property
    def solar_systems(self):
        return SolarSystem.filter(constellation=self)
    
    def __repr__(self):
        return "<Constellation: {}/{}>".format(self.region.name, self.name)
    
    @classmethod
    def filter(cls, name=None, id=None, region=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)

        regionid = None
        if region is not None:
            if not isinstance(region, Region):
                region = Region(name=region)
            regionid = region.id

        qb.conditions(locals(),
                      name = "constellationName",
                      regionid = "regionID",
                      id = "constellationID",
        )
        
        for data in qb.select():
            yield cls.new_from_id(data['constellationID'], data=data)

class SolarSystemJumps(LocalObject):
    _table = 'mapSolarSystemJumps'

    @cached_property
    def from_solar_system(self):
        return SolarSystem.new_from_id(self._data['fromSolarSystemID'])

    @cached_property
    def to_solar_system(self):
        return SolarSystem.new_from_id(self._data['toSolarSystemID'])
    
    def __repr__(self):
        return "<SolarSystemJump: {} -> {}>".format(self.from_solar_system.name, self.to_solar_system.name)

    @classmethod
    def filter(cls, from_solar_system=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)

        fromid = None
        if from_solar_system is not None:
            if not isinstance(from_solar_system, SolarSystem):
                from_solar_system = SolarSystem(name=from_solar_system)
            fromid = from_solar_system.id

        qb.conditions(locals(),
                      fromid = "fromSolarSystemID",
        )

        for data in qb.select():
            yield cls.new_from_id(data['rowid'], data=data)

class SolarSystem(MapObject):
    _table = 'mapSolarSystems'
    
    @property
    def name(self):
        return self._data['solarSystemName']
    
    @cached_property
    def region(self):
        return Region.new_from_id(self._data['regionID'])
    
    @cached_property
    def constellation(self):
        return Constellation.new_from_id(self._data['constellationID'])
    
    @property
    def luminosity(self):
        return self._data['luminosity']
    
    @property
    def border(self):
        return bool(self._data['border'])
    
    @property
    def fringe(self):
        return bool(self._data['fringe'])

    @property
    def corridor(self):
        return bool(self._data['corridor'])

    @property
    def hub(self):
        return bool(self._data['hub'])

    @property
    def international(self):
        return bool(self._data['international'])

    @property
    def regional(self):
        return bool(self._data['regional'])

    @property
    def constellational(self):
        return bool(self._data['constellation'])

    @property
    def security(self):
        return self._data['security']

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

    @property
    def security_class(self):
        return self._data['securityClass']

    @cached_property
    def jumps(self):
        jumps = SolarSystemJumps.filter(from_solar_system=self)
        return [jump.to_solar_system for jump in jumps]

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
    
    @classmethod
    def filter(cls, name=None, id=None, region=None, constellation=None, luminosity=None, border=None, fringe=None, corridor=None, hub=None, international=None, regional=None, constellational=None, security=None, security_class=None):
        cfg = _getcf()
        qb = QueryBuilder(cls)
        
        regionid = None
        if region is not None:
            if not isinstance(region, Region):
                region = Region(name=region)
            regionid = region.id
        
        constellationid = None
        if constellation is not None:
            if not isinstance(constellation, Constellation):
                constellation = Constellation(name=constellation)
            constellationid = constellation.id
        
        qb.conditions(locals(),
                      name = "solarSystemName",
                      constellationid = "constellationID",
                      regionid = "regionID",
                      id = "solarSystemID",
                      luminosity = "luminosity",
                      border = "border",
                      fringe = "fringe",
                      corridor = "corridor",
                      hub = "hub",
                      international = "international",
                      regional = "regional",
                      constellational = "constellation",
                      security = "security",
                      security_class = "securityClass"
        )

        for data in qb.select():
            yield cls.new_from_id(data['solarSystemID'], data=data)
    
