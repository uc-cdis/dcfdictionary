import json
from datetime import datetime
from dictionaryutils import dump_schemas_from_dir

with open('../gen3.nesi_' + datetime.today().strftime('%Y_%m_%d') + '.json', 'w') as f:
    json.dump(dump_schemas_from_dir('../gadrdictionary/schemas/'), f)
