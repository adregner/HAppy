# HAppy

import os
import sys
import re
import signal
import socket
import logging
import logging.handlers
import threading
import ConfigParser
from time import sleep, time

from happy.resources import *

DEFAULT_LOG = 'syslog'
DEFAULT_LEVEL = 'warn'
DEFAULT_RESOURCES = 'haresources:/etc/ha.d/haresources'
DEFAULT_CONFIG = '/etc/happy.conf'
DEFAULT_PORT = 694
DEFAULT_BIND_ADDR = "0.0.0.0"
DEFAULT_DEAD_TIME = 8

BUFFER_SIZE = 1024

logger = logging.getLogger(__name__)

class HAppy(object):

    def __init__(self, options = None):
        if options is not None:
            self.log_level = options.log_level
            self.daemonize = not options.foreground
            self.config = options.config
        else:
            self.config = 'happy.conf'
            self.daemonize = False
            self.log_level = 'debug'

        self._catch_signals()
        self._parse_config()
        self._resources = None
        self._uname = None

        self.owner = {}
        self.dead_time = self.get_config('dead_time', DEFAULT_DEAD_TIME)

    def daemon(self):
        if self.daemonize and os.fork() > 0:
            sys.exit()

        partner = self.get_config('partner', None)
        port = self.get_config('udp_port', DEFAULT_PORT)

        if partner is None:
            logger.error("No partner configured, exiting!")
            raise RuntimeError("No partner configured!")

        logger.info("Peering with {0}:{1}".format(partner, port))
        self.partner_pair = (partner, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((DEFAULT_BIND_ADDR, port))

        self.last_seen = 0

        class Listener(threading.Thread):
            def __init__(self, daemon, **kwargs):
                super(Listener, self).__init__(**kwargs)
                self.setName("HAppy-Listener")
                self.setDaemon(True)
                self.daemon = daemon

            def run(self):
                while True:
                    data, addr = self.daemon.sock.recvfrom(BUFFER_SIZE)
                    logger.debug("Recieved: {0} from {1}".format(data, addr))

                    source, message = data.split(': ', 1)

                    # TODO think about this
                    #if source != partner:
                    #    continue

                    self.daemon.partner_is_alive()

        listener = Listener(self)
        listener.start()

        while True:
            self.send("{0}: hello {1}".format(self.uname, partner))
            #logger.debug("Partner status: {0}".format(self.partner_status))

            if not self.have_the_ball:
                pass

            sleep(5)

    def send(self, message):
        self.sock.sendto(message, self.partner_pair)

    def partner_is_alive(self):
        self.last_seen = time()

    @property
    def partner_status(self):
        return 'dead' if time() - self.last_seen > self.dead_time else 'alive'

    def takeover(self):
        pass

    def release(self):
        pass

    def status(self):
        pass

    @property
    def resources(self):
        if self._resources is not None:
            return self._resources

        resource_source = self.get_config('resources', DEFAULT_RESOURCES)

        if resource_source[:11] == 'haresources':
            # parse the heartbeat haresources file
            filename = resource_source.split(':')
            filename = filename[1] if len(filename) > 1 else '/etc/ha.d/haresources'
            fd = open(filename, 'r')
            haresources = fd.read()
            fd.close()

            resources = {}

            haresources = re.sub("\\\\\r?\n", ' ', haresources)
            haresources = re.split("\r?\n", haresources)

            for haresource in haresources:
                haresource = haresource.strip()
                if haresource == '' or haresource[0] == '#':
                    continue

                haresource = re.split("[ \t]+", haresource)
                node_name = haresource.pop(0)
                ident = haresource[0]
                resource_list = []

                for resource in haresource:
                    ip_check = re.match("[0-9]+(\\.[0-9]+){3}", resource)
                    if ip_check:
                        if '/' in resource:
                            resource = resource.split('/')
                            ip = resource[0]
                            mask = resource[1]
                        else:
                            ip = resource
                            mask = '32'

                        resource_list.append(IPAddrResource(ip, mask))

                    elif resource.startswith('Filesystem::'):
                        filesystem, block_device, mount_point = resource.split('::')
                        resource_list.append(FilesystemResource(block_device, mount_point))

                    elif resource.startswith('drbddisk::'):
                        drbd, name = resource.split('::')
                        resource_list.append(DRBDResource(name))

                    else:
                        resource = resource.split('::')
                        resource_list.append(ServiceResource(resource[0], resource[1:]))

                resources[ident] = {
                        'preferred': node_name, # this is ignored for now
                        'resources': resource_list,
                        }

            self._resources = resources

            self.owners = {}
            for ident, resources in self._resources.items():
                self.owner[ident] = True
                for resource in resources['resources']:
                    if not resource.status():
                        self.owner[ident] = False
                        break

            return self._resources

    @property
    def uname(self):
        if self._uname is None:
            self._uname = self.get_config('node_name', os.uname()[1])
        return self._uname

    def get_config(self, key, default, section = 'DEFAULT'):
        try:
            return self._config.get(section, key)
        except ConfigParser.NoOptionError:
            return default

    def _setup_logging(self):
        levels = {
                'debug' : logging.DEBUG,
                'info' : logging.INFO,
                'warn' : logging.WARN,
                'error' : logging.ERROR,
                }
        level = self.log_level
        logger.setLevel(levels[level])

        target = self.get_config('log', DEFAULT_LOG)

        if not self.daemonize or target == 'stdout':
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(levels[level])
            logger.addHandler(handler)
        elif target[0] == '/' and os.path.isfile(target):
            handler = logging.FileHandler(target)
            handler.setLevel(levels[level])
            logger.addHandler(handler)
        elif target == 'syslog':
            handler = logging.handlers.SysLogHandler(address='/dev/log', facility=logging.handlers.SysLogHandler.LOG_DAEMON)
            handler.setLevel(levels[level])
            formatter = logging.Formatter('%(name)s[{0}] %(levelname)s: %(message)s'.format(os.getpid()))
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def _parse_config(self):
        if not os.path.isfile(self.config):
            logger.error("{0} does not exist".format(self.config))
            raise IOError("{0} does not exist".format(self.config))

        # happy.conf program config
        class FakeSectionHeader(object):
            def __init__(self, fp):
                self.fp = fp
                self.header = '[DEFAULT]\n'
            def readline(self):
                if self.header:
                    try: return self.header
                    finally: self.header = None
                else:
                    return self.fp.readline()

        parser = ConfigParser.RawConfigParser()
        with open(self.config) as config_fd:
            parser.readfp(FakeSectionHeader(config_fd))
        self._config = parser

        self._setup_logging()

    def signals(self, sig, frame):
        if sig in (signal.SIGINT, signal.SIGTERM):
            # exit gracefully
            if sig == signal.SIGINT and not self.daemonize:
                sys.stdout.write("\r")
            logger.warn("Exiting")
            sys.exit()

        elif sig == signal.SIGHUP:
            # reload configurations
            logger.info("Reloading configurations")
            self._parse_config()
            self._resources = None
            self._uname = None

    def _catch_signals(self):
        signal.signal(signal.SIGINT, self.signals)
        signal.signal(signal.SIGTERM, self.signals)
        signal.signal(signal.SIGHUP, self.signals)
