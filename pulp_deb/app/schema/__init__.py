import json
import os

location = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(location, "copy_config.json")) as copy_config_json:
    COPY_CONFIG_SCHEMA = json.load(copy_config_json)
