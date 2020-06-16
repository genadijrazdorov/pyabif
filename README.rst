pyABIF
======

A Python ABIF (Applied Biosystems Genetic Analysis Data File Format) reader.

* no external dependencies
* minimal pythonification

ABIF is a directory of items, where every item is identified by unique *name*
and *number*.

pyABIF is a class with attributes corresponding to name/number items::

    >>> from pyabif import pyABIF

    >>> abif = pyABIF('abif.fsa')
    >>> abif.User1
    joe

    >>> abif.DATA1


pyabif can be used as a console script:

.. code-block:: console

    $ pyabif abif.fsa
    Converted to txt

    $ ls abif
    abif.fsa
    abif.fsa.csv.zip
