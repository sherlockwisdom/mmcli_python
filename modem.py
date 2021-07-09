#!/bin/python3

# modem has
# - SMS
# - USSD

import traceback
import subprocess
from subprocess import Popen, PIPE

def mmcli_exception_output(error):
    message=None
    status=None
    returncode = error.returncode
    err_output = error.output.decode('utf-8').replace('\n', '')
    message=err_output
    print(message)

class SMS():
    index=None
    modem=None

    number=None
    text=None

    pdu_type=None
    state=None
    timestamp=None
    query_command=None

    # required for sending
    delivery_report=None
    validity=None
    data=None
    _set=False

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
    def __list(self):
        data=None
        sms_list = []
        sms_list += self.modem.query_command + ["--messaging-list-sms"]
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

    def __create(self, number, text, delivery_report):
        mmcli_create_sms = []
        mmcli_create_sms += self.modem.query_command + ["--messaging-create-sms"]
        mmcli_create_sms[-1] += f'=number={number},text="{text}"'
        try: 
            mmcli_output = subprocess.check_output(mmcli_create_sms, stderr=subprocess.STDOUT).decode('utf-8').replace('\n', '')

        except subprocess.CalledProcessError as error:
            mmcli_exception_output(error)
            print(traceback.format_exc())
        else:
            # print(mmcli_output)
            mmcli_output = mmcli_output.split(': ')
            creation_status = mmcli_output[0]
            sms_index = mmcli_output[1].split('/')[-1]
            if not sms_index.isdigit():
                raise Exception("error - sms index isn't an index:", sms_index)
                return False
            else:
                self.index = sms_index
        return True

    def __init__(self, modem=None, index=None):
        if modem is not None:
            self.modem = modem
        if index is not None:
            self.index = index
            self.query_command = ["mmcli", "-Ks", self.index]
            self.__extract_message()
        elif(modem is None and index is None):
            raise Exception('modem or index needed to initialize sms')

    def get_messages(self):
        data = self.__list()
        print(data)
        messages = []
        for index in data:
            sms = SMS(self.modem, index=index)
            messages.append( sms )
        return messages

    def set(self, number, text, delivery_report=None, validity=None, data=None):
        self.number = number
        self.text = text
        self.delivery_report=delivery_report
        self.validity=validity
        self.data=data

        if self.__create(number, text, delivery_report):
            self._set=True
            return True
        return False

    def is_set(self):
        return self._set

    def send(self):
        print(f"\n- sending sms: {self.index}")
        if self.index is None:
            raise Exception("failed to create sms - no index available")

        mmcli_send = self.modem.query_command + ["-s", self.index, "--send", "--timeout=10"] 

        try: 
            mmcli_output = subprocess.check_output(mmcli_send, stderr=subprocess.STDOUT).decode('utf-8').replace('\n', '')

        except subprocess.CalledProcessError as error:
            # mmcli_exception_output(error)
            raise Exception(error)
        else:
            return True
        return False

    def delete(self):
        print(f"\n- deleting sms: {self.index}")
        command = []
        command = self.modem.query_command + [f"--messaging-delete-sms={self.index}"] 
        try: 
           # mmcli_output = subprocess.check_output(mmcli_delete_sms, stderr=subprocess.STDOUT).decode('utf-8').replace('\n', '')
           mmcli_output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode('utf-8').replace('\n', '')
        except subprocess.CalledProcessError as error:
            # mmcli_exception_output(error)
            raise Exception(error)
        else:
            return True
        return False


class USSD():
    modem=None
    def __init__(self, modem):
        self.modem = modem

    def initiate(self, command):
        ussd_command = self.modem.query_command + [f"--3gpp-ussd-initiate={command}"]
        try: 
            mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            mmcli_output = mmcli_output.split(": ", 1)[1].split("'")[1]
            return mmcli_output

    def respond(self, command):
        ussd_command = self.modem.query_command + [f"--3gpp-ussd-respond={command}"]
        try: 
            mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            mmcli_output = mmcli_output.split(": '", 1)[1][:-1]
            return mmcli_output

    def cancel(self):
        ussd_command = self.modem.query_command + [f"--3gpp-ussd-cancel"]
        try: 
            mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            return True
        
        return False

    def status(self):
        ussd_command = self.modem.query_command + [f"--3gpp-ussd-status"]

        try: 
            mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('utf-8')
        except subprocess.CalledProcessError as error:
            print(traceback.format_exc())
        else:
            mmcli_output = mmcli_output.split('\n')
            s_details = {}
            for output in mmcli_output:
                s_detail = output.split(': ')
                if len(s_detail) < 2:
                    continue
                key = s_detail[0].replace(' ', '')
                s_details[key] = s_detail[1]

            return s_details

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

    @staticmethod
    def list():
        try:
            query_command=["mmcli", "-KL"]
            data = Modem.f_layer_parse(subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('utf-8'))
            return [index[1].split('/')[-1] for index in f_layer_parse(data)]
        except subprocess.CalledProcessError as error:
            raise Exception(f"execution failed cmd={error.cmd} index={self.index} returncode={error.returncode} std(out/err)={error.stderr}")

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
        try:
            self.query_command = ["mmcli", f"-Km", index]
            self.index = index
            self.refresh()

            self.sms = SMS(self)
            self.ussd = USSD(self)
        except Exception as error:
            # print(traceback.format_exc())
            print(error)
        finally:
            print("modem instantiation failed...")

    def refresh(self):
        try:
            data = Modem.f_layer_parse(subprocess.check_output(self.query_command, stderr=subprocess.STDOUT).decode('utf-8'))
            self.__build_attributes(data)
        except subprocess.CalledProcessError as error:
            raise Exception(f"execution failed cmd={error.cmd} index={self.index} returncode={error.returncode} std(out/err)={error.stderr}")

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

    assert(modem.sms.set(number=sys.argv[2], text="Hello world") == True)
    print(f"\n- sending:text - {modem.sms.text}")
    print(f"- sending:number - {modem.sms.number}")
    print(f"- sending:index - {modem.sms.index}")
    assert(modem.sms.send() == True)
    assert(modem.sms.delete() == True)
    
    smsses = modem.sms.get_messages()
    print(smsses)
    for sms in smsses:
        print(f"\n- index: {sms.index}")
        print(f"- number: {sms.number}")
        print(f"- text: {sms.text}")
        print(f"- pdu-type: {sms.pdu_type}")
        print(f"- state: {sms.state}")
        print(f"- timestamp: {sms.timestamp}")
        assert(sms.delete() == True)

    print('ussd initiate ', modem.ussd.initiate("*123#"))
    print('ussd respond ', modem.ussd.respond("6"))
    print('ussd respond ', modem.ussd.respond("4"))
