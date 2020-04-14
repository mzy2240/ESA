ESA has already been utilized in several research projects past and
present. If you use ESA in your work, please file an issue on
`GitHub <https://github.com/mzy2240/ESA/issues>`__ and we'll list your
project here! Please cite ESA if you use it in your work: see
:ref:`citation`.

-   In `gym-powerworld <https://github.com/blthayer/gym-powerworld>`__,
    ESA was used to create a standardized reinforcement learning
    environment for power system voltage control. This environment was
    then `used to carry out deep reinforcement learning (DRL)
    experiments <https://github.com/blthayer/drl-powerworld>`__
    in which the algorithm attempts to learn how to best control grid
    voltages under a diverse set of grid conditions.
-   In `this paper
    <https://ieeexplore.ieee.org/abstract/document/9042493>`__,
    ESA was leveraged to create and simulate different electric grid
    scenarios where load, renewable generation levels, generation
    capacities, scheduled outages, and unit commitment were all varied.
    The resulting scenarios were used in the
    `Grid Optimization (GO) competition
    <https://gocompetition.energy.gov/>`__
    hosted by the U.S. Department of Energy (DOE).
-   Geomagnetic disturbances (GMDs) affect the magnetic and electric field
    of the earth, inducing dc voltage sources superimposed on transmission
    lines. In an accepted paper by Martinez et al. entitled
    "Undergraduate Research on Design Considerations for a GMD
    Mitigation Systems" (to be published in mid-late 2020), a
    planning-based GMD mitigation strategy was developed for large power
    systems. ESA is leveraged to programmatically place GIC blocking
    devices in test systems per the proposed algorithm, thus minimizing
    the effects of GMDs on the power grid.
-   ESA is used by an ongoing research project entitled "Real Time
    Monitoring Applications for the Power Grid under Geomagnetic
    Disturbances (GMD)": Recently, a real-world GMD monitoring system
    consisting of six magnetometers was deployed in Texas. The resulting
    magnetic field measurements are coupled with ground conductivity models
    to calculate real-time electric fields. These can then be fed to a grid
    model of Texas using ESA to enable calculation of real-time
    geomagnetically induced currents (GICs) for monitoring and
    visualization.
-   ESA is used by an ongoing research project entitled "Contingency
    Analysis Based on Graph Theory Concepts and Line Outage Distribution
    Factors (LODF)." In this project, ESA is leveraged to extract the
    topology of the power system model and obtain the LODF matrix.