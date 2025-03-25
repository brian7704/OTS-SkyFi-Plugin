import os
import traceback
from dataclasses import dataclass
from opentakserver.extensions import logger
from flask import current_app as app
import yaml


@dataclass
class DefaultConfig:
    # Config options go here in all caps with the name of your plugin first
    # This file will be loaded first, followed by user overrides from config.yml
    # Make sure not to duplicate any setting name in OpenTAKServers' defaultconfig.py

    OTS_PLUGIN_TEMPLATE_ENABLED = True  # This setting is required. Rename it with your plugin's name
    OTS_PLUGIN_TEMPLATE_SOME_SETTING = "my_setting_value"

    # Use this method to validate config values input by the user in the OTS web UI
    # Make sure the return dict is {"success": bool, "error", "Some error message or blank if no errors"}
    @staticmethod
    def validate(config: dict) -> dict[str, bool | str]:
        try:
            for key, value in config.items():
                if key not in DefaultConfig.__dict__.keys():
                    return {"success": False, "error": f"{key} is not a valid config key"}
                elif key == "OTS_PLUGIN_TEMPLATE_SOME_SETTING" and type(key) is not str:
                    return {"success": False, "error": f"{key} should be a string"}

            return {"success": True, "error": ""}
        except BaseException as e:
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    # In most cases you should keep this method as-is and call it after you successfully validate new config settings
    # Calling this method will write the new settings to config.yml
    @staticmethod
    def save_config_settings(settings: dict[str, any]):
        try:
            with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), "r") as config_file:
                config = yaml.safe_load(config_file.read())

            for setting, value in settings:
                # Update the config to be written to config.yml
                config[setting] = value

                # Update OpenTAKServer's running config
                app.config.update({setting: value})

            with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), "w") as config_file:
                yaml.safe_dump(config, config_file)

        except BaseException as e:
            logger.error(f"Failed to save settings {settings}: {e}")

    # Use this method to first validate user input and then write it to config.yml
    @staticmethod
    def update_config(config: dict) -> dict:
        try:
            valid = DefaultConfig.validate(config)
            if valid["success"]:
                DefaultConfig.save_config_settings(config)
                return {"success": True}
            else:
                return valid
        except BaseException as e:
            logger.error(f"Failed to update config: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}