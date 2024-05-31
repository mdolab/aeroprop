def add_geo_dvs(model, vars, filter):
    """Adds geometric DV's to an OpenMDAO model.

    Parameters
    ----------
    model : OpenMDAO Model
        An OpenMDAO model instance.
    vars : list(named_tuple)
        A list of named tuples containing the geometric variable info.
    filter : dict
        A dictionary that filters the components, groups,
        cross sections, and angles that will be added to the model from
        the vars list.
    """
    for var in vars:
        dv_name = f"geo_dvs.{var.comp}:{var.group}:{var.var}"
        for key in filter.keys():
            if var.comp == key and var.group in filter[key]:
                model.add_design_var(dv_name, lower=var.lower, upper=var.upper, ref=var.ref)
