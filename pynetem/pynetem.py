# -*- coding: utf-8 -*-
import logging
import subprocess

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


def exec_command(command):
    _exec = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info, err = _exec.communicate()
    if err:
        return 'ERROR', err.decode('utf-8')
    else:
        return 'SUCCESS', info.decode('utf-8')


def get_qdisc_ls(eth):
    command = _tc_qdisc_ls.format(ETH=eth)
    msg = exec_command(command)
    return msg


def del_qdisc_root(eth):
    command = _tc_del_qdisc_root.format(ETH=eth)
    msg = exec_command(command)
    return msg


def add_qdisc_root(eth, **kwargs):
    del_qdisc_root(eth)
    command = _tc_add_qdisc_root_netem.format(ETH=eth)
    for each in kwargs:
        if kwargs[each]:
            if kwargs[each].strip() != '':
                command = ' '.join([command, each, kwargs[each]])
    msg = exec_command(command)
    return msg


def add_qdisc_rate_control(eth, rate, buffer=1600, limit=3000, **kwargs):
    buffer = 1600 if buffer is None else buffer
    limit = 3000 if limit is None else limit
    del_qdisc_root(eth)
    if len(kwargs) != 0:
        c1 = _tc_traffic_rate_netem.format(ETH=eth)
        for each in kwargs:
            if kwargs[each]:
                if kwargs[each].strip() != '':
                    c1 = ' '.join([c1, each, kwargs[each]])
        msg = exec_command(c1)
        if msg[0] == 'ERROR':
            return msg
        c2 = _tc_traffic_rate_control.format(ETH=eth, RATE=rate, BUFFER=buffer, LIMIT=limit)
        msg = exec_command(c2)
        return msg
    else:
        msg = 'ERROR', 'Must use netem parameters, such as delay, loss, duplicate, corrupt.'
    return msg


def add_qdisc_traffic(eth, rate, buffer=1600, limit=3000, cidr=None, **kwargs):
    buffer = 1600 if buffer is None else buffer
    limit = 3000 if limit is None else limit
    del_qdisc_root(eth)
    c1 = _tc_traffic_root.format(ETH=eth)
    msg = exec_command(c1)
    if msg[0] == 'ERROR':
        return msg
    c2 = _tc_traffic_rate.format(ETH=eth, RATE=rate, BUFFER=buffer, LIMIT=limit)
    msg = exec_command(c2)
    if msg[0] == 'ERROR':
        return msg
    if len(kwargs) != 0:
        c3 = _tc_traffic_netem.format(ETH=eth)
        for each in kwargs:
            if kwargs[each]:
                if kwargs[each].strip() != '':
                    c3 = ' '.join([c3, each, kwargs[each]])
        msg = exec_command(c3)
        if msg[0] == 'ERROR':
            return msg
    if cidr:
        c4 = _tc_traffic_filter_ip.format(ETH=eth, CIDR=cidr)
        msg = exec_command(c4)
        if msg[0] == 'ERROR':
            return msg
    return msg


def brctl_addbr(stp='on'):
    exec_command(_brctl_delbr)
    msg = exec_command(_brctl_addbr)
    if msg[0] == 'ERROR':
        return msg
    msg = exec_command(_btctl_stp.format(STP=stp))
    return msg


def brctl_addif(eth):
    msg = exec_command(_brctl_addif.format(ETH=eth))
    return msg


def brctl_delbr():
    msg = exec_command(_brctl_delbr)
    return msg


def brctl_delif(eth):
    msg = exec_command(_brctl_delif.format(ETH=eth))
    return msg
