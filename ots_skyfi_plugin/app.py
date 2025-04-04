import os
import pathlib
import traceback

import requests
import yaml
from flask import Blueprint, render_template, jsonify, Flask, current_app as app, send_from_directory, request
from flask_security import roles_accepted
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import *

from .default_config import DefaultConfig
import importlib.metadata

BASE_URL = "https://app.skyfi.com/platform-api/"


class SkyFiPlugin(Plugin):
    # Do not change url_prefix
    url_prefix = f"/api/plugins/{pathlib.Path(__file__).resolve().parent.name}"
    blueprint = Blueprint("SkyFiPlugin", __name__, url_prefix=url_prefix)

    def __init__(self):
        super().__init__()
        self.load_metadata()

    # This is your plugin's entry point. It will be called from OpenTAKServer to start the plugin
    def activate(self, app: Flask):
        # Do not change these three lines
        self._app = app
        self._load_config()
        self.load_metadata()

        try:
            # Do stuff here
            logger.info(f"Successfully Loaded {self.name}")
        except BaseException as e:
            logger.error(f"Failed to load {self.name}: {e}")
            logger.error(traceback.format_exc())

    # Do not change this
    def load_metadata(self):
        try:
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    self.name = distributions[distro][0]
                    self.distro = distro
                    info = importlib.metadata.metadata(self.distro)
                    self._metadata = info.json
                    break

        except BaseException as e:
            logger.error(e)

    # Loads default config and user config from ~/ots/config.yml
    # Do not change
    def _load_config(self):
        # Gets default config key/value pairs from the plugin's default_config.py
        for key in dir(DefaultConfig):
            if key.isupper():
                self._config[key] = getattr(DefaultConfig, key)
                self._app.config.update({key: getattr(DefaultConfig, key)})

        # Get user overrides from config.yml
        with open(os.path.join(self._app.config.get("OTS_DATA_FOLDER"), "config.yml")) as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            for key in self._config.keys():
                value = yaml_config.get(key)
                if value:
                    self._config[key] = value
                    self._app.config.update({key: value})

    def get_info(self):
        self.load_metadata()
        self.get_plugin_routes(self.url_prefix)
        return {'name': self.name, 'distro': self.distro, 'routes': self.routes}

    def stop(self):
        # Shut down your plugin gracefully here
        pass

    # Make route methods static to avoid "no-self-use" errors
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/")
    def plugin_info():  # Do not put "self" as a method parameter here
        # This method will return JSON with info about the plugin derived from pyproject.toml, please do not change it
        # Make sure that your plugin has a README.md to show in the UI's about page
        try:
            distribution = None
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    distribution = distributions[distro][0]
                    break

            if distribution:
                info = importlib.metadata.metadata(distribution)
                return jsonify(info.json)
            else:
                return jsonify({'success': False, 'error': 'Plugin not found'}), 404
        except BaseException as e:
            logger.error(e)
            return jsonify({'success': False, 'error': e}), 500

    # OpenTAKServer's web UI will display your plugin's UI in an iframe
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/ui")
    def ui():
        # Uncomment the following line if your plugin does not require a UI
        # return '', 200

        # Otherwise use this line if your plugin requires a UI
        return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui", "index.html", as_attachment=False)

    # Endpoint to serve static UI files
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route('/assets/<file_name>')
    def serve(file_name):
        logger.debug(f"Path: {file_name}")
        logger.warning(os.path.join(pathlib.Path(__file__).parent.resolve(), "ui", "assets", file_name))
        if file_name != "" and os.path.exists(os.path.join(pathlib.Path(__file__).parent.resolve(), "ui", "assets", file_name)):
            logger.info(f"Serving {file_name}")
            return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui/assets", file_name)
        else:
            return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui", 'index.html')

    # Gets the plugin config for the web UI, do not change
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config")
    def config():
        config = {}

        for key in dir(DefaultConfig):
            if key.isupper():
                config[key] = app.config.get(key)

        return jsonify(config)

    # Updates the plugin config
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config", methods=["POST"])
    def update_config():
        try:
            result = DefaultConfig.update_config(request.json)
            if result["success"]:
                DefaultConfig.update_config(request.json)
                return jsonify(result)
            else:
                return jsonify(result), 400
        except BaseException as e:
            logger.error("Failed to update config:" + str(e))
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 400

    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/orders", methods=["GET"])
    def get_orders():
        try:
            page = 0
            if request.args.get("page"):
                page = request.args.get("page")

            # The user's browser can't query the SkyFi API directly due to CORS so we do it this way instead
            r = requests.get(f"{BASE_URL}/orders", headers={"X-Skyfi-Api-Key": app.config["OTS_SKYFI_PLUGIN_API_KEY"]}, json={}, params={"page": page})

            if r.status_code == 200:
                return jsonify(r.json())
            else:
                return jsonify({"success": False, "error": "Please check your API key and try again"}), 400

        except BaseException as e:
            logger.error(f"Failed to get orders:{e}")
            return jsonify({"success": False, "error": f"Failed to get orders: {str(e)}"}), 400
