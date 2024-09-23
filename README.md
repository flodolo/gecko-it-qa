# Italian QA scripts for Firefox and Fennec

[![Spellcheck](https://github.com/flodolo/gecko-it-qa/actions/workflows/linter.yaml/badge.svg)](https://github.com/flodolo/gecko-it-qa/actions/workflows/linter.yaml)

To run the script:
- Copy `config/config.dist` as `config/config.ini` and configure the path to the clone of [l10n-central/it](https://hg.mozilla.org/l10n-central/it).
- Run`scripts/check_strings.sh` (it will create and activate a virtualenv and install the dependencies).

## Hunspell

`chunspell` will not work out of the box on macOS, returning an error:

```
Traceback (most recent call last):
  File "scripts/check_strings.py", line 6, in <module>
    from hunspell import Hunspell
  File ".venv/lib/python3.12/site-packages/hunspell/__init__.py", line 4, in <module>
    from .hunspell import HunspellWrap as Hunspell, HunspellFilePathError  # noqa: F401
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ImportError: dlopen(.venv/lib/python3.12/site-packages/hunspell/hunspell.cpython-312-darwin.so, 0x0002): symbol not found in flat namespace '__ZN8Hunspell14add_with_affixERKNSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEES8_'
````

First, you need to install Hunspell and `jq` via `brew`:

```
brew install hunspell jq
```

Then you will need to manually activate the virtualenv in `.venv` and run these commands to install `chunspell` from the repository (note that the version of Hunspell might change, these commands work for `1.7.2`):

```
source .venv/bin/activate
ln -s /opt/homebrew/Cellar/hunspell/1.7.2/lib/libhunspell-1.7.dylib /opt/homebrew/Cellar/hunspell/1.7.2/lib/libhunspell.dylib
ln -s /opt/homebrew/Cellar/hunspell/1.7.2/lib/libhunspell-1.7.a /opt/homebrew/Cellar/hunspell/1.7.2/lib/libhunspell.a
uv pip install setuptools
cd .venv && git clone https://github.com/cdhigh/chunspell --depth 1
cd chunspell && python setup.py install
```

You can test that the library is available by running `python -c "from hunspell import Hunspell"`. If the command runs without errors, deactivate the virtual environment with `deactivate` and try running `scripts/check_strings.sh` directly.
