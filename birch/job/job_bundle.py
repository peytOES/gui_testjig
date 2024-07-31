import zipfile
import os
import logging
from pathlib import Path

from zipfile import ZipFile, BadZipFile
import json

from ..fixture import fixture_id

event_logger = logging.getLogger("event_logger")


class Eui():
    def __init__(self, asc):
        """
        Excect a hex string or int value as EUI
        """
        self.asc = asc
        self.val = int(asc, 16)


class EuiGenerator():
    def __init__(self, eui_name, eui_ranges=[], eui_used=[]):
        # build a set of possible EUIs
        self.name = "eui"
        self.eui_range = []

        for r in eui_ranges:
            start = r["start_%s" % self.name]
            end = r["end_%s" % self.name]
            self.eui_range.extend(EuiGenerator.expand(start, end))

        self.eui_range = sorted(list(set(self.eui_range)))

    def expand(start, end):
        start_addr = int(start, 16)
        end_addr = int(end, 16) + 1
        fmt = "%%%dx" % (len(start) - 2)
        addr_range = sorted([fmt % x for x in range(start_addr, end_addr)])
        return addr_range


class JobBundle():
    """
    Provided abstracted handling of job bundles.

    """

    def __init__(self, zipfile):
        self.zipfile = zipfile
        self.job_id = None
        self.error_msg = None

    def install(self, install_path):
        """
        Install job in a directory. 

        Return True if successful.
        """
        if self.job_id is None:
            self.error_msg = "Job ID undefined"
            return False

        try:
            os.makedirs(install_path)
        except FileExistsError:
            pass

        p = Path(install_path) / self.job_id
        if p.exists():
            self.error_msg = "Job exists: " + str(self.job_id)
            return False

        with ZipFile(self.zipfile, "r") as zf:
            zf.extractall(p)

        # remove file
        try:
            os.remove(self.zipfile)
        except OSError:
            pass

        return True

    def validate(self):
        """
        Validation consists of a sequence of steps, this function
        provides a single point of entry of in-order validation.

        Validation should catch most
        """

        if not self.validate_bundle_file():
            return False

        if not self.validate_signature():
            # not used
            return False

        if not self.validate_contents():
            return False

        # generate token data - validation happened previously
        if not self.generate_tokens():
            return False

        return True

    def validation_error_msg(self):
        """
        Handle to error messages raised in validation
        """
        return self.error_msg

    def validate_bundle_file(self):
        """
        Checks that we have a valid zip file, which contains a 
        job.json specification.

        TODO: validate job.json schema
        """
        try:
            # check if zip file
            with ZipFile(self.zipfile, "r") as zf:
                # check if zip file contains job.json file
                with zf.open("job.json", "r") as f:
                    job_data = f.read()
                    # check if job.json is valid
                    json.loads(job_data)

        except BadZipFile as e:
            self.error_msg = "Job bundle is not a valid zipfile"
            return False
        except KeyError as e:
            self.error_msg = "Job bundle does not contain 'job.json'"
            return False
        except ValueError as e:
            self.error_msg = "Parsing job.json failed. " + str(e)
            return False

        return True

    def validate_signature(self):
        """
        Validate job bundle signature
        """
        # self.error_msg = "Job bundle signature mismatch."
        return True

    def validate_contents(self):
        """
        Relying on previous validation
        """
        with ZipFile(self.zipfile, "r") as zf:
            with zf.open("job.json", "r") as f:
                job_data = json.loads(f.read())
                # print(job_data)

                if not ("id" in job_data and
                        "fixture_id" in job_data):
                    self.error_msg = "Invalid job file"
                    return False

                if fixture_id() != job_data["fixture_id"]:
                    self.error_msg = "Mismatched fixture ID"
                    return False

                self.job_id = job_data["id"]

        return True

    def generate_tokens(self):
        return True

    @classmethod
    def from_zipfile(cls, zipfile):
        return cls(zipfile)

    def list_bundles(path):
        """
        Returns a list of potential bundles in path
        """
        try:
            filelist = os.listdir(path)
        except FileNotFoundError:
            return []

        bundle_list = []
        for f in filelist:
            base, ext = os.path.splitext(f)
            if ext.lower() == ".zip":
                bundle_list.append(Path(path) / Path(f))

        return sorted(bundle_list)


class FirmwareJobBundle(JobBundle):
    """
    Job bundle with firmware payload
    """

    def validate_contents(self):
        """
        Stage 1 specific checks:
        - Firmware directory must be present
        """
        if not super().validate_contents():
            return False

        firmware_found = False
        with ZipFile(self.zipfile, "r") as zf:
            files = [s.split("/") for s in zf.namelist()]
            for f in files:
                if f[0] == "firmware":
                    firmware_found = True

        if not firmware_found:
            self.error_msg = "Firmware not found"
            return False

        return True
