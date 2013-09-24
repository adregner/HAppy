#

from socket import inet_aton

from happy.resource import Resource

# TODO convert this all to the non-deprecated 'ip' command

class IPAddrResource(Resource):

    def __init__(self, ip, mask = '32'):
        self.ip = ip
        self.mask = mask

    @property
    def addresses(self):
        retcode, output = self.call('ip', 'a', output=True)

        if not retcode:
            raise RuntimeError("Error running 'ip a' command to get current IP addresses!")

        addresses = []
        for line in output.split("\n"):
            line = line.strip().split(' ')
            if line[0] in ('inet', 'inet6'):
                addr = line[1].split('/')[0]
                addresses.append(addr)

        return addresses

    def interfaces(self, target_addr = None):
        retcode, output = call('ifconfig')

        if not retcode:
            raise RuntimeError("Error getting interface names")

        interfaces = {}
        for line in output.split("\n"):
            if line[0] != ' ':
                # start of new interface
                ifname = line.split(' ')[0]
                interfaces[ifname] = []
            elif ' inet addr:' in line:
                m = re.search("addr:([0-9\\.]+).+Mask:([0-9\\.]+)", line)
                addr = m.group(1).split('.')
                mask = m.group(2).split('.')

                if target_addr is not None and addr == target_addr:
                    return ifname

                network = inet_aton(".".join([ int(addr[x]) & int(mask[x]) for x in xrange(4) ]))
                bcast = inet_aton(".".join([ int(addr[x]) | (255 ^ int(mask[x])) for x in xrange(4) ]))
                interfaces[ifname].append((network, bcast))
            elif ' inet6 addr:' in line:
                # TODO IPv6 support
                m = re.search("addr: ([0-9a-f:]+)/([0-9]+)", line)
                addr = m.group(1)
                mask = m.group(2)
                pass

        return interfaces

    def start(self):
        target_iface = None
        target_addr = inet_aton(self.ip)
        interfaces = self.interfaces()

        for ifname, addr_range in interfaces:
            if addr_range[0] < target_addr and target_addr < addr_range[1]:
                target_iface = ifname
                break

        if target_iface is None:
            raise RuntimeError("Unable to find an interface to assign {0} to".format(self.ip))

        target_sub_interface = 0
        sub_interfaces = [ ifname.split(':').pop() for ifname in interfaces.keys() if ifname.startswith(target_iface) ]

        while ':' not in target_iface:
            sub_ifname = "{0}:{1}".format(target_iface, target_sub_interface)
            if sub_ifname not in sub_interfaces:
                target_iface = sub_ifname
                break
            else:
                target_sub_interface += 1

        return self.call('ifconfig', target_iface, self.ip, 'netmask', self.len2mask(self.mask))

    def stop(self):
        target_iface = self.interfaces(target_addr = self.ip)
        return self.call('ifconfig', target_iface, 'down')

    def status(self):
        return self.ip in self.addresses

    def len2mask(self, mask):
        mask = int(mask)
        bits = 0
        for i in xrange(32-mask,32):
            bits |= (1 << i)
        return "%d.%d.%d.%d" % ((bits & 0xff000000) >> 24, (bits & 0xff0000) >> 16, (bits & 0xff00) >> 8 , (bits & 0xff))

    def mask2len(self, mask):
        binary = ''
        mask = mask.split('.')
        for octet in mask:
            binary += bin(int(octet))[2:].zfill(8)
        return len(binary.rstrip('0'))
