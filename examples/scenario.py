import pyrolib.fuels as pl

# verbose level
# 0: only fuel name
# 1: name + ROS
# 2: name + ROS + every property value
verbose_level = 2

# create some fuels
fuel1 = pl.BalbiFuel()
fuel2 = pl.BalbiFuel(e=2., Md=0.15)

# create a scenario
scenario = pl.Scenario(
    name='scenario',
    longname='testscenario',
    infos='This is a test scenario'
    )

# add fuels to scenario
scenario.add_fuels(fuel1, fuel2)

# show fuels and no wind/no slope ROS contained in the scenario
scenario.show(verbose=verbose_level)

# save scenario in yml file
scenario.save()

# Create a scenario from existing local file (scenario.yml)
new_scenario = pl.Scenario(load='scenario')
new_scenario.show(verbose=verbose_level)

# Show available default scenario
pl.show_default_scenario()

# Create a scenario from a default file
scenario_from_default = pl.Scenario(load='FireFluxI')
scenario_from_default.show(verbose=verbose_level)