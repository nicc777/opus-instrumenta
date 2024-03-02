import sys
import os
import copy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
print('sys.path={}'.format(sys.path))

import unittest

from task_processors.shell_script_v1 import ShellScript
from opus.operarius import LoggerWrapper, Task, Tasks, Identifier, Identifiers, IdentifierContext, IdentifierContexts

running_path = os.getcwd()
print('Current Working Path: {}'.format(running_path))


class TestLogger(LoggerWrapper):

    def __init__(self):
        super().__init__()
        self.info_lines = list()
        self.warn_lines = list()
        self.debug_lines = list()
        self.critical_lines = list()
        self.error_lines = list()
        self.all_lines_in_sequence = list()

    def info(self, message: str):
        self.info_lines.append('[LOG] INFO: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.info_lines[-1])
        )

    def warn(self, message: str):
        self.warn_lines.append('[LOG] WARNING: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.warn_lines[-1])
        )

    def warning(self, message: str):
        self.warn_lines.append('[LOG] WARNING: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.warn_lines[-1])
        )

    def debug(self, message: str):
        self.debug_lines.append('[LOG] DEBUG: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.debug_lines[-1])
        )

    def critical(self, message: str):
        self.critical_lines.append('[LOG] CRITICAL: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.critical_lines[-1])
        )

    def error(self, message: str):
        self.error_lines.append('[LOG] ERROR: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.error_lines[-1])
        )

    def reset(self):
        self.info_lines = list()
        self.warn_lines = list()
        self.debug_lines = list()
        self.critical_lines = list()
        self.error_lines = list()


def print_logger_lines(logger:LoggerWrapper):
    for line in logger.all_lines_in_sequence:
        print(line)


class TestScenariosInLine(unittest.TestCase):    # pragma: no cover

    def setUp(self) -> None:
        print()
        print('-'*80)
        self.logger = TestLogger()
        return super().setUp()

    def tearDown(self):
        print_logger_lines(logger=self.logger)
        self.logger = None
        return super().tearDown()

    def test_echo_hello_world_01(self):
        shell_script = ShellScript(logger=self.logger)
        task = Task(
            kind='',
            version='',
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "Hello World!"'
                }
            },
            logger=self.logger
        )
        tasks = Tasks(logger=self.logger)
        tasks.register_task_processor(processor=shell_script)
        tasks.add_task(task.task)
        tasks.process_context(command='apply', context='unittest')
        

if __name__ == '__main__':
    unittest.main()