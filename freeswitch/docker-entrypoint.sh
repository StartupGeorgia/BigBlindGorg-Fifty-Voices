#!/bin/bash
set -e

# Run FreeSWITCH as the freeswitch user
# -nonat  : Disable NAT traversal (running behind Docker network)
# -c      : Run in console mode (foreground, for Docker)
exec /usr/bin/freeswitch -nonat -c -u freeswitch -g freeswitch "$@"
