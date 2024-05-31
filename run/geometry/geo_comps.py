# External modules
import openmdao.api as om


class TELink(om.ExplicitComponent):
    def setup(self):
        self.add_input("XSecCurve_0", desc="Nacelle inner trailing edge diameter")

        self.add_output("XSecCurve_8", desc="Nacelle outer trailing edge diameter")

        self.declare_partials("XSecCurve_8", "XSecCurve_0", val=1.0)

    def compute(self, inputs, outputs):
        outputs["XSecCurve_8"] = inputs["XSecCurve_0"] + 0.2


class FanLink(om.ExplicitComponent):
    def setup(self):
        self.add_input("XSecCurve_1", desc="Fan exit diameter")

        self.add_output("XSecCurve_2", desc="Fan face diameter")

        self.declare_partials("XSecCurve_2", "XSecCurve_1", val=1.0)

    def compute(self, inputs, outputs):
        outputs["XSecCurve_2"] = inputs["XSecCurve_1"]

class GeoLink(om.Group):
    def setup(self):
        self.add_subsystem("te_link", TELink(), promotes=["*"])
        self.add_subsystem("fan_link", FanLink(), promotes=["*"])
