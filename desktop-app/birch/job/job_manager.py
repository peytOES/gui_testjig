"""
Manage job files: installation, selection, 
"""
import attr
import json
from pathlib import Path
import threading
from pubsub import pub
import re
import logging
import os
import shutil

event_logger = logging.getLogger("event_logger")


@attr.s()
class Job():
    _job_file = attr.ib()
    _description = attr.ib()
    _fixture_id = attr.ib()
    _id = attr.ib()
    _parameters = attr.ib()
    _test_suite = attr.ib()
    _timestamp = attr.ib()
    _type = attr.ib()
    _path = attr.ib(default=".")
    _lock = threading.Lock()
    _config = attr.ib(default=None)
    _complete = False
    _source = attr.ib(default="")
    _serial_number_template = attr.ib(default=None)
    _token_total = attr.ib(default=0)  # total number of tokens at installation
    _units_passed = attr.ib(default=0)  # units successfully passed
    _units_tested = attr.ib(default=0)  # units tested
    _required_pass = attr.ib(default=0)  # required number of passes to complete job
    _reserved_tokens = {}  # list of tokens reserved for consumption
    _token_filter = "[a-zA-Z0-9]*"  # token file naming format

    # Testing
    # debug set in conf.json
    _debug = attr.ib(default=False)
    # disable save set on job level
    _disable_save = attr.ib(default=False)

    def __str__(self):
        return str(self._id)

    def save(self):
        event_logger.info("saving result")
        if self._disable_save:
            return

        with self._lock:
            data = {
                "description": self._description,
                "fixture_id": self._fixture_id,
                "id": self._id,  # test id, maps to directory
                "parameters": self._parameters,  # list of test parameters
                "serial_number_template": self._serial_number_template,
                "test_suite": self._test_suite,
                "timestamp": self._timestamp,
                "source": self._source,
                "type": self._type,
                "token_total": self._token_total,
                "units_passed": self._units_passed,
                "units_tested": self._units_tested,
                "required_pass": self._required_pass
            }
            # thread safe save.
            with open(self._job_file, "w") as fp:
                json.dump(data, fp, indent=4, sort_keys=True)

    def path(self):
        return self._path

    def is_complete(self):
        """
        Return True is job is complete.

        For a job without tokens and no required_pass data, always return False
        For a job without tokens, but a required pass field, return True when units_passed >= required_pass
        For a job with tokens, but no required pass, return True when all tokens have been consumed (tokens available + reserved == 0)
        For a job with token and a required_pass field, return True when units_passed >= required_pass. 
        """
        if self._token_total == 0:  # no tokens
            if self._required_pass == 0:
                # job does not terminate
                self._complete = False
            elif self._required_pass > 0:
                # number of passed required
                if self._units_passed >= self._required_pass:
                    self._complete = True
        else:  # tokens
            if self._required_pass == 0:
                if self.calc_tokens_remaining() == 0:
                    print("Delete job when tokens are all used")
                    self._complete = True
                #    return True
                # return False
            else:
                # number of passed required
                if self._units_passed >= self._required_pass:
                    self._complete = True
        #
        #            return False
        # raise Exception("Token total not implemented")

        return self._complete

    def units_passed_str(self):
        if self._required_pass > 0:
            return "%d/%d" % (self._units_passed, self._required_pass)
        else:
            return str(self._units_passed)

    def unit_passed(self):
        """
        Called to increment the pass counter
        """
        with self._lock:
            self._units_passed += 1
        pub.sendMessage("status", message={"units_passed": self._units_passed})

    def reset_units_passed(self):
        """
        Called to reset the pass counter
        """
        with self._lock:
            self._units_passed =0
        pub.sendMessage("status", message={"units_passed": self._units_passed})
        self.save()    
        
    def reset_units_tested(self):
        """
        Called to reset the tested counter
        """
        with self._lock:
            self._units_tested =0
        pub.sendMessage("status", message={"units_tested": self._units_tested})
        self.save()

    def unit_tested(self):
        """
        Called to increment the tested counter
        """
        with self._lock:
            self._units_tested += 1
        pub.sendMessage("status", message={"units_tested": self._units_tested})
        self.save()

    def token_total(self):
        return self._token_total

    def calc_tokens_remaining(self):
        token_path = Path(self._path) / "tokens"
        ret = len([f for f in token_path.glob(self._token_filter)])
        return ret

    def tokens_remaining(self):
        """
        Number of tokens remaining

        Look in job_path/tokens for files matching [a-zA-Z0-9]*
        """
        token_path = Path(self._path) / "tokens"
        if not token_path.is_dir():
            return 0

        with self._lock:
            return self.calc_tokens_remaining()

        return 0

    def use_token(self, token):
        """
        Use a token
        - token must exist && be reserved
        """
        with self._lock:
            if token in self._reserved_tokens:
                token_file = self._reserved_tokens.pop(token)
                event_logger.info("Using token " + str(token_file))
                if not self._disable_save:
                    os.remove(token_file)

                pub.sendMessage("status",
                                message={
                                    "tokens_remaining": self.calc_tokens_remaining(),
                                    "next_eui": self._next_eui()
                                }
                                )
                return True
        return False

    def release_token(self, token):
        """
        Release a previously reserved token
        """
        with self._lock:
            if token in self._reserved_tokens:
                token_file = self._reserved_tokens.pop(token)
                event_logger.info("Releasing token " + str(token_file))
                pub.sendMessage("status",
                                message={
                                    "tokens_remaining": self.calc_tokens_remaining(),
                                    "next_eui": self._next_eui()
                                }
                                )
                return True

        return False

    def _next_eui(self):
        """
        Return name of the next token to be used
        """
        token_path = Path(self._path) / "tokens"
        if not token_path.is_dir():
            return None

        for f in sorted(token_path.glob(self._token_filter)):
            key = f.name.split(".")[0]
            if key not in self._reserved_tokens:
                return key

    def reserve_token(self):
        """
        Reserve a token for future use.  Return None if nothing is available
        """
        token_path = Path(self._path) / "tokens"
        if not token_path.is_dir():
            return None

        with self._lock:
            for f in sorted(token_path.glob(self._token_filter)):
                key = f.name.split(".")[0]
                if key not in self._reserved_tokens:
                    self._reserved_tokens[key] = f
                    event_logger.info("Reserving token " + str(f))
                    pub.sendMessage("status",
                                    message={
                                        "tokens_remaining": self.calc_tokens_remaining(),
                                        "next_eui": self._next_eui()
                                    }
                                    )
                    return key
        return None

    def read_token_data(self, token):
        fname = self._reserved_tokens[token]

        with open(fname, "r") as f:
            return json.load(f)
        return None

    def validate_barcode(self, input_barcode):
        """
        Return True if a barcode matches the requirements specified in serial_number_template

        e.g. 
            "serial_number_template": "^CCQ[0-9]{4}[[0-9a-zA-Z]{4}$",
        """
        if self._serial_number_template is None or self._serial_number_template == "":
            return True

        m = re.fullmatch(self._serial_number_template, input_barcode)

        if m is None:
            return False
        
        return True

    def delete(self):
        """
        Remove the job
        """
        event_logger.info("Removing job %s %s" % (self._id, self._path))

        if self._debug:
            # do not delete in debug mode
            return

        shutil.rmtree(self._path)

    @classmethod
    def load(cls, path=None, debug=False):
        """
        Load a specific job file
        """

        job_file = Path(path) / "job.json"
        try:
            with open(job_file, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            pub.sendMessage("system", message={
                "message": "Job file loading failed %s:\n%s" % (
                    path, e)
            })
            return None

        obj = cls(
            job_file=job_file,
            path=path,
            debug=debug,
            **data
        )

        # for test in obj._parameters:
        #    if test in ["FW_LOAD"]:
        #        if "firmware" in obj._parameters[test]:
        #            if len(obj._parameters[test]["firmware"]) > 0:
        #                obj._firmware = obj._parameters[test]["firmware"][0]["filename"]
        #                break

        pub.sendMessage("status", message={
            "job": obj._id,
            "job_data": data,
            "testsuite": obj._test_suite["filename"],
            "pass_threshold": obj._required_pass,
            "tokens_remaining": obj.tokens_remaining(),
            "units_passed": obj._units_passed,
            "units_tested": obj._units_tested,
            "next_eui": obj._next_eui(),
            # "firmware": obj._firmware,
        })
        return obj


class JobManager():
    """
    Manages job selection, provides UI interface, maintains list of available jobs and the selected (loaded) one. 

    The loaded job is used by the Slot objects to track job progress.
    """

    def __init__(self, job_path, active_job_names, select_callback, debug=False):
        self.job_path = job_path
        self.active_job_names = active_job_names
        self.select_callback = select_callback
        self.selected_job = None
        self.debug = debug

        self.event_logger = logging.getLogger("event_logger")

        self.msg_topic = "system"
        pub.subscribe(self.pub_listener, self.msg_topic)

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local UI update calls using wx callafter
        """
        fn_map = {
            "job_select": self.select
        }

        for f in fn_map.keys():
            if f in message:
                try:
                    fn_map[f](message[f])
                except Exception as e:
                    self.event_logger("Message call failed: %s %s", f, str(message))

        # print(f"job_manager:pub_listener {message} {arg2}")

    def get_job_stats(self):
        """
        Return job stats for UI:

        self.lb.InsertColumn(0, "Name", width=250)
        self.lb.InsertColumn(1, "Description", width=300)
        self.lb.InsertColumn(2, "Tokens remaining", width=150)
        self.lb.InsertColumn(3, "Tokens total", width=150)
        self.lb.InsertColumn(4, "Units tested", width=150)
        """
        result = []
        for job_name in self.active_job_names:
            try:
                job = Job.load(Path(self.job_path) / job_name)
                if job is not None:
                    result.append(
                        [job._id, job._description, job.tokens_remaining(), job._token_total, job.units_passed_str()])
            except KeyError:
                self.event_logger.error("Error loading job %s" % job_name)

        return result

    def select(self, index):
        try:
            if index < len(self.active_job_names):
                # try to load selected job
                self.selected_job = Job.load(Path(self.job_path) / self.active_job_names[index], self.debug)
                
                # enable warnings
                pub.sendMessage("status", message={"enable_warnings": True})

                # If the job selected is testmode then enable the checkbox option
                if("VALIDATION" in self.selected_job._id):
                    pub.sendMessage("status", message={"validation_mode": True})                    
                else:
                    pub.sendMessage("status", message={"validation_mode": False})



                if self.selected_job is None:
                    return False
                if self.select_callback:
                    self.select_callback()
                return True
            return False
        except Exception as e:
            # Handle malformed job files
            self.event_logger.error("JobManager.select" + str(e))
            return False

    def get_selected(self):
        if self.selected_job is not None:
            return self.selected_job
        return None



    @classmethod
    def load(cls, active_dir="assets/active", select_callback=None, debug=False):
        """
        1) Scan input directory for new job files
        2) Build a list of available jobs
        """
        active_job_names = []

        p = Path(active_dir)
        if not p.exists():
            p.mkdir()

        active_job_names = sorted([str(x.name) for x in p.iterdir() if x.is_dir()])

        job_path = str(p)
        # with open(p, "r") as f:
        #    data = json.load(f)
        return cls(
            job_path,
            active_job_names,
            select_callback,
            debug
        )

            
