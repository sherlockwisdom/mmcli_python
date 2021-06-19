#!/bin/python3

# modem has
# - SMS
# - USSD

import traceback
import subprocess
from subprocess import Popen, PIPE

class SMS():
    modem=None

    number=None
    text=None
    pdu_type=None
    state=None
    timestamp=None
    query_command=None

    @staticmethod
    def s_layer_parse(data):
        data = data.split('\n')
        n_modems = int(data[0].split(': ')[1])
        sms = []
        for i in range(1, (n_modems + 1)):
            sms_index = data[i].split('/')[-1]
            if not sms_index.isdigit():
                continue
            sms.append( sms_index )

        return sms

    # private method
    def __list(self, modem):
        data=None
        sms_list = []
        sms_list += modem.query_command + ["--messaging-list-sms"]
        try: 
            mmcli_output = subprocess.check_output(sms_list, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            data = SMS.s_layer_parse(mmcli_output)
        return data

    def __build_attributes(self, data):
        self.text = data["sms.content.text"]
        self.state = data["sms.properties.state"]
        self.number = data["sms.content.number"]
        self.timestamp = data["sms.properties.timestamp"]
        self.pdu_type = data["sms.properties.pdu-type"]

    def __extract_message(self):
        try: 
            mmcli_output = subprocess.check_output(self.query_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            data=Modem.f_layer_parse(mmcli_output)
            self.__build_attributes(data)

    def __init__(self, modem=None, index=None):
        if modem is not None:
            self.modem = modem

        elif index is not None:
            self.index = index
            self.query_command = ["mmcli", "-Ks", self.index]
            self.__extract_message()
        else:
            raise Exception('modem or index needed to initialize sms')

    def get_messages(self):
        data = self.__list(self.modem)
        messages = []
        for index in data:
            sms = SMS(index=index)
            messages.append( sms )
        return messages



class USSD():
    modem=None
    def __init__(self, modem):
        self.modem = modem

    def initiate(self, command):
        ussd_command = self.modem.query_command + [f"--3gpp-ussd-initiate={command}"]
        # print( ussd_command )
        try: 
            mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            # print(f"[stderr]>> return code[{error.returncode}], output[{error.output.decode('utf-8')}")
            raise Exception(f"[stderr]>> return code[{error.returncode}], output[{error.output.decode('utf-8')}")
        else:
            # remote 'new reply from network:'
            mmcli_output = mmcli_output.split(": ", 1)[1].split("'")[1]
            # print( mmcli_output )
            return mmcli_output

class Modem():
    imei=None
    model=None
    index=None
    state=None
    dbus_path=None
    power_state=None
    operator_code=None
    operator_name=None
    query_command=None

    # sub-classes
    sms=None
    ussd=None

    # private methods
    @staticmethod
    def f_layer_parse(data):
        data = data.split('\n')
        details = {}
        m_detail=None
        for output in data:
            m_detail = output.split(': ')
            if len(m_detail) < 2:
                continue
            key = m_detail[0].replace(' ', '')
            details[key] = m_detail[1]

        return details

    def __build_attributes(self, data):
        self.imei = data["modem.3gpp.imei"]
        self.state = data["modem.generic.state"]
        self.model = data["modem.generic.model"]
        self.dbus_path = data["modem.dbus-path"]
        self.power_state = data["modem.generic.power-state"]
        self.operator_code = data["modem.3gpp.operator-code"]
        self.operator_name = data["modem.3gpp.operator-name"]

    # public methods
    def __init__(self, index):
        self.query_command = ["mmcli", f"-Km", index]
        self.index = index
        self.refresh()

        self.sms = SMS(self)
        self.ussd = USSD(self)

    def refresh(self):
        data = Modem.f_layer_parse(subprocess.check_output(self.query_command, stderr=subprocess.STDOUT).decode('utf-8'))
        self.__build_attributes(data)

    def get_sms_messages(self):
        return self.sms.get_messages()

if __name__ == "__main__":
    import sys
    modem = Modem(sys.argv[1])
    print(f"- imei: {modem.imei}")
    print(f"- model: {modem.model}")
    print(f"- index: {modem.index}")
    print(f"- state: {modem.state}")
    print(f"- dbus path: {modem.dbus_path}")
    print(f"- power state: {modem.power_state}")
    print(f"- operator code: {modem.operator_code}")
    print(f"- operator name: {modem.operator_name}")

    smsses = modem.get_sms_messages()
    for sms in smsses:
        print(f"\n- number: {sms.number}")
        print(f"- text: {sms.text}")
        print(f"- pdu-type: {sms.pdu_type}")
        print(f"- state: {sms.state}")
        print(f"- timestamp: {sms.timestamp}")
