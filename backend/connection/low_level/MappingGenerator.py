import operator
from functools import reduce

from backend.connection import ConnectionVariable


def set_mapping_type(endpoint_mapping: dict) -> dict:
    """Function to determine the type of connection between data source and target

    :param endpoint_mapping: the configuration between data source and target
    :return: a modified endpoint_mapping with a set type
    """
    if endpoint_mapping["target"]["label"] == "Variables":
        endpoint_mapping["type"] = "variables"
    elif search_in_scripts(endpoint_mapping):
        endpoint_mapping["type"] = "script"
    else:
        endpoint_mapping["type"] = "glom"
    return endpoint_mapping


def generate_glom_mapping(connection_id: str, endpoint_mapping: dict) -> None | dict:
    """Function to generate a Glom mapping and fill it

    This function generates a mapping specifically for the Glom package as a base model. This base model is used to
    generate data for the target, in the format it requires. This base model is then filled to references to the data
    sources.

    :param connection_id: unique identifier for the connection between applications
    :param endpoint_mapping: the configuration between data source and target
    :return: a dict representing a Glom mapping
    """
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
                        "Error generating glom mapping: one of the low level data connection data targets could not "
                        "be found, schema mapping id: " + connection["id"]
                    )
            else:
                print(
                    "Error generating glom mapping: one of the low level data connection data sources could not be "
                    "found, schema mapping id: " + connection["id"]
                )
                return
        base_model = generate_base_data_model(endpoint_mapping["target"]["schema"])
        return fill_base_model(base_model, connection_list)
    else:
        return


def check_glom_mapping_state(
    glom_mapping: any, list_incomplete_elements: bool = False
) -> tuple[bool, list]:
    """ Helper function to iterate through a Glom mapping

    :param glom_mapping: a dict with the data schema as a dict and Glom mapping relations
    :param list_incomplete_elements: boolean if to list the elements that are incomplete
    :return: a tuple, a boolean if the mapping is complete and a list of incomplete items if not complete and a list
    is requested
    """

    def iterate_dict(
        mapping: any, list_incomplete_elements: bool, incomplete_elements: list
    ) -> bool:
        """ Function to recursively go trough a model of a data schema with glom relations while searching for a data
        element that does not have a Glom relation. If such an element is found this means that the mapping is
        incomplete

        :param mapping: a dict with the data schema as a dict and Glom mapping relations
        :param list_incomplete_elements: boolean if to list the elements that are incomplete
        :param incomplete_elements: list of current items that are incomplete
        :return: if the glom mapping is complete
        """
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


def generate_base_data_model(target_schema: any) -> any:
    """ Function to generate an empty data set that is compliant with the target schema.
    The target schema being a data schema and the base data model being an empty version of that

    :param target_schema: data schema to mimic
    :return: an empty data element with target schema as its description
    """
    if "type" in target_schema and target_schema["type"]:
        if target_schema["type"] == "array":
            return generate_base_data_model_array(target_schema)
        elif target_schema["type"] == "object":
            return generate_base_data_model_object(target_schema)
        else:
            return ""


def generate_base_data_model_array(target_schema: dict) -> any:
    """ Helper function for generate_base_data_model() in case the current element is an array

    :param target_schema: data schema to mimic
    :return: an empty data element with target schema as its description
    """
    if "items" in target_schema and target_schema["items"]:
        if "type" in target_schema["items"] and (
            target_schema["items"]["type"] == "array"
            or target_schema["items"]["type"] == "object"
        ):
            return generate_base_data_model(target_schema["items"])
        else:
            return ""


def generate_base_data_model_object(target_schema: dict) -> any:
    """ Helper function for generate_base_data_model() in case the current element is an dict

    :param target_schema: data schema to mimic
    :return: an empty data element with target schema as its description
    """
    if "properties" in target_schema and target_schema["properties"]:
        init_dict = {}
        for key, value in target_schema["properties"].items():
            init_dict[key] = generate_base_data_model(value)
        if init_dict:
            return init_dict
        else:
            return ""


