"""change_fuel_properties_in_db.py

Modify some fuel properties in the database
"""
from pyrolib.fuelmap import FuelDatabase, FuelMap, BalbiFuel

# create fuel db
my_db = FuelDatabase()

# load existing database
my_db.load_fuel_database("FireFluxI")

# change some fuel properties for tall grass fuel represented as a BalbiFuel
my_db["FireFluxI_tall_grass"]["BalbiFuel"].Md.set(0.2)
my_db["FireFluxI_tall_grass"]["BalbiFuel"].e.set(1.2)

# check new properties
print(my_db["FireFluxI_tall_grass"]["BalbiFuel"])