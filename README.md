# Italian QA scripts for Firefox and Fennec

[![Spellcheck](https://github.com/flodolo/gecko-it-qa/actions/workflows/linter.yaml/badge.svg)](https://github.com/flodolo/gecko-it-qa/actions/workflows/linter.yaml)

To run the script:
- Copy `config/config.dist` as `config/config.ini` and configure the path to the clone of [l10n-central/it](https://hg.mozilla.org/l10n-central/it).
- Run`scripts/check_strings.sh` (it will create and activate a virtualenv with Python 3 and install the dependencies).

## Hunspell

If you’re using macOS, you need to install Hunspell and `jq` via `brew`

```
brew install hunspell jq
```

Be aware of the multiple issues existing ([one](https://github.com/blatinier/pyhunspell/issues/26), [two](https://github.com/blatinier/pyhunspell/issues/33)).

You might need to manually activate the virtualenv in `python-venv` and run these commands (Hunspell's version will change over time):

```
source python-venv/bin/activate
ln -s /usr/local/lib/libhunspell-1.7.a /usr/local/lib/libhunspell.a
ln -s /usr/local/Cellar/hunspell/1.7.0_2/lib/libhunspell-1.7.dylib /usr/local/Cellar/hunspell/1.7.0_2/lib/libhunspell.dylib
CFLAGS=$(pkg-config --cflags hunspell) LDFLAGS=$(pkg-config --libs hunspell) pip3 install hunspell
```

On macOS Monterey the files are located in `/opt/homebrew` instead of `/usr/local`.

```
ln -s /opt/homebrew/lib/libhunspell-1.7.a /opt/homebrew/lib/libhunspell.a
ln -s /opt/homebrew/Cellar/hunspell/1.7.0_2/lib/libhunspell-1.7.dylib /opt/homebrew/Cellar/hunspell/1.7.0_2/lib/libhunspell.dylib
```
