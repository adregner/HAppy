#

from happy.resource import Resource

class DRBDResource(Resource):

    def __init__(self, name):
        self.name = name
