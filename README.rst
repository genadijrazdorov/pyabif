pyABIF
======

A Python ABIF (Applied Biosystems Genetic Analysis Data File Format) reader,
based on 07/2006 specification.

ABIF is a directory of items, where every item is identified by unique *tag*
and *number*.

Interface
---------

|ABIF| is a class with attributes corresponding to name/number items::

    >>> from pyabif import ABIF

    >>> abif = ABIF('abif.fsa')
    >>> abif.User1
    joe

    >>> abif.DATA1
    ...

..., or for 1 numbered items this also works::

    >>> abif.DATA
    ...

For items described in 07/2006 specification, there is available description::

    >>> help(ABIF.DATA)
    Help on property:

        Channel 1 raw data

..., or::

    >>> abif.describe('DATA')
    'Channel 1 raw data'


Console script
--------------

pyABIF can be used as a console script:

.. code-block:: console

    $ pyabif abif.fsa
    Converted to txt

    $ ls abif
    abif.fsa
    abif.fsa.csv.zip

For usage help:

.. code-block:: console

    $ pyabif --help
    Usage: pyabif [OPTIONS] [PATTERNS]...

    Converts PATTERNS from ABIF to txt format

    PATTERNS are glob filenames of ABIF files to convert.

    Options:
    -f, --force                     Force conversion even if resulting file
                                    already exists  [default: False]

    -b, --batch                     Combine data files in batches  [default:
                                    False]

    -d, --digits INTEGER            Number of digits for migration times
                                    [default: 3]

    -u, --migration-units [seconds|minutes]
                                    Migration units  [default: minutes]
    --help                          Show this message and exit.


.. |ABIF| replace:: ``ABIF``
