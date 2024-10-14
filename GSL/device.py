from .app import App
from .update import FirmwareUpdate, AppUpdate
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

    def __init__(self, device_path: str):
        self.device_path = device_path
        self.xml_filepath = os.path.join(device_path, "GARMIN/GarminDevice.xml")
        with open(self.xml_filepath, "r") as f:
            self.xml_raw = f.read()
        self.xml = ElementTree.parse(self.xml_filepath)
        # TODO: check xml schema
        self.part_number = self.xml.getroot().find('{*}Model').find('{*}PartNumber').text
        self.max_nb_apps = int(self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}MaxApps').text)
        self.apps = [
            App(
                name=app_xml.find('{*}AppName').text,
                ciq_guid=app_xml.find('{*}StoreId').text,
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
                    datatype.find('{*}Name').text,
                    [
                        Datatype.File(
                            file.find('{*}Location').find('{*}Path').text,
                            file.find('{*}Specification').find('{*}Identifier').text if file.find('{*}Specification').find('{*}Identifier') is not None else None,
                            file.find('{*}Location').find('{*}BaseName').text if file.find('{*}Location').find('{*}BaseName') is not None else None,
                            Datatype.TransfertDirection.get(file.find('{*}TransferDirection').text) if file.find('{*}TransferDirection') is not None else None,
                            file.find('{*}Location').find('{*}FileExtension').text if file.find('{*}Location').find('{*}FileExtension') is not None else None,
                            bool(file.find('{*}Location').find('{*}SupportsBackup').text) if file.find('{*}Location').find('{*}SupportsBackup') is not None else None,
                            file.find('{*}Location').find('{*}ExternalPath').text if file.find('{*}Location').find('{*}ExternalPath') is not None else None
                        )
                        for file in datatype.findall('{*}File')
                    ]
                )
            )
            for datatype in self.xml.getroot().find('{*}MassStorageMode').findall('{*}DataType')
        ])
        info = Device.get_device_info(part_number=self.part_number)
        self.name = info["name"]
        self.url_name = info["urlName"]
        self.additional_names = info["additionalNames"]
        self.image_url = info["imageUrl"]
        self.firmware_updates = None
        self.app_updates = None

    def get_firmware_updates(self, force_reload: bool = False) -> list:
        if self.firmware_updates is not None and not force_reload:
            return self.firmware_updates
        
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
            raise Exception(f"Failed to get the updates {resp.url}: {resp.text}")

        resp = resp.json()
        self.firmware_updates = []
        for update_json in resp["SoftwareUpdateOptions"]:
            # check if the update is already installed
            update_major = int(float(update_json["SoftwareVersion"]))
            update_minor = int(float(update_json["SoftwareVersion"]) * 100) % 100
            if update_json["PartNumber"] in self.firmware_versions.keys():
                installed_major, installed_minor = self.firmware_versions[update_json["PartNumber"]]
            if update_json["PartNumber"] not in self.firmware_versions.keys() or update_major > installed_major or (update_major == installed_major and update_minor > installed_minor):
                update = FirmwareUpdate(
                    update_json["Url"]["IsRelative"],
                    update_json["Url"]["Url"],
                    update_json["FilePathOnUnit"].replace('\\', '/'),
                    self.device_path,
                    update_json["Changes"],
                    update_json["DisplayName"],
                    update_json["EulaUrl"],
                    update_json["IsRecommended"],
                    update_json["Url"]["Md5"],
                    update_json["Url"]["Size"],
                    update_json["IsRestartRequired"],
                    update_json["PartNumber"],
                    update_major,
                    update_minor,
                    update_json["IsPrimaryFirmware"],
                    update_json["Locale"],
                    update_json["ChangeSeverity"],
                    update_json["IsReinstall"],
                    FirmwareUpdate.Type.get(update_json["DataType"]),
                    int(update_json["InstallationOrder"])
                )
                self.firmware_updates.append(update)
        self.firmware_updates.sort(key=lambda update: update.installation_order)

        return self.firmware_updates

    def get_app_updates(self, session_cookie: str = None, force_reload: bool = False) -> list:
        if self.app_updates is not None and not force_reload:
            return self.app_updates

        if session_cookie is None:
            raise Exception("Session cookie is required to get the app updates")

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
            raise Exception(f"Failed to get the app updates {resp.url}: {resp.text}")

        resp = resp.json()
        self.app_updates = []
        for update_json in resp:

            app_type = App.Type.get(update_json["type"])

            # TODO: assuming there is only one file (files[0])
            unit_path = self.datatypes[App.Type.get_datatype_key(app_type)].files[0].path

            installed_app = [app for app in self.apps if app.guid == update_json["appId"]][0]

            if update_json["latestInternalVersionNumber"] > installed_app.version_int:
                update = AppUpdate(
                    update_json["appId"],
                    self.url_name,
                    session_cookie,
                    os.path.join(unit_path, installed_app.filename),
                    self.device_path,
                    update_json["developerName"],
                    update_json["name"],
                    app_type,
                    update_json["size"],
                    update_json["latestInternalVersionNumber"],
                    update_json["latestVersionName"],
                    update_json["permissionsChanged"],
                    [AppUpdate.Permission.get(permission_str) for permission_str in update_json["permissions"]],
                    update_json["hasSettings"],
                    update_json["minFirmwareVersion"],
                    update_json["maxFirmwareVersion"]
                )

                self.app_updates.append(update)

        return self.app_updates

    def get_updates(self, session_cookie: str = None, force_reload: bool = False) -> list:    
        return self.get_firmware_updates(force_reload) + self.get_app_updates(session_cookie, force_reload)

    def get_firmware_updates_names(self, force_reload: bool = False) -> list:
        return [update.name for update in self.get_firmware_updates(force_reload)]

    def get_apps_updates_names(self, session_cookie: str = None, force_reload: bool = False) -> list:
        return [update.name for update in self.get_app_updates(session_cookie, force_reload)]

    def get_updates_names(self, session_cookie: str = None, force_reload: bool = False) -> list:
        return [update.name for update in self.get_updates(session_cookie, force_reload)]

    def update_firmwares(self, update_id: int = None, update_name: str = None, force_reload: bool = False) -> list:
        # by name
        if update_name is not None:
            if update_name not in self.get_firmware_updates_names(force_reload):
                raise Exception(f"Invalid update name: {update_name}")
            for i, update in enumerate(self.firmware_updates):
                if update.name == update_name:
                    return [self.firmware_updates.pop(i).process()]
        
        # by id
        if update_id is not None:
            if update_id >= len(self.get_firmware_updates(force_reload)):
                raise Exception(f"Invalid update id: {update_id}")
            return [self.firmware_updates.pop(update_id).process()]

        # all
        paths = []
        for update in self.get_firmware_updates(force_reload):
            paths.append(update.process())
        self.firmware_updates = []
        return paths

    def update_apps(self, update_id: int = None, update_name: str = None, session_cookie: str = None, force_reload: bool = False) -> list:
        # by name
        if update_name is not None:
            if update_name not in self.get_apps_updates_names(session_cookie, force_reload):
                raise Exception(f"Invalid update name: {update_name}")
            for i, update in enumerate(self.app_updates):
                if update.name == update_name:
                    return [self.app_updates.pop(i).process()]
        
        # by id
        if update_id is not None:
            if update_id >= len(self.get_app_updates(session_cookie, force_reload)):
                raise Exception(f"Invalid update id: {update_id}")
            return [self.app_updates.pop(update_id).process()]

        # all
        paths = []
        for update in self.get_app_updates(session_cookie, force_reload):
            paths.append(update.process())
        self.app_updates = []
        return paths

    def update(self, update_id: int = None, update_name: str = None, session_cookie: str = None, force_reload: bool = False) -> list:
        # by name
        if update_name is not None:
            if update_name not in self.get_updates_names(session_cookie, force_reload):
                raise Exception(f"Invalid update name: {update_name}")
            for i, update in enumerate(self.firmware_updates):
                if update.name == update_name:
                    return [self.firmware_updates.pop(i).process()]
            for i, update in enumerate(self.app_updates):
                if update.name == update_name:
                    return [self.app_updates.pop(i).process()]

        # by id
        if update_id is not None:
            if update_id >= len(self.get_updates(session_cookie, force_reload)):
                raise Exception(f"Invalid update id: {update_id}")
            if update_id < len(self.firmware_updates):
                return [self.firmware_updates.pop(update_id).process()]
            return [self.app_updates.pop(update_id - len(self.firmware_updates)).process()]

        # all
        paths = []
        for update in self.get_updates(session_cookie, force_reload):
            paths.append(update.process())
        self.updates = []
        return paths

    def install(self, session_cookie: str, app: App = None, locale: str = 'en-us', **kwargs) -> None:
        if len(self.apps) >= self.max_nb_apps:
            raise Exception("The maximum number of apps is already installed")
        if app is None:
            app = App(**kwargs, force_load_info=True)
        if app.guid in [app.guid for app in self.apps]:
            raise Exception("The app is already installed")

        # application file
        filetype = self.datatypes[App.Type.get_datatype_key(app.type)].files[0]   # TODO: assuming there is only one file (files[0])
        file_extension = filetype.extension
        if file_extension is None:
            print("The file extension is not defined in the xml file: defaulting to .PRG")
            file_extension = "PRG"
        if filetype.transfert_direction is None:
            print("The transfert direction is not defined in the xml file: we assume it is either an input to the unit or an input/output")
        elif filetype.transfert_direction == Datatype.TransfertDirection.OutputFromUnit:
            raise Exception("The transfert direction is output from the unit")
        app.filename = f'{app.guid}.{file_extension}'
        app_filepath = os.path.join(self.device_path, filetype.path, app.filename)

        # settings file
        filetype = self.datatypes[App._settings_datatype_key].files[0]   # TODO: assuming there is only one file (files[0])
        file_extension = filetype.extension
        if file_extension is None:
            print("The file extension is not defined in the xml file: defaulting to .SET")
            file_extension = "SET"
        if filetype.transfert_direction is None:
            print("The transfert direction is not defined in the xml file: we assume it is either an input to the unit or an input/output")
        elif filetype.transfert_direction == Datatype.TransfertDirection.OutputFromUnit:
            raise Exception("The transfert direction is output from the unit")
        set_filepath = os.path.join(self.device_path, filetype.path, f'{app.guid}.{file_extension}')

        # download the app and the settings
        app.download(device_url_name=self.url_name, output_path=app_filepath, session_cookie=session_cookie)
        app.download_settings(device_part_number=self.part_number, output_path=set_filepath, locale=locale)

        # update the xml file
        app_xml = app.parse_xml()
        self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps').append(app_xml)
        xml_str = ElementTree.tostring(self.xml.getroot(), encoding='unicode', method='xml')
        xml_str = re.sub(r"ns\d+:", "", xml_str)
        with open(self.xml_filepath, "w") as f:
            f.write(xml_str)

        # update the apps list
        self.apps.append(app)

        # TODO: What are doing 'AppSpace', 'AppId' and RSA keys in the xml file?
