import ast

import pymongo
from bson import objectid
from flask import Blueprint, jsonify, request

import ConnectionConfig
import DataTypeUtils

connection_variable = Blueprint(
    "ConnectionVariable", __name__, template_folder="templates"
)

mongo_client = pymongo.MongoClient("mongodb://database:27017/")


@connection_variable.route(
    "/api/connection/get/variables/<connection_id>", methods=["GET"]
)
def get_variables(connection_id: str, internal: bool = False) -> list | tuple:
    """Returns all the variables for this connection

    This function retrieves all the variables for a specific connection. If none exist none will be returned.
    The types of the values are converted from Python to more readable JSON data types.

    More info here: http://json-schema.org/understanding-json-schema/reference/type.html

    :param internal:
    :param connection_id: Mongodb id of connection given as a string
    :return: an JSON object containing the variables
    """
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    if "variables" in connection_config:
        variables = connection_config["variables"]
        for variable in variables:
            variable["type"] = DataTypeUtils.convert_python_to_json(
                type(variable["value"]).__name__
            )  # get type of value as a string, example: "int" or "dict" and convert it to JSON data types example:
            # "number" or "object"
            if not internal:
                variable["value"] = str(
                    variable["value"]
                )  # cast type to string for display purposes
        if internal:
            return variables
        else:
            return (
                jsonify({"success": True, "data": variables}),
                200,
                {"ContentType": "application/json"},
            )
    else:
        if internal:
            return []
        else:
            return (
                jsonify({"success": True, "data": None}),
                200,
                {"ContentType": "application/json"},
            )


def get_variables_for_glom(connection_id: str) -> dict:
    """ Function to convert variables to GLOM format

    :param connection_id: Mongodb id of connection given as a string
    :return: dict with all variables
    """
    variables_dict = {"variables": {}}
    variables = get_variables(connection_id, internal=True)
    for variable in variables:
        variables_dict["variables"][variable["id"]] = variable["value"]
    return variables_dict


@connection_variable.route(
    "/api/connection/variable/<connection_id>", methods=["POST"]
)
def add_variable(connection_id: str) -> tuple:
    """Returns state after adding a variable to the connection

    This function adds a variable to the connection config.
    :param connection_id: Mongodb id of connection given as a string
    :return: an JSON object if updating of the variable was successful
    """
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    variable = request.get_json()
    variable["id"] = str(objectid.ObjectId())
    state, value = convert_value_to_correct_data_type(variable["value"])
    if not state:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error recognizing the type of value (integer, boolean, string etc)",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )
    variable["value"] = value
    if "variables" not in connection_config:
        connection_config["variables"] = []
    connection_config["variables"].append(variable)
    variable_id = ConnectionConfig.update_connection_config(
        connection_id, connection_config, internal=True
    )
    if variable_id:
        return jsonify({"success": True}), 200, {"ContentType": "application/json"}
    else:
        return (
            jsonify({"success": False, "message": "Saving the new variable failed"}),
            500,
            {"ContentType": "application/json"},
        )


@connection_variable.route(
    "/api/connection/variable/<connection_id>/<variable_id>", methods=["DELETE"]
)
def delete_variable(connection_id: str, variable_id: str) -> tuple:
    """Returns state after deletion of a connection variable

    This function deletes a variable from the connection config.
    :param variable_id:
    :param connection_id: Mongodb id of connection given as a string
    :return: an JSON object if updating of the variable was successful
    """
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    variable_index = next(
        (
            index
            for (index, value) in enumerate(connection_config["variables"])
            if value["id"] == variable_id
        ),
        None,
    )
    if variable_index is not None:
        connection_config["variables"].pop()
        variable_id = ConnectionConfig.update_connection_config(
            connection_id, connection_config, internal=True
        )
        if variable_id:
            return jsonify({"success": True}), 200, {"ContentType": "application/json"}
        else:
            return (
                jsonify({"success": False, "message": "Deleting the variable failed"}),
                500,
                {"ContentType": "application/json"},
            )
    return (
        jsonify(
            {
                "success": False,
                "message": "Deleting the variable failed, because the variable was not found",
            }
        ),
        500,
        {"ContentType": "application/json"},
    )


