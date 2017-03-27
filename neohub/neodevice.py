class NeoDevice(object):
    """One neodevice superclass"""
    def __init__(self, hub, name):
        self.hub = hub
        self.name = name
        #self.id = hub.devices[name]["id"]

    def update(self):
        self.hub.update()

    def __getitem__(self, key):
        return self.hub.devices[self.name][key]

    def __setitem__(self, key, val):
        self.hub.devices[self.name][key] = val
        return val

    def __repr__(self):
        return "<NeoDevice unknown>"
