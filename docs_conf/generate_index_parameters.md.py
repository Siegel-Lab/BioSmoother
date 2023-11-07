import sys
from libbiosmoother import open_default_json, open_button_names_json, open_descriptions_json, open_valid_json, open_button_tabs_json
from libbiosmoother.parameters import list_parameters, values_for_parameter, open_valid_json, is_spinner, is_range_spinner, parameter_type
import json

def quarry_from_json(json, key, help_m=""):
    if len(key) > 0:
        if key[0] in json:
            return quarry_from_json(json[key[0]], key[1:], help_m)
        if len(help_m) > 0:
            print("WARNING did not find:", ".".join(key), help_m)
        return "???"
    else:
        return json

def generate_index_parameters(out_folder):
    default_json = {"settings": json.load(open_default_json())}
    button_names_json = json.load(open_button_names_json())
    button_tabs_json = json.load(open_button_tabs_json())
    descriptions_json = json.load(open_descriptions_json())
    valid_json = json.load(open_valid_json())

    with open(out_folder + "/IndexParameters.md", "w") as f:
        f.write(".. _index_parameters_section: \n\n")
        f.write("### Index Parameters\n\n")
        f.write("Below is a list of all parameters that can be changed in an index session. \n")
        f.write("This changing can be done using the :ref:`set <set_command>` and :ref:`get <get_command>` commands or via the graphical user interface.\n\n")



        ps = list(list_parameters(default_json, valid_json))
        def rec(d, setting):
            if isinstance(d, dict):
                for k in d.keys():
                    rec(d[k], setting + [k])
            else:
                ps.append(setting)

        rec(button_names_json, [])

        ps = list(ps)
        ps.sort()
        ps2 = []
        for p in ps:
            if len(ps2) == 0 or ps2[-1] != p:
                ps2.append(p)

        last_heading = ["", ""]
        for p in ps2: # @todo things not under settings are missing... / hardcode area and v4c col and row
            if len(p) >= 2 and p[0] != last_heading[0]:
                f.write("#### The " + p[0][0].upper() + p[0][1:] + " group \n\n")
                last_heading[0] = p[0]
                last_heading[1] = ""
            if len(p) >= 3 and p[1] != last_heading[1]:
                f.write("##### The " + p[1][0].upper() + p[1][1:] + " subgroup\n\n")
                last_heading[1] = p[1]

            parameter_name = ".".join(p)
            if is_spinner(quarry_from_json(default_json, p)):
                parameter_name = "`" + parameter_name + ".val`"
            if is_range_spinner(quarry_from_json(default_json, p)):
                parameter_name = "`" +  parameter_name + ".val_min` and `" + parameter_name + ".val_max`"
            else:
                parameter_name = "`" + parameter_name + "`"
            f.write("#####" + ("#" if len(p) >= 3 else "") + " " + p[-1] + "\n")
            f.write("*Full parameter name:* " + parameter_name + "\\\n")
            f.write("*Description:* " + quarry_from_json(descriptions_json, p, "(in description.json)") + "\\\n\n")
            f.write("*Accepted values:* " + values_for_parameter(p, default_json, valid_json) + "\\\n")
            f.write("*Value type:* " + parameter_type(p, default_json, valid_json) + "\\\n")
            button_tab = quarry_from_json(button_tabs_json, p)
            button_tab_h = ""
            link_text = "`"
            if button_tab != "":
                link_text = "` :ref:`(see in manual) <" + button_tab.split("->")[-1].lower().replace(" ", "_").replace(".", "") + "_sub_tab>`"
                button_tab_h = ":kbd:`" + button_tab + "`"
            button_name = quarry_from_json(button_names_json, p)
            if button_name != "???":
                f.write("*Button in GUI:* " + button_tab_h + " :guilabel:`" + button_name + link_text + "\n\n")
            else:
                f.write("*This parameter has no button in the GUI*\n\n")

    

if __name__ == "__main__":
    generate_index_parameters(*sys.argv[1:])