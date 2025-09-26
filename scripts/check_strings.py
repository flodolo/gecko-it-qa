#!/usr/bin/python3

from moz.l10n.formats import Format
from moz.l10n.message import serialize_message
from moz.l10n.model import Entry, Message, Resource
from moz.l10n.resource import parse_resource

import argparse
import configparser
import os
import json
import re
import sys
from html.parser import HTMLParser
from hunspell import Hunspell
import nltk
import string


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, data):
        self.fed.append(data)

    def get_data(self):
        return " ".join(self.fed)


class CheckStrings:
    def __init__(self, script_path, repository_path, verbose):
        """Initialize object"""

        # Set defaults
        self.supported_formats = [
            ".dtd",
            ".ftl",
            ".inc",
            ".ini",
            ".properties",
        ]
        self.file_list = []
        self.verbose = verbose
        self.strings = {}
        self.script_path = script_path
        self.exceptions_path = os.path.join(script_path, os.path.pardir, "exceptions")
        self.errors_path = os.path.join(script_path, os.path.pardir, "errors")
        self.repository_path = repository_path.rstrip(os.path.sep)

        # Set up spellcheckers
        # Load hunspell dictionaries
        dictionary_path = os.path.join(self.script_path, os.path.pardir, "dictionaries")
        self.spellchecker = Hunspell("it_IT", hunspell_data_dir=f"{dictionary_path}")
        self.spellchecker.add_dic(
            os.path.join(dictionary_path, "mozilla_qa_specialized.dic")
        )

        # Extract strings
        self.extractStrings()

        # Run checks
        self.checkQuotes()
        self.checkSpelling()
        self.printOutput()

    def parse_file(
        self,
        resource: Resource,
        storage: dict[str, str],
        filename: str,
        id_format: str,
    ) -> None:
        def get_entry_value(value: Message) -> str:
            entry_value = serialize_message(resource.format, value)
            if resource.format == Format.android:
                # In Android resources, unescape quotes
                entry_value = entry_value.replace('\\"', '"').replace("\\'", "'")

            return entry_value

        try:
            for section in resource.sections:
                for entry in section.entries:
                    if isinstance(entry, Entry):
                        if resource.format == Format.ini:
                            entry_id = ".".join(entry.id)
                        else:
                            entry_id = ".".join(section.id + entry.id)
                        string_id = f"{id_format}:{entry_id}"
                        if entry.properties:
                            # Store the value of an entry with attributes only
                            # if the value is not empty.
                            if not entry.value.is_empty():
                                storage[string_id] = get_entry_value(entry.value)
                            for attribute, attr_value in entry.properties.items():
                                attr_id = f"{string_id}.{attribute}"
                                storage[attr_id] = get_entry_value(attr_value)
                        else:
                            storage[string_id] = get_entry_value(entry.value)
        except Exception as e:
            print(f"Error parsing file: {filename}")
            print(e)

    def extractStrings(self):
        """Extract strings in files"""

        # Create a list of files to analyze
        self.extractFileList()

        for file_path in self.file_list:
            file_name = self.getRelativePath(file_path)
            if file_name.endswith("region.properties"):
                continue
            try:
                resource = parse_resource(file_path)
                self.parse_file(resource, self.strings, file_name, f"{file_name}")
            except Exception as e:
                print(f"Error parsing resource: {file_name}")
                print(e)

    def extractFileList(self):
        """Extract the list of supported files"""

        excluded_folders = [
            "calendar",
            "chat",
            "editor",
            "extensions",
            "mail",
            "other-licenses",
            "suite",
        ]

        for root, dirs, files in os.walk(self.repository_path, followlinks=True):
            # Ignore excluded folders
            if root == self.repository_path:
                dirs[:] = [d for d in dirs if d not in excluded_folders]

            for f in files:
                for supported_format in self.supported_formats:
                    if f.endswith(supported_format):
                        self.file_list.append(os.path.join(root, f))
        self.file_list.sort()

    def getRelativePath(self, file_name):
        """Get the relative path of a filename"""

        relative_path = file_name[len(self.repository_path) + 1 :]

        return relative_path

    def strip_tags(self, text):
        html_stripper = MLStripper()
        html_stripper.feed(text)

        return html_stripper.get_data()

    def checkQuotes(self):
        """Check quotes"""

        # Load exceptions
        exceptions = []
        exceptions_filename = os.path.join(self.exceptions_path, "quotes.json")
        with open(exceptions_filename, "r") as f:
            exceptions = json.load(f)
        # Keep track of the exceptions used to clean up the file
        matched_exceptions = []

        ftl_functions = [
            # Parameterized terms
            re.compile(
                r'(?<!\{)\{\s*(?:-[A-Za-z0-9._-]+)(?:[\[(]?[A-Za-z0-9_\-, :"]+[\])])*\s*\}'
            ),
            # DATETIME() and NUMBER() function
            re.compile(r"{\s*(?:DATETIME|NUMBER)(.*)\s*}"),
            # Special characters and empty string
            re.compile(r'{\s*"(?:[\s{}]{0,1})"\s*}'),
        ]
        straight_quotes = re.compile(r'\'|"|‘')

        all_errors = []
        for message_id, message in self.strings.items():
            if message_id in exceptions:
                matched_exceptions.append(message_id)
                continue
            if message and straight_quotes.findall(message):
                # Remove HTML tags
                cleaned_msg = self.strip_tags(message)
                # Remove various Fluent syntax that requires double quotes
                for f in ftl_functions:
                    cleaned_msg = f.sub("", cleaned_msg)

                # Continue if message is now clean
                if not straight_quotes.findall(cleaned_msg):
                    continue

                all_errors.append(message_id)
                if self.verbose:
                    print(f"{message_id}: wrong quotes\n{message}")

        with open(
            os.path.join(self.errors_path, "quotes.json"), "w", encoding="utf8"
        ) as f:
            json.dump(all_errors, f, indent=2, sort_keys=True, ensure_ascii=False)

        if matched_exceptions != exceptions:
            with open(exceptions_filename, "w") as f:
                json.dump(
                    matched_exceptions, f, indent=2, sort_keys=True, ensure_ascii=False
                )

        self.quote_errors = all_errors

    def excludeToken(self, token):
        """Exclude specific tokens after spellcheck"""

        # Ignore acronyms (all uppercase) and token made up only by
        # unicode characters, or punctuation
        if token == token.upper():
            return True

        # Ignore domains in strings
        if any(k in token for k in ["example.com", "mozilla.org"]):
            return True

        # Ignore DevTools accesskeys
        if any(k in token for k in ["Alt+", "Cmd+", "Ctrl+"]):
            return True

        return False

    def checkSpelling(self):
        """Check for spelling mistakes"""

        # Load exceptions and exclusions
        exceptions_filename = os.path.join(self.exceptions_path, "spelling.json")
        with open(exceptions_filename, "r") as f:
            exceptions = json.load(f)

        with open(
            os.path.join(self.exceptions_path, "spelling_exclusions.json"), "r"
        ) as f:
            exclusions = json.load(f)
            excluded_files = tuple(exclusions["excluded_files"])
            excluded_strings = exclusions["excluded_strings"]

        punctuation = list(string.punctuation)
        stop_words = nltk.corpus.stopwords.words("italian")

        placeables = {
            ".ftl": [
                # Message references, variables, terms
                re.compile(
                    r'(?<!\{)\{\s*([\$|-]?[A-Za-z0-9._-]+)(?:[\[(]?[A-Za-z0-9_\-, :"]+[\])])*\s*\}'
                ),
                # DATETIME()
                re.compile(r"\{\s*DATETIME\(.*\)\s*\}"),
                # Variants syntax
                re.compile(r"\{?\s*\$[a-zA-Z]+\s*->"),
                # Variants names
                re.compile(r"^\s*\*?\[[a-zA-Z0-9_-]*\]"),
            ],
            ".properties": [
                # printf
                re.compile(r"(%(?:[0-9]+\$){0,1}(?:[0-9].){0,1}([sS]))"),
                # webl10n in pdf.js
                re.compile(
                    r"\{\[\s?plural\([a-zA-Z]+\)\s?\]\}|\{{1,2}\s?[a-zA-Z_-]+\s?\}{1,2}"
                ),
            ],
            ".dtd": [
                re.compile(r"&([A-Za-z0-9\.]+);"),
            ],
            ".ini": [
                re.compile(r"%[A-Z_-]+%"),
            ],
        }

        all_errors = {}
        total_errors = 0
        misspelled_words = {}
        ignored_strings = []
        for message_id, message in self.strings.items():
            filename, extension = os.path.splitext(message_id.split(":")[0])

            # Ignore excluded files and strings
            if message_id.split(":")[0].startswith(excluded_files):
                continue
            if message_id in excluded_strings:
                if message_id not in ignored_strings:
                    ignored_strings.append(message_id)
                continue

            # Ignore style attributes in fluent messages
            if extension == ".ftl" and message_id.endswith(".style"):
                continue

            # Ignore empty messages
            if not message:
                continue
            if message == '{""}' or message == '{ "" }':
                continue

            # Strip HTML
            cleaned_message = self.strip_tags(message)

            # Remove ellipsis and newlines
            cleaned_message = cleaned_message.replace("…", "")
            cleaned_message = cleaned_message.replace(r"\n", " ")

            # Replace other characters to reduce errors
            cleaned_message = cleaned_message.replace("/", " ")
            cleaned_message = cleaned_message.replace("=", " = ")

            # Remove placeables from FTL and properties strings
            if extension in placeables:
                try:
                    # Check placeables line by line
                    lines = str(cleaned_message).splitlines()
                    for i in range(len(lines)):
                        for pattern in placeables[extension]:
                            lines[i] = pattern.sub(" ", lines[i])
                    cleaned_message = "\n".join(lines)
                except Exception as e:
                    print("Error removing placeables")
                    print(message_id)
                    print(e)

            # Tokenize sentence
            tokens = nltk.word_tokenize(cleaned_message)
            errors = []
            for i, token in enumerate(tokens):
                if message_id in exceptions and token in exceptions[message_id]:
                    if message_id not in ignored_strings:
                        ignored_strings.append(message_id)
                    continue

                """
                    Clean up tokens. Not doing it before the for cycle, because
                    I need to be able to access the full sentence with indexes
                    later on.
                """
                if token in punctuation:
                    continue

                if token.lower() in stop_words:
                    continue

                if not self.spellchecker.spell(token):
                    # It's misspelled, but I still need to remove a few outliers
                    if self.excludeToken(token):
                        continue

                    """
                      Check if the next token is an apostrophe. If it is,
                      check spelling together with the two next tokens.
                      This allows to ignore things like "cos’altro".
                    """
                    if i + 3 <= len(tokens) and tokens[i + 1] == "’":
                        group = "".join(tokens[i : i + 3])
                        if self.spellchecker.spell(group):
                            continue

                    """
                      It might be a brand with two words, e.g. Common Voice.
                      Need to look in both direction.
                    """
                    if i + 2 <= len(tokens):
                        group = " ".join(tokens[i : i + 2])
                        if self.spellchecker.spell(group):
                            continue
                    if i >= 1:
                        group = " ".join(tokens[i - 1 : i + 1])
                        if self.spellchecker.spell(group):
                            continue

                    errors.append(token)
                    if token not in misspelled_words:
                        misspelled_words[token] = 1
                    else:
                        misspelled_words[token] += 1

            if errors:
                total_errors += len(errors)
                if self.verbose:
                    print(f"{message_id}: spelling error")
                    for e in errors:
                        print(f"Original: {message}")
                        print(f"Cleaned: {cleaned_message}")
                        print(f"  {e}")
                        print(nltk.word_tokenize(message))
                        print(nltk.word_tokenize(cleaned_message))
                all_errors[message_id] = errors

        with open(
            os.path.join(self.errors_path, "spelling.json"), "w", encoding="utf8"
        ) as f:
            json.dump(all_errors, f, indent=2, sort_keys=True, ensure_ascii=False)

        # Remove things that are not errors from the list of exceptions.
        for message_id in list(exceptions.keys()):
            if message_id not in self.strings:
                # String does not exist anymore
                del exceptions[message_id]
                continue

            if message_id not in ignored_strings:
                # There was no need to ignore the string during check, which
                # means errors are gone.
                del exceptions[message_id]
                continue

            if (
                message_id in all_errors
                and all_errors[message_id] != exceptions[message_id]
            ):
                # Assume the tokens in exceptions need to be updated
                exceptions[message_id] = all_errors[message_id]

        # Write back updated exceptions file
        with open(exceptions_filename, "w", encoding="utf8") as f:
            json.dump(exceptions, f, indent=2, sort_keys=True, ensure_ascii=False)

        if total_errors:
            print(f"Total number of strings with errors: {len(all_errors)}")
            print(f"Total number of errors: {total_errors}")

        # Display misspelled words and their count, if above 4
        threshold = 4
        above_threshold = []
        for k, v in sorted(
            misspelled_words.items(), key=lambda item: item[1], reverse=True
        ):
            if v >= threshold:
                above_threshold.append(f"{k}: {v}")
        if above_threshold:
            print(f"Errors and number of occurrences (only above {threshold}):")
            print("\n".join(above_threshold))

        self.spelling_errors = total_errors

    def printOutput(self):
        if self.spelling_errors or self.quote_errors:
            for type in ["quotes", "spelling"]:
                filename = os.path.join(self.errors_path, f"{type}.json")
                with open(filename, "r") as f:
                    json_data = json.load(f)
                    if json_data:
                        print(f"Errors for {type}:")
                        print(json.dumps(json_data, indent=2))
            sys.exit(1)
        else:
            print("No errors found.")


def main():
    script_path = os.path.abspath(os.path.dirname(__file__))

    config_file = os.path.join(script_path, os.pardir, "config", "config.ini")
    if not os.path.isfile(config_file):
        sys.exit("Missing configuration file.")
    config = configparser.ConfigParser()
    config.read(config_file)
    repo_path = config["default"]["repo_path"]
    if not os.path.isdir(repo_path):
        sys.exit("Path to repository in config file is not a directory.")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose output (e.g. tokens"
    )
    args = parser.parse_args()

    CheckStrings(script_path, repo_path, args.verbose)


if __name__ == "__main__":
    main()
