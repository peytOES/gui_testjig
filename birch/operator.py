"""
Control operator names and loading
"""
import enum
import json
import attr
from pathlib import Path
from pubsub import pub


@attr.s
class Operator():
    """
    Operator data
    """
    name = attr.ib()
    auth = attr.ib()


class OperatorList():
    """
    List of operators from file.


    GUI interface:
    get_operator_names() for list op operators
    select(i) to select an operator.  if successful, will cause a transition in the master state machine.
    """

    def __init__(self, operator_data=None, select_callback=None):
        self.operators = []
        self.select_callback = select_callback
        self.selected = None
        for l in operator_data:
            if "auth" in l:
                self.operators.append(Operator(l["name"], l["auth"]))
            else:
                self.operators.append(Operator(l["name"], None))

    def select(self, index):
        if index < len(self.operators):
            self.selected = index
            print("Selected operator: " + self.get_selected_name())
            if self.select_callback:
                self.select_callback()
            return True
        return False

    def get_selected_name(self):
        if self.selected is not None:
            return self.operators[self.selected].name
        return None

    def get_operator_names(self):
        """
        Returns a list of operator names
        """
        return [o.name for o in self.operators]

    @classmethod
    def load(cls, config_path=None, callback=None):
        """
        Load a configuration file
        """

        p = Path(config_path) / "operator.json"
        with open(p, "r") as f:
            data = json.load(f)
        return cls(
            data,
            callback
        )
