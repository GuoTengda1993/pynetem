# -*- coding: utf-8 -*-
import logging
import subprocess
import paramiko
from paramiko.ssh_exception import SSHException


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_tc_add_qdisc = 'sudo tc qdisc add'
_tc_del_qdisc = 'sudo tc qdisc del'
_tc_add_qdisc_root_netem = 'sudo tc qdisc add dev {ETH} root netem'
_tc_del_qdisc_root = 'sudo tc qdisc del dev {ETH} root'
_tc_root_netem = 'dev {ETH} root netem'

_tc_traffic_root = 'sudo tc qdisc add dev {ETH} root handle 1: prio'
_tc_traffic_rate = 'sudo tc qdisc add dev {ETH} parent 1:3 handle 30: tbf rate {RATE} buffer {BUFFER} limit {LIMIT}'
_tc_traffic_netem = 'sudo tc qdisc add dev {ETH} parent 30:1 handle 31: netem'
_tc_traffic_filter_ip = 'sudo tc filter add dev {ETH} protocol ip parent 1:0 prio 3 u32 match ip dst {CIDR} flowid 1:3'

_tc_traffic_rate_netem = 'sudo tc qdisc add dev {ETH} root handle 1:0 netem'
_tc_traffic_rate_control = 'sudo tc qdisc add dev {ETH} parent 1:1 handle 10: tbf rate {RATE} buffer {BUFFER} limit {LIMIT}'

_tc_qdisc_ls = 'sudo tc qdisc ls dev {ETH}'


_brctl_addbr = 'sudo brctl addbr pynetem_bridge'
_brctl_delbr = 'sudo brctl delbr pynetem_bridge'
_brctl_addif = 'sudo brctl addif pynetem_bridge {ETH}'
_brctl_delif = 'sudo brctl delif pynetem_bridge {ETH}'
_btctl_stp = 'sudo brctl stp pynetem_bridge {STP}'


class SSHAgent:

    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.username = username
        self.password = password
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.ip, port=port, username=self.username, password=self.password)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ssh.close()

    def remote_command(self, command):
        stdin, stdout, stderr = self.ssh.exec_command(command)
        logger.info('Send command - {ip}: {command}'.format(ip=self.ip, command=command))
        error = stderr.read().decode('utf-8')
        if error:
            return 'error', error
        else:
            return 'success', stdout.read().decode('utf-8')


def exec_command(command, remote_ssh=False, host=None, username=None, password=None):
    bad_chars = ["&", "|", ";", "$", ">", "<", "`", "\\", "!"]
    if any([char in command for char in bad_chars]):
        return 'error', 'Illegal characters in command that may result in arbitrary execution'

    if not remote_ssh:
        _exec = subprocess.Popen(command.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        info, err = _exec.communicate()
        if err:
            return 'error', err.decode('utf-8')
        else:
            return 'success', info.decode('utf-8')
    else:
        try:
            ssh = SSHAgent(ip=host, username=username, password=password)
            with ssh:
                output = ssh.remote_command(command)
        except SSHException as e:
            output = 'error', e
        return output


def get_qdisc_ls(eth, remote_ssh=False, host=None, username=None, password=None):
    command = _tc_qdisc_ls.format(ETH=eth)
    msg = exec_command(command, remote_ssh, host, username, password)
    return msg


def del_qdisc_root(eth, remote_ssh=False, host=None, username=None, password=None):
    command = _tc_del_qdisc_root.format(ETH=eth)
    msg = exec_command(command, remote_ssh, host, username, password)
    return msg


def add_qdisc_root(eth, remote_ssh=False, host=None, username=None, password=None, **kwargs):
    del_qdisc_root(eth, remote_ssh, host, username, password)
    command = _tc_add_qdisc_root_netem.format(ETH=eth)
    for each in kwargs:
        if kwargs[each]:
            if kwargs[each].strip() != '':
                command = ' '.join([command, each, kwargs[each]])
    msg = exec_command(command, remote_ssh, host, username, password)
    return msg


def add_qdisc_rate_control(eth, rate, buffer=1600, limit=3000, remote_ssh=False, host=None, username=None, password=None, **kwargs):
    buffer = 1600 if buffer is None else buffer
    limit = 3000 if limit is None else limit
    del_qdisc_root(eth, remote_ssh, host, username, password)
    if len(kwargs) != 0:
        c1 = _tc_traffic_rate_netem.format(ETH=eth)
        for each in kwargs:
            if kwargs[each]:
                if kwargs[each].strip() != '':
                    c1 = ' '.join([c1, each, kwargs[each]])
        msg = exec_command(c1, remote_ssh, host, username, password)
        if msg[0] == 'error':
            return msg
        c2 = _tc_traffic_rate_control.format(ETH=eth, RATE=rate, BUFFER=buffer, LIMIT=limit)
        msg = exec_command(c2, remote_ssh, host, username, password)
        return msg
    else:
        msg = 'error', 'Must use netem parameters, such as delay, loss, duplicate, corrupt.'
    return msg


def add_qdisc_traffic(eth, rate, buffer=1600, limit=3000, cidr=None, remote_ssh=False, host=None, username=None, password=None, **kwargs):
    buffer = 1600 if buffer is None else buffer
    limit = 3000 if limit is None else limit
    del_qdisc_root(eth, remote_ssh, host, username, password)
    c1 = _tc_traffic_root.format(ETH=eth)
    msg = exec_command(c1, remote_ssh, host, username, password)
    if msg[0] == 'error':
        return msg
    c2 = _tc_traffic_rate.format(ETH=eth, RATE=rate, BUFFER=buffer, LIMIT=limit)
    msg = exec_command(c2, remote_ssh, host, username, password)
    if msg[0] == 'error':
        return msg
    if len(kwargs) != 0:
        c3 = _tc_traffic_netem.format(ETH=eth)
        for each in kwargs:
            if kwargs[each]:
                if kwargs[each].strip() != '':
                    c3 = ' '.join([c3, each, kwargs[each]])
        msg = exec_command(c3, remote_ssh, host, username, password)
        if msg[0] == 'error':
            return msg
    if cidr:
        c4 = _tc_traffic_filter_ip.format(ETH=eth, CIDR=cidr)
        msg = exec_command(c4, remote_ssh, host, username, password)
        if msg[0] == 'error':
            return msg
    return msg


def brctl_addbr(stp='on', remote_ssh=False, host=None, username=None, password=None):
    exec_command(_brctl_delbr, remote_ssh, host, username, password)
    msg = exec_command(_brctl_addbr, remote_ssh, host, username, password)
    if msg[0] == 'error':
        return msg
    msg = exec_command(_btctl_stp.format(STP=stp), remote_ssh, host, username, password)
    return msg


def brctl_addif(eth, remote_ssh=False, host=None, username=None, password=None):
    msg = exec_command(_brctl_addif.format(ETH=eth), remote_ssh, host, username, password)
    return msg


def brctl_delbr(remote_ssh=False, host=None, username=None, password=None):
    msg = exec_command(_brctl_delbr, remote_ssh, host, username, password)
    return msg


def brctl_delif(eth, remote_ssh=False, host=None, username=None, password=None):
    msg = exec_command(_brctl_delif.format(ETH=eth), remote_ssh, host, username, password)
    return msg
