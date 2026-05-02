This is a three-body problem simulator which runs simulations in bulk, saving the trajectories to a .h5-file and metadata to a .parquet-file. 

Simulations are mainly ran in bulk with a variation of intial-values to later analyse correlations between variable and system lifespan. 

A lifespan calculator is included, which looks for maxima in acceleration data to determine when a body is no longer interacting with the system.

Inspired by (and original simulation code retrieved from) https://github.com/jman4162/Three-Body-Problem-Simulator


This program was made as a part of a larger school-project, and therefore I'm now too lazy to fix the things which only works in very specific scenarios and remove/improve comments. Some unused code is also still in the files but isn't activated. 
