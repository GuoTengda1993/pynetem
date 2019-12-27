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

You can also use original command of `tc/netem`.
For more information about `tc/netem`, you can click here: [netem](https://wiki.linuxfoundation.org/networking/netem)

It is recommended to use web mode, when you have several hosts to control, or you want to build a web page for easier usage.

Run in web mode: `pynetem --web`, default port is 8899, you can specify by yourself `pynetem --web --port=9090`

There are five APIs:
```
[GET] /pynetem/help                                     -- Get demo post data and simple description
[GET] /pynetem/listInterfaces                           -- Get interfaces name of host
[GET] /pynetem/getRules?eht=<interface name>            -- Get qdisc rules by interface
[GET/DELETE] /pynetem/clear?eth=<interface name>        -- Clear all rules
[POST] /pynetem/setRules?eth=<interface name>           -- Set tc qdisc rule
```
Post Body, if you set parameter `None` or `''`, the parameter will be ignored.:
```json
{
    "delay": "100ms 10ms 25%",
    "distribution": "normal",
    "reorder": "25% 50%",
    "loss": "0.3% 25%",
    "duplicate": "1%",
    "corrupt": "0.1%",
    "rate": "256kbit",
    "buffer": 1600,
    "limit": 3000,
    "dst": "10.10.10.0/24"
}
```
**ATTENTION!**

When you press `ctrl + c` to stop the web server, **ALL qdisc rules in all interfaces** will be cleared automatically.