"""
This script dumps all schema files in currently installed gdcdictionary
to one json schema to ./artifacts folder.

"""
import json
import os
from contextlib import contextmanager
import glob
import yaml
DICTCOMMIT="520a25999fd183f6c5b7ddef2980f3e839517da5"
DICTVERSION="0.2.1-9-g520a259"

# from . import dump_schemas_from_dir

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

def dump_schemas_from_dir(directory):
    """Dump schema as a json"""

    with visit_directory(directory):
        result = {path: load_yaml(path) for path in glob.glob("*.yaml")}
        if not "_settings.yaml" in result:
            result["_settings.yaml"] = {}
        result["_settings.yaml"]["_dict_commit"] = DICTCOMMIT
        result["_settings.yaml"]["_dict_version"] = DICTVERSION
        return result

dictionary_dir = os.path.join(os.path.dirname(__file__), '../../gdcdictionary')
artifact_dir = dictionary_dir + "/artifacts"
schema_dir = dictionary_dir + '/schemas'

try:
    os.mkdir(artifact_dir)
except OSError:
    pass


print("Dumping schemas from " + schema_dir + "...")
with open(os.path.abspath(os.path.join(artifact_dir, "schema.json")), "w") as f:
    json.dump(dump_schemas_from_dir(schema_dir), f)
print("Schema dumped to JSON in: " + artifact_dir)
