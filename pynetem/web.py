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
    app = Flask('pynetem')
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
        return {'status': status, 'msg': msg}, 210
    if eth not in interfaces:
        status, msg = 'error', '{} not in this host'.format(eth)
        return {'status': status, 'msg': msg}, 210
    del_qdisc_root(eth=eth)
    return jsonify({'status': 'success', 'msg': ''})


@api.route('/getRules', methods=['GET'])
def get_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return {'status': status, 'msg': msg}, 210
    if eth not in interfaces:
        status, msg = 'error', '{} not in this host'.format(eth)
        return {'status': status, 'msg': msg}, 210
    resp = get_qdisc_ls(eth=eth)
    if resp[0] == 'ERROR':
        status, msg, code = 'error', resp[1], 210
    else:
        status, code = 'success', 200
        msg = resp[1].strip().split('\n')
    return {'status': status, 'msg': msg}, code


@api.route('/setRules', methods=['POST'])
def set_rules():
    eth = request.args.get('eth')
    if not eth:
        status, msg = 'error', 'Miss parameter: eth'
        return {'status': status, 'msg': msg}, 210
    if eth not in netifaces.interfaces():
        status, msg = 'error', '{} not in this host'.format(eth)
        return {'status': status, 'msg': msg}, 210

    data = request.json
    if data is None:
        return {'status': 'error', 'msg': 'The request body should be in JSON format.'}, 210
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
        return {'status': status, 'msg': msg}, 210
    if distribution and len(delay.split(' ')) == 1:
        status, msg = 'error', 'distribution specified but no latency and jitter values'
        return {'status': status, 'msg': msg}, 210
    if distribution and distribution not in ['normal', 'pareto', 'paretonormal', '', None]:
        status, msg = 'error', 'distribution must be normal/pareto/paretonormal, or set it None'
        return {'status': status, 'msg': msg}, 210
    if reorder and not delay:
        status, msg = 'error', 'Cannot use reorder without delay'
        return {'status': status, 'msg': msg}, 210
    if not rate and (buffer or limit or cidr):
        status, msg = 'error', 'Cannot use buffer, limit or dst without rate'
        return {'status': status, 'msg': msg}, 210

    netem = dict()
    netem['delay'] = delay
    netem['distribution'] = distribution
    netem['reorder'] = reorder
    netem['loss'] = loss
    netem['duplicate'] = duplicate
    netem['corrupt'] = corrupt

    if len(netem) == 0:
        status, msg = 'error', 'Must use netem parameters, such as delay, loss, duplicate, corrupt.'
        return {'status': status, 'msg': msg}, 210

    if rate:
        if cidr:
            resp = add_qdisc_traffic(eth=eth, rate=rate, buffer=buffer, limit=limit, cidr=cidr, **netem)
            if resp[0] == 'ERROR':
                status, msg, code = 'error', resp[1], 210
            else:
                status, msg, code = 'success', resp[1], 200
        else:
            resp = add_qdisc_rate_control(eth=eth, rate=rate, buffer=buffer, limit=limit, **netem)
            if resp[0] == 'ERROR':
                status, msg, code = 'error', resp[1], 210
            else:
                status, msg, code = 'success', resp[1], 200
    else:
        resp = add_qdisc_root(eth=eth, **netem)
        if resp[0] == 'ERROR':
            status, msg, code = 'error', resp[1], 210
        else:
            status, msg, code = 'success', resp[1], 200
    return {'status': status, 'msg': msg}, code


@api.route('/brctl/addbr', methods=['POST'])
def add_bridge():
    data = request.json
    if data is None:
        return {'status': 'error', 'msg': 'The request body should be in JSON format.'}, 210
    eths = data.get('interfaces', [])
    stp = data.get('stp', 'on')
    _eth_mark = False
    if type(eths, list) and len(eths > 0):
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return {'status': status, 'msg': msg}, 210
    resp = brctl_addbr(stp=stp)
    if resp[0] == 'ERROR':
        status, msg = 'error', resp[1]
        return {'status': status, 'msg': msg}, 210
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
    if data is None:
        return {'status': 'error', 'msg': 'The request body should be in JSON format.'}, 210
    eths = data.get('interfaces', [])
    if isinstance(eths, list) and len(eths) > 0:
        _eth_mark = True
        for each in eths:
            if each not in interfaces:
                status, msg = 'error', '{} is not exist in the host'.format(each)
                return {'status': status, 'msg': msg}, 210
    else:
        status, msg = 'error', 'interfaces is a list with eths, or missing parameter of interfaces in request body.'
        return {'status': status, 'msg': msg}, 210
    res = dict()
    for each in eths:
        m = brctl_addif(eth=each)
        res[each] = m[0]
    return jsonify({'status': 'success', 'msg': '', 'res': res})


def start(options):
    app = create_app()
    app.run(host='0.0.0.0', port=options.port, threaded=True, debug=False)
