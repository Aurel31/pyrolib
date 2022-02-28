import pyrolib.fuels as pl

# print fuel classes available and default property values
pl.show_fuel_classes()

# create default fuel
fuel1 = pl.BalbiFuel()

# create default fuel and changes some properties
fuel2 = pl.BalbiFuel(e=2., Md=0.15)

# copy fuel2 and changes some properties
fuel3 = fuel2.copy(DeltaH=20e7, LAI=2)

# change property value after creation
fuel1.Ml.set(0.9)