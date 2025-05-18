import re
from ..Script import Script

class LevelingMeshOptimizer(Script):
    def getSettingDataString(self):
        return """{
            "name": "Leveling Mesh Optimizer",
            "key": "LevelingMeshOptimizer",
            "metadata": {},
            "version": 2,
            "settings": {
                "spacing": {
                    "label": "Spacing",
                    "description": "How far apart to space the probe points within the mesh",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 10
                },
                "scaling_factor": {
                    "label": "Scaling Factor",
                    "description": "Factor used to adjust the grid density dynamically",
                    "unit": "float",
                    "type": "float",
                    "default_value": 0.08
                },
                "min_grid_size": {
                    "label": "Min Grid Size",
                    "description": "Minimum number of points in the grid",
                    "unit": "int",
                    "type": "int",
                    "default_value": 3
                },
                "max_grid_size": {
                    "label": "Max Grid Size",
                    "description": "Maximum number of points in the grid",
                    "unit": "int",
                    "type": "int",
                    "default_value": 9
                }
            }
        }"""

    ## Calculates and fills in the bounds of the first layer.
    def execute(self, data: [str]) -> [str]:
        _DATA_START_GCODE = 1
        _DATA_LAYER_0 = 2

        # Calculate bounds of first layer
        bounds = self.findBounds(data[_DATA_LAYER_0])

        # Determine grid size dynamically based on model size and user settings
        grid_size_x, grid_size_y = self.calculateGridSize(bounds)

        # Fill in bounds in start GCODE
        data[_DATA_START_GCODE] = self.fillBounds(data[_DATA_START_GCODE], bounds, grid_size_x, grid_size_y)

        return data

    ## Finds the min and max X and Y coordinates in a G-code layer.
    def findBounds(self, data: str) -> {str: {str: float}}:
        bounds = {
            "X": {"min": float("inf"), "max": float("-inf")},
            "Y": {"min": float("inf"), "max": float("-inf")},
        }

        for line in data.split("\n"):
            for match in re.findall(r"([XY])([\d.]+)", line):
                axis = match[0]
                if axis not in bounds:
                    continue
                value = float(match[1])
                bounds[axis]["min"] = min(bounds[axis]["min"], value)
                bounds[axis]["max"] = max(bounds[axis]["max"], value)

        return bounds

    ## Determines the optimal grid size using an adaptive scaling factor & user settings.
    def calculateGridSize(self, bounds: {str: {str: float}}) -> (int, int):
        model_width = bounds["X"]["max"] - bounds["X"]["min"]
        model_height = bounds["Y"]["max"] - bounds["Y"]["min"]

        scaling_factor = 0.08  # The adaptive scaling factor to adjust mesh density
        min_grid_size = 3  # User-defined minimum
        max_grid_size = 9  # User-defined maximum

        grid_size_x = max(min_grid_size, min(int(model_width * scaling_factor), max_grid_size))
        grid_size_y = max(min_grid_size, min(int(model_height * scaling_factor), max_grid_size))

        return grid_size_x, grid_size_y

    ## Replaces the G29 command with one bounded to the model size and dynamic grid.
    def fillBounds(self, data: str, bounds: {str: {str: float}}, grid_size_x: int, grid_size_y: int) -> str:
        new_cmd = "G29 L%.3f R%.3f F%.3f B%.3f P0 G %d %d ; Dynamic UBL Grid with Custom Settings" % (
            bounds["X"]["min"],  # L = Left
            bounds["X"]["max"],  # R = Right
            bounds["Y"]["min"],  # F = Front
            bounds["Y"]["max"],  # B = Back
            grid_size_x,         # Grid size X
            grid_size_y          # Grid size Y
        )

        # Replace any existing G29 line (even commented variants)
        return re.sub(r"^G29.*$", new_cmd, data, flags=re.MULTILINE)