import sys
import re
from optparse import OptionParser
import pynetem
from .pynetem import *
from pynetem import web

version = pynetem.__version__


def parse_options():
    """
    Handle command-line options with optparse.OptionParser.

    Return list of arguments, largely for use in `parse_arguments`.
    """

    # Initialize
    parser = OptionParser(usage="pynetem [options] [PynetemClass [PynetemClass2 ... ]]")

    parser.add_option(
        '-i', '--interface',
        dest='interface',
        type='str',
        help="The interface of host, which is to be simulated weak network."
    )

    parser.add_option(
        '-d', '--delay',
        dest='delay',
        type='str',
        help="Emulating wide area network delays, if multi parameters of delay, use ',' to split them. "
             "For example: -d 100ms,10ms,25%"
    )

    parser.add_option(
        '--distribution',
        dest='distribution',
        type='str',
        help="Delay distribution, with three parameters: normal/pareto/paretonormal, and must use with --'delay' together",
    )

    parser.add_option(
        '--loss',
        dest='loss',
        type='str',
        help="Random packet loss is specified in the 'tc' command in percent. For example: --loss=0.3%,25%",
    )

    parser.add_option(
        '--duplicate',
        type='str',
        dest='duplicate',
        help="Packet duplication is specified the same way as packet loss. For example: --duplicate=1%",
    )

    parser.add_option(
        '--corrupt',
        type='str',
        dest='corrupt',
        help="Random noise can be emulated (in 2.6.16 or later) with the corrupt option. "
             "This introduces a single bit error at a random offset in the packet. For example: --corrupt=0.1%",
    )

    parser.add_option(
        '--reorder',
        type='str',
        dest='reorder',
        help="Packet re-ordering, must use with --'delay' together. For example: --reorder=25%,50%",
    )

    parser.add_option(
        '--netem-rate',
        type='str',
        dest='netem_rate',
        help="Use netem to limit throughput bitrate. For example: --netem-rate=256kbit",
    )

    parser.add_option(
        '--netem-limit',
        type='int',
        dest='netem_limit',
        help="Maximum number of queued packets. For example: --netem-limit=3000",
    )

    parser.add_option(
        '--rate',
        type='str',
        dest='rate',
        help="Use Token Bucket Filter (TBF) to limit throughput bitrate. For example: --rate=256kbit",
    )

    parser.add_option(
        '--buffer',
        type='int',
        dest='buffer',
        help="Use with '--rate'. For example: --buffer=1600",
    )

    parser.add_option(
        '--limit',
        type='int',
        dest='limit',
        help="Use with '--rate'. For example: --limit=3000",
    )

    parser.add_option(
        '--dst',
        type='str',
        dest='dst',
        help="Only controls traffic to special IP address, and must use with '--rate'. For example: --dst=10.10.10.0/24",
    )

    parser.add_option(
        '-c', '--clear',
        action='store_true',
        dest='clear',
        default=False,
        help="Clear the tc qdisc rules on dev"
    )

    parser.add_option(
        '--web',
        action='store_true',
        dest='web',
        default=False,
        help="Run in web mode."
    )

    parser.add_option(
        '--port',
        type='int',
        dest='port',
        default=8899,
        help="default is 8899."
    )

    parser.add_option(
        '--host',
        type='str',
        dest='host',
        help="The host IP"
    )

    parser.add_option(
        '--username',
        type='str',
        dest='username',
        help="The host username"
    )

    parser.add_option(
        '--password',
        type='str',
        dest='password',
        help="The host password"
    )

    # Version number (optparse gives you --version but we have to do it
    # ourselves to get -V too. sigh)
    parser.add_option(
        '-v', '-V', '--version',
        action='store_true',
        dest='version',
        default=False,
        help="show version number of pynetem and exit"
    )
    # Finalize
    # Return three-tuple of parser + the output from parse_args (opt obj, args)
    opts, args = parser.parse_args()
    return parser, opts, args


