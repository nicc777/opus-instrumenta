import os
import traceback
import json
from magnum_opus.operarius import LoggerWrapper, StatePersistence
from opus_adstator.file_io import get_file_size, read_large_text_file, read_text_file, file_exists


class FileBasedStatePersistence(StatePersistence): 

    def __init__(self, logger: LoggerWrapper = LoggerWrapper(), configuration: dict = dict()):
        if configuration is None:
            raise Exception('Configuration can not be NoneType')
        if isinstance(configuration, dict) is False:
            raise Exception('Configuration must be of type "dict"')
        if 'StateFile' not in configuration:
            raise Exception('Field "StateFile" must be present in configuration')
        if file_exists(file=configuration['StateFile']) is False:
            with open(configuration['StateFile'], 'w') as f:
                f.write(json.dumps(dict()))
        super().__init__(logger, configuration)

    def retrieve_all_state_from_persistence(self, on_failure: object=False)->bool:
        failed = False
        try:
            size_100mib = 100 * 1024 * 1024
            file_size = get_file_size(file_path=self.configuration['StateFile'])
            file_data = ''
            if file_size > size_100mib:
                file_data = read_large_text_file(path_to_file=self.configuration['StateFile'], chunk_size=size_100mib)
            else:
                file_data = read_text_file(path_to_file=self.configuration['StateFile'])
            self.state_cache = json.loads(file_data)
        except:
            failed = True
            self.logger.error('EXCEPTION: {}'.format(traceback.format_exc()))
        if failed is True:
            if isinstance(on_failure, Exception):
                raise on_failure
        return on_failure
    
    def persist_all_state(self):
        try:
            os.unlink(self.configuration['StateFile'])
            with open(self.configuration['StateFile'], 'w') as f:
                f.write(json.dumps(self.state_cache))
        except:
            self.logger.error('EXCEPTION: {}'.format(traceback.format_exc()))

