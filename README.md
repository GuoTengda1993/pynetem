# pynetem
PyNetem is a tool that allow the user to limit the bandwidth or simulate weak network.
It does so by using iproute's tc command, but greatly simplifies its operation.
And provide apis if you need in your work.
## Installation
```
pip install pynetem
```
## How to Use It?
In command mode, type `pynetem -h`, you will see help information, parameters in this tool is same as 'tc/netem'.

If the host cannot download package from PyPI, you can use PyNetem (>=0.1.2) in your PC (no mater Windows or Linux) with the following parameters in addition:
```bash
--host          The host IP, which you will send command to
--usrname       The username of host
--password      The password of host
```

You can also use original command of `tc/netem`.
For more information about `tc/netem`, you can click here: [netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html)

It is recommended to use web mode, when you have several hosts to control, or you want to build a web page for easier usage.

Run in web mode: `pynetem --web`, default port is 8899, you can specify by yourself `pynetem --web --port=9090`

There are 8 APIs:
```
[GET] /pynetem/help                                     -- Get demo post data and simple description
[GET] /pynetem/listInterfaces                           -- Get interfaces name of host
[GET] /pynetem/getRules?eth=<interface name>            -- Get qdisc rules by interface
[GET/DELETE] /pynetem/clear?eth=<interface name>        -- Clear all rules
[POST] /pynetem/setRules?eth=<interface name>           -- Set tc qdisc rule

[POST] /pynetem/brctl/addbr                             -- Set bridge, the bridge name is pynetem_bridge by defaut
[GET/DELETE] /pynetem/brctl/delbr                       -- Delete pynetem_bridge
[POST] /pynetem/brctl/addif                             -- Add interface(s) to pynetem_bridge
```
Post Body, if you set parameter `None` or `''`, the parameter will be ignored.

Format for the options is the same as [tc-netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html)'s and
[tc-tbf](https://man7.org/linux/man-pages/man8/tc-tbf.8.html)'s.

`[POST] /pynetem/setRules?eth=<interface name>`
```python
{
    "delay": "100ms 10ms 25%",
    "distribution": "normal",
    "reorder": "25% 50%",
    "loss": "0.3% 25%",
    "duplicate": "1%",
    "corrupt": "0.1%",
    # Bitrate control using Netem 
    "netem_rate": "256kbit",
    "netem_limit": 3000,
    # Bitrate control using TBF
    "rate": "256kbit",
    "buffer": 1600,
    "limit": 3000,
    "dst": "10.10.10.0/24"
}
```
`netem_rate` and `rate` are mutually exclusive.

`buffer`, `limit`, and `dst` can only be used if `rate` is set.

---
`[POST] /pynetem/brctl/addbr`

`stp` is "on" by default.
```json
{
    "interfaces": ["eth0", "eth1"],
    "stp": "on"
}
```
---
`[POST] /pynetem/brctl/addif`
```json
{
    "interfaces": ["eth2"]
}
```

---
**ATTENTION!**

When you press `ctrl + c` to stop the web server, **ALL qdisc rules in all interfaces AND the pynetem_bridge** will be cleared automatically.
