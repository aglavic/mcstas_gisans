Project to model GISANS samples within McStas

Installation
============

__On Windows__:
* Clone repository 
* Install [McStas 3.3 metapackage](https://download.mcstas.org/mcstas-3.3/windows/McStas-Metapackage-3.3-win64.exe)
* Use anaconda to create an environment from the `conda.yml` file

Other systems the installation process will be different, but the code should work, too.

Simulation
==========

For an installation on Windows as described above, the jupyter notebook `ExecuteSimulation.ipynb` can
be executed using the newly created anaconda environment with `jupyter notebook`.
This should open a browser windows where you can open the file.

Otherwise you will need to manually run McStas and python for:

- GISANS_events.instr: creates events at sample position
- events2BA.py {model file name}: uses events for BornAgain simulation with sample_model.py defining the model
- GISANS_events_back.instr: reads back modified events and simulated until detector
- PlotMcStasResults.ipynb: IPython notebook plotting McStas results
