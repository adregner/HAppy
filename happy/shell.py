# HAppy

import sys
import logging
from optparse import OptionParser

logger = logging.getLogger(__name__)

SUB_COMMANDS = [
        'daemon',
        'takeover',
        'release',
        'status',
        ]

def parse_args(argv):

    if len(argv) > 0 and argv[0] in SUB_COMMANDS:
        subcommand = argv.pop(0)
    else:
        subcommand = 'daemon'

    parser = OptionParser()

    parser.add_option('-f', '--foreground', dest='foreground', default=False, action='store_true',
            help = "Don't daemonize by forking into the background.")
    parser.add_option('-l', '--level', dest='log_level', default='warn',
            help = "Set logging level (debug, info, warn, error) Default: warn")
    parser.add_option('-c', '--config', dest='config', default='/etc/happy.conf',
            help = "Path to HAppy configuration file. Default: /etc/happy.conf")

    options, args = parser.parse_args()
    options.subcommand = subcommand

    return options

def main():
    options = parse_args(sys.argv[1:])

    import happy
    prog = happy.HAppy(options)
    getattr(prog, options.subcommand)()

if __name__ == '__main__':
    main()
