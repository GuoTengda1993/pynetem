# -*- coding: utf-8 -*-
import os
import atexit
from functools import wraps

from flask import Flask, request, jsonify, Blueprint
from .pynetem import *

import netifaces


interfaces = netifaces.interfaces()
api = Blueprint('pynetem', __name__)


def tear_down():
    brctl_delbr()
    for i in interfaces:
        del_qdisc_root(i)


def create_app():
    app = Flask('pynetem')
    app.root_path = os.path.dirname(os.path.abspath(__file__))
    app.register_blueprint(api, url_prefix='/pynetem')
    atexit.register(tear_down)
    return app


def format_response(func):
    @wraps(func)
    def formatter(*args, **kwargs):
        p = func(*args, **kwargs)
        if len(p) == 3:
            status, msg, code = p
            res = None
        else:
            status, msg, res, code = p
        _response = {
            "status": status,
            "msg": msg,
            "res": res,
            "code": code
        }
        return _response, code
    return formatter


@api.route('/listInterfaces', methods=['GET'])
def list_interfaces():
    return jsonify({'status': 'success', 'interfaces': interfaces})


@api.route('/help', methods=['GET'])
def get_demo():
    demo = {
        'delay': '100ms 10ms 25%',
        'distribution': 'normal',
        'reorder': '25% 50%',
        'loss': '0.3% 25%',
        'duplicate': '1%',
        'corrupt': '0.1%',
        'netem_limit': 3000,
        'rate': '256kbit',
        'buffer': 1600,
        'limit': 3000,
        'dst': '10.10.10.0/24',
        'description':
            'This demo is just for API: [POST] /pynetem/setRules?eth=eth0.  '
            'If you set parameter None or \'\', the parameter will be ignored.  '
            '"netem_rate" can also be used to control bandwidth (instead of "rate" that uses TBF).  '
            'Format for the options can be found here: https://man7.org/linux/man-pages/man8/tc-netem.8.html.  '
            'And for TBF rate options: https://man7.org/linux/man-pages/man8/tc-tbf.8.html',
        'otherAPIs': ['[GET/DELETE] /pynetem/clear?eth=eth0 -- clear all rules',
                      '[GET] /pynetem/listInterfaces -- list all interfaces of host']
    }
    return jsonify(demo)


@api.route('/clear', methods=['GET', 'DELETE'])
@format_response
def clear():
    eth = request.args.get('eth')
    if not eth:
        status, msg, code = 'error', 'Miss parameter: eth', 210
        return status, msg, code
    if eth not in interfaces:
        status, msg, code = 'error', '{} not in this host'.format(eth), 210
        return status, msg, code
    status, msg = del_qdisc_root(eth=eth)
    return status, msg, 200


@api.route('/getRules', methods=['GET'])
@format_response
def get_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return status, msg, 210
    if eth not in interfaces:
        status, msg = 'error', '{} not in this host'.format(eth)
        return status, msg, 210
    status, msg = get_qdisc_ls(eth=eth)
    if status == 'error':
        return status, msg, 210
    msg = msg.strip().split('\n')
    return status, msg, 200


@api.route('/setRules', methods=['POST'])
@format_response
def set_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return status, msg, 210
    if eth not in netifaces.interfaces():
        status, msg = 'error', '{} not in this host'.format(eth)
        return status, msg, 210

    data = request.json
    if data is None:
        status, msg = 'error', 'The request body should be in JSON format.'
        return status, msg, 210
    delay = data.get('delay')
    distribution = data.get('distribution')
    reorder = data.get('reorder')
    loss = data.get('loss')
    duplicate = data.get('duplicate')
    corrupt = data.get('corrupt')
    netem_rate = data.get('netem_rate')
    netem_limit = data.get('netem_limit')

    rate = data.get('rate')
    buffer = data.get('buffer')
    limit = data.get('limit')
    cidr = data.get('dst')

    if distribution and not delay:
        status, msg = 'error', 'Cannot use distribution without delay'
        return status, msg, 210
    if distribution and len(delay.split(' ')) == 1:
        status, msg = 'error', 'distribution specified but no latency and jitter values'
        return status, msg, 210
    if distribution and distribution not in ['normal', 'pareto', 'paretonormal', '', None]:
        status, msg = 'error', 'distribution must be normal/pareto/paretonormal, or set it None'
        return status, msg, 210
    if reorder and not delay:
        status, msg = 'error', 'Cannot use reorder without delay'
        return status, msg, 210
    if rate and netem_rate:
        status, msg = 'error', 'Cannot use rate (TBF) and netem_rate together'
        return status, msg, 210
    if not rate and (buffer or limit or cidr):
        status, msg = 'error', 'Cannot use buffer, limit or dst without rate'
        return status, msg, 210

    netem = dict()
    netem['delay'] = delay
    netem['distribution'] = distribution
    netem['reorder'] = reorder
    netem['loss'] = loss
    netem['duplicate'] = duplicate
    netem['corrupt'] = corrupt
    netem['rate'] = netem_rate
    netem['limit'] = str(netem_limit) if netem_limit else None

    if len(netem) == 0:
        status, msg = 'error', 'Must use netem parameters, such as delay, loss, duplicate, corrupt.'
        return status, msg, 210

    if rate:
        if cidr:
            status, msg = add_qdisc_traffic(eth=eth, rate=rate, buffer=buffer, limit=limit, cidr=cidr, **netem)
            if status == 'error':
                return status, msg, 210
            return status, msg, 200
        status, msg = add_qdisc_rate_control(eth=eth, rate=rate, buffer=buffer, limit=limit, **netem)
        if status == 'error':
            return status, msg, 210
        return status, msg, 200

    status, msg = add_qdisc_root(eth=eth, **netem)
    if status == 'error':
        return status, msg, 210
    return status, msg, 200


@api.route('/brctl/addbr', methods=['POST'])
@format_response
def add_bridge():
    data = request.json
    if data is None:
        status, msg = 'error', 'The request body should be in JSON format.'
        return status, msg, 210
    eths = data.get('interfaces', [])
    stp = data.get('stp', 'on')
    _eth_mark = False
    if type(eths, list) and len(eths > 0):
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return status, msg, 210
    status, msg = brctl_addbr(stp=stp)
    if status == 'error':
        return status, msg, 210
    res = dict()
    if _eth_mark:
        for each in eths:
            m = brctl_addif(eth=each)
            res[each] = m[0]
    return status, msg, res, 200


@api.route('/brctl/delbr', methods=['GET', 'DELETE'])
@format_response
def del_bridge():
    status, msg = brctl_delbr()
    if status == 'success':
        return status, msg, 200
    return status, msg, 210


@api.route('/brctl/addif', methods=['POST'])
@format_response
def add_if_to_br():
    data = request.json
    if data is None:
        status, msg = 'error', 'The request body should be in JSON format.'
        return status, msg, 210
    eths = data.get('interfaces', [])
    if isinstance(eths, list) and len(eths) > 0:
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return status, msg, 210
    else:
        status, msg = 'error', 'interfaces is a list with eths, or missing parameter of interfaces in request body.'
        return status, msg, 210
    res = dict()
    for each in eths:
        m = brctl_addif(eth=each)
        res[each] = m[0]
    return 'success', None, res, 200


def start(options):
    app = create_app()
    app.run(host='0.0.0.0', port=options.port, threaded=True, debug=False)
