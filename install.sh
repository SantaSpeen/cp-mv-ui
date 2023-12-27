#!/bin/sh

command_exists python3 || {
      fmt_error "python3 is not installed"
    exit 1
}
fmt_error() {
  printf '%sError: %s%s\n' "${FMT_BOLD}${FMT_RED}" "$*" "$FMT_RESET" >&2
}

USER=${USER:-$(id -u -n)}
HOME="${HOME:-$(getent passwd $USER 2>/dev/null | cut -d: -f6)}"
# macOS does not have getent, but this works even if $HOME is unset
HOME="${HOME:-$(eval echo ~$USER)}"

command_exists() {
  command -v "$@" >/dev/null 2>&1
}

# Check python

# curl file
curl https://raw.githubusercontent.com/SantaSpeen/cp-mv-ui/master/src/main.py -o "$HOME/cp-mv-ui.py"

# set symbolic link
ln -s "$HOME/cp-mv-ui.py" /usr/bin/cpu
ln -s "$HOME/cp-mv-ui.py" /usr/bin/mvu

echo Ready to use: mvu cpg
