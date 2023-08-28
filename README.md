Project to model GISANS samples within McStas

============
Installation
============

Clone repository and install McStas and necessary python packages.
On windows you can use the conda.yml file to creat new Anaconda environment.

==========
Simulation
==========

- GISANS_events.instr: creates events at sample position
- events2BA.py: uses events for BornAgain simulation with sample_model.py defining the model
- GISANS_events_back.instr: reads back modified events and simulated until detector
- PlotMcStasResults.ipynb: IPython notebook plotting McStas results
