CMake.py [![Unlicensed work](https://raw.githubusercontent.com/unlicense/unlicense.org/master/static/favicon.png)](https://unlicense.org/)
===============
[![GitLab Build Status](https://gitlab.com/KOLANICH/CMake.py/badges/master/pipeline.svg)](https://gitlab.com/KOLANICH/CMake.py/pipelines/master/latest)
![GitLab Coverage](https://gitlab.com/KOLANICH/CMake.py/badges/master/coverage.svg)
[![Coveralls Coverage](https://img.shields.io/coveralls/KOLANICH/CMake.py.svg)](https://coveralls.io/r/KOLANICH/CMake.py)
[![Libraries.io Status](https://img.shields.io/librariesio/github/KOLANICH/CMake.py.svg)](https://libraries.io/github/KOLANICH/CMake.py)
[![Code style: antiflash](https://img.shields.io/badge/code%20style-antiflash-FFF.svg)](https://github.com/KOLANICH-tools/antiflash.py)

This is just a dumb implementation of CMake interpreter. Probably incorrect, but works fine enough for my purposes. The purpose of it is to parse CMake scripts used to configure CPack to extract from them info about how packaging should be done.

Requirements
------------
* [`Python >=3.4`](https://www.python.org/downloads/). [`Python 2` is dead, stop raping its corpse.](https://python3statement.org/) Use `2to3` with manual postprocessing to migrate incompatible code to `3`. It shouldn't take so much time. For unit-testing you need Python 3.6+ or PyPy3 because their `dict` is ordered and deterministic. Python 3 is also semi-dead, 3.7 is the last minor release in 3.
* [`cmake-ast`](https://github.com/polysquare/cmake-ast) ![Licence](https://img.shields.io/github/license/polysquare/cmake-ast.svg) [![PyPi Status](https://img.shields.io/pypi/v/cmake-ast.svg)](https://pypi.python.org/pypi/cmake-ast) [![TravisCI Build Status](https://travis-ci.org/polysquare/cmake-ast.svg?branch=master)](https://travis-ci.org/polysquare/cmake-ast) [![Libraries.io Status](https://img.shields.io/librariesio/github/polysquare/cmake-ast.svg)](https://libraries.io/github/polysquare/cmake-ast)
