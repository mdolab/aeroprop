# External modules
import openmdao.api as om


class FullBody(om.ExplicitComponent):
    def setup(self):
        self.add_input(
            "aero:half_mdot:fan_face", desc="Half-body mass flow rate from CFD at the fan face", units="kg/s"
        )
        self.add_input(
            "aero:half_mdot:fan_exit", desc="Half-body mass flow rate from CFD at the fan exit", units="kg/s"
        )

        self.add_input("aero:half_area:fan_face", desc="Half-body area at the fan face", units="m**2")
        self.add_input("aero:half_area:fan_exit", desc="Half-body area at the fan exit", units="m**2")

        self.add_input("aero:half_fan_power", desc="Half-body fan power from CFD", units="kW")

        self.add_output("aero:mdot:fan_face", desc="Full-body mass flow rate from CFD at the fan face", units="kg/s")
        self.add_output("aero:mdot:fan_exit", desc="Full-body mass flow rate from CFD at teh fan exit", units="kg/s")

        self.add_output("aero:area:fan_face", desc="Full-body area at the fan face", units="m**2")
        self.add_output("aero:area:fan_exit", desc="Full-body area at the fan exit", units="m**2")

        self.add_output("aero:fan_power", desc="Full-body fan power from CFD", units="kW")

        self.declare_partials("aero:mdot:fan_face", "aero:half_mdot:fan_face", val=-2.0)
        self.declare_partials("aero:mdot:fan_exit", "aero:half_mdot:fan_exit", val=2.0)

        self.declare_partials("aero:area:fan_face", "aero:half_area:fan_face", val=2.0)
        self.declare_partials("aero:area:fan_exit", "aero:half_area:fan_exit", val=2.0)

        self.declare_partials("aero:fan_power", "aero:half_fan_power", val=2.0)

    def compute(self, inputs, outputs):
        outputs["aero:mdot:fan_face"] = -2.0 * inputs["aero:half_mdot:fan_face"]
        outputs["aero:mdot:fan_exit"] = 2.0 * inputs["aero:half_mdot:fan_exit"]
        outputs["aero:area:fan_face"] = 2.0 * inputs["aero:half_area:fan_face"]
        outputs["aero:area:fan_exit"] = 2.0 * inputs["aero:half_area:fan_exit"]
        outputs["aero:fan_power"] = 2.0 * inputs["aero:half_fan_power"]
