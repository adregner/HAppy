#

from happy.resource import Resource

class ServiceResource(Resource):

    def __init__(self, service, args = []):
        self.service = service
        self.args = args

    def start(self):
        self.call('service', self.service, 'start', *self.args)

    def stop(self):
        self.call('service', self.service, 'stop', *self.args)

    def status(self):
        self.call('service', self.service, 'status', *self.args)
