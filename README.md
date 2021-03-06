Lillith
=======

*a sane Python API for EVE*

Lillith is a Python module for accessing data about the EVE world,
inspired by the APIs generated by Django's database model system.

Currently, it provides access to large parts of:

 * The EVE static data dump (in [sqlite form][])
 * EVE Market Data (from [eve-marketdata.com][])

 [sqlite form]: https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
 [eve-marketdata.com]: http://eve-marketdata.com/

Get started with:

    python3 -m lillith.shell path/to/static-data.sqlite CharacterName

then poke around with `dir()` and `help()`, for the moment.

A Short Example
---------------

~~~~{.py}
item = ItemType(name="Metal Scraps")
print(item.get_prices(region="Sinq Laison"))
~~~~

For a more detailed example, see *pricecheck.py*.
