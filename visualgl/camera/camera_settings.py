import enum
import json
import math
import pathlib


class CameraSettings:
    class Defaults(enum.Enum):
        # TODO: This shouldn't be a setting. The caller should pass the path.
        FILE_PATH = str(pathlib.Path(__file__).parent.parent.resolve()) + "\settings.json"
        ORBIT_SPEED = 0.05
        ROLL_SPEED = 0.005
        SCALE_SPEED = 5
        ORBIT_STEP = math.radians(5)
        ROLL_STEP = math.radians(5)
        SCALE_STEP = 100
        TRACK_STEP = 20
        SCALE_IN = 1
        FIT_SCALE = 0.75

    # TODO: Accept a dictionary instead of a file path. Create a CameraSettings.from_file() constructor instead.
    def __init__(self, path=Defaults.FILE_PATH.value):
        self.get_settings(path)

        self.needs_write = {}

    def __getattr__(self, attribute):
        if attribute == "needs_write":
            self.needs_write = {}
            return self.needs_write

        return getattr(self.Defaults, str.upper(attribute)).value

    def __setattr__(self, attribute, value):
        self.__dict__[attribute] = value
        if attribute != "needs_write":
            self.needs_write[attribute] = value

    def get_settings(self, path):
        settings = self.load(path)
        for name, value in settings["camera"].items():
            setattr(self, str.upper(name), value)

    def load(self, path):
        with open(path) as f:
            return json.load(f)

    def write(self, path=Defaults.FILE_PATH.value):
        settings = self.load(path)
        with open(path, "w") as f:
            for name, value in self.needs_write.items():
                settings["camera"][name] = value
            json.dump(settings, f, indent=2)
