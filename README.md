# Heatmiser NeoHub, NeoStat, NeoPlug Library

This library controls the wireless mesh NeoStat thermostats, via the NeoHub.

It talks the JSON-over-TCP protocol, on the LAN, to the Neo Hub - so no internet
access is required.

I do not have any wifi neostats, just the "mesh networked" (aka zigbee) ones.


### Example CLI Usage

    $ export NEOHUB_IP="192.168.0.123"
    $ ./neocli.py list

    <NeoStat id=1  temp=20.8 name='Bedroom'>
    <NeoStat id=2 temp=21.7 name='Office'>
    <NeoStat id=3  temp=23.4 name='Kitchen'>

    <NeoPlug id=4  status=OFF name='Desktop fan plug'>


    $ ./neocli.py rename_zone "Bedroom" "Master Bedroom"
    $ ./neocli.py frost_on "Master Bedroom"
    $ ./neocli.py switch_on "Desktop fan plug"

