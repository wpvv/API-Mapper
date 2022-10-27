import json
import os
import random
import shutil
import string
import tempfile
import zipfile

import requests

import ApplicationConfig


def generate_sdk(application_id: str) -> bool:
    """Returns an updated config after generating a client SDK with the given config

    This function uses the given config and sends it to the OpenAPI SDK generator. This generator is located in a
    docker container. It sends back a zip containing Python code to connect to the APIs in teh configuration. This
    zip is unzipped renamed and stored in: generated_clients

    :param application_id: unique identifier of an application
    :return: bool if generation of the sdk was successful
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    sdk_id = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    header = {"Content-Type": "application/json", "Accept": "application/json"}
    options = {
        "generateSourceCodeOnly": True,
        "packageName": sdk_id,
        "packageVersion": config["version"],
    }

    data = {"spec": config["specs"], "options": options}
    response = requests.post(
        "http://codegenerator:8080/api/gen/clients/python",
        json.dumps(data),
        headers=header,
    )
    response_dict = response.json()
    if "link" in response_dict:
        url = response_dict["link"]
        response_sdk = requests.get(url)
        file_path = "./generated_clients/"
        tmp = tempfile.NamedTemporaryFile()
        try:
            tmp.write(response_sdk.content)
            if zipfile.is_zipfile(tmp.name):
                with zipfile.ZipFile(tmp.name, "r") as sdk_client:
                    sdk_client.extractall(file_path)
                    try:
                        shutil.copytree(
                            file_path + "python-client/" + sdk_id, file_path + sdk_id
                        )
                        shutil.rmtree(file_path + "python-client")
                    except Exception as e:
                        print(e)
                        return False
            else:
                print("generated client is not a zip")
                return False
        finally:
            sdk_client.close()
            tmp.close()
            config["sdkGenerated"] = True
            config["sdkId"] = sdk_id
            config.pop("automaticImportURL", None)
            config.pop("automaticImportFile", None)
            updated, _, _ = ApplicationConfig.update_application_config(
                application_id, config, check_sdk=False
            )
            if updated.get_json()["success"]:
                return True
            else:
                return False
    else:
        print("Error:" + str(response_dict))
        return False


def delete_sdk(application_id: str) -> bool:
    """Returns status after deleted the application's client SDK

    This function removes the folder (in ./generated_clients) and all of its contents of the client SDK given in the
    config

    :param application_id: unique identifier fo an application
    :return: bool if deletion of the sdk was successful
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    sdk_path = "./generated_clients/" + config["sdkId"]
    if "sdkGenerated" in config and config["sdkGenerated"]:
        try:
            shutil.rmtree(sdk_path)
            # os.remove(sdk_path + "_README.md")
            config["sdkGenerated"] = False
            updated, _, _ = ApplicationConfig.update_application_config(
                application_id, config, check_sdk=False
            )
            if updated.get_json()["success"]:
                return True
            else:
                return False
        except OSError as e:
            print("Error: " + sdk_path + e.strerror)
            return False
    else:
        return False


def update_sdk(application_id: str) -> bool:
    """Returns status after updating the application's client SDK

    This function removes the old SDK and generates a new one bases on the updated config

    :param application_id: unique identifier fo an application
    :return: bool if update of the sdk was successful
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    if "sdkGenerated" in config:
        if config["sdkGenerated"]:
            if not delete_sdk(application_id):
                return False
        if generate_sdk(application_id):
            return True
        else:
            return False
    return False


def double_check_sdk(application_id: str) -> bool:
    """Returns if sdk exists

    This function double checks if client/SDK exists not only in the config but also in the "generated_clients"
    folder, if the sdk is supposed to exist according to the config, but it doesn't exist in the "generated_clients"
    folder then teh client is regenerated.

    :param application_id: unique identifier fo an application
    :return: bool if deletion of the sdk was successful
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    if "sdkGenerated" in config:
        if config["sdkGenerated"]:
            sdk_path = "./generated_clients/" + config["sdkId"]
            if os.path.exists(sdk_path):
                return True
            else:
                if generate_sdk(application_id):
                    return True
    return False
