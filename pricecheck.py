import lillith
import sys
import math

db = "data.db"
charname = "Grifasi"

def niceisk(n, sigfigs=3):
    units = {
        0 : 'isk',
        1 : 'kisk',
        2 : 'Misk',
        3 : 'Gisk',
        4 : 'Tisk',
    }
    n = round(n, -math.floor(math.log10(n) - sigfigs + 1))
    unit = math.floor(math.log10(n) / 3)
    unit = max(unit, min(units.keys()))
    unit = min(unit, max(units.keys()))
    n *= 1000**(-unit)
    if math.floor(math.log10(int(n))) == math.floor(math.log10(n)):
        n = int(n)
    return "{} {}".format(n, units[unit])

if __name__ == '__main__':
    lillith.initialize(db, charname)
    if len(sys.argv) > 3 or len(sys.argv) <= 1:
        print("usage: {} <system/region> [item]".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    
    place = sys.argv[1]
    item = None
    if len(sys.argv) == 3:
        item = sys.argv[2]
        try:
            item = lillith.ItemType(name=lillith.Like(item))
        except ValueError:
            print("invalid item: {}".format(item), file=sys.stderr)
            sys.exit(1)
    
    try:
        placename = place
        place = lillith.SolarSystem(name=lillith.Like(placename))
        prices = lillith.ItemPrice.filter(solar_system=place, type=item)
    except ValueError:
        try:
            place = lillith.Region(name=lillith.Like(placename))
            prices = lillith.ItemPrice.filter(region=place, type=item)
        except ValueError:
            print("invalid place: {}".format(placename), file=sys.stderr)
            sys.exit(1)
    
    for price in prices:
        print("{} {}: {} ({}/m^3)".format(price.type.name, price.buysell, niceisk(price.price), niceisk(price.price / item.volume)))
