"""user_fuel_database.py

Create your own fuel database
"""
from pyrolib.fuelmap import FuelDatabase, FuelMap, BalbiFuel

# create fuel db
my_db = FuelDatabase()

# create fuel corresponding to your needs
short_grass_balbi = BalbiFuel(e=0.3)
tall_grass_balbi = BalbiFuel(e=0.3)

# add fuels to the database
## the key BalbiFuel means you are adding a BalbiFuel
my_db['short_grass'] = {"BalbiFuel": short_grass_balbi}
my_db['tall_grass'] = {"BalbiFuel": tall_grass_balbi}

# # save database
my_db.dump_database(
    filename = "user_db",
    info = "some information about the db",
    compact = True
)