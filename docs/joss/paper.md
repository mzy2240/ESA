---
title: 'Easy SimAuto (ESA): A Python Package that Eases Interaction with PowerWorld Simulator'
tags:
  - Python
  - PowerWorld
  - Simulator
  - Automation
  - Server
  - SimAuto
  - ESA
  - Power Systems
  - Electric Grid
  - Smart Grid
  - Energy
  - Numpy
  - Pandas
authors:
  - name: Brandon L. Thayer
    orcid: 0000-0002-6517-1295
    affiliation: "1, 2"
    footnote: 1
  - name: Zeyu Mao
    orcid: 0000-0003-0841-5123
    affiliation: 1
    footnote: 1
    equal: 1
  - name: Yijing Liu
    orcid: 0000-0002-5104-325X
    affiliation: 1
  - name: Katherine Davis
    orcid: 0000-0002-1603-1122
    affiliation: 1
  - name: Thomas Overbye
    orcid: 0000-0002-2382-2811
    affiliation: 1
affiliations:
  - name: "Texas A&M University"
    index: 1
  - name: "Pacific Northwest National Laboratory"
date: 08 April 2020
bibliography: paper.bib
---

# Summary

The electric power system is an essential cornerstone of modern society,
enabling everything from the internet to refrigeration. Due to a variety
of forces including climate change, changing economics, and the digital
computer revolution, the electric grid is undergoing a period of major
change. In order to overcome current and upcoming challenges in the
electric power system, such as integrating renewable resources into a
system that was not designed for intermittent power sources,
researchers and industry practitioners must simulate the electric grid,
its component devices, and its operation.

[PowerWorld Simulator](https://www.powerworld.com/) is a commercial
power systems simulation tool that
contains a suite of modeling and simulation features including power 
flow simulation, contingency analysis, transient stability simulation,
and more [@powerworld]. The Simulator Automation Server (SimAuto) add-on
for PowerWorld provides an application programming interface (API) that
operates in-memory, allowing users to rapidly configure, run, and 
obtain results for simulations. PowerWorld and SimAuto are commonly
used throughout the research community as well as in industry.

SimAuto was designed to be flexible enough to work with most available
programming languages. However, the combination of this flexibility and
the in-memory nature of SimAuto communication can make using SimAuto
challenging, requiring error-checking, data type conversions, data
parsing, and more.

[Easy SimAuto (ESA)](https://github.com/mzy2240/ESA) is a Python package
that significantly simplifies interfacing the PowerWorld Simulator 
[@esa]. ESA wraps all available SimAuto functions; provides high-level
 helper functions to execute common tasks in less code; leverages the
  script commands and the auxiliary file [@aux] to provide more
   functionalities that the native SimAuto cannot offer; performs 
automatic error checking, data type conversions, and data parsing; is 
easily installable via Python's package manager (Pip); has 100% testing
 coverage; and is fully documented. Similar packages have been created 
 in the past, but lack functions, tests, documentation, and other useful
  features ESA provides [@pypowerworld], [@matpws].
Most SimAuto users tend to write their own one-off functions and 
boilerplate code for interfacing with SimAuto - ESA eliminates this 
redundancy and abstracts away all the low-level SimAuto interactions
so that users can focus on performing higher-level tasks such as 
configuring simulations and analyzing results.

ESA helps to meet the needs of both power system researchers and 
practitioners. As the design and operation of the electric grid becomes
more complex, researchers and developers need the ability to incorporate
their programs, algorithms, control schemes, etc. into power system
simulations. Since ESA uses data types common to data science and
scientific computing (e.g. Pandas DataFrames and Numpy Array), it's well
 suited to both academic research and task automation in industry
 . Additionally, ESA provides a much-needed bridge between power system
simulation and machine learning libraries. On the one hand, when 
compared to other Python-based power system simulator, ESA provides much
more functions with faster calculation speed and industry-level 
accuracy; on the other hand, ESA provides a more user-friendly interface
when compared to other traditional power system simulators.

ESA has already been utilized in several research projects past and
present:

- In [@gym-powerworld], [@brandon_thesis], ESA was used to create a
standardized reinforcement learning environment for power system voltage
control. This environment was then used to carry out deep reinforcement
learning (DRL) experiments in which the algorithm attempts to learn how
to best control grid voltages under a diverse set of grid conditions. 
- In [@scenario_development], ESA was leveraged to create and simulate 
different electric grid scenarios where load, renewable generation 
levels, generation capacities, scheduled outages, and unit commitment
were all varied. The resulting scenarios were used in the
[Grid Optimization (GO) competition](https://gocompetition.energy.gov/)
hosted by the U.S. Department of Energy (DOE).
- Geomagnetic disturbances (GMDs) affect the magnetic and electric field
of the earth, inducing dc voltage sources superimposed on transmission
lines. In [@OverbyeKPEC]^[accepted, to be published after delayed conference
 takes place], a planning-based GMD mitigation strategy
 was
developed for large power systems. ESA is leveraged to programmatically
place GIC blocking devices in test systems per the proposed algorithm,
thus minimizing the effects of GMDs on the power grid.
- ESA is used by an ongoing research project entitled "Real Time
Monitoring Applications for the Power Grid under Geomagnetic
Disturbances (GMD)": Recently, a real-world GMD monitoring system
consisting of six magnetometers was deployed in Texas. The resulting
magnetic field measurements are coupled with ground conductivity models
to calculate real-time electric fields. These can then be fed to a grid
model of Texas using ESA to enable calculation of real-time
geomagnetically induced currents (GICs) for monitoring and
visualization.
- ESA is used by an ongoing research project entitled "Contingency 
Analysis Based on Graph Theory Concepts and Line Outage Distribution 
Factor" (LODF). In this project, ESA is leveraged to extract the
topology of the power system model and obtain the LODF matrix.

# Acknowledgements

ESA was developed by researchers at Texas A&M University. Funding was
provided by the Texas A&M Engineering Experiment Station's Smart Grid
Center and the U.S. Department of Energy (DOE) under award DE-OE0000895.

The authors of ESA would like to also thank our fellow researchers at
Texas A&M who have provided essential feedback during ESA's creation.

# References