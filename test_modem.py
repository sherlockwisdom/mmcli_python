#!/usr/bin/env python3

import unittest
from modem import Modem

class TestModem(unittest.TestCase):
    def test_key_value_parser(self):
        mmcli_Km = '''modem.dbus-path                                 : /org/freedesktop/ModemManager1/Modem/0
modem.generic.manufacturer                      : huawei
modem.generic.model                             : E1552
modem.generic.revision                          : 11.608.13.00.314
modem.generic.supported-capabilities.value[1]   : gsm-umts
modem.generic.drivers.value[1]                  : option
modem.generic.sim                               : /org/freedesktop/ModemManager1/SIM/0
modem.generic.primary-sim-slot                  : --
'''
        expected = {"modem.dbus-path": "/org/freedesktop/ModemManager1/Modem/0",
                "modem.generic.manufacturer": "huawei",
                "modem.generic.model": "E1552",
                "modem.generic.revision": "11.608.13.00.314",
                "modem.generic.supported-capabilities.value[1]": "gsm-umts",
                "modem.generic.drivers.value[1]": "option",
                "modem.generic.sim": "/org/freedesktop/ModemManager1/SIM/0",
                "modem.generic.primary-sim-slot": "--"}

        self.assertEqual(Modem.key_value_parser(mmcli_Km),
                expected)


    def test_index_value_parser(self):
        mmcli_KL = '''modem-list.length   : 1
modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/0
'''
        expected = ['0'] 

        self.assertEqual(Modem.index_value_parser(mmcli_KL),
                expected)

    def test_sms_key_value_parser(self):
        mmcli_Ks = '''sms.dbus-path                      : /org/freedesktop/ModemManager1/SMS/0
sms.content.number                 : MTN
sms.content.text                   : D\303\251sol\303\251 vous avez \303\251puis\303\251 votre quota journalier de SMS. Les prochains SMS envoy\303\251s durant cette journ\303\251e seront factur\303\251s en accord avec votre plan tarifaire.
sms.content.data                   : --
sms.properties.timestamp           : 2021-11-28T14:37:14+01:00
'''
        expected = {"sms.dbus-path": "/org/freedesktop/ModemManager1/SMS/0", 
                "sms.content.number": "MTN",
                "sms.content.text": "D\303\251sol\303\251 vous avez \303\251puis\303\251 votre quota journalier de SMS. Les prochains SMS envoy\303\251s durant cette journ\303\251e seront factur\303\251s en accord avec votre plan tarifaire.",
                "sms.content.data" : "--",
                "sms.properties.timestamp": "2021-11-28T14:37:14+01:00"}

        self.assertEqual(Modem.SMS.sms_key_value_parser(mmcli_Ks),
                expected)

    def test_sms_index_type_parser(self):
        mmcli_Km_messaging_list_sms = '''/org/freedesktop/ModemManager1/SMS/3 (received)
    /org/freedesktop/ModemManager1/SMS/2 (received)
    /org/freedesktop/ModemManager1/SMS/1 (received)
    /org/freedesktop/ModemManager1/SMS/0 (received)
'''
        expected = {"3": "received",
                "2": "received",
                "1": "received",
                "0": "received"}
        self.assertEqual(
                Modem.SMS.sms_index_type_parser(mmcli_Km_messaging_list_sms), 
                expected)

if __name__ == "__main__":
    unittest.main()
