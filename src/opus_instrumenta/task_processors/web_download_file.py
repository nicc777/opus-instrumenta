import os
import json
import traceback
import copy
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

from magnum_opus.operarius import LoggerWrapper, TaskProcessor, KeyValueStore, Task, StatePersistence
from magnum_opus_adstator.file_io import get_file_size


class WebDownloadFile(TaskProcessor):

    def __init__(self, kind: str='WebDownloadFile', kind_versions: list=['v1',], supported_commands: list = list(), logger: LoggerWrapper = LoggerWrapper()):
        self.spec = dict()
        self.metadata = dict()
        super().__init__(kind, kind_versions, supported_commands, logger)

    def _get_url_content_length(self, url: str, log_header:str='')->dict:
        try:
            response = requests.head(url, allow_redirects=True)
            self.log(message='Headers: {}'.format(response.headers), level='debug')
            for header_name, header_value in response.headers.items():
                if header_name.lower() == 'content-length':
                    self.log(message='Content-Length: {}'.format(int(header_value)), build_log_message_header=False, level='info', header=log_header)
                    return int(header_value)
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
        # It may be impossible to get the initial length as we did not take into account proxy or authentication. In these cases assume a LARGE file
        self.log(message='Unable to determine content length from URL {}'.format(url), build_log_message_header=False, level='warning', header=log_header)
        return 999999999999

    def _build_proxy_dict(self, proxy_host: str, proxy_username: str, proxy_password: str, log_header:str='')->dict:
        proxies = dict()
        proxy_str = ''
        if proxy_host is not None:
            if isinstance(proxy_host, str):
                if proxy_host.startswith('http'):
                    proxy_str = proxy_host
                    if proxy_username is not None and proxy_password is not None:
                        if isinstance(proxy_username, str) and isinstance(proxy_password, str):
                            creds = '//{}:{}@'.format(proxy_username, proxy_password)
                            creds_logging = '//{}:{}@'.format(proxy_username, '*' * len(proxy_password))
                            final_proxy_str = '{}{}{}'.format(proxy_str.split('/')[0], creds, '/'.join(proxy_str.split('/')[2:]))
                            final_proxy_str_logging = '{}{}{}'.format(proxy_str.split('/')[0], creds_logging, '/'.join(proxy_str.split('/')[2:]))
                            self.log(message='Using proxy "{}"'.format(final_proxy_str_logging), build_log_message_header=False, level='info', header=log_header)
                            proxies['http'] = final_proxy_str
                            proxies['https'] = final_proxy_str
        return proxies

    def _build_http_basic_auth_dict(self, username: str, password: str, log_header:str='')->HTTPBasicAuth:
        auth = None
        if username is not None and password is not None:
            if len(username) > 0 and len(password) > 0:
                auth = HTTPBasicAuth(username, password)
        return auth

    def _get_data_basic_request(
        self,
        url: str,
        target_file: str,
        verify_ssl: bool,
        proxy_host: str,
        proxy_username: str,
        proxy_password: str,
        username: str,
        password: str,
        headers: dict,
        method: str,
        body: str,
        log_header:str=''
    )->str:
        self.log(message='Running Method "_get_data_basic_request()"', build_log_message_header=False, level='debug', header=log_header)
        http_status_code = None
        try:
            proxies=self._build_proxy_dict(proxy_host=proxy_host, proxy_username=proxy_username, proxy_password=proxy_password)
            auth = self._build_http_basic_auth_dict(username=username, password=password)
            r = requests.request(method=method, url=url, allow_redirects=True, verify=verify_ssl, proxies=proxies, auth=auth, headers=headers, data=body)
            if r:
                http_status_code = '{}'.format(r.status_code)
            if r.content:
                with open(target_file, 'wb') as f:
                    f.write(r.content)
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
        return http_status_code

    def _get_data_basic_request_stream(
        self,
        url: str,
        target_file: str,
        verify_ssl: bool,
        proxy_host: str,
        proxy_username: str,
        proxy_password: str,
        username: str,
        password: str,
        headers: dict,
        method: str,
        body: str,
        log_header:str=''
    )->bool:
        # Refer to https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
        self.log(message='Running Method "_get_data_basic_request_stream()"', build_log_message_header=False, level='debug', header=log_header)
        http_status_code = None
        try:
            proxies=self._build_proxy_dict(proxy_host=proxy_host, proxy_username=proxy_username, proxy_password=proxy_password)
            auth = self._build_http_basic_auth_dict(username=username, password=password)
            with requests.request(method=method, url=url, allow_redirects=True, verify=verify_ssl, proxies=proxies, auth=auth, headers=headers, stream=True, data=body) as r:
                if r:
                    http_status_code = '{}'.format(r.status_code)
                r.raise_for_status()
                with open(target_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
            return None
        return http_status_code

    def _store_values(self, key_value_store: KeyValueStore, value: object, task_id: str, command: str, context: str, log_header:str='')->KeyValueStore:
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        final_key = '{}:{}:{}:{}:RESULT'.format(self.kind, task_id, command, context)
        self.log(message='  Storing value in key "{}"'.format(final_key), build_log_message_header=False, level='info', header=log_header)
        new_key_value_store.save(key=final_key, value=value)
        return new_key_value_store

    def delete_output_file(
        self,
        task_id: str,
        command: str,
        context: str,
        key_value_store: KeyValueStore=KeyValueStore(),
        remove_target_output_file_stored_result_on_file_deletion: bool=True,
        log_header: str=''
    )->KeyValueStore:
        """A helper function that the client can use to delete a previously downloaded artifact, or an artifact that is
        defined in the `spec` that may exist on the filesystem.

        Args:
            task_id: The task ID
            command: The command
            context: The context
            key_value_store: A copy of the current `KeyValueStore`. A new instance with updated values will be returned.
            remove_target_output_file_stored_result_on_file_deletion: A boolean indicating if the `KeyValueStore` result must also be removed when the file is deleted. The default is `True`.
            log_header: A string that is added as a leader string to all log messages. The string can be empty, but not `None`

        Returns:
            A new instance of `KeyValueStore`. 
            
            If the argument `remove_target_output_file_stored_result_on_file_deletion` was set to `True` and a previous
            download was done with a stored result, the previous result data will be removed from the `KeyValueStore`.
        """
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        try:
            if 'targetOutputFile' in self.spec:
                if self.spec['targetOutputFile'] is not None:
                    if isinstance(self.spec['targetOutputFile'], str):
                        os.unlink(self.spec['targetOutputFile'])            
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
        if remove_target_output_file_stored_result_on_file_deletion is True:
            key = 'WebDownloadFile:{}:{}:{}:RESULT'.format(task_id,command,context)
            if key in key_value_store.store is True:
                new_key_value_store.store.pop(key)
        return new_key_value_store

    def process_task(self, task: Task, command: str, context: str = 'default', key_value_store: KeyValueStore = KeyValueStore(), state_persistence: StatePersistence = StatePersistence()) -> KeyValueStore:
        """This task processor will download a file from a HTTP or HTTPS server.

        # Spec fields

        Root levels spec fields

        | Field                     | Type    | Required | In Versions | Description                                                                                                                                                                                    |
        |---------------------------|:-------:|:--------:|:-----------:|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | `sourceUrl`               | string  | Yes      | v1          | The URL from where to download the file                                                                                                                                                        |
        | `targetOutputFile`        | string  | Yes      | v1          | The destination file. NOTE: The directory MUST exist. To create the directory first (if needed) consider using a ShellScript as a dependency.                                                  |
        | `skipSslVerification`     | bool    | No       | v1          | If set to true, skips SSL verification. WARNING: use with caution as this may pose a serious security risk                                                                                     |
        | `proxy`                   | dict    | No       | v1          | Proxy configuration.                                                                                                                                                                           |
        | `extraHeaders`            | list    | No       | v1          | A list of name and value items with additional headers to set for the request. Things like a Authorization header might need to be set.                                                        |
        | `method`                  | string  | No       | v1          | The HTTP method to use (default=GET)                                                                                                                                                           |
        | `body`                    | string  | No       | v1          | Some request types, like POST, requires a body with the data to send. Also remember to set additional headers like "Content Type" as required                                                  |
        | `httpBasicAuthentication  | dict    | No       | v1          | If the remote site requires basic authentication, set the username using this field                                                                                                            |
        | `successCodes`            | string  | No       | v1          | A string describing the HTTP return codes to be considered as success. Any other code besides this will be considered an error state. Default: `200-399`                                       |
        | `exceptionOnError`        | bool    | No       | v1          | If set to `True`, any HTTP return value considered to be an error will result in the processing raising an error. Setting this value to `False` will not raise an `Exception`. Default: `True` |

        ## Fields for `proxy`

        | Field                 | Type    | Required    | In Versions | Description                                                                                                                                                         |
        |-----------------------|:-------:|:-----------:|:-----------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | `host`                | string  | Conditional | v1          | If you need to pass through a proxy, set the proxy host here. Include the protocol and port, for example `http://` or `https://`. An example: `http://myproxy:3128` |
        | `basicAuthentication` | dict    | No          | v1          | Proxy basic username and password configuration                                                                                                                     |

        NOTE: If the environment variables `http_proxy`, `https_proxy`, `HTTP_PROXY` or `HTTPS_PROXY`, those values will
        be used if `host` (or the root `proxy` field) is not supplied. Setting the `host` value here will override any
        environment variables.

        ### Fields for `basicAuthentication`

        | Field      | Type    | Required | In Versions | Description                                                                                   |
        |------------|:-------:|:--------:|:-----------:|-----------------------------------------------------------------------------------------------|
        | `username` | string  | No       | v1          | If the proxy requires authentication and supports basic authentication, set the username here |
        | `password` | string  | No       | v1          | The password.                                                                                 |

        ## Fields for `httpBasicAuthentication`

        | Field      | Type    | Required | In Versions | Description                                                                                   |
        |------------|:-------:|:--------:|:-----------:|-----------------------------------------------------------------------------------------------|
        | `username` | string  | No       | v1          | If the proxy requires authentication and supports basic authentication, set the username here |
        | `password` | string  | No       | v1          | The password.                                                                                 |
 
        Args:
            task: The `Task` of kind `ShellScript` version `v1` to process
            command: The command is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the command.
            context: The context is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the context.
            key_value_store: An instance of the `KeyValueStore`. If none is supplied, a new instance will be created.
            state_persistence: An implementation of `StatePersistence` that the task processor can use to retrieve previous copies of the `Task` manifest in order to determine the actions to be performed.

        Returns:
            An updated `KeyValueStore`.

            * The HTTP return code will be stored in: `task.kind:task.task_id:command:context:RESULT`

        Raises:
            Exception: As determined by the processing logic.
        """
        self.spec = copy.deepcopy(task.spec)
        self.metadata = copy.deepcopy(task.metadata)
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START', build_log_message_header=False, level='info', header=log_header)
        self.log(message='   spec: {}'.format(json.dumps(self.spec)), build_log_message_header=False, level='debug', header=log_header)
        if '{}:{}:{}:{}:RESULT'.format(task.kind,task.task_id,command,context) in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store

        url: str
        url = None
        if 'sourceurl' in self.spec:
            if self.spec['sourceurl'] is not None:
                if isinstance(self.spec['sourceurl'], str):
                    url = self.spec['sourceurl']
        if url is None:
            raise Exception('No "sourceUrl" found. This field is required.')
        
        target_file: str
        target_file = None
        if 'targetoutputfile' in self.spec:
            if self.spec['targetoutputfile'] is not None:
                if isinstance(self.spec['targetoutputfile'], str):
                    target_file = self.spec['targetoutputfile']
        if target_file is None:
            raise Exception('No "targetOutputFile" found. This field is required.')

        large_file = False
        remote_file_size = self._get_url_content_length(url=self.spec['sourceurl'], log_header=log_header)
        self.log(message='Checking if {} > 104857600...'.format(remote_file_size), build_log_message_header=False, level='info', header=log_header)
        if remote_file_size > 104857600:   # Anything larger than 100MiB is considered large and will be downloaded in chunks
            large_file = True

        # Check if the local file exists:
        if os.path.exists(self.spec['targetoutputfile']) is True:
            if Path(self.spec['targetoutputfile']).is_file() is True:
                local_file_size = int(get_file_size(file_path=self.spec['targetoutputfile']))
                self.log(message='local_file_size={}   remote_file_size={}'.format(local_file_size, remote_file_size), build_log_message_header=False, level='info', header=log_header)
                if local_file_size == remote_file_size:
                    return self._store_values(key_value_store=copy.deepcopy(new_key_value_store), value='n/a', task_id=task.task_id, command=command, context=context, log_header=log_header)
            else:
                raise Exception('The target output file cannot be used as the named target exists but is not a file')

        use_ssl = False
        verify_ssl = True
        use_proxy = False
        use_proxy_authentication = False
        proxy_host = None
        proxy_username = None
        proxy_password = None
        use_http_basic_authentication = False
        http_basic_authentication_username = None
        http_basic_authentication_password = None
        extra_headers = None
        use_custom_headers = False
        http_method = 'GET'
        http_body = None
        use_body = False

        if url.lower().startswith('https'):
            use_ssl = True
        if use_ssl is True and 'skipsslverification' in self.spec:
            if self.spec['skipsslverification'] is not None:
                if isinstance(self.spec['skipsslverification'], bool):
                    verify_ssl = not self.spec['skipsslverification']
                else:
                    self.log(message='Found `skipSslVerification` but value is not a boolean type - ignoring', build_log_message_header=False, level='warning', header=log_header)
            else:
                self.log(message='Found `skipSslVerification` but value is None type - ignoring', build_log_message_header=False, level='warning', header=log_header)

        if 'proxy' in self.spec:
            if self.spec['proxy'] is not None:
                if isinstance(self.spec['proxy'], dict) is True:
                    if 'host' in self.spec['proxy']:
                        if self.spec['proxy']['host'] is not None:
                            if isinstance(self.spec['proxy']['host'], str) is True:
                                use_proxy = True
                                proxy_host = self.spec['proxy']['host']
                                if 'basicauthentication' in self.spec['proxy']:
                                    if self.spec['proxy']['basicauthentication'] is not None:
                                        if isinstance(self.spec['proxy']['basicauthentication'], dict) is True:
                                            use_proxy_authentication = True
                                            if 'username' in ['proxy']['basicauthentication']:
                                                if self.spec['proxy']['basicauthentication']['username'] is not None:
                                                    if isinstance(self.spec['proxy']['basicauthentication']['username'], str) is True:
                                                        proxy_username = self.spec['proxy']['basicauthentication']['username']
                                            if 'password' in ['proxy']['basicauthentication']:
                                                if self.spec['proxy']['basicauthentication']['password'] is not None:
                                                    if isinstance(self.spec['proxy']['basicauthentication']['password'], str) is True:
                                                        proxy_password = self.spec['proxy']['basicauthentication']['password']
                                            if proxy_password is None:
                                                use_proxy_authentication = False

        if 'httpbasicauthentication' in self.spec:
            if self.spec['httpbasicauthentication'] is not None:
                if isinstance(self.spec['httpbasicauthentication'], dict) is True:
                    use_http_basic_authentication = True
                    if 'username' in self.spec['httpbasicauthentication']:
                        if self.spec['httpbasicauthentication']['username'] is not None:
                            if isinstance(self.spec['httpbasicauthentication']['username'], dict) is True:
                                http_basic_authentication_username = self.spec['httpbasicauthentication']['username']
                    if 'password' in self.spec['httpbasicauthentication']:
                        if self.spec['httpbasicauthentication']['password'] is not None:
                            if isinstance(self.spec['httpbasicauthentication']['password'], dict) is True:
                                http_basic_authentication_password =  self.spec['httpbasicauthentication']['password']
                    if http_basic_authentication_password is None or http_basic_authentication_username is None:
                        use_http_basic_authentication = False

        if 'extraheaders' in self.spec:
            if self.spec['extraheaders'] is not None:
                if isinstance(self.spec['extraheaders'], list) is True:
                    extra_headers = dict()
                    for header_data in self.spec['extraheaders']:
                        if header_data is not None:
                            if isinstance(header_data, dict) is True:
                                if 'name' in header_data and 'value' in header_data:
                                    extra_headers[header_data['name']] = header_data['value']
                                else:
                                    self.log(message='      Ignoring extra header item as it does not contain the keys "name" and/or "value"', build_log_message_header=False, level='warning', header=log_header)
        try:
            if len(extra_headers) > 0:
                use_custom_headers = True
        except:
            self.log(message='extra_headers length is zero - not using custom headers', build_log_message_header=False, level='info', header=log_header)

        if 'method' in self.spec:
            if self.spec['method'] is not None:
                if isinstance(self.spec['method'], str) is True:
                    http_method = self.spec['method'].upper()
                    if http_method not in ('GET','HEAD','POST','PUT','DELETE','PATCH',):
                        self.log(message='      HTTP method "{}" not recognized. Defaulting to GET'.format(http_method), build_log_message_header=False, level='warning', header=log_header)
                        http_method = 'GET'

        if http_method != 'GET' and 'body' in self.spec:
            if self.spec['body'] is not None:
                http_body = self.spec['body']
        elif http_method == 'GET' and 'body' in self.spec:
            self.log(message='Body cannot be set with GET requests - ignoring body content', build_log_message_header=False, level='warning', header=log_header)
        if http_body is not None:
            if len(http_body) > 0:
                use_body = True

        self.log(message='   * Large File                      : {}'.format(large_file), build_log_message_header=False, level='info', header=log_header)
        self.log(message='   * Using SSL                       : {}'.format(use_ssl), build_log_message_header=False, level='info', header=log_header)
        if use_ssl:
            self.log(message='   * Skip SSL Verification           : {}'.format(not verify_ssl), build_log_message_header=False, level='info', header=log_header)
        self.log(message='   * Using Proxy                     : {}'.format(use_proxy), build_log_message_header=False, level='info', header=log_header)
        if use_proxy:
            self.log(message='   * Proxy Host                      : {}'.format(proxy_host), build_log_message_header=False, level='info', header=log_header)
            self.log(message='   * Using Proxy Authentication      : {}'.format(use_proxy_authentication), build_log_message_header=False, level='info', header=log_header)
            if use_proxy_authentication is True:
                self.log(message='   * Proxy Password Length           : {}'.format(len(proxy_password)), build_log_message_header=False, level='info', header=log_header)
        self.log(message='   * Using HTTP Basic Authentication : {}'.format(use_http_basic_authentication), build_log_message_header=False, level='info', header=log_header)
        if use_http_basic_authentication:
            self.log(message='   * HTTP Password Length            : {}'.format(len(http_basic_authentication_password)), build_log_message_header=False, level='info', header=log_header)
        if extra_headers is not None:
            if len(extra_headers) > 0:
                self.log(message='   * Extra Header Keys               : {}'.format(list(extra_headers.keys())), build_log_message_header=False, level='info', header=log_header)
            else:
                self.log(message='   * Extra Header Keys               : None - Using Default Headers', build_log_message_header=False, level='info', header=log_header)
        else:
            self.log(message='   * Extra Header Keys               : None - Using Default Headers', build_log_message_header=False, level='info', header=log_header)
        self.log(message='   * HTTP Method                     : {}'.format(http_method), build_log_message_header=False, level='info', header=log_header)
        if http_body is not None:
            self.log(message='   * HTTP Body Bytes                 : {}'.format(len(http_body)), build_log_message_header=False, level='info', header=log_header)
        else:
            self.log(message='   * HTTP Body Bytes                 : None', build_log_message_header=False, level='info', header=log_header)

        work_values = {
            'large_file': large_file,
            'verify_ssl': verify_ssl,
            'use_proxy': use_proxy,
            'use_proxy_authentication': use_proxy_authentication,
            'use_http_basic_authentication': use_http_basic_authentication,
            'http_method': http_method,
            'use_custom_headers': use_custom_headers,
            'use_body': use_body,
        }

        parameters = {
            'url': url,
            'target_file': target_file,
            'verify_ssl': verify_ssl,
            'proxy_host': proxy_host,
            'proxy_username': proxy_username,
            'proxy_password': proxy_password,
            'username': http_basic_authentication_username,
            'password': http_basic_authentication_password,
            'headers': extra_headers,
            'method': http_method,
            'body': http_body
        }
        download_scenarios = [
            {
                'values': {
                    'large_file': False,
                },
                'method': self._get_data_basic_request
            },
            {
                'values': {
                    'large_file': True,
                },
                'method': self._get_data_basic_request_stream
            },
        ]

        effective_method = None
        for scenario in download_scenarios:
            values = scenario['values']
            criterion_match = True
            for criterion, condition in values.items():
                if criterion != 'http_method':
                    if condition != work_values[criterion]:
                        criterion_match = False
                else:
                    if work_values['http_method'] not in condition:
                        criterion_match = False
            if criterion_match is True:
                effective_method = scenario['method']

        if effective_method is not None:
            result = effective_method(**parameters)
            if result is not None:
                new_key_value_store = self._store_values(key_value_store=copy.deepcopy(new_key_value_store), value=result, task_id=task.task_id, command=command, context=context, log_header=log_header)
            else:
                raise Exception('Failed to download "{}" to file "{}"'.format(url, target_file))
        else:
            raise Exception('No suitable method could be found to handle the download.')

        self.spec = dict()
        self.metadata = dict()
        self.log(message='DONE', build_log_message_header=False, level='info', header=log_header)
        return new_key_value_store

