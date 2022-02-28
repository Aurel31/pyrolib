"""simplecase.py
"""
import pyrolib.fuels as pl

# create default Balbi fuel
fuel1 = pl.BalbiFuel()

# create a scenario to store fuel
scenario = pl.Scenario(
    name='test',
    longname='test scenario',
    infos='This is a test scenario',
    )
scenario.add_fuel(fuel1)

# Create FuelMap
fuelmap = pl.FuelMap(scenario=scenario)

# add fuel patch and ignition patch
fuelmap.addRectanglePatch(xpos=[50, 450], ypos=[50, 450], fuelindex=1)
fuelmap.addRectanglePatch(xpos=[100, 105], ypos=[245, 255], ignitiontime=10)

# write FuelMap.nc file and create FuelMap.des
fuelmap.write(save2dfile=True)
