#! /usr/bin/env bash

script_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
root_path="${script_path}/.."

cd $root_path

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

function setupVirtualEnv() {
    # Create virtualenv folder if missing
    if [ ! -d python-venv ]
    then
        echo "Setting up new virtualenv..."
        python3 -m venv python-venv || exit 1
    fi

    # Install or update dependencies
    source python-venv/bin/activate || exit 1
    pip install --upgrade --quiet pip
    pip install -r $script_path/requirements.txt --upgrade --quiet
    deactivate
}

# Setup virtualenv
setupVirtualEnv

# Activate virtualenv
source $root_path/python-venv/bin/activate || exit 1

# Check extra dictionary
python $script_path/check_extra_dict.py

# Running main script
python -c "import nltk;nltk.download('stopwords');nltk.download('punkt')"
python $script_path/check_strings.py $@
