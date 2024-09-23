#! /usr/bin/env bash

script_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";

cd $script_path/..

# Get sha of latest commit on the dictionary repo
latest=$(curl -s https://api.github.com/repos/flodolo/dizionario-it/git/refs/heads/v.next | jq ".object.sha")
local=$(cat dictionaries/latest.txt)

if [[ $local != $latest ]];
then
    echo "Downloading latest version of the dictionary"
    echo $latest > dictionaries/latest.txt
    curl -s -o dictionaries/it_IT.aff https://raw.githubusercontent.com/flodolo/dizionario-it/v.next/extension/dictionaries/it_IT.aff
    curl -s -o dictionaries/it_IT.dic https://raw.githubusercontent.com/flodolo/dizionario-it/v.next/extension/dictionaries/it_IT.dic
    curl -s -o dictionaries/mozilla_qa_specialized.dic https://raw.githubusercontent.com/flodolo/dizionario-it/v.next/mozilla_qa/mozilla_qa_specialized.dic
fi

# Keep the existing .venv (required for macOS)
uv venv --python 3.12 --allow-existing
source .venv/bin/activate
uv pip install -r scripts/requirements.txt
if [ -d .venv/chunspell ];
then
    export PYTHONPATH=".venv/chunspell"
fi
# Check extra dictionary
python $script_path/check_extra_dict.py

# Running main script
python -c "import nltk;nltk.download('stopwords');nltk.download('punkt');nltk.download('punkt_tab')"
python $script_path/check_strings.py $@
