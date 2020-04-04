ESA is useful for a wide range of audiences, including:

*   Industry practitioners (e.g. power system planners, energy traders, etc.)
*   Power system researchers
*   Researchers from other domains who wish to perform co-simulation
    with power system models
*   University students and faculty
*   Power system enthusiasts

ESA users should be proficient in Python, and it's recommended that
users get familiar with Numpy and Pandas, as ESA makes significant use
of these packages. ESA users do not need to have any knowledge
whatsoever related to how the Windows COM API works, nor do users need
to be familiar with PyWin32.

Ultimately, ESA is a tool for interacting with PowerWorld Simulator -
thus, users should have some familiarity with Simulator. Users do not
need to directly understand how to use SimAuto, as ESA abstracts those
details away. Advanced users will have a solid understanding of
PowerWorld variables and object types, and will make extensive use of
the ``RunScriptCommand`` method to enable the execution of PowerWorld
functions previously only accessible via `"Auxiliary Files"
<https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__.