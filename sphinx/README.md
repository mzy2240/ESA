# sphinx
This directory is for holding configuration files and documentation
related to [sphinx](http://www.sphinx-doc.org/en/master/index.html), 
which we'll use to auto-generate our documentation.

## Build the Documentation
Note you'll need to substitute for your own paths. These directions 
assume you have the repository cloned into `C:\Users\blthayer\git\ESA` and your virtual 
environment exists at `C:\Users\blthayer\git\ESA\vent`

### Activate Your Virtual Environment
Do this each time.

1. Open a command prompt.
2. Change directories to the repository: `cd C:\Users\blthayer\git\ESA`.
3. In your command prompt, run `venv\Scripts\activate.bat`.
4. Notice that your prompt is now prefixed with `(venv)`. 

### Install sphinx.
You should only need to do this once ever, unless you delete or modify
your virtual environment.

Simply run `pip install sphinx`.

### Build.
1. In your command prompt (which already has your virtual environment 
activated), change directories to `sphix`: `cd sphinx`.
2. Execute `make html`

## One Time Setup (DO NOT RUN THIS)
The following is just for recording what was done to 