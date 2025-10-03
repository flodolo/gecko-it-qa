#!/usr/bin/python3

import os

from hunspell import Hunspell


def main():
    script_path = os.path.abspath(os.path.dirname(__file__))

    # Load Hunspell dictionaries
    dictionary_path = os.path.join(script_path, os.path.pardir, "dictionaries")
    spellchecker = Hunspell("it_IT", hunspell_data_dir=f"{dictionary_path}")

    # Load the extra dictionary as a normal file
    extra_dict = os.path.join(dictionary_path, "mozilla_qa_specialized.dic")
    with open(extra_dict) as f:
        terms = []
        for i, line in enumerate(f):
            # Strip new line character
            line = line.rstrip()

            # Ignore the number of items at the beginning
            if i == 0 and line.isdigit():
                continue

            # Ignore comments and empty lines
            if line == "" or line.startswith("/"):
                continue

            terms.append(line.split("/")[0])

    print(f"Additional terms loaded: {len(terms)}")

    # Check spelling for each term. If it passes, it should be removed,
    # because it's already included in the main dictionary.
    terms_to_remove = []
    for term in terms:
        if spellchecker.spell(term):
            terms_to_remove.append(term)

    if terms_to_remove:
        print("Terms to remove:")
        print("\n".join(terms_to_remove))


if __name__ == "__main__":
    main()