def main():
    parser, options, arguments = parse_options()
    _mark = 0

    if options.version:
        logger.info("pynetem %s" % (version,))
        sys.exit(0)

    if options.web:
        web.start(options)
        sys.exit(0)

    if not options.interface:
        logger.error('Must allocate one interfaces. For example: -i eth0')
        sys.exit(1)

    if options.distribution and not options.delay:
        logger.error('Cannot use "--distribution" without "-d"')
        sys.exit(1)

    if options.reorder and not options.delay:
        logger.error('Cannot use "--reorder" without "-d"')
        sys.exit(1)

    if options.rate and options.netem_rate:
        logger.error('Cannot use "--rate" (TBF) and "--netem-rate" together')
        sys.exit(1)

    if options.buffer and not options.rate:
        logger.error('Cannot use "--buffer" without "--rate"')
        sys.exit(1)

    if options.limit and not options.rate:
        logger.error('Cannot use "--limit" without "--rate"')
        sys.exit(1)

    if options.dst and not options.rate:
        logger.error('Cannot use "--dst" without "--rate"')
        sys.exit(1)

    if options.host and not (options.username and options.password):
        logger.error('Cannot use "--host" without "username" and "password"')
        sys.exit(1)

    if options.host and options.web:
        logger.error('Cannot user "--host" and "--web" together.')
        sys.exit(1)

    eth = options.interface
    remote_ssh = False
    _host = None
    _username = None
    _password = None

    if options.host:
        _host = options.host
        _username = options.username
        _password = options.password
        remote_ssh = True

    if options.clear:
        del_qdisc_root(eth=eth, remote_ssh=remote_ssh, host=_host, username=_username, password=_password, )
        sys.exit(0)

    netem = dict()
    if options.delay:
        delay = re.split('[,;，；]', options.delay)
        netem['delay'] = ' '.join(delay)
        if options.distribution:
            if options.distribution in ['normal', 'pareto', 'paretonormal']:
                if len(delay) >= 2:
                    netem['distribution'] = options.distribution
                else:
                    logger.error('distribution specified but no latency and jitter values')
                    sys.exit(1)
            else:
                logger.error('--distribution must be normal, pareto or paretonormal')
                sys.exit(1)
        if options.reorder:
            netem['reorder'] = ' '.join(re.split('[,;，；]', options.reorder))
    if options.loss:
        netem['loss'] = ' '.join(re.split('[,;，；]', options.loss))
    if options.duplicate:
        netem['duplicate'] = options.duplicate
    if options.corrupt:
        netem['corrupt'] = options.corrupt
    if options.netem_rate:
        netem['rate'] = options.netem_rate
    if options.netem_limit:
        netem['limit'] = str(options.netem_limit)

    if len(netem) == 0:
        logger.error('Must use netem parameters, such as delay, loss, duplicate, corrupt.')
        sys.exit(1)

    if options.rate:
        rate = options.rate
        buffer = options.buffer if options.buffer else 1600
        limit = options.limit if options.limit else 3000
        cidr = options.dst if options.dst else None
        if cidr:
            msg = add_qdisc_traffic(eth=eth, rate=rate, buffer=buffer, limit=limit, cidr=cidr, remote_ssh=remote_ssh, host=_host, username=_username, password=_password, **netem)
            if msg[0] == 'error':
                logger.error(msg[1])
                sys.exit(0)
            else:
                logger.info(msg[1])
                sys.exit(0)
        else:
            msg = add_qdisc_rate_control(eth=eth, rate=rate, buffer=buffer, limit=limit, remote_ssh=remote_ssh, host=_host, username=_username, password=_password, **netem)
            if msg[0] == 'error':
                logger.error(msg[1])
                sys.exit(0)
            else:
                logger.info(msg[1])
                sys.exit(0)
    else:
        msg = add_qdisc_root(eth=eth, remote_ssh=remote_ssh, host=_host, username=_username, password=_password, **netem)
        if msg[0] == 'error':
            logger.error(msg[1])
            sys.exit(0)
        else:
            logger.info(msg[1])
            sys.exit(0)
