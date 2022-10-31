import operator
from functools import reduce

import ConnectionScript
import ConnectionVariable


def set_mapping_type(endpoint_mapping):
    if endpoint_mapping["target"]["label"] == "Variables":
        endpoint_mapping["type"] = "variables"
    elif ConnectionScript.search_in_scripts(endpoint_mapping):
        endpoint_mapping["type"] = "script"
    else:
        endpoint_mapping["type"] = "glom"
    return endpoint_mapping


def generate_glom_mapping(connection_id, endpoint_mapping):
    connection_list = []
    if "schemaMapping" in endpoint_mapping and endpoint_mapping["schemaMapping"]:
        for connection in endpoint_mapping["schemaMapping"]:
            connection_endpoints = {}
            for connection_end in ["source", "target"]:
                data_location = find_schema_item(
                    connection_id,
                    connection_end,
                    endpoint_mapping,
                    connection[connection_end],
                )
                if data_location == "schema":
                    found_paths = find_path_in_json_schema(
                        endpoint_mapping[connection_end]["schema"],
                        connection[connection_end],
                    )
                    if len(found_paths) == 1:
                        connection_endpoints[connection_end] = found_paths[0]
                    elif len(found_paths) == 0:
                        print(
                            "Error generating glom mapping: location in JSON of "
                            + connection[connection_end]
                            + " could not be found"
                        )
                        return
                    else:
                        print(
                            "Error generating glom mapping: duplicate location in JSON found for "
                            + connection[connection_end]
                        )
                        return
                elif (
                    data_location == "sourceParameter"
                    or data_location == "targetParameter"
                    or data_location == "variables"
                ):
                    connection_endpoints[connection_end] = (
                        data_location + "." + connection[connection_end]
                    )
                else:
                    print(
                        "Error generating glom mapping: location of connection "
                        + connection_end
                        + " could not be found, connection id: "
                        + connection["id"]
                        + " given location: "
                        + str(data_location)
                    )
                    return
            if "source" in connection_endpoints and connection_endpoints["source"]:
                if "target" in connection_endpoints and connection_endpoints["target"]:
                    connection_list.append(connection_endpoints)
                else:
                    print(
                        "Error generating glom mapping: one of the low level data connection data targets could not be found, schema mapping id: "
                        + connection["id"]
                    )
            else:
                print(
                    "Error generating glom mapping: one of the low level data connection data sources could not be found, schema mapping id: "
                    + connection["id"]
                )
                return
        base_model = generate_base_data_model(endpoint_mapping["target"]["schema"])
        return fill_base_model(base_model, connection_list)
    else:
        return


def check_glom_mapping_state(glom_mapping, list_incomplete_elements=False):
    def iterate_dict(mapping, list_incomplete_elements, incomplete_elements):
        iteration_complete = True
        if isinstance(mapping, dict):
            for key, value in mapping.items():
                if isinstance(value, dict):
                    iteration_complete = iterate_dict(
                        mapping[key], list_incomplete_elements, incomplete_elements
                    )
                elif value == "":
                    iteration_complete = False
                    if list_incomplete_elements:
                        incomplete_elements.append((key, "target body"))
        else:
            if mapping == "":
                iteration_complete = False
        return iteration_complete

    incomplete_elements = []
    complete = iterate_dict(glom_mapping, list_incomplete_elements, incomplete_elements)
    return complete, incomplete_elements


def generate_base_data_model(target_schema):
    if "type" in target_schema and target_schema["type"]:
        if target_schema["type"] == "array":
            return generate_base_data_model_array(target_schema)
        elif target_schema["type"] == "object":
            return generate_base_data_model_object(target_schema)
        else:
            return ""


def generate_base_data_model_array(target_schema):
    if "items" in target_schema and target_schema["items"]:
        if "type" in target_schema["items"] and (
            target_schema["items"]["type"] == "array"
            or target_schema["items"]["type"] == "object"
        ):
            return generate_base_data_model(target_schema["items"])
        else:
            return ""


def generate_base_data_model_object(target_schema):
    if "properties" in target_schema and target_schema["properties"]:
        init_dict = {}
        for key, value in target_schema["properties"].items():
            init_dict[key] = generate_base_data_model(value)
        if init_dict:
            return init_dict
        else:
            return ""


def find_path_in_json_schema(schema, id):
    current_path = ""
    found_paths = []

    def extract(schema, current_path, found_paths, id):
        if isinstance(schema, dict):
            if (
                "type" in schema
                and "properties" in schema
                and schema["type"] == "object"
            ):
                for key, value in schema["properties"].items():
                    if isinstance(value, dict):
                        if (
                            "type" in value
                            and "properties" in value
                            and value["type"] == "object"
                        ):
                            extract(
                                value,
                                current_path + "." + key if current_path != "" else key,
                                found_paths,
                                id,
                            )
                        elif (
                            "type" in value
                            and "items" in value
                            and value["type"] == "array"
                        ):
                            extract(
                                value["items"],
                                current_path + "." + key if current_path != "" else key,
                                found_paths,
                                id,
                            )
                        elif "id" in value and value["id"] == id:
                            found_paths.append(
                                current_path + "." + key if current_path != "" else key
                            )
            elif "type" in schema and "items" in schema and schema["type"] == "array":
                extract(schema["items"], current_path, found_paths, id)
            elif "id" in schema and schema["id"] == id:
                found_paths.append(current_path)
        return found_paths

    return extract(schema, current_path, found_paths, id)


def find_schema_item(connection_id, type, endpoint_mapping, id):
    if next(
        (item for item in endpoint_mapping[type]["schemaItems"] if item["id"] == id),
        None,
    ):
        return "schema"
    elif next(
        (
            item
            for item in endpoint_mapping["source"]["parameterItems"]
            if item["id"] == id
        ),
        None,
    ):
        return "sourceParameter"
    elif next(
        (
            item
            for item in endpoint_mapping["target"]["parameterItems"]
            if item["id"] == id
        ),
        None,
    ):
        return "targetParameter"
    elif next(
        (
            item
            for item in ConnectionVariable.get_variable_sources(connection_id)
            if item["id"] == id
        ),
        None,
    ):
        return "variables"
    else:
        return


def fill_base_model(base_model, connections):
    for connection in connections:
        if (
            not connection["target"].startswith("sourceParameter")
            and not connection["target"].startswith("targetParameter")
            and not connection["target"].startswith("variables")
        ):
            target_paths = connection["target"].split(".")
            set_by_path(base_model, target_paths, connection["source"])
    return base_model


def get_by_path(base_model, items):
    return reduce(operator.getitem, items, base_model)


def set_by_path(base_model, items, value):
    get_by_path(base_model, items[:-1])[items[-1]] = value
