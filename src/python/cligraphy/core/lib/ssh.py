#!/usr/bin/env python
# Copyright 2015 Netflix, Inc.

"""
Wrappers and helpers around paramiko, with two general goals:
- concentrate dependency on paramiko in this module
- support our sometimes intricate uses cases (eg. efficient bastion hopping)
"""

from cligraphy.core import ctx

import paramiko
import OpenSSL.crypto as openssl

import os
import logging
import time

DEFAULT_TIMEOUT = 5
DEFAULT_COMMAND_TIMEOUT = 60

def _setup():
    # basically silence paramiko transport
    logging.getLogger('paramiko.transport').setLevel(logging.CRITICAL)


_setup()


class OpenSSLRSAKey(paramiko.rsakey.RSAKey):
    """For speed, use openssl instead of paramiko's slow pycrypto to sign our auth message"""

    def _from_private_key_file(self, filename, password):
        # paramiko key loading
        data = self._read_private_key_file('RSA', filename, password)
        self._decode_key(data)
        # openssl key loading
        with open(filename, 'rt') as fp:
            self._ssl_key = openssl.load_privatekey(openssl.FILETYPE_PEM, fp.read(), password)

    def sign_ssh_data(self, data):
        sig = openssl.sign(self._ssl_key, data, 'sha1')
        m = paramiko.message.Message()
        m.add_string('ssh-rsa')
        m.add_string(sig)
        return m

def get_proxy_client(password=None):
    """Creates a new client object connected to ${ssh.proxy.host}"""
    return ssh_client_builder().hostname(ctx.conf.ssh.proxy.host).password(password).allow_agent().ssh_config().connect()


def get_awsprod_client(password=None):
    """Creates a new client object connected to an awsprod bastion"""
    return ssh_client_builder().hostname('awsprod').password(password).allow_agent().ssh_config().connect()


def get_client(proxy_client, dest, username='root', port=22, agent=True, keys=None, password=None):
    """Creates a new client object connected to a remove server, by hopping through a bastion host using the given proxy_client"""

    if proxy_client:
        proxy_transport = proxy_client.get_transport()
        fwd = proxy_transport.open_channel("direct-tcpip", (dest, port), ('127.0.0.1', 0))
    else:
        fwd = None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connected = False

    if not connected and agent:
        logging.debug('Trying agent auth')
        try:
            client.connect(dest, username=username, sock=fwd, timeout=DEFAULT_TIMEOUT, allow_agent=True)
            connected = True
        except paramiko.ssh_exception.SSHException:
            logging.debug('Could not auth using agent')


    if not connected and keys:
        logging.debug('Trying key auth')
        # FIXME: here we reconnect for each key attempt; don't do that and use the same connection instead.
        for key in keys:
            try:
                client.connect(dest, username=username, sock=fwd, timeout=DEFAULT_TIMEOUT, allow_agent=False, pkey=key)
                connected = True
                break
            except paramiko.ssh_exception.SSHException:
                continue

    if not connected and password:
        logging.debug('Trying password auth')
        try:
            client.connect(dest, username=username, sock=fwd, timeout=DEFAULT_TIMEOUT, allow_agent=False, password=password)
            connected = True
        except paramiko.ssh_exception.SSHException:
            logging.debug('Could not auth using password')

    if not connected:
        raise Exception('Could not authenticate')

    return client


