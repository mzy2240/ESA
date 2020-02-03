# Tests
This directory should contain all code, PowerWorld cases, and data 
needed to fully test ESA. There should be a Python module named 
"test_<module>" for each ESA module. At present, ESA only has the 
SAW module.

## Cases
Use this directory to store PowerWorld cases.

## Data
Use this directory to store other data needed for testing.

## ltc_filter.aux
PowerWorld auxiliary file that defines a filter which obtains only LTC 
type transformers. Used for testing ProcessAuxFile, and is also a useful
template for defining filters in aux files.