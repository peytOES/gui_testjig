import enum


class TestStatus(enum.IntEnum):
    """
    Definitions for possible test status
    """
    PASS = 1
    FAIL = 2
    INCOMPLETE = 3
    UNTESTED = 4
    SKIP = 5
    ERROR = 6
    NO_TOKENS = 7
    JOB_COMPLETE = 8
    INACTIVE = 9
    DISABLED = 10

    def str(i):
        """
        Strings used for display and logging
        """
        d = {
            TestStatus.PASS: "PASS",
            TestStatus.FAIL: "FAIL",
            TestStatus.INCOMPLETE: "INCOMPLETE",
            TestStatus.UNTESTED: "UNTESTED",
            TestStatus.SKIP: "SKIP",
            TestStatus.ERROR: "ERROR",
            TestStatus.NO_TOKENS: "NO TOKENS",
            TestStatus.JOB_COMPLETE: "JOB COMPLETE",
            TestStatus.INACTIVE: "",
            TestStatus.DISABLED: "DISABLED",
        }
        return d[i]

    def color(i):
        """
        RGB tuples for display of status
        """
        d = {
            TestStatus.PASS: (0, 196, 0),
            TestStatus.FAIL: (255, 64, 64),
            TestStatus.SKIP: (0, 0, 255),
            TestStatus.UNTESTED: (255, 255, 255),
            TestStatus.INCOMPLETE: (255, 255, 255),
            TestStatus.ERROR: (127, 127, 127),
            TestStatus.NO_TOKENS: (255, 255, 255),
            TestStatus.JOB_COMPLETE: (255, 255, 255),
            TestStatus.INACTIVE: (200, 200, 200),
            TestStatus.DISABLED: (127, 127, 127)
        }
        return d[i]
