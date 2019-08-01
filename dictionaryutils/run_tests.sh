#!/bin/bash
set -e

# Test if running under a dictionary/ folder
if [[ -d ../.git && -d ../gdcdictionary ]]; then
  (
    cd ..
    DICTCOMMIT=`git rev-parse HEAD` && echo "DICTCOMMIT=\"${DICTCOMMIT}\"" >dictionaryutils/dictionaryutils/version_data.py
    DICTVERSION=`git describe --always --tags` && echo "DICTVERSION=\"${DICTVERSION}\"" >>dictionaryutils/dictionaryutils/version_data.py
  )
fi

pip install -r dev-requirements.txt
# always use this version of dictionaryutils...
pip uninstall -y dictionaryutils
python setup.py install --force
nosetests -s -v
python bin/dump_schema.py
set +e
