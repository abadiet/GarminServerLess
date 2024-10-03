import requests
from enum import Enum
import hashlib
import os


class Update:
    class ChangeSeverity(Enum):
        UNSPECIFIED = 0
        CRITICAL = 1
        RECOMMENDED = 2
        OPTIONAL = 3

    class Type(Enum):
        PrimaryFirmware = 0
        Firmware = 1
        Map = 2
        Garage  = 3
        Computer = 4
        LanguagePack = 5
        ConnectItem = 6
        Application = 7
        SafetyCamera = 8
        MarineChart = 9
        GeneralDlc = 10

        @staticmethod
        def get(type_str: str):
            match type_str:
                case "PrimaryFirmware":
                    return Update.Type.PrimaryFirmware
                case "Firmware":
                    return Update.Type.Firmware
                case "Map":
                    return Update.Type.Map
                case "Garage":
                    return Update.Type.Garage
                case "Computer":
                    return Update.Type.Computer
                case "LanguagePack":
                    return Update.Type.LanguagePack
                case "ConnectItem":
                    return Update.Type.ConnectItem
                case "Application":
                    return Update.Type.Application
                case "SafetyCamera":
                    return Update.Type.SafetyCamera
                case "MarineChart":
                    return Update.Type.MarineChart
                case "GeneralDlc":
                    return Update.Type.GeneralDlc
                case _:
                    raise Exception(f"Invalid update type: {type_str}")

    def __init__(self, changes: list = None, display_name: str = None, eula_url: str = None, unit_filepath: str = None, is_recommended: bool = None, url: str = None, md5: str = None, size: int = None, url_is_relative: bool = None, is_restart_required: bool = None, part_number: str = None, version: str = None, is_primary_firmware: bool = None, locale: str = None, change_severity: ChangeSeverity = None, is_reinstall: bool = None, type: Type = None):
        self.changes = changes
        self.display_name = display_name
        self.eula_url = eula_url
        self.unit_filepath = unit_filepath
        self.is_recommended = is_recommended
        self.url = url
        self.md5 = md5
        self.size = size
        self.url_is_relative = url_is_relative
        self.is_restart_required = is_restart_required
        self.part_number = part_number
        self.version = version
        self.is_primary_firmware = is_primary_firmware
        self.locale = locale
        self.change_severity = change_severity
        self.is_reinstall = is_reinstall
        self.type = type

    def fix_path_case(self, current_path, path_parts=[]):
        path_dir = os.path.dirname(current_path)
        if not os.path.isdir(path_dir):
            path_parts.append(os.path.basename(current_path))
            # check until a proper directory parent path is found
            return self.fix_path_case(path_dir, path_parts)
        else:
            if len(path_parts) > 0:
                #try to check if uppercase director exists
                new_dir_path = os.path.join(path_dir, os.path.basename(current_path).upper())
                if not os.path.isdir(new_dir_path):
                    # non existing child directory path found in update
                    # make new path as it is, as this comes from software update
                    new_dir_path = os.path.join(path_dir, os.path.basename(current_path))
                    os.mkdir(new_dir_path)
                new_current_path =  os.path.join(new_dir_path, path_parts.pop())
                return self.fix_path_case(new_current_path, path_parts)
            else:
                return current_path

    def process(self, device_path: str) -> str:
        if self.url_is_relative:
            raise Exception("Relative URLs are not supported")
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download the update {self.name}: {resp.text}")
        if self.size != len(resp.content):
            raise Exception(f"Failed to download the update {self.name}: size does not match")
        if self.md5 != hashlib.md5(resp.content).hexdigest():
            raise Exception(f"Failed to download the update {self.name}: MD5 does not match")
        filepath = os.path.join(device_path, self.unit_filepath)
        filepath = self.fix_path_case(filepath, [])
        with open(filepath, "wb") as f:
            f.write(resp.content)

        # TODO: Update the xml file

        return filepath
