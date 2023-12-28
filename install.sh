#!/bin/sh

setup_color() {
  if ! [ -t 1 ]; then
    FMT_RED=""
    FMT_BOLD=""
    FMT_RESET=""
    return
  fi

  FMT_RED=$(printf '\033[31m')
  FMT_BOLD=$(printf '\033[1m')
  FMT_RESET=$(printf '\033[0m')
}

setup_color

user_can_sudo() {
  command_exists sudo || return 1
  case "$PREFIX" in
  *com.termux*) return 1 ;;
  esac
  # shellcheck disable=SC1007
  ! LANG= sudo -n -v 2>&1 | grep -q "may not run sudo"
}

command_exists() {
  command -v "$@" >/dev/null 2>&1
}

fmt_error() {
  printf '%sError: %s%s\n' "${FMT_BOLD}${FMT_RED}" "$*" "$FMT_RESET" >&2
}

USER=${USER:-$(id -u -n)}
HOME="${HOME:-$(getent passwd $USER 2>/dev/null | cut -d: -f6)}"
# macOS does not have getent, but this works even if $HOME is unset
HOME="${HOME:-$(eval echo ~$USER)}"


# Check python
command_exists python3 || {
      fmt_error "python3 is not installed"
    exit 1
}

# curl file
curl https://raw.githubusercontent.com/SantaSpeen/cp-mv-ui/master/src/main.py -o "$HOME/.cp-mv-ui.py"
chmod +x "$HOME/.cp-mv-ui.py"

# set symbolic link
if user_can_sudo; then
  sudo ln -s "$HOME/.cp-mv-ui.py" /usr/local/bin/cpu
  sudo ln -s "$HOME/.cp-mv-ui.py" /usr/local/bin/mvu
else
  ln -s "$HOME/.cp-mv-ui.py" /usr/local/bin/cpu
  ln -s "$HOME/.cp-mv-ui.py" /usr/local/bin/mvu
fi

echo Ready to use: mvu cpu

