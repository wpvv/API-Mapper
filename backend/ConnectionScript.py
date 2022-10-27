import os

from flask import Blueprint, jsonify, request
from bson import objectid
import base64

import ConnectionLowLevelFlow
import ConnectionConfig
import MappingGenerator
import ConnectionVariable

connection_script = Blueprint(
    "ConnectionScript", __name__, template_folder="templates"
)


@connection_script.route(
    "/api/connection/script/<connection_id>/<mapping_id>/<script_id>", methods=["GET"]
)
def get_script(connection_id, mapping_id, script_id, internal=False):
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    if "schemaMapping" in schema_config:
        script_config = [mapping for mapping in schema_config["schemaMapping"] if
                         mapping["id"] == script_id and "type" in mapping and mapping["type"] == "script"][0]
        if not script_config:
            if internal:
                return
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "You can add a script when the script node is connected to both APIs",
                        }
                    ),
                    400,
                    {"ContentType": "application/json"},
                )
        else:
            with open("connection_scripts/" + script_id + ".py", encoding='utf-8') as file:
                contents = file.read().encode("ascii")
                contents = base64.b64encode(contents)  # bytes
                script_config["script"] = contents.decode('ascii')  # to string
                if internal:
                    print(script_config)
                    return script_config
                else:
                    return (
                        jsonify({"success": True, "config": script_config}),
                        200,
                        {"ContentType": "application/json"},
                    )

    else:
        if internal:
            return
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Schema mapping is not found",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )


@connection_script.route(
    "/api/connection/script/<connection_id>/<mapping_id>/<script_id>", methods=["POST"]
)
def add_script(connection_id, mapping_id, script_id):
    script_element_config = request.get_json()
    new_connection = {
        "id": script_id,
        "target": script_element_config["target"],
        "source": script_element_config["source"],
        "type": "script",
        "scriptPosition": script_element_config["position"]
    }
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        if "schemaMapping" not in schema_config:
            schema_config["schemaMapping"] = []
        schema_config["schemaMapping"].append(new_connection)
        success = ConnectionLowLevelFlow.update_endpoint_mapping(connection_id, mapping_id, schema_config)
        if success:
            with open("connection_scripts/" + script_id + ".py", encoding='utf-8', mode='a') as file:
                file.write(
                    "def main(" + generate_script_function_arguments(connection_id, mapping_id, script_id) + "):")
                file.write("\n    return " + generate_script_function_return(connection_id, mapping_id, script_id))
                return (
                    jsonify({"success": True, "id": new_connection["id"]}),
                    200,
                    {"ContentType": "application/json"},
                )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Saving the new schema mapping failed",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while looking for the low level mapping details",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )


@connection_script.route(
    "/api/connection/script/<connection_id>/<mapping_id>/<script_id>", methods=["PUT"]
)
def update_script(connection_id, mapping_id, script_id):
    script_node = request.get_json()
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    if "schemaMapping" in schema_config:
        schema_index = next(
            (
                index
                for (index, value) in enumerate(schema_config["schemaMapping"])
                if value["id"] == script_id and value["type"] == "script"
            ),
            None,
        )
        if schema_index is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "You can add a script when the script node is connected to both APIs",
                    }
                ),
                400,
                {"ContentType": "application/json"},
            )
        else:
            schema_config["schemaMapping"][schema_index]["scriptPosition"] = script_node["position"]
            if ConnectionLowLevelFlow.update_endpoint_mapping(connection_id, mapping_id, schema_config):
                contents = script_node["script"]
                contents = contents.encode("ascii")
                contents = base64.b64decode(contents)
                contents = contents.decode('ascii')
                with open("connection_scripts/" + script_id + ".py", encoding='utf-8', mode='a') as file:
                    file.truncate(0)
                    file.write(contents)
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "An error occurred while updating the position of the script node",
                        }
                    ),
                    500,
                    {"ContentType": "application/json"},
                )


@connection_script.route(
    "/api/connection/script/<connection_id>/<mapping_id>/<script_id>", methods=["DELETE"]
)
def delete_script(connection_id, mapping_id, script_id):
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    if "schemaMapping" in schema_config:
        schema_index = next(
            (
                index
                for (index, value) in enumerate(schema_config["schemaMapping"])
                if value["id"] == script_id and value["type"] == "script"
            ),
            None,
        )
        if schema_index is not None:
            schema_config["schemaMapping"].pop(schema_index)
            success = ConnectionLowLevelFlow.update_endpoint_mapping(connection_id, mapping_id, schema_config)
            if success:
                try:
                    os.remove("connection_scripts/" + script_id + ".py")
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
                except OSError as e:
                    print("Error while deleting the file of the script node: " + e.filename, e.strerror)
                    return (
                        jsonify({"success": False, "message": "Deleting the script file failed"}),
                        500,
                        {"ContentType": "application/json"},
                    )
        else:
            return (
                jsonify({"success": False, "message": "Finding the script failed"}),
                500,
                {"ContentType": "application/json"},
            )
    return (
        jsonify({"success": False, "message": "Deleting the script failed"}),
        500,
        {"ContentType": "application/json"},
    )


def generate_script_function_arguments(connection_id, mapping_id, script_id):
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    script_config = get_script(connection_id, mapping_id, script_id, internal=True)
    location = MappingGenerator.find_schema_item(connection_id, "source", schema_config, script_config["source"])
    main_argument_name = ""
    if location == "schema":
        main_argument_name = ConnectionConfig.get_application_name(schema_config["source"]["applicationId"])
        main_argument_name = main_argument_name.replace(" ", "_")
        main_argument_name = main_argument_name.lower()
        if main_argument_name.startswith("_"):
            main_argument_name = main_argument_name[1:]
        if not main_argument_name.endswith("_"):
            main_argument_name += "_data"
        else:
            main_argument_name += "data"
    elif location == "variables":
        variable = ConnectionVariable.get_variable(connection_id, script_config["source"])
        main_argument_name = variable["name"]
    return main_argument_name + ", **variables"


def generate_script_function_return(connection_id, mapping_id, script_id):
    schema_config = ConnectionLowLevelFlow.get_endpoint_mapping(connection_id, mapping_id)
    script_config = get_script(connection_id, mapping_id, script_id, internal=True)
    location = MappingGenerator.find_schema_item(connection_id, "target", schema_config, script_config["target"])
    main_return_name = ""
    if location == "schema":
        main_return_name = ConnectionConfig.get_application_name(schema_config["target"]["applicationId"])
        main_return_name = main_return_name.replace(" ", "_")
        main_return_name = main_return_name.lower()
        if main_return_name.startswith("_"):
            main_return_name = main_return_name[1:]
        if not main_return_name.endswith("_"):
            main_return_name += "_data"
        else:
            main_return_name += "data"
    elif location == "variables":
        variable = ConnectionVariable.get_variable(connection_id, script_config["target"])
        main_return_name = variable["name"]
    return main_return_name


def search_in_scripts(endpoint_mapping):
    if "schemaMapping" in endpoint_mapping and endpoint_mapping["schemaMapping"]:
        return next(
        (
            index
            for (index, value) in enumerate(endpoint_mapping["schemaMapping"])
            if value["type"] == "script"
        ),
        None,
        ) is not None
    else:
        return False

