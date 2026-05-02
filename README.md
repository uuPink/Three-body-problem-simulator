
----------------------
**Three-body problem simulator**
----------------------
Inspired by (and original simulation code retrieved from) https://github.com/jman4162/Three-Body-Problem-Simulator

This is a three-body problem simulator made in Python which runs simulations with SciPy in bulk, saving the trajectories to a .h5-file and metadata to a .parquet-file. 

Simulations are mainly ran in bulk with a variation of intial-values to later analyse correlations between variable and system lifespan. 

A lifespan calculator is included, which looks for maxima in acceleration data to determine when a body is no longer interacting with the system.

Acceleration- and velocitydata as well as lifespan data can be saved to excel-files automatically.

Matplotlib is used toi visualize trajectories.


---------------------------------------
This program was made as a part of a larger school-project, and therefore I'm now too lazy to fix the things which only works in very specific scenarios and remove/improve comments. Some unused code is also still in the files but isn't activated. Some comments are also in swedish (sorry).

Maybe will come back to this project later to improve it and give it a UI for easy-use but for now I don't have the time to work on this anymore.

---------------------------------------

**Python-modules and versions used:**
Python 3.11
SciPy 1.16.1
Numpy 1.26.4
H5py 3.15.1
Pandas 2.3.3
Matplotlib 3.10.3
Pandas xlsxwriter 3.2.9

----------------------------------------
Example:
<img width="682" height="592" alt="2_39_47304000_1777223920 7912383" src="https://github.com/user-attachments/assets/2ee72b8f-7ff2-481c-b373-6a4915f5df2a" />
