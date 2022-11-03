import jsonpickle
from flask import Blueprint

from backend.connection import ConnectionConfig
from backend.connection.low_level import MappingGenerator
from backend.connection.low_level.table import DataHandler

connection_low_level_state = Blueprint("ConnectionLowLevelState", __name__)


def check_parameter_state(schema_mapping: dict) -> tuple[bool, list]:
    """ Function to check if all parameters in a connection between APIs are satisfied

    :param schema_mapping: section of the mapping with all connections and separate elements of the connections
    :return: a tuple with a boolean if all parameters are complete and a list if of incomplete parameters if not
    complete
    """
    incomplete_parameter_items = []
    if "schemaMapping" in schema_mapping and schema_mapping["schemaMapping"]:
        for connection in ["source", "target"]:
            if "parameterItems" in schema_mapping[connection]:
                for parameter in schema_mapping[connection]["parameterItems"]:
                    if "required" in parameter and parameter["required"]:
                        index = next(
                            (
                                i
                                for i, item in enumerate(
                                schema_mapping["schemaMapping"]
                            )
                                if item["source"] == parameter["id"]
                                   or item["target"] == parameter["id"]
                            ),
                            None,
                        )
                        if index is None:
                            incomplete_parameter_items.append(
                                (parameter["name"], connection + " parameter")
                            )
        if incomplete_parameter_items:
            return False, incomplete_parameter_items
        else:
            return True, []
    else:
        return False, []


def check_low_level_state(endpoint_mapping: dict) -> tuple[bool, list]:
    """ Function to check the state of a connection between APIs or other data endpoints

    This function checks if all mappings and parameters are complete. This is ignored if the connection is made
    with a script or variable

    :param endpoint_mapping: config of a connection between source and target
    :return: a tuple if the connection is complete and a list of incomplete items if incomplete
    """
    incomplete_glom_items = []
    glom_complete = False
    if endpoint_mapping["type"] == "glom":
        (
            glom_complete,
            incomplete_glom_items,
        ) = MappingGenerator.check_glom_mapping_state(
            jsonpickle.decode(endpoint_mapping["glomMapping"]), True
        )
    parameter_complete, incomplete_parameter_items = check_parameter_state(
        endpoint_mapping
    )
    if (
            endpoint_mapping["type"] == "glom" and not glom_complete
    ) or not parameter_complete:
        return False, incomplete_glom_items + incomplete_parameter_items
    else:
        return True, []


@connection_low_level_state.route(
    "/api/schemamapping/flow/save/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def save_mapping(connection_id: str, endpoint_mapping: dict) -> bool:
    """ Function to check the mapping and to save all incomplete items of an individual connection

    :param connection_id: Unique identifier for the connection configuration between applications
    :param endpoint_mapping: config of a connection between source and target
    :return: boolean if saving of the state and incomplete items was sucessful
    """
    endpoint_mapping = MappingGenerator.set_mapping_type(endpoint_mapping)
    if endpoint_mapping["type"] == "glom":
        glom_mapping = MappingGenerator.generate_glom_mapping(
            connection_id, endpoint_mapping
        )
        if glom_mapping:
            endpoint_mapping["glomMapping"] = jsonpickle.encode(glom_mapping)
            (
                endpoint_mapping["complete"],
                endpoint_mapping["incompleteItems"],
            ) = check_low_level_state(endpoint_mapping)
            success = DataHandler.update_endpoint_mapping(
                connection_id, endpoint_mapping["id"], endpoint_mapping
            )
            return success
        else:
            endpoint_mapping["complete"] = False
            success = DataHandler.update_endpoint_mapping(
                connection_id, endpoint_mapping["id"], endpoint_mapping
            )
            return success
    else:
        (
            endpoint_mapping["complete"],
            endpoint_mapping["incompleteItems"],
        ) = check_low_level_state(endpoint_mapping)
        success = DataHandler.update_endpoint_mapping(
            connection_id, endpoint_mapping["id"], endpoint_mapping
        )
        return success


def save_mappings(connection_id: str) -> bool:
    """  Function to check all connection with a connection between data endpoints

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: boolean if saving of state was sucessful
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    if "endpointMapping" in connection_config and connection_config["endpointMapping"]:
        for endpoint_mapping in connection_config["endpointMapping"]:
            if not save_mapping(connection_id, endpoint_mapping):
                print(
                    "Error in save_mappings(): saving failed, mapping id: "
                    + endpoint_mapping["id"]
                )
                return False
    return True


def generate_connection_name(api: dict) -> str:
    """ Function to generate a name for a connection between data endpoints based on their type, path and operation

    :param api: dict with the information about target and source properties
    :return: a string with the name of the connection
    """
    if "path" not in api["source"]:
        name = (
                "Variables -> "
                + api["target"]["path"]
                + " ("
                + api["target"]["operation"]
                + ")"
        )
    elif "path" not in api["target"]:
        name = (
                api["source"]["path"] + " (" + api["source"]["operation"] + ") -> Variables"
        )
    else:
        name = (
                api["source"]["path"]
                + " ("
                + api["source"]["operation"]
                + ") -> "
                + api["target"]["path"]
                + " ("
                + api["target"]["operation"]
                + ")"
        )
    return name
