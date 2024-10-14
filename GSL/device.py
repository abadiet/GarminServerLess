from .app import App
from .update import Update
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
        self.part_number = self.xml.getroot().find('{*}Model').find('{*}PartNumber').text
        self.max_nb_apps = int(self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}MaxApps').text)
        self.apps = [
            App(name=app_xml.find('{*}AppName').text, ciq_guid=app_xml.find('{*}StoreId').text, version_int=int(app_xml.find('{*}Version').text), filename=app_xml.find('{*}FileName').text, type=App.Type.get(app_xml.find('{*}AppType').text))
            for app_xml in self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps')    
        ]
        info = Device.get_device_info(part_number=self.part_number)
        self.name = info["name"]
        self.url_name = info["urlName"]
        self.additional_names = info["additionalNames"]
        self.image_url = info["imageUrl"]
        self.soft_updates = None
        self.app_updates = None
        self.soft_versions = dict([
            (update_xml.find('{*}PartNumber').text, (int(update_xml.find('{*}Version').find('{*}Major').text), int(update_xml.find('{*}Version').find('{*}Minor').text)))
            for update_xml in self.xml.getroot().find('{*}MassStorageMode').findall('{*}UpdateFile')
        ])

    def get_software_updates(self, force_reload: bool = False) -> list:
        if self.soft_updates is not None and not force_reload:
            return self.soft_updates
        
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
        self.soft_updates = []
        for update_json in resp["SoftwareUpdateOptions"]:
            # check if the update is already installed
            update_major = int(float(update_json["SoftwareVersion"]))
            update_minor = int(float(update_json["SoftwareVersion"]) * 100) % 100
            if update_json["PartNumber"] in self.soft_versions.keys():
                installed_major, installed_minor = self.soft_versions[update_json["PartNumber"]]
            if update_json["PartNumber"] not in self.soft_versions.keys() or update_major > installed_major or (update_major == installed_major and update_minor > installed_minor):
                update = Update(update_json["Changes"], update_json["DisplayName"], update_json["EulaUrl"], update_json["FilePathOnUnit"].replace('\\', '/'), update_json["IsRecommended"], update_json["Url"]["Url"], update_json["Url"]["Md5"], update_json["Url"]["Size"], update_json["Url"]["IsRelative"], update_json["IsRestartRequired"], update_json["PartNumber"], update_major, update_minor, update_json["IsPrimaryFirmware"], update_json["Locale"], update_json["ChangeSeverity"], update_json["IsReinstall"], Update.Type.get(update_json["DataType"]), int(update_json["InstallationOrder"]))
                self.soft_updates.append(update)
        self.soft_updates.sort(key=lambda update: update.installation_order)

        return self.soft_updates

    def get_app_updates(self, force_reload: bool = False) -> list:
        if self.app_updates is not None and not force_reload:
            return self.app_updates
        raise NotImplementedError("App updates are not implemented yet")

    def get_updates(self, force_reload: bool = False) -> list:    
        return self.get_software_updates(force_reload) + self.get_app_updates(force_reload)

    def get_updates_names(self) -> list:
        return [update.display_name for update in self.get_updates()]

    def update(self, update_id: int = None, update_name: str = None) -> list:
        if self.updates is None:
            self.get_updates()
        if update_name is not None:
            if update_name not in self.get_updates_names():
                raise Exception(f"Invalid update name: {update_name}")
            for i, update in enumerate(self.updates):
                if update.display_name == update_name:
                    return [self.updates.pop(i).process(self.device_path)]
        if update_id is not None:
            if update_id >= len(self.updates):
                raise Exception(f"Invalid update id: {update_id}")
            return [self.updates.pop(update_id).process(self.device_path)]
        paths = []
        for update in self.updates:
            paths.append(update.process(self.device_path))
        self.updates = []
        return paths

    def install(self, session_cookie: str, app: App = None, locale: str = 'en-us', **kwargs) -> None:
        if len(self.apps) >= self.max_nb_apps:
            raise Exception("The maximum number of apps is already installed")
        if app is None:
            app = App(**kwargs)
        if app.guid in [app.guid for app in self.apps]:
            raise Exception("The app is already installed")
        app_filepath = os.path.join(self.device_path, f"GARMIN/APPS/{app.guid}.PRG")
        set_filepath = os.path.join(self.device_path, f"GARMIN/APPS/SETTINGS/{app.guid}.SET")
        app.filename = f'{app.guid}.PRG'
        app.download(device_url_name=self.url_name, output_path=app_filepath, session_cookie=session_cookie)
        app.download_settings(device_part_number=self.part_number, output_path=set_filepath, locale=locale)
        app_xml = app.parse_xml()
        self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps').append(app_xml)
        xml_str = ElementTree.tostring(self.xml.getroot(), encoding='unicode', method='xml')
        xml_str = re.sub(r"ns\d+:", "", xml_str)
        with open(self.xml_filepath, "w") as f:
            f.write(xml_str)
        self.apps.append(app)
        # TODO: What are doing 'AppSpace', 'AppId' and RSA keys in the xml file?
