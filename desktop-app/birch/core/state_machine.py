import enum
import time
import attr
import logging
from .common import LogObject
from .stoppable_thread import StoppableThread


@attr.s()
class State():
    """
    Generic state, wraps calling of entry , run and exit functions
    """
    enter_fn = attr.ib()
    run_fn = attr.ib()
    exit_fn = attr.ib()

    def enter(self):
        if self.enter_fn:
            self.enter_fn()

    def run(self):
        if self.run_fn:
            self.run_fn()

    def exit(self):
        if self.exit_fn:
            self.exit_fn()


class StateMachine(LogObject):
    event_logger = logging.getLogger("event_logger")
    """
    State transition machinery
    """

    def __init__(self, prefix="SM", tick_period=0.1, debug=True, *args, **kwargs):
        super().__init__(prefix)
        self.state = None
        self.running = False
        self.state_table = {}
        self.tick_period = tick_period
        self.debug = debug
        self.thread = None
        self.state_timer = 0

    def start(self):
        self.log_debug("start")
        self.running = True

    def stop(self):
        self.log_debug("stop")
        self.running = False

    def state_transition(self, new_state):
        self.state = new_state

    def run(self):
        self.start()

        current_state = None
        while self.running:
            self.log_info("%s -> %s" % (current_state, self.state))
            current_state = self.state
            s = self.state_table[current_state]
            s.enter()
            self.state_timer = time.time()
            while current_state == self.state and self.running:
                time.sleep(self.tick_period)
                s.run()
            s.exit()

    def state_elapsed_time(self):
        return time.time() - self.state_timer

    def start_thread(self):
        """
        Run as thread
        """
        if self.thread is None:
            self.thread = StoppableThread(target=self.run, daemon=True)
            self.thread.start()

    def stop_thread(self):
        """
        Stop thread
        """
        self.thread.stop()