class _SSHClientBuilder(object):

    def __init__(self):
        super(_SSHClientBuilder, self).__init__()
        self._hostname = None
        self._port = 22
        self._username = None
        self._password = None
        self._config = paramiko.SSHConfig()
        self._client_class = paramiko.SSHClient
        self._missing_host_key_policy = paramiko.AutoAddPolicy
        self._timeout = DEFAULT_TIMEOUT
        self._banner_timeout = DEFAULT_TIMEOUT
        self._allow_agent = None
        self._proxy_command = None
        self._sock = None

    def ssh_config(self, filename='~/.ssh/config'):
        """Parse the given ssh config file. Optional.
        No config file is parsed by default, but if this is called without a filename, ~/.ssh/config will be parsed."""
        absolute_filename = os.path.expanduser(filename)
        if not os.path.exists(absolute_filename):
            logging.warning('ssh config file %s does not exist, skipping it', absolute_filename)
            return self
        logging.debug('Reading ssh configuration from %s', absolute_filename)
        with open(absolute_filename, 'r') as fpin:
            self._config.parse(fpin)
        return self

    def client(self, client_class):
        """Sets the client class to build with. Optional, defaults to paramiko.SSHClient"""
        logging.debug('Setting client class to %s', client_class)
        self._client_class = client_class
        return self

    def missing_host_key_policy(self, policy_class):
        """Set the client class to build with. Optional, defaults to paramiko.AutoAddPolicy"""
        logging.debug('Setting missing host key policy to %s', policy_class)
        self._missing_host_key_policy = policy
        return self

    def hostname(self, hostname):
        """Set the destination hostname. Mandatory"""
        logging.debug('Setting hostname to %s', hostname)
        self._hostname = hostname
        return self

    def username(self, username):
        """Set the username. Optional, defaults to $USER"""
        logging.debug('Setting username to %s', username)
        self._username = username
        return self

    def password(self, password):
        """Set a password. Optional, no default"""
        logging.debug('Setting password (password not shown here for security reasons)')
        self._password = password
        return self

    def port(self, port):
        """Set the destination port number. Optional, defaults to 22"""
        logging.debug('Setting port to %d', port)
        self._port = port
        return self

    def timeout(self, timeout=5, banner_timeout=5):
        logging.debug('Setting timeouts: timeout=%d, banner_timeout=%d', timeout, banner_timeout)
        self._timeout = timeout
        self._banner_timeout = banner_timeout
        return self

    def allow_agent(self, allow_agent=True):
        """Allow or disallow ssh agent. Optional. Defaults to true"""
        self._allow_agent = allow_agent
        return self

    def proxy(self, proxy_command):
        self._proxy_command = proxy_command
        return self

    def sock(self, sock):
        self._sock = sock
        return self

    def connect(self):
        """Finish building the client and connects to the target server, returning a paramiko client object"""
        assert self._client_class
        assert self._hostname is not None, 'destination hostname was not specified'
        client = self._client_class()
        if self._missing_host_key_policy:
            client.set_missing_host_key_policy(self._missing_host_key_policy())

        config_data = self._config.lookup(self._hostname)
        ssh_kwargs = {
            'timeout': self._timeout,
            'banner_timeout': self._banner_timeout,
            'port': self._port
        }

        # unless one is explicitely specified with .user(), get our username from configuration, defaulting to $USER
        if self._username is None:
            ssh_kwargs['username'] = config_data.get('user', os.getenv('USER'))
        else:
            ssh_kwargs['username'] = self._username

        if self._password is not None:
            ssh_kwargs['password'] = self._password

        if 'proxycommand' in config_data:
            ssh_kwargs['sock'] = paramiko.ProxyCommand(config_data['proxycommand'])
        elif self._proxy_command is not None:
            ssh_kwargs['sock'] = paramiko.ProxyCommand(self._proxy_command)

        if config_data.get('identity_file') is not None:
            ssh_kwargs['key_filename'] = config_data.get('identity_file')

        # unless explicitely specified with .allow_agent, allow agent by default unless identitiesonly is yes in our config
        if self._allow_agent is None:
            ssh_kwargs['allow_agent'] = config_data.get('identitiesonly', 'no') != 'yes'
        else:
            ssh_kwargs['allow_agent'] = self._allow_agent

        if self._sock is not None:
            ssh_kwargs['sock'] = self._sock

        logging.debug('Connecting to %s with options %s', config_data['hostname'], ssh_kwargs)
        client.connect(config_data['hostname'], **ssh_kwargs)
        return client

def ssh_client_builder():
    return _SSHClientBuilder()


class TaskException(Exception):
    pass

class ConnectException(TaskException):
    pass

class CommandException(TaskException):
    pass


def exec_command(client, command, command_timeout=DEFAULT_COMMAND_TIMEOUT,
                 feed_data=None, get_files=[], put_files=[],
                 io_step_s=0.1, io_chunk_size=1024,
                 out=None, err=None):
    """Execute a command on the given client, grabbing stdout/stderr and the exit status code"""
    transport = client.get_transport()
    channel = transport.open_session()
    sftp = None
    if get_files or put_files:
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get_channel().settimeout(command_timeout)

    try:
        if put_files:
            for path, content in put_files.items():
                with sftp.open(path, 'wb') as remote_fp:
                    remote_fp.write(content)

        channel.exec_command(command)
        if feed_data is not None:
            channel.settimeout(command_timeout)
            channel.sendall(feed_data)

        channel.shutdown_write()
        channel.settimeout(io_step_s)
        out = out if out is not None else []
        err = err if err is not None else []
        deadline = time.time() + command_timeout
        while time.time() <= deadline and not channel.exit_status_ready():
            ready = channel.recv_ready(), channel.recv_stderr_ready()
            if not ready[0] and not ready[1]:
                time.sleep(io_step_s)
                continue
            if ready[0]:
                out.append(channel.recv(io_chunk_size))
            if ready[1]:
                err.append(channel.recv_stderr(io_chunk_size))

        if not channel.exit_status_ready():
            raise CommandException("Timeout during command execution")

        while channel.recv_ready():
            out.append(channel.recv(io_chunk_size))
        while channel.recv_stderr_ready():
            out.append(channel.recv_stderr(io_chunk_size))

        status = channel.recv_exit_status()

        get_files_result = {}
        if get_files:
            for path in get_files:
                with sftp.open(path, 'rb') as remote_fp:
                    get_files_result[path] = remote_fp.read()

        return out, err, status, get_files_result
    finally:
        if sftp:
            sftp.close()
        channel.close()
