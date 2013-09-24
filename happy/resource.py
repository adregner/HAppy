# HAppy resource

import subprocess

class Resource(object):

    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def status(self):
        pass

    def call(self, *args, output=False):
        kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                }
        process = subprocess.Popen(*args, *kwargs)

        retcode = True if process.wait() == 0 else False

        return (retcode, process.stdout.read()) if output else retcode
