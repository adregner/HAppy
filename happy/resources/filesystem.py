#

from happy.resource import Resource

class FilesystemResource(Resource):

    def __init__(self, block_device, mount_point):
        self.block_device = block_device
        self.mount_point = mount_point

    def start(self):
        if not self.status():
            self.call('mount', self.block_device, self.mount_point)

    def stop(self):
        if self.status():
            self.call('umount', self.block_device)

    def status(self):
        mount_line = "{0} {1}".format(self.block_device, self.mount_point)
        with open("/proc/mounts") as fd:
            for mount in fd:
                if mount.startswith(mount_line):
                    return True

        return False
