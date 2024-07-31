import enum


class ProvisionStatus(enum.IntEnum):
    """
    Definitions for possible test status
    """
    COMPLETE = 1
    INCOMPLETE = 2

    def str(i):
        """
        Strings used for display and logging
        """
        d = {
            ProvisionStatus.COMPLETE: "COMPLETE",
            ProvisionStatus.INCOMPLETE: "INCOMPLETE",
            }
        return d[i]
