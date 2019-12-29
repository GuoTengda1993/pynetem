# -*- coding: utf-8 -*-
import os
import atexit
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
    app = Flask(__name__)
    app.root_path = os.path.dirname(os.path.abspath(__file__))
    app.register_blueprint(api, url_prefix='/pynetem')
    atexit.register(tear_down)
    return app


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
        'rate': '256kbit',
        'buffer': 1600,
        'limit': 3000,
        'dst': '10.10.10.0/24',
        'description': 'This demo is just for API: [POST] /pynetem/setRules?eth=eth0.  '
                       'If you set parameter None or \'\', the parameter will be ignored.',
        'otherAPIs': ['[GET/DELETE] /pynetem/clear?eth=eth0 -- clear all rules',
                      '[GET] /pynetem/listInterfaces -- list all interfaces of host']
    }
    return jsonify(demo)


@api.route('/clear', methods=['GET', 'DELETE'])
def clear():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return jsonify({'status': status, 'msg': msg})
    if eth not in interfaces:
        status, msg = 'error', '{} not in this host'.format(eth)
        return jsonify({'status': status, 'msg': msg})
    del_qdisc_root(eth=eth)
    return jsonify({'status': 'success', 'msg': ''})


@api.route('/getRules', methods=['GET'])
def get_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return jsonify({'status': status, 'msg': msg})
    if eth not in interfaces:
        status, msg = 'error', '{} not in this host'.format(eth)
        return jsonify({'status': status, 'msg': msg})
    resp = get_qdisc_ls(eth=eth)
    if resp[0] == 'ERROR':
        status, msg = 'error', resp[1]
    else:
        status = 'success'
        msg = resp[1].strip().split('\n')
    return jsonify({'status': status, 'msg': msg})


@api.route('/setRules', methods=['POST'])
def set_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return jsonify({'status': status, 'msg': msg})
    if eth not in netifaces.interfaces():
        status, msg = 'error', '{} not in this host'.format(eth)
        return jsonify({'status': status, 'msg': msg})

    data = request.json
    delay = data.get('delay')
    distribution = data.get('distribution')
    reorder = data.get('reorder')
    loss = data.get('loss')
    duplicate = data.get('duplicate')
    corrupt = data.get('corrupt')

    rate = data.get('rate')
    buffer = data.get('buffer')
    limit = data.get('limit')
    cidr = data.get('dst')

    if distribution and not delay:
        status, msg = 'error', 'Cannot use distribution without delay'
        return jsonify({'status': status, 'msg': msg})
    if distribution and len(delay.split(' ')) == 1:
        status, msg = 'error', 'distribution specified but no latency and jitter values'
        return jsonify({'status': status, 'msg': msg})
    if distribution and distribution not in ['normal', 'pareto', 'paretonormal', '', None]:
        status, msg = 'error', 'distribution must be normal/pareto/paretonormal, or set it None'
        return jsonify({'status': status, 'msg': msg})
    if reorder and not delay:
        status, msg = 'error', 'Cannot use reorder without delay'
        return jsonify({'status': status, 'msg': msg})
    if not rate and (buffer or limit or cidr):
        status, msg = 'error', 'Cannot use buffer, limit or dst without rate'
        return jsonify({'status': status, 'msg': msg})

    netem = dict()
    netem['delay'] = delay
    netem['distribution'] = distribution
    netem['reorder'] = reorder
    netem['loss'] = loss
    netem['duplicate'] = duplicate
    netem['corrupt'] = corrupt

    if len(netem) == 0:
        status, msg = 'error', 'Must use netem parameters, such as delay, loss, duplicate, corrupt.'
        return jsonify({'status': status, 'msg': msg})

    if rate:
        if cidr:
            resp = add_qdisc_traffic(eth=eth, rate=rate, buffer=buffer, limit=limit, cidr=cidr, **netem)
            if resp[0] == 'ERROR':
                status, msg = 'error', resp[1]
            else:
                status, msg = 'success', resp[1]
        else:
            resp = add_qdisc_rate_control(eth=eth, rate=rate, buffer=buffer, limit=limit, **netem)
            if resp[0] == 'ERROR':
                status, msg = 'error', resp[1]
            else:
                status, msg = 'success', resp[1]
    else:
        resp = add_qdisc_root(eth=eth, **netem)
        if resp[0] == 'ERROR':
            status, msg = 'error', resp[1]
        else:
            status, msg = 'success', resp[1]
    return jsonify({'status': status, 'msg': msg})


@api.route('/brctl/addbr', methods=['POST'])
def add_bridge():
    data = request.json
    eths = data.get('interfaces', [])
    stp = data.get('stp', 'on')
    _eth_mark = False
    if type(eths, list) and len(eths > 0):
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return jsonify({'status': status, 'msg': msg})
    resp = brctl_addbr(stp=stp)
    if resp[0] == 'ERROR':
        status, msg = 'error', resp[1]
        return jsonify({'status': status, 'msg': msg})
    res = dict()
    if _eth_mark:
        for each in eths:
            m = brctl_addif(eth=each)
            res[each] = m[0]
    return jsonify({'status': 'success', 'msg': resp[1], 'res': res})


@api.route('/brctl/delbr', methods=['GET', 'DELETE'])
def del_bridge():
    resp = brctl_delbr()
    return jsonify({'status': resp[0].lower(), 'msg': resp[1]})


@api.route('/brctl/addif', methods=['POST'])
def add_if_to_br():
    data = request.json
    eths = data.get('interfaces', [])
    if type(eths, list) and len(eths > 0):
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return jsonify({'status': status, 'msg': msg})
    res = dict()
    for each in eths:
        m = brctl_addif(eth=each)
        res[each] = m[0]
    return jsonify({'status': 'success', 'msg': '', 'res': res})


def start(options):
    app = create_app()
    app.run(host='0.0.0.0', port=options.port, threaded=True, debug=False)
