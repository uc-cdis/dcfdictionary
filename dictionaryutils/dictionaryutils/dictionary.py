"""
This modules provide the same interface as gdcdictionary.gdcdictionary
It can be 'reinstialized' after it's called init() with another dictionary
For example, using
``gdcdictionary.gdcdictionary`` as the dictionary:

.. code-block:: python

    dictionary.init(gdcdictionary.gdcdictionary)
"""

import sys
from dictionaryutils import add_default_schema


# Get this module as a variable so its attributes can be set later.
this_module = sys.modules[__name__]

#: The data dictionary must implement these attributes.
required_attrs = ["resolvers", "schema"]

optional_attrs = ["settings"]

resolvers = None
schema = None
settings = None


def init(dictionary):
    """
    Initialize this file with the same attributes as ``dictionary``

    Args:
        dictionary (DataDictionary): a dictionary instance

    Return:
        None
    """
    for required_attr in required_attrs:
        try:
            # Basically do: this_module.required_attr = models.required_attr
            setattr(this_module, required_attr, getattr(dictionary, required_attr))
        except AttributeError:
            raise ValueError("given dictionary does not define " + required_attr)

    for optional_attr in optional_attrs:
        try:
            # Basically do: this_module.required_attr = models.required_attr
            setattr(this_module, optional_attr, getattr(dictionary, optional_attr))
        except AttributeError:
            pass


try:
    from gdcdictionary import gdcdictionary

    add_default_schema(gdcdictionary)
    init(gdcdictionary)
except:
    pass
