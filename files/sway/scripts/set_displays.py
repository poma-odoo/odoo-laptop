#!/usr/bin/env python
import logging
import sys
from subprocess import check_output, run
import json

THREEWAY_SCALE = 1.2
TOP, MIDDLE, BOTTOM = 0, 1, 2


class DisplayConfigurator:
    outputs = {}

    def __init__(self):
        self.get_outputs()
        self.config = {TOP: [], MIDDLE: [], BOTTOM: []}

    def get_outputs(self):
        displays = check_output(["swaymsg", "-rt", "get_outputs"]).decode("utf-8")
        outputs_raw = json.loads(displays)
        self.outputs = {
            output["name"]: {
                "active": output["active"],
                "scale": output.get("scale", 1),
                "model": output["model"],
                "make": output["make"],
                "serial": output["serial"],
                "x": output["rect"]["x"],
                "y": output["rect"]["y"],
                "width": output["rect"]["width"],
                "height": output["rect"]["height"],
            }
            for output in outputs_raw
        }

    def set_output(self, name, x=None, y=None, scale=None, active=None):
        # convert to apply config
        if name not in self.outputs:
            logging.error(f"Display {name} not found")
            exit(3)
        if x is not None and y is not None:
            run(["swaymsg", "output", name, "position", str(x), str(y)])
        if scale:
            run(["swaymsg", "output", name, "scale", str(scale or 1)])
        if active is not None:
            if active:
                run(["swaymsg", "output", name, "enable"])
            else:
                run(["swaymsg", "output", name, "disable"])

    def check_target_displays_count(self, count):
        if count > len(self.outputs):
            logging.error("Not enough displays.")
            exit(1)
        elif len(self.outputs) - count > 1:
            logging.error("Dont know which display to disable.")
            exit(2)

    def run(self, target_displays_count=0):
        if target_displays_count == 0:
            target_displays_count = len(self.outputs)
        if target_displays_count == 1 or len(self.outputs) == 1:
            self.set_output("eDP-1", active=True)
            self.set_output("eDP-1", 0, 0)
            logging.info("Using eDP-1 only")
            return
        self.check_target_displays_count(target_displays_count)

        if enable_edp1 := len(self.outputs) == target_displays_count:
            self.set_output("eDP-1", active=True)
            self.get_outputs()
            if target_displays_count == 3:
                self.set_output("eDP-1", scale=THREEWAY_SCALE)
            else:
                self.set_output("eDP-1", scale=1)
        else:
            self.set_output("eDP-1", active=False)

        for name, info in self.outputs.items():
            # LLN2
            if info["serial"] == "1178622401810":
                self.config[TOP].insert(0, name)

            elif info["serial"] == "1215232713315":
                self.config[TOP].append(name)
            # home
            elif info["serial"] == "QKCM9HA013648":  # AOC
                self.config[TOP].insert(0, name)

            elif info["serial"] == "1178621102124":
                self.config[TOP].append(name)
            elif name != 'eDP-1':
                self.config[MIDDLE].append(name)


        if enable_edp1:
            if self.config[BOTTOM]:
                # put eDP-1 on the bottom center
                self.config[BOTTOM].insert(len(self.config[BOTTOM]) // 2, "eDP-1")
            elif self.config[MIDDLE] and self.config[TOP]:
                self.config[BOTTOM].append("eDP-1")
            elif self.config[MIDDLE]:
                self.config[BOTTOM].append("eDP-1")
            elif self.config[TOP]:
                self.config[MIDDLE].append("eDP-1")
            else:
                # There is only one display!
                self.config[BOTTOM].append("eDP-1")

        top_heights, middle_heights, bottom_heights = [], [], []
        top_width, middle_width, bottom_width = 0, 0, 0
        outputs = self.outputs
        for display in self.config[TOP]:
            top_width += outputs[display]["width"]
            top_heights.append(outputs[display]["height"])
        for display in self.config[MIDDLE]:
            middle_width += outputs[display]["width"]
            middle_heights.append(outputs[display]["height"])
        for display in self.config[BOTTOM]:
            bottom_width += outputs[display]["width"]
            bottom_heights.append(outputs[display]["height"])

        max_width = max(top_width, middle_width, bottom_width)
        x = (max_width - top_width) // 2
        y = 0
        anchor = len(set(outputs[d]["height"] for d in self.config[TOP])) == 1 and "ALL"
        for display in self.config[TOP]:
            self.set_output(display, x, y)
            x += outputs[display]["width"]
            if not anchor and outputs[display]["height"] == max(top_heights):
                anchor = display

        x = (max_width - middle_width) // 2
        if anchor == "ALL":
            y = outputs[self.config[TOP][0]]["height"]
        elif anchor:
            # if the top row outputs are not the same height,
            # stick to the first tallest one to avoid having gaps or overlaps
            y = outputs[anchor]["height"]
            x = outputs[anchor]["x"]
        anchor = len(set(outputs[d]["height"] for d in self.config[MIDDLE])) == 1 and "ALL"
        for display in self.config[MIDDLE]:
            self.set_output(display, x, y)
            x += outputs[display]["width"]
            if not anchor and outputs[display]["height"] == max(middle_heights):
                anchor = display

        x = (max_width - bottom_width) // 2
        if anchor == "ALL":
            y = outputs[self.config[MIDDLE][0]]["height"]
        elif anchor:
            # if the middle row outputs are not the same height,
            # stick to the first tallest one to avoid having gaps or overlaps
            y = outputs[anchor]["height"]
            x = outputs[anchor]["x"]
        for display in self.config[BOTTOM]:
            self.set_output(display, x, y)
            x += outputs[display]["width"]


def main():
    config = DisplayConfigurator()
    target_displays_count = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    config.run(target_displays_count)


if __name__ == "__main__":
    main()

