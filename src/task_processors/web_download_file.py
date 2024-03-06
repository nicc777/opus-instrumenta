import os
import traceback
import copy
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

from opus.operarius import LoggerWrapper, TaskProcessor, KeyValueStore, Task, StatePersistence
from opus_adstator.file_io import get_file_size


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
                    self.log(message='Content-Length: {}'.format(int(header_value)), level='info')
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
                            self.log(message='Using proxy "{}"'.format(final_proxy_str_logging), level='info')
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
    )->bool:
        self.log(message='Running Method "_get_data_basic_request()"', build_log_message_header=False, level='debug', header=log_header)
        try:
            proxies=self._build_proxy_dict(proxy_host=proxy_host, proxy_username=proxy_username, proxy_password=proxy_password)
            auth = self._build_http_basic_auth_dict(username=username, password=password)
            r = requests.request(method=method, url=url, allow_redirects=True, verify=verify_ssl, proxies=proxies, auth=auth, headers=headers, data=body)
            with open(target_file, 'wb') as f:
                f.write(r.content)
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
            return False
        return True

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
        try:
            proxies=self._build_proxy_dict(proxy_host=proxy_host, proxy_username=proxy_username, proxy_password=proxy_password)
            auth = self._build_http_basic_auth_dict(username=username, password=password)
            with requests.request(method=method, url=url, allow_redirects=True, verify=verify_ssl, proxies=proxies, auth=auth, headers=headers, stream=True, data=body) as r:
                r.raise_for_status()
                with open(target_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
            return False
        return True

    def _store_values(self, key_value_store: KeyValueStore, value: object, task_id: str, command: str, context: str, log_header:str='')->KeyValueStore:
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        final_key = '{}:{}:{}:{}:RESULT'.format(self.kind, task_id, command, context)
        self.log(message='  Storing value in key "{}"'.format(final_key), build_log_message_header=False, level='info', header=log_header)
        new_key_value_store.save(key=final_key, value=value)
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
        self.spec = copy.deepcopy(task.original_data['spec'])
        self.metadata = copy.deepcopy(task.original_data['metadata'])
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START', build_log_message_header=False, level='info', header=log_header)
        if '{}:{}:{}:{}:RESULT'.format(task.kind,task.task_id,command,context) in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store

        url: str
        url = None
        if 'sourceUrl' in self.spec:
            if self.spec['sourceUrl'] is not None:
                if isinstance(self.spec['sourceUrl'], str):
                    url = self.spec['sourceUrl']
        if url is None:
            raise Exception('No "sourceUrl" found. This field is required.')
        
        target_file: str
        target_file = None
        if 'targetOutputFile' in self.spec:
            if self.spec['targetOutputFile'] is not None:
                if isinstance(self.spec['targetOutputFile'], str):
                    target_file = self.spec['targetOutputFile']
        if target_file is None:
            raise Exception('No "targetOutputFile" found. This field is required.')

        large_file = False
        remote_file_size = self._get_url_content_length(url=self.spec['sourceUrl'], log_header=log_header)
        self.log(message='Checking if {} > 104857600...'.format(remote_file_size), build_log_message_header=False, level='info', header=log_header)
        if remote_file_size > 104857600:   # Anything larger than 100MiB is considered large and will be downloaded in chunks
            large_file = True

        # Check if the local file exists:
        if os.path.exists(self.spec['targetOutputFile']) is True:
            if Path(self.spec['targetOutputFile']).is_file() is True:
                local_file_size = int(get_file_size(file_path=self.spec['targetOutputFile']))
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
        if use_ssl is True and 'skipSslVerification' in self.spec:
            if self.spec['skipSslVerification'] is not None:
                if isinstance(self.spec['skipSslVerification'], bool):
                    verify_ssl = not self.spec['skipSslVerification']
                else:
                    self.log(message='Found `skipSslVerification` but value is not a boolean type - ignoring', build_log_message_header=False, level='warning', header=log_header)
            else:
                self.log(message='Found `skipSslVerification` but value is None type - ignoring', build_log_message_header=False, level='warning', header=log_header)

        if 'proxy' in self.spec:
            if self.spec['proxy'] is not None:
                if 'host' in self.spec['proxy']:
                    if self.spec['proxy']['host'] is not None:
                        if isinstance(self.spec['proxy']['host'], str):
                            use_proxy = True
                            proxy_host = self.spec['proxy']['host']
                            if 'basicAuthentication' in self.spec['proxy']:
                                if self.spec['proxy']['basicAuthentication'] is not None:
                                    if isinstance(self.spec['proxy']['basicAuthentication'], dict):
                                        use_proxy_authentication = True
                                        if 'username' in ['proxy']['basicAuthentication']:
                                            if self.spec['proxy']['basicAuthentication']['username'] is not None:
                                                if isinstance(self.spec['proxy']['basicAuthentication']['username'], str):
                                                    proxy_username = self.spec['proxy']['basicAuthentication']['username']
                                        if 'password' in ['proxy']['basicAuthentication']:
                                            if self.spec['proxy']['basicAuthentication']['password'] is not None:
                                                if isinstance(self.spec['proxy']['basicAuthentication']['password'], str):
                                                    proxy_password = self.spec['proxy']['basicAuthentication']['password']
                                        if proxy_password is None:
                                            use_proxy_authentication = False

        if 'httpBasicAuthentication' in self.spec:
            use_http_basic_authentication = True
            http_basic_authentication_username = self.spec['httpBasicAuthentication']['username']
            http_basic_authentication_password = variable_cache.get_value(
                variable_name=self.spec['httpBasicAuthentication']['passwordVariableName'],
                value_if_expired=None,
                default_value_if_not_found=None,
                raise_exception_on_expired=False,
                raise_exception_on_not_found=False
            ).strip()
            if http_basic_authentication_password is None:
                self.log(message='      Basic Authentication Password not Set - Ignoring HTTP Basic Authentication Configuration', level='warning')
                use_http_basic_authentication = False

        if 'extraHeaders' in self.spec:
            extra_headers = dict()
            for header_data in self.spec['extraHeaders']:
                if 'name' in header_data and 'value' in header_data:
                    extra_headers[header_data['name']] = header_data['value']
                else:
                    self.log(message='      Ignoring extra header item as it does not contain the keys "name" and/or "value"', level='warning')
        try:
            if len(extra_headers) > 0:
                use_custom_headers = True
        except:
            self.log(message='extra_headers length is zero - not using custom headers', level='info')

        if 'method' in self.spec:
            http_method = self.spec['method'].upper()
            if http_method not in ('GET','HEAD','POST','PUT','DELETE','PATCH',):
                self.log(message='      HTTP method "{}" not recognized. Defaulting to GET'.format(http_method), level='warning')
                http_method = 'GET'

        if http_method != 'GET' and 'body' in self.spec:
            http_body = self.spec['body']
        elif http_method == 'GET' and 'body' in self.spec:
            self.log(message='Body cannot be set with GET requests - ignoring body content', level='warning')
        if http_body is not None:
            if len(http_body) > 0:
                use_body = True

        self.log(message='   * Large File                      : {}'.format(large_file), level='info')
        self.log(message='   * Using SSL                       : {}'.format(use_ssl), level='info')
        if use_ssl:
            self.log(message='   * Skip SSL Verification           : {}'.format(not verify_ssl), level='info')
        self.log(message='   * Using Proxy                     : {}'.format(use_proxy), level='info')
        if use_proxy:
            self.log(message='   * Proxy Host                      : {}'.format(proxy_host), level='info')
            self.log(message='   * Using Proxy Authentication      : {}'.format(use_proxy_authentication), level='info')
            if use_proxy_authentication is True:
                self.log(message='   * Proxy Password Length           : {}'.format(len(proxy_password)), level='info')
        self.log(message='   * Using HTTP Basic Authentication : {}'.format(use_http_basic_authentication), level='info')
        if use_http_basic_authentication:
            self.log(message='   * HTTP Password Length            : {}'.format(len(http_basic_authentication_password)), level='info')
        if extra_headers is not None:
            if len(extra_headers) > 0:
                self.log(message='   * Extra Header Keys               : {}'.format(list(extra_headers.keys())), level='info')
            else:
                self.log(message='   * Extra Header Keys               : None - Using Default Headers', level='info')
        else:
            self.log(message='   * Extra Header Keys               : None - Using Default Headers', level='info')
        self.log(message='   * HTTP Method                     : {}'.format(http_method), level='info')
        if http_body is not None:
            self.log(message='   * HTTP Body Bytes                 : {}'.format(len(http_body)), level='info')
        else:
            self.log(message='   * HTTP Body Bytes                 : None', level='info')

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
            if result is True:
                self._set_variables(all_ok=True, deleted=False, variable_cache=variable_cache, target_environment=target_environment)
            else:
                raise Exception('Failed to download "{}" to file "{}"'.format(url, target_file))
        else:
            raise Exception('No suitable method could be found to handle the download.')

        self.spec = dict()
        self.metadata = dict()
        self.log(message='DONE', build_log_message_header=False, level='info', header=log_header)
        return new_key_value_store

