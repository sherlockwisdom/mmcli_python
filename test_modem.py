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
modem.generic.primary-sim-slot                  : --'''
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
modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/0'''
        expected = ['0'] 

        self.assertEqual(Modem.index_value_parser(mmcli_KL),
                expected)

    """
    def test_sms_key_value_parser:
    def test_sms_index_type_parser
    def test_get_exception
    """


if __name__ == "__main__":
    unittest.main()
