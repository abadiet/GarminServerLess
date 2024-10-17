from .app import App
from enum import Enum


class Datatype:
    class TransfertDirection(Enum):
        pass


class Datatype:

    class TransfertDirection(Enum):
        InputToUnit = 1,
        OutputFromUnit = 2,
        InputOutput = 3

        @staticmethod
        def get(value: str) -> Datatype.TransfertDirection:
            match value:
                case "InputToUnit":
                    return Datatype.TransfertDirection.InputToUnit
                case "OutputFromUnit":
                    return Datatype.TransfertDirection.OutputFromUnit
                case "InputOutput":
                    return Datatype.TransfertDirection.InputOutput
                case _:
                    raise ValueError(f"Invalid value: {value}")

    class File:
        def __init__(
                self,
                path: str,
                identifier: str = None,
                basename: str = None,
                transfert_direction: Datatype.TransfertDirection = None,
                extension: str = None,
                support_backup: bool = None,
                external_path: str = None
            ):
            self.identifier = identifier
            self.path = path
            self.basename = basename
            self.transfert_direction = transfert_direction
            self.extension = extension
            self.support_backup = support_backup
            self.external_path = external_path
    
    def __init__(self, name: str, files: list):
        self.name = name
        self.files = files
