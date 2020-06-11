Current Directions
------------------
Use the `paper preview service <https://whedon.theoj.org/>`__ from JOSS to compile the paper.

Files:
^^^^^^

- paper.bib: BibTex file for paper references.
- paper.md: The actual paper, in MarkDown format.
- paper.pdf: Current compiled .pdf version of the paper.
- README.rst: This file.

Old Directions
--------------
Please note the directions below are no longer applicable. JOSS does not
allow for modification as mentioned in `this comment <https://github.com/openjournals/joss-reviews/issues/2289#issuecomment-642588057>`__.

The original latex.template is from `the whedon
repository <https://github.com/openjournals/whedon/tree/master/resources
/joss>`__.

To compile the paper in Windows, you will need to install the Pandoc
and the MiKTex. When you are installing the MiKTex, make sure to check
the option to "install the packages on-the-fly".

After the installation, restart your computer.

When the Pandoc and the MiKTex are ready, you can now compile the paper
using the command:

.. code:: bat

    pandoc --filter pandoc-citeproc --bibliography paper.bib paper.md --template latex.template -o paper.pdf --pdf-engine=xelatex

One thing worth to note is, when we submit the paper to JOSS, we need to
let them know that we have our own custom latex.template file for
compiling. Additionally, before JOSS submittal the commented-out line
related to the logo needs to be "un-commented." The line looks like:

.. code:: latex

    %\fancyhead[L]{\hspace{-0.75cm}\includegraphics[width=5.5cm]{$logo_path$}}
