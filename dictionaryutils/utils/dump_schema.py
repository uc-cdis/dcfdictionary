"""
This script dumps all schema files in currently installed gdcdictionary
to one json schema to ./artifacts folder.

"""
import json
import os

from . import dump_schemas_from_dir

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
