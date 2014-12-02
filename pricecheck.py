import lillith
import sys
import argparse
import math

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
    parse = argparse.ArgumentParser(description="a simple price checker")
    parse.add_argument('item')
    parse.add_argument('-l', '--location')
    lillith.config.add_arguments(parse)
    p = parse.parse_args()

    try:
        item = lillith.ItemType(name__like=p.item)
    except ValueError:
        print ("invalid item: {0}".format(p.item), file=sys.stderr)
        sys.exit(1)

    if p.location:
        try:
            place = lillith.SolarSystem(name__like=p.location)
            prices = lillith.ItemPrice.filter(solar_system=place, type=item)
        except ValueError:
            try:
                place = lillith.Region(name__like=p.location)
                prices = lillith.ItemPrice.filter(region=place, type=item)
            except ValueError:
                print("invalid place: {0}".format(p.location), file=sys.stderr)
                sys.exit(1)
    else:
        prices = lillith.ItemPrice.filter(type=item)               
    
    for price in prices:
        if price.price <= 0:
            continue
        print("{0} {1}: {2} ({3}/m^3)".format(price.type.name, price.buysell, niceisk(price.price), niceisk(price.price / item.volume)))