@connection_variable.route(
    "/api/connection/variable/<connection_id>", methods=["PUT"]
)
def update_variable(connection_id: str, variable: dict = None, internal: bool = False) -> bool | tuple:
    """Returns state after updating a variable

    This function updates the connection config with the newly updated variable.
    :param internal:
    :param variable:
    :param connection_id: Mongodb id of connection given as a string
    :return: an JSON object if updating of the variable was successful
    """
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    if not internal:
        variable = request.get_json()
    state, value = convert_value_to_correct_data_type(variable["value"])
    if not state:
        if internal:
            return False
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "There was an error recognizing the type of value (integer, boolean, string etc)",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
    variable["value"] = value
    connection_config["variables"][
        next(
            index
            for (index, value) in enumerate(connection_config["variables"])
            if value["id"] == variable["id"]
        )
    ] = variable
    updated = ConnectionConfig.update_connection_config(
        connection_id, connection_config, internal=True
    )
    if updated is not None:
        if internal:
            return True
        else:
            return jsonify({"success": True}), 200, {"ContentType": "application/json"}
    else:
        if internal:
            return False
        else:
            return (
                jsonify({"success": False, "message": "Updating the variable failed"}),
                500,
                {"ContentType": "application/json"},
            )


def get_variable_sources(connection_id: str) -> list:
    """Returns a list of all the variables as sources

    In order to use a variable as a data source in the mapping, the variables need to be converted and made readable.
    This function gets all the variables an
    This function updates the connection config with the newly updated variable.
    :param connection_id: Mongodb id of connection given as a string
    :return: an JSON object if updating of the variable was successful
    """
    variables = get_variables(connection_id, internal=True)
    return_variables = []
    if variables is not None:
        for temp in variables:
            return_variables.append(
                {
                    "id": temp["id"],
                    "name": temp["name"] + " (variable)",
                    "type": temp["type"],
                    "value": temp["value"],
                }
            )
    return return_variables


def convert_value_to_correct_data_type(value: any) -> tuple[bool, str]:
    """ Returns the value after casting it to the correct type

    Because the type of the variable cannot be set in the frontend, all will be set to a string. In order to have the
    correct type in the saved this function will detect the type and cast it to that type and return it.
    :param value: any value given in the frontend for variable value
    :return: a boolean if casting and detection succeeded and the cast value
    """
    if value == "true" or value == "false":
        value = value.capitalize()
    try:
        return True, ast.literal_eval(value)  # cast value to its assumed type
    except ValueError:
        try:
            return True, ast.literal_eval(
                "\"" + value + "\"")  # value error is often raised when a string contains spaces, extra quotes
            # mitigates this, but cannot initially be added because of dicts
        except Exception as e:
            print("Error in ConnectionVariable.convert_value_to_correct_data_type():", e)
            return False, ""
    except SyntaxError as e:
        try:
            return True, ast.literal_eval(
                "\"" + value + "\"")  # value error is often raised when a string begins with a couple of integers,
            # extra quotes mitigates this, but cannot initially be added because of dicts
        except Exception as e:
            print("Error in ConnectionVariable.convert_value_to_correct_data_type():", e)
            return False, ""


def get_variable(connection_id: str, variable_id: str) -> dict:
    """ Function to get a specific variable

    :param connection_id: Mongodb id of connection given as a string
    :param variable_id: identifier for variable
    :return: a dict containing the variable
    """
    variables = get_variables(connection_id, internal=True)
    return next((item for item in variables if item["id"] == variable_id), None)


def search_in_variables(connection_id: str, variable_id: str) -> bool:
    """

    :param connection_id: Mongodb id of connection given as a string
    :param variable_id: identifier for variable
    :return: bool if variable with variable exists
    """
    return get_variable(connection_id, variable_id) is not None


def set_variable(connection_id: str, variable_id: str, value: any) -> bool:
    """

    :param connection_id: Mongodb id of connection given as a string
    :param variable_id: identifier for variable
    :param value: value to set the variable to
    :return: bool if value got updated
    """
    variable = get_variable(connection_id, variable_id)
    variable["value"] = value
    return update_variable(connection_id, variable, internal=True)
