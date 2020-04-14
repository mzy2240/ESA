The original latex.template and the logo.png are from `Whedon's
repository <https://github.com/openjournals/whedon/tree/master/resources
/joss>`__.

To compile the paper in Windows, you will need to install the Pandoc
and the MikTex. When you are installing the MikTex, make sure to check
the option to "install the packages on-the-fly".

After the installation, restart your computer.

When the Pandoc and the MikTex are ready, you can now compile the paper
using the script ``pandoc --filter pandoc-citeproc --bibliography
paper.bib paper.md --template latex.template -o paper.pdf
--pdf-engine=xelatex``.

One thing worth to note is, when we submit the paper to JOSS, we need to
let them know that we have our own custom latex.template file for
compiling.

