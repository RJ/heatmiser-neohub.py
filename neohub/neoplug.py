from .neodevice import NeoDevice


class NeoPlug(NeoDevice):
    def __repr__(self):
        st = "OFF"
        if self.is_on():
            st = "ON"
        return "<NeoPlug id=%-2d status=%-3s name='%s'>" % (self['id'], st, self.name)

    def is_on(self):
        return self["TIME_CLOCK_OVERIDE_BIT"] and self["TIMER"]

    def switch_on(self):
        if self.hub.switch_plug_on(self.name):
          self["TIME_CLOCK_OVERIDE_BIT"] = True
          self["TIMER"] = True
          return True
        else:
          return False

    def switch_off(self):
        if self.hub.switch_plug_off(self.name):
          self["TIME_CLOCK_OVERIDE_BIT"] = False
          self["TIMER"] = False
          return True
        else:
          return False
