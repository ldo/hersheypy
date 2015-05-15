#+
# Distutils script to install the hershey_font.py module. Invoke from
# the command line in this directory as follows:
#
#     python3 setup.py build
#     sudo python3 setup.py install
#
# Written by Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
#-

import distutils.core

distutils.core.setup \
  (
    name = "HersheyPy",
    version = "0.6",
    description = "Hershey fonts as user fonts with the Cairo graphics library",
    author = "Lawrence D'Oliveiro",
    author_email = "ldo@geek-central.gen.nz",
    url = "http://github.com/ldo/hersheypy",
    py_modules = ["hershey_font"],
  )
