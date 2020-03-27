Directly interacting with PowerWorld via the Windows COM object can be
quite cumbersome. Data type inputs and outputs can be odd, returns come
back unlabeled, and you have to directly use pywin32 to interface with
SimAuto.

ESA makes all these tasks quick and easy, is well documented,
automagically translates data to the appropriate types, and uses Pandas
DataFrames and Series where possible. For some motivating examples,
please the the "Quick Start" section of this document.