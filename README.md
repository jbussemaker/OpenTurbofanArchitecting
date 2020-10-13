# Open Turbofan Architecting

OTA is an open-source system architecture optimization problem with the purpose of demonstrating the principle of
system architecture optimization, and implementing a realistic problem for optimization algorithm benchmarking.

System architectures are defined by assigning components to functions, and by connecting components among each other. A
system architecture design space can consist of multiple components able to fulfill a function, which gives architecting
decisions and thereby defines the architecture design space. An architecture optimization problem gathers all these
decisions (e.g. function assignment, component attributes, component connections) and formulates it as a formal
optimization problem: in terms of design variables, objectives, and constraints.

The turbofan architecting problem has the goal of finding the best possible turbofan architecture according to one or
more objectives: for example fuel burn, emissions, or weight. It is also possible to use multiple of these objectives at
the same time when performing multi-objective optimization, with the result of finding a Pareto front of optimal
architectures.

For evaluation of the turbofan architectures, [pyCycle](https://github.com/OpenMDAO/pyCycle) is used.
PyCycle is a modular engine cycle analysis and sizing framework based on [OpenMDAO](https://openmdao.org/), a powerful
Python-based Multidisciplinary Design Optimization (MDO) framework.