def find_path_in_json_schema(schema: dict, item_id: str) -> list:
    """ Helper function to call extract

    :param schema: schema to find a path in
    :param item_id: the id to find the path to
    :return:
    """
    current_path = ""
    found_paths = []

    def extract(
        schema: any, current_path: str, found_paths: list, item_id: str
    ) -> list:
        """ Function to find a path to a specific item in a JSON schema given the item's identifier

        :param schema: schema to find a path in
        :param current_path: current path that has been taken as a list of steps
        :param found_paths: path that has been found to the item
        :param item_id: the id to find the path to
        :return:
        """
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
                                item_id,
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
                                item_id,
                            )
                        elif "id" in value and value["id"] == item_id:
                            found_paths.append(
                                current_path + "." + key if current_path != "" else key
                            )
            elif "type" in schema and "items" in schema and schema["type"] == "array":
                extract(schema["items"], current_path, found_paths, item_id)
            elif "id" in schema and schema["id"] == item_id:
                found_paths.append(current_path)
        return found_paths

    return extract(schema, current_path, found_paths, item_id)


def find_schema_item(
    connection_id: str, connection_type: str, endpoint_mapping: dict, item_id: str
) -> str | None:
    """ Function to find what kind of item the given item id is part of, options are: schema, sourceParameter,
    targetParameter and variables

    :param connection_id: unique identifier for the connection between applications
    :param connection_type:
    :param endpoint_mapping: the configuration between data source and target
    :param item_id: identifier of the item to find the type of
    :return: the found type
    """
    if next(
        (
            item
            for item in endpoint_mapping[connection_type]["schemaItems"]
            if item["id"] == item_id
        ),
        None,
    ):
        return "schema"
    elif next(
        (
            item
            for item in endpoint_mapping["source"]["parameterItems"]
            if item["id"] == item_id
        ),
        None,
    ):
        return "sourceParameter"
    elif next(
        (
            item
            for item in endpoint_mapping["target"]["parameterItems"]
            if item["id"] == item_id
        ),
        None,
    ):
        return "targetParameter"
    elif next(
        (
            item
            for item in ConnectionVariable.get_variable_sources(connection_id)
            if item["id"] == item_id
        ),
        None,
    ):
        return "variables"
    else:
        return


def fill_base_model(base_model: any, connections: list) -> any:
    """ Function to fill the empty base model with Glom relations

    :param base_model: empty model of the data schema
    :param connections: a list of connections that need to be converted to Glom mappings
    :return: a filled with Glom relations base model
    """
    for connection in connections:
        if (
            not connection["target"].startswith("sourceParameter")
            and not connection["target"].startswith("targetParameter")
            and not connection["target"].startswith("variables")
        ):
            target_paths = connection["target"].split(".")
            set_by_path(base_model, target_paths, connection["source"])
    return base_model


def get_by_path(base_model: any, items: list) -> any:
    """ Helper function to find teh searched item given its paths as items

    :param base_model: empty model of the data schema
    :param items: path to the item as a list
    :return: the searched item
    """
    return reduce(operator.getitem, items, base_model)


def set_by_path(base_model: any, items: list, value: any) -> None:
    """ Function to set a value to an item in the base model

    :param base_model: the base model where an item is set and returned through call by reference
    :param items: path the item as a list
    :param value: value to assign to the item
    """
    get_by_path(base_model, items[:-1])[items[-1]] = value


def search_in_scripts(endpoint_mapping: dict) -> bool:
    """Find a script type of connection in an API endpoint connection

    :param endpoint_mapping:
    :return: boolean if the API connection has a script and is therefore of type script
    """
    if "schemaMapping" in endpoint_mapping and endpoint_mapping["schemaMapping"]:
        return (
            next(
                (
                    index
                    for (index, value) in enumerate(endpoint_mapping["schemaMapping"])
                    if value["type"] == "script"
                ),
                None,
            )
            is not None
        )
    else:
        return False
