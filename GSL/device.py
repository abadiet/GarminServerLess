from .app import App
from .update import FirmwareUpdate, AppUpdate, Update
from .filesystem import Datatype
import requests
import xml.etree.ElementTree as ElementTree
import os
import re


class Device:
    _types = None
    _names_idx = dict()
    _part_numbers_idx = dict()

    @staticmethod
    def _load_devices() -> None:
        resp = requests.get("https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/deviceTypes")
        if resp.status_code != 200:
            raise Exception(f"Failed to get the device types {resp.url}: {resp.text}")
        Device._types = resp.json()

        for i, device in enumerate(Device._types):
            Device._names_idx[device['name']] = i
            Device._part_numbers_idx[device['partNumber']] = i

    @staticmethod
    def get_devices_info() -> list:
        if Device._types is None:
            Device._load_devices()
        return Device._types

    @staticmethod
    def get_devices_names() -> list:
        if Device._types is None:
            Device._load_devices()
        return list(Device._names_idx.keys())

    @staticmethod
    def get_devices_part_numbers() -> list:
        if Device._types is None:
            Device._load_devices()
        return list(Device._part_numbers_idx.keys())

    @staticmethod
    def get_device_info(name: str = None, part_number: str = None) -> dict:
        if name is not None:
            if name not in Device.get_devices_names():
                raise Exception(f"Invalid device name: {name}")
            return Device.get_devices_info()[Device._names_idx[name]]
        if part_number is not None:
            if part_number not in Device.get_devices_part_numbers():
                raise Exception(f"Invalid device part number: {part_number}")
            return Device.get_devices_info()[Device._part_numbers_idx[part_number]]
        raise Exception("Either device name or part number is required")

    def __init__(self, device_rootpath: str):

        # read XML file
        self.device_rootpath = device_rootpath
        self.xml_filepath = os.path.join(self.device_rootpath, "GARMIN/GarminDevice.xml")
        self.read_xml()
    
        # check XML schema
        namespace = [elem for _, elem in ElementTree.iterparse(self.xml_filepath, events=['start-ns'])]
        target_ns = [('', 'http://www.garmin.com/xmlschemas/GarminDevice/v2'), ('xsi', 'http://www.w3.org/2001/XMLSchema-instance'), ('', 'http://www.garmin.com/xmlschemas/IqExt/v1')]
        if namespace != target_ns:
            raise NotImplementedError("Unknown XML schema: please report this issue on the GitHub repository to add support for this schema (https://github.com/abadiet/GarminServerLess). Your schema is: {namespace}")

        # parse XML
        try:
            self.part_number = self.xml.getroot().find('{*}Model').find('{*}PartNumber').text
            self.max_nb_apps = int(self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}MaxApps').text)
            self.apps = [
                App(
                    name=app_xml.find('{*}AppName').text,
                    ciq_guid=app_xml.find('{*}StoreId').text,
                    # app_guid=app_xml.find('{*}AppId').text,
                    version_int=int(app_xml.find('{*}Version').text),
                    filename=app_xml.find('{*}FileName').text,
                    type=App.Type.get(app_xml.find('{*}AppType').text)
                )
                for app_xml in self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps')    
            ]
            self.firmware_versions = dict([
                (
                    update_xml.find('{*}PartNumber').text,
                    (
                        int(update_xml.find('{*}Version').find('{*}Major').text),
                        int(update_xml.find('{*}Version').find('{*}Minor').text)
                    )
                )
                for update_xml in self.xml.getroot().find('{*}MassStorageMode').findall('{*}UpdateFile')
            ])
            self.datatypes = dict([
                (
                    datatype.find('{*}Name').text,
                    Datatype(
                        name=datatype.find('{*}Name').text,
                        files=[
                            Datatype.File(
                                path=file.find('{*}Location').find('{*}Path').text,
                                # identifier=file.find('{*}Specification').find('{*}Identifier').text if file.find('{*}Specification').find('{*}Identifier') is not None else None,
                                # basename=file.find('{*}Location').find('{*}BaseName').text if file.find('{*}Location').find('{*}BaseName') is not None else None,
                                transfert_direction=Datatype.TransfertDirection.get(file.find('{*}TransferDirection').text) if file.find('{*}TransferDirection') is not None else None,
                                extension=file.find('{*}Location').find('{*}FileExtension').text if file.find('{*}Location').find('{*}FileExtension') is not None else None,
                                # support_backup=bool(file.find('{*}Location').find('{*}SupportsBackup').text) if file.find('{*}Location').find('{*}SupportsBackup') is not None else None,
                                # external_path=file.find('{*}Location').find('{*}ExternalPath').text if file.find('{*}Location').find('{*}ExternalPath') is not None else None
                            )
                            for file in datatype.findall('{*}File')
                        ]
                    )
                )
                for datatype in self.xml.getroot().find('{*}MassStorageMode').findall('{*}DataType')
            ])
        except Exception as e:
            raise Exception(f"Failed to parse the device XML: {e}")

        # get device additional information
        info = Device.get_device_info(part_number=self.part_number)
        self.name = info["name"]
        self.url_name = info["urlName"]
        self.additional_names = info["additionalNames"]
        self.image_url = info["imageUrl"]

        # init
        self.firmwares_updates = None
        self.apps_updates = None

    def read_xml(self) -> None:
        if not os.path.exists(self.xml_filepath):
            raise FileNotFoundError(f"Device XML file not found: {self.xml_filepath}")
        try:
            with open(self.xml_filepath, "r") as f:
                self.xml_raw = f.read()
        except Exception as e:
            raise Exception(f"Failed to read the device XML file {self.xml_filepath}: {e}")
        self.xml = ElementTree.parse(self.xml_filepath)

    def get_firmwares_updates(self, force_reload: bool = False) -> list:
        if self.firmwares_updates is not None and not force_reload:
            return self.firmwares_updates

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        json = {
            "ClientInfo": {
                # "ClientType": "",
                # "LocaleCode": "",
                # "OperatingSystemType": "",
                # "OperatingSystemVersion": ""
            },
            "GarminDeviceXml": self.xml_raw,        # TODO: use only part of the xml to keep privacy
            "IsUserInteractive": False
        }
        resp = requests.post("https://omt.garmin.com/Rce/ProtobufApi/SoftwareUpdateService/GetAllUnitSoftwareUpdates", headers=headers, json=json)
        if resp.status_code != 200:
            raise Exception(f"Failed to get the firmware updates, error {resp.status_code}:\n{resp.text}")

        try:
            resp = resp.json()
        except Exception as e:
            raise Exception(f"Failed to parse the firmware updates response: {e}")

        self.firmwares_updates = []
        for update_json in resp["SoftwareUpdateOptions"]:

            try:
                # check if the update is already installed
                update_major = int(float(update_json["SoftwareVersion"]))
                update_minor = int(float(update_json["SoftwareVersion"]) * 100) % 100
                if update_json["PartNumber"] in self.firmware_versions.keys():
                    installed_major, installed_minor = self.firmware_versions[update_json["PartNumber"]]
                else:
                    installed_major, installed_minor = None, None
                if (
                    installed_major is None or
                    installed_minor is None or
                    update_major > installed_major or
                    (update_major == installed_major and update_minor > installed_minor)
                ):
                    # adding the update
                    self.firmwares_updates.append(
                        FirmwareUpdate(
                            url_is_relative=update_json["Url"]["IsRelative"],
                            url=update_json["Url"]["Url"],
                            unit_filepath=update_json["FilePathOnUnit"].replace('\\', '/'),
                            # changes=update_json["Changes"],
                            display_name=update_json["DisplayName"],
                            # eula_url=update_json["EulaUrl"],
                            # is_recommended=update_json["IsRecommended"],
                            md5=update_json["Url"]["Md5"],
                            size=update_json["Url"]["Size"],
                            # is_restart_required=update_json["IsRestartRequired"],
                            # part_number=update_json["PartNumber"],
                            # major=update_major,
                            # minor=update_minor,
                            # is_primary_firmware=update_json["IsPrimaryFirmware"],
                            # locale=update_json["Locale"],
                            # change_severity=update_json["ChangeSeverity"],
                            # is_reinstall=update_json["IsReinstall"],
                            type=Update.Type.get(update_json["DataType"]),
                            installation_order=int(update_json["InstallationOrder"])
                        )
                    )

            except Exception as e:
                print(f"[WARNING] Failed to parse a firmware update, skipping this update: {e}")

        # sort by installation order
        self.firmwares_updates.sort(key=lambda update: update.installation_order)

        return self.firmwares_updates

    def get_apps_updates(self, session_cookie: str = None, force_reload: bool = False) -> list:
        if self.apps_updates is not None and not force_reload:
            return self.apps_updates

        if session_cookie is None:
            raise Exception("A session cookie is required to get the app updates")

        cookies = {"session": session_cookie}
        headers = {
            "Content-Type": "application/json",
            "X-garmin-client-id": "EXPRESS"
        }
        json = {
            "apps": [
                {"appId": app.guid, "internalVersionNumber": app.version_int} for app in self.apps
            ],
            "deviceSKU": self.part_number,
            "locale": "",
        }
        resp = requests.post("https://services.garmin.com/express/appstore/rest/apps/updates", headers=headers, cookies=cookies, json=json)
        if resp.status_code != 200:
            raise Exception(f"Failed to get the app updates, error {resp.status_code}:\n{resp.text}")

        try:
            resp = resp.json()
        except Exception as e:
            raise Exception(f"Failed to parse the app updates response: {e}")

        self.apps_updates = []
        for update_json in resp:
            try:
                # get the application path on the device
                app_type = App.Type.get(update_json["type"])
                # TODO: assuming there is only one file (files[0])
                type_files = self.datatypes[App.Type.get_datatype_key(app_type)].files
                if len(type_files) != 1:
                    raise Exception(f"{len(type_files)} file{'s are' if len(type_files) > 0 else ' is'} available for the datatype associated to the application type {app_type}")
                unit_path = type_files[0].path

                # check if the update is already installed
                installed_app = [app for app in self.apps if app.guid == update_json["appId"]][0]
                if update_json["latestInternalVersionNumber"] > installed_app.version_int:

                    # adding the update
                    self.apps_updates.append(
                        AppUpdate(
                            app_guid=update_json["appId"],
                            unit_filepath=os.path.join(unit_path, installed_app.filename),
                            # developer_name=update_json["developerName"],
                            name=update_json["name"],
                            # type=app_type,
                            size=update_json["size"],
                            # version_int=update_json["latestInternalVersionNumber"],
                            # version_name=update_json["latestVersionName"],
                            # has_permissions_changed=update_json["permissionsChanged"],
                            # permissions=[AppUpdate.Permission.get(permission_str) for permission_str in update_json["permissions"]],
                            # has_settings=update_json["hasSettings"],
                            # min_version_firmware=update_json["minFirmwareVersion"],
                            # max_version_firmware=update_json["maxFirmwareVersion"]
                        )
                    )

            except Exception as e:
                print(f"[WARNING] Failed to parse an application update, skipping this update: {e}")

        return self.apps_updates

    def get_updates(self, session_cookie: str = None, force_reload: bool = False) -> list:    
        return self.get_firmwares_updates(force_reload) + self.get_apps_updates(session_cookie, force_reload)

    def get_firmwares_updates_name(self, force_reload: bool = False) -> list:
        return [update.name for update in self.get_firmwares_updates(force_reload)]

    def get_apps_updates_name(self, session_cookie: str = None, force_reload: bool = False) -> list:
        return [update.name for update in self.get_apps_updates(session_cookie, force_reload)]

    def get_updates_name(self, session_cookie: str = None, force_reload: bool = False) -> list:
        return [update.name for update in self.get_updates(session_cookie, force_reload)]

    def update_firmwares(self, ids: list | int = None, names: list | str = None, force_reload: bool = False) -> list:
        paths = []

        # Reload if forced
        if force_reload:
            self.get_firmwares_updates(force_reload=True)

        # check the inputs
        if ids is not None and names is not None:
            raise Exception("Either ids or names can be provided, not both")
        if ids is not None and isinstance(ids, int):
            ids = [ids]
        if names is not None and isinstance(names, str):
            names = [names]

        # by name
        if names is not None:
            updates_name = self.get_firmwares_updates_name(force_reload=False)
            # check the names
            for name in names:
                if name not in updates_name:
                    raise Exception(f"Invalid firmware update name: {name}")
            # look for the updates in the firmware updates list
            ids_torm = []
            for id, update in enumerate(self.get_firmwares_updates(force_reload=False)):
                if update.name in names:
                    paths.append(self.firmwares_updates.pop(id).process(self.device_rootpath))
                    ids_torm.append(id)
            for id in ids_torm:
                self.apps_updates.pop(id)

        # by id
        if ids is not None:
            max_id = len(self.get_firmwares_updates(force_reload=False))
            for id in ids:
                if id >= max_id:
                    raise Exception(f"Invalid firmware update id: {id}")
                paths.append(self.firmwares_updates.pop(id).process(self.device_rootpath))

        # all
        if ids is None and names is None:
            for update in self.get_firmwares_updates(force_reload=False):
                paths.append(update.process(self.device_rootpath))
            self.firmwares_updates = []

        print ("[WARNING] The firmwares' updates have been processed but the XML file has not been updated: this feature is not implemented yet.")
        # TODO update the xml file

        return paths

    def update_apps(self, session_cookie: str, ids: list | int = None, names: list | str = None, force_reload: bool = False) -> list:
        paths = []

        # Reload if forced
        if force_reload:
            self.get_apps_updates(session_cookie=session_cookie, force_reload=True)

        # check the inputs
        if ids is not None and names is not None:
            raise Exception("Either ids or names can be provided, not both")
        if ids is not None and isinstance(ids, int):
            ids = [ids]
        if names is not None and isinstance(names, str):
            names = [names]

        # by name
        if names is not None:
            updates_name = self.get_apps_updates_name(session_cookie=session_cookie, force_reload=False)
            # check the names
            for name in names:
                if name not in updates_name:
                    raise Exception(f"Invalid application update name: {name}")
            # look for the updates in the apps updates list
            ids_torm = []
            for id, update in enumerate(self.get_apps_updates(session_cookie=session_cookie, force_reload=False)):
                if update.name in names:
                    paths.append(update.process(self.device_rootpath, self.url_name, session_cookie))
                    ids_torm.append(id)
            for id in ids_torm:
                self.apps_updates.pop(id)

        # by id
        if ids is not None:
            max_id = len(self.get_apps_updates(session_cookie=session_cookie, force_reload=False))
            for id in ids:
                if id >= max_id:
                    raise Exception(f"Invalid application update id: {id}")
                paths.append(self.apps_updates.pop(id).process(self.device_rootpath, self.url_name, session_cookie))

        # all
        if ids is None and names is None:
            for update in self.get_apps_updates(session_cookie=session_cookie, force_reload=False):
                paths.append(update.process(self.device_rootpath, self.url_name, session_cookie))
            self.apps_updates = []

        print ("[WARNING] The applications' updates have been processed but the XML file has not been updated: this feature is not implemented yet.")
        # TODO update the xml file

        return paths

    def update(self, session_cookie: str, ids: list | int = None, names: list | str = None, force_reload: bool = False) -> list:
        paths = []

        # Reload if forced
        if force_reload:
            self.get_updates(session_cookie=session_cookie, force_reload=True)

        # check the inputs
        if ids is not None and names is not None:
            raise Exception("Either ids or names can be provided, not both")
        if ids is not None and isinstance(ids, int):
            ids = [ids]
        if names is not None and isinstance(names, str):
            names = [names]

        # by name
        if names is not None:
            names_firmwares = [name for name in names if name in self.get_firmwares_updates_name(force_reload=False)]
            names_apps = [name for name in names if name in self.get_apps_updates_name(session_cookie=session_cookie, force_reload=False)]
            paths += self.update_firmwares(names=names_firmwares, force_reload=False)
            paths += self.update_apps(session_cookie=session_cookie, names=names_apps, force_reload=False)

        # by id
        if ids is not None:
            max_firmwares_id = len(self.get_firmwares_updates(force_reload=False))
            max_apps_id = len(self.get_updates(session_cookie=session_cookie, force_reload=False))
            ids_firmwares = [id for id in ids if id < max_firmwares_id]
            ids_apps = [(id - max_firmwares_id) for id in ids if (id >= max_firmwares_id and id < max_apps_id)]
            paths += self.update_firmwares(ids=ids_firmwares, force_reload=False)
            paths += self.update_apps(session_cookie=session_cookie, ids=ids_apps, force_reload=False)

        if ids is None and names is None:
            paths += self.update_firmwares(force_reload=False)
            paths += self.update_apps(session_cookie=session_cookie, force_reload=False)

        return paths

    def install(self, session_cookie: str, app: App = None, locale: str = 'en-us', **kwargs) -> bool:

        # check if an application can be installed
        if len(self.apps) >= self.max_nb_apps:
            print("[WARNING] Maximum number of applications reached, skipping the installation")
            return False

        # load app if needed
        if app is None:
            app = App(**kwargs, force_load_info=True)

        # check if the app is already installed
        if app.guid in [app.guid for app in self.apps]:
            print("[WARNING] The application is already installed, skipping the installation")
            return False

        # application file
        type_files = self.datatypes[App.Type.get_datatype_key(app.type)].files
        if len(type_files) != 1:
            raise Exception(f"{len(type_files)} file{'s are' if len(type_files) > 0 else ' is'} available for the datatype associated to the application type {app.type}")
        type_file = type_files[0]
        file_extension = type_file.extension
        if file_extension is None:
            print("[WARNING] The file extension is not defined in the xml file: defaulting to .PRG")
            file_extension = "PRG"
        if type_file.transfert_direction is None:
            print("[WARNING] The transfert direction is not defined in the xml file: assuming it is either an input to the unit or an input/output")
        elif type_file.transfert_direction == Datatype.TransfertDirection.OutputFromUnit:
            raise Exception("The transfert direction is output from the unit")
        app.filename = f'{app.guid}.{file_extension}'
        app_filepath = os.path.join(self.device_rootpath, type_file.path, app.filename)

        # settings file
        type_files = self.datatypes[App._settings_datatype_key].files
        if len(type_files) != 1:
            raise Exception(f"{len(type_files)} file{'s are' if len(type_files) > 0 else ' is'} available for the datatype associated to the setting type {App._settings_datatype_key}")
        type_file = type_files[0]
        file_extension = type_file.extension
        if file_extension is None:
            print("[WARNING] The file extension is not defined in the xml file: defaulting to .SET")
            file_extension = "SET"
        if type_file.transfert_direction is None:
            print("[WARNING] The transfert direction is not defined in the xml file: assuming it is either an input to the unit or an input/output")
        elif type_file.transfert_direction == Datatype.TransfertDirection.OutputFromUnit:
            raise Exception("The transfert direction is output from the unit")
        set_filepath = os.path.join(self.device_rootpath, type_file.path, f'{app.guid}.{file_extension}')

        # download the app and the settings
        try:
            app.download(device_url_name=self.url_name, output_path=app_filepath, session_cookie=session_cookie)
            if app.has_settings:
                app.download_settings(device_part_number=self.part_number, output_path=set_filepath, locale=locale)
        except Exception as e:
            raise Exception(f"Failed to download the application and the settings: {e}")

        # update the xml file
        try:
            app_xml = app.parse_xml()
            new_xml_raw = self.xml_raw.replace("</Apps>", f"{app_xml}</Apps>")
            with open(self.xml_filepath, "w") as f:
                f.write(new_xml_raw)
            self.read_xml()
        except Exception as e:
            raise Exception(f"Failed to update the device XML file: {e}")

        # update the apps list
        self.apps.append(app)

        # TODO: What are doing 'AppSpace', 'AppId' and RSA keys in the xml file?

        return True
