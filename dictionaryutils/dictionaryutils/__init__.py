from .json_load import json_loads_byteified
from .errors import DictionaryError
from .version_data import DICTVERSION, DICTCOMMIT

from copy import deepcopy
from collections import namedtuple
from contextlib import contextmanager
from jsonschema import RefResolver

import glob
import logging
import requests
import os
import yaml

MOD_DIR = os.path.abspath(os.path.dirname(__file__))

ResolverPair = namedtuple("ResolverPair", ["resolver", "source"])


@contextmanager
def visit_directory(path):
    """Perform contained actions with current working directory at
    :param:``path``.  Always return to previous directory when done.

    """

    cdir = os.getcwd()
    try:
        os.chdir(path)
        yield os.getcwd()
    finally:
        os.chdir(cdir)


def load_yaml(name):
    """Return contents of yaml file as dict"""
    with open(name, "r") as f:
        return yaml.safe_load(f)


def add_default_schema(dictionary):
    """
    add default schema nodes to a dictionary
    """
    yamls, resolvers = load_schemas_from_dir(os.path.join(MOD_DIR, "schemas"))
    dictionary.resolvers.update(resolvers)

    schemas = {
        schema["id"]: dictionary.resolve_schema(schema, deepcopy(schema))
        for path, schema in yamls.iteritems()
        if path not in dictionary.exclude
    }
    dictionary.schema.update(schemas)


def load_schemas_from_url(url, logger, schemas=None, resolvers=None):
    error_msg = "Fail to get schema from {}".format(url)
    try:
        r = requests.get(url)
    except Exception as e:
        error_msg = "{}: {}".format(error_msg, e.message)
        logger.exception(error_msg)
        raise DictionaryError(error_msg)
    if r.status_code != 200:
        error_msg = "{}: {}".format(error_msg, r.text)
        logger.error(error_msg)
        raise DictionaryError(error_msg)
    if schemas is None:
        schemas = {}
    if resolvers is None:
        resolvers = {}
    response = json_loads_byteified(r.text)
    for key, schema in response.iteritems():
        schemas[key] = schema
        resolver = RefResolver("{}#".format(key), schema)
        resolvers[key] = ResolverPair(resolver, schema)

    return schemas, resolvers


def dump_schemas_from_dir(directory):
    """Dump schema as a json"""

    with visit_directory(directory):
        result = {path: load_yaml(path) for path in glob.glob("*.yaml")}
        if not "_settings.yaml" in result:
            result["_settings.yaml"] = {}
        result["_settings.yaml"]["_dict_commit"] = DICTCOMMIT
        result["_settings.yaml"]["_dict_version"] = DICTVERSION
        return result


def load_schemas_from_dir(directory, schemas=None, resolvers=None):
    """Returns all yamls and resolvers of those yamls from dir"""

    if schemas is None:
        schemas = {}
    if resolvers is None:
        resolvers = {}

    with visit_directory(directory):
        for path in glob.glob("*.yaml"):
            schema = load_yaml(path)
            schemas[path] = schema
            resolver = RefResolver("{}#".format(path), schema)
            resolvers[path] = ResolverPair(resolver, schema)

    return schemas, resolvers


class DataDictionary(object):

    _metaschema_path = "metaschema.yaml"
    _definitions_paths = ["_definitions.yaml", "_terms.yaml"]
    settings_path = "_settings.yaml"

    logger = logging.getLogger("DataDictionary")

    def __init__(
        self,
        lazy=False,
        root_dir=None,
        definitions_paths=None,
        metaschema_path=None,
        url=None,
    ):
        """Creates a new dictionary instance.

        :param root_dir: The directory to find schemas
        :param metaschema_path: The metaschema to validate schemas with
        :param definitions_paths: Paths to resolve $ref to
        :param lazy: If true, wait to load dictionary
        :param url:Load data from an url

        """

        self.root_dir = root_dir or os.path.join(MOD_DIR, "schemas")
        self.metaschema_path = metaschema_path or self._metaschema_path
        self.definitions_paths = definitions_paths or self._definitions_paths
        self.exclude = (
            [self.metaschema_path] + self.definitions_paths + [self.settings_path]
        )
        self.schema = dict()
        self.resolvers = dict()

        self.metaschema = load_yaml(
            os.path.join(MOD_DIR, "schemas", self.metaschema_path)
        )

        if not lazy:
            self.load_data(directory=self.root_dir, url=url)

    def load_data(self, directory=None, url=None):
        """Load and reslove all schemas from directory or url"""
        yamls, resolvers = load_schemas_from_dir(os.path.join(MOD_DIR, "schemas"))

        if url is None:
            yamls, resolvers = load_schemas_from_dir(
                directory, schemas=yamls, resolvers=resolvers
            )
        else:
            yamls, resolvers = load_schemas_from_url(
                url, self.logger, schemas=yamls, resolvers=resolvers
            )

        self.settings = yamls.get(self.settings_path) or {}
        self.resolvers.update(resolvers)

        schemas = {
            schema["id"]: self.resolve_schema(schema, deepcopy(schema))
            for path, schema in yamls.iteritems()
            if path not in self.exclude
        }
        self.schema.update(schemas)

    def resolve_reference(self, value, root):
        """Resolves a reference.

        :param value: The actual reference, e.g. ``_yaml.yaml#/def``
        :param root:
            The containing root of :param:`value`. This needs to be
            passed in order to resolve self-referential $refs,
            e.g. ``#/def``.
        :returns: JSON Schema pointed to by :param:`value`

        """
        base, ref = value.split("#", 1)

        if base:
            resolver, new_root = self.resolvers[base]
            referrer, resolution = resolver.resolve(value)
            self.resolve_schema(resolution, new_root)
        else:
            resolver = RefResolver("#", root)
            referrer, resolution = resolver.resolve(value)

        return resolution

    def resolve_schema(self, obj, root):
        """Recursively resolves all references in a schema against
        ``self.resolvers``.

        :param obj: The object to recursively resolve.
        :param root:
            The containing root of :param:`value`. This needs to be
            passed in order to resolve self-referential $refs,
            e.g. ``#/def``.
        :returns: A denormalized/resolved version of :param:`obj`.

        """
        refkey = "$ref"
        if isinstance(obj, dict):
            all_refkeys = [k for k in obj.keys() if k.startswith(refkey)]
            for key in all_refkeys:
                val = obj.pop(key)
                obj.update(self.resolve_reference(val, root))
            return {k: self.resolve_schema(v, root) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.resolve_schema(item, root) for item in obj]
        else:
            return obj
