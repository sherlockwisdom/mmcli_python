#!/bin/python3

# modem has
# - SMS
# - USSD

import traceback
import subprocess
import re
from subprocess import Popen, PIPE

import enum
class Modem():
    imei=None
    model=None
    index=None
    state=None
    dbus_path=None
    power_state=None
    operator_code=None
    operator_name=None
    model=None
    manufacturer=None
    query_command=None

    class IDENTIFIERS(enum.Enum):
        IMEI=1
        INDEX=2

    class SMS():
        index=None
        modem=None

        number=None
        text=None

        pdu_type=None
        state=None
        timestamp=None

        # required for sending
        delivery_report=None
        validity=None
        data=None
        _set=False

        query_command=None

        # private method
        @classmethod
        def list(cls, _filter=None):
            def filter_type(index, _type, expected):
                if _type == expected:
                    return index

            data=None
            sms_list = []
            sms_list += cls.modem.query_command + ["--messaging-list-sms"]
            if _filter is not None:
                sms_list[1] = sms_list[1].replace('K', '')
            try: 
                mmcli_output = subprocess.check_output(sms_list, stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                if _filter is not None:
                    data = Modem.nok_layer_parse(mmcli_output)
                    cats = []
                    for index, _type in data.items():
                        filtered=filter_type(index, _type, _filter)
                        if filtered is not None:
                            cats.append(filtered)
                    data = cats
                else:
                    data = Modem.s_layer_parse(mmcli_output)
            return data

        @classmethod
        def __build_attributes(cls, data):
            cls.text = data["sms.content.text"]
            cls.state = data["sms.properties.state"]
            cls.number = data["sms.content.number"]
            cls.timestamp = data["sms.properties.timestamp"]
            cls.pdu_type = data["sms.properties.pdu-type"]

        @classmethod
        def __extract_message(cls):
            try: 
                mmcli_output = subprocess.check_output(cls.query_command, stderr=subprocess.STDOUT, encoding='unicode_escape')
                # self.logging.debug(mmcli_output)
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                data=Modem.sms_f_layer_parse(mmcli_output)
                cls.__build_attributes(data)

        @classmethod
        def __create(cls, number, text, delivery_report):
            mmcli_create_sms = []
            mmcli_create_sms += cls.modem.query_command + ["--messaging-create-sms"]
            mmcli_create_sms[-1] += f'=number={number},text="{text}"'
            try: 
                mmcli_output = subprocess.check_output(mmcli_create_sms, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')

            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                mmcli_output = mmcli_output.split(': ')
                creation_status = mmcli_output[0]
                sms_index = mmcli_output[1].split('/')[-1]
                if not sms_index.isdigit():
                    raise Exception("error - sms index isn't an index:", sms_index)
                    return False
                else:
                    cls.index = sms_index
            return True

        # SMS:__init__
        @classmethod
        def __init__(cls, modem=None, index=None):
            if modem is not None:
                cls.modem = modem
            if index is not None:
                cls.index = index
                cls.query_command = ["mmcli", "-Ks", cls.index]
                cls.__extract_message()
            elif(modem is None and index is None):
                raise Exception('modem or index needed to initialize sms')

        @classmethod
        def set(cls, number, text, delivery_report=None, validity=None, data=None):
            cls.number = number
            cls.text = text
            cls.delivery_report=delivery_report
            cls.validity=validity
            cls.data=data

            if cls.__create(number, text, delivery_report):
                cls._set=True
            
            return cls

        @classmethod
        def is_set(cls):
            return cls._set

        @classmethod
        def send(cls, timeout=20):
            if cls.index is None:
                raise Exception("failed to create sms - no index available")

            mmcli_send = cls.modem.query_command + ["-s", cls.index, "--send", f"--timeout={timeout}"] 
            try: 
                mmcli_output = subprocess.check_output(mmcli_send, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                return True
            return False

        @classmethod
        def delete(cls, index):
            command = []
            command = cls.modem.query_command + [f"--messaging-delete-sms={index}"] 
            try: 
               mmcli_output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                return True
            return False

    class USSD():
        modem=None

        class CannotInitiateUSSD(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output

        class UnknownError(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output

        class ActiveSession(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output

        @classmethod
        def get_exception(cls, command, output):
            if (str(output).find(
                'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.WrongState: Cannot initiate USSD: a session is already active')
                > -1):
                return cls.ActiveSession(command, output)
            if (str(output).find(
                'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.WrongState: Cannot initiate USSD')
                > -1 or str(output).find(
                    'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.Aborted')
                > -1):
                return cls.CannotInitiateUSSD(command, output)
            return cls.UnknownError(command, output)

        @classmethod
        def __init__(cls, modem):
            cls.modem = modem

        @classmethod
        def initiate(cls, command, timeout=60):
            query_command = cls.modem.query_command
            query_command[1] = query_command[1].replace('K', '')
            ussd_command = query_command + [f'--3gpp-ussd-initiate={command}', f'--timeout={timeout}']
            try: 
                mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                raise cls.get_exception(command=error.cmd, output=error.output)
            else:
                mmcli_output = mmcli_output.split(": ", 1)[1].split("'")[1]
                return mmcli_output

        @classmethod
        def respond(cls, command, timeout=60):
            query_command = cls.modem.query_command
            query_command[1] = query_command[1].replace('K', '')
            ussd_command = query_command + [f'--3gpp-ussd-respond={command}']
            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, 
                        output=error.output, returncode=error.returncode)
            else:
                mmcli_output = mmcli_output.split(": '", 1)[1][:-1]
                return mmcli_output

        @classmethod
        def cancel(cls):
            ussd_command = cls.modem.query_command + [f"--3gpp-ussd-cancel"]
            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                # raise(error)
                pass
            else:
                return True
            
            return False

        @classmethod
        def status(cls):
            ussd_command = cls.modem.query_command + [f"--3gpp-ussd-status"]

            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output,
                        returncode=error.returncode)
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


    @staticmethod
    def list():
        try:
            query_command=["mmcli", "-KL"]
            return [index for index in Modem.s_layer_parse(subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape'))]
        except subprocess.CalledProcessError as error:
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)

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
    
    @staticmethod
    def sms_f_layer_parse(data):
        data = data.split('\n')
        details = {}
        m_detail=None
        sms_text = []

        is_sms_text = False
        for output in data:
            if output.find("sms.content.text") > -1:
                is_sms_text = True
                m_detail = output.split(': ')
                if len(m_detail) < 2:
                    continue
                sms_text.append(m_detail[1])
                continue

            if not is_sms_text or (
                    is_sms_text and re.search(r"^sms\.\w*\S\w*[\S]\w*\s*: ", output)):
                is_sms_text = False

                m_detail = output.split(': ')
                if len(m_detail) < 2:
                    continue
                key = m_detail[0].replace(' ', '')
                details[key] = m_detail[1]
            else:
                sms_text.append(output)
        sms_text = '\n'.join(sms_text)
        details['sms.content.text'] = sms_text
        # print(details)
        return details

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
    
    @staticmethod
    def nok_layer_parse(data):
        data = data.split('\n')
        cats = {}
        for line in data:
            if len(line) < 1:
                continue
            secs = line.split(' ')
            cats[secs[-2].split('/')[-1]] = secs[-1].replace('(', '').replace(')', '')
        return cats

    def __build_attributes(self, data):
        '''look into
        - modem.generic.device-identifier
        - modem.generic.equipment-identifier
        '''

        self.imei = data["modem.3gpp.imei"]
        self.state = data["modem.generic.state"]
        self.model = data["modem.generic.model"]
        self.dbus_path = data["modem.dbus-path"]
        self.power_state = data["modem.generic.power-state"]
        self.operator_code = data["modem.3gpp.operator-code"]
        self.operator_name = data["modem.3gpp.operator-name"]
        self.manufacturer = data["modem.generic.manufacturer"]

    # MODEM:__init__
    def __init__(self, index):
        try:
            self.query_command = ["mmcli", f"-Km", index]
            self.index = index
            self.refresh()

            self.SMS(self)
            self.USSD(self)
        except Exception as error:
            raise Exception(error)

    def refresh(self):
        try:
            data=subprocess.check_output(self.query_command, stderr=subprocess.STDOUT)
            data=data.decode('unicode_escape')
            data = Modem.f_layer_parse(data)
            self.__build_attributes(data)
        except subprocess.CalledProcessError as error:
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
    
    def disable(self):
        try:
            query_command = self.query_command + ['-d']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)

    def enable(self):
        try:
            query_command = self.query_command + ['-e']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)

    ''' reset may not be allowed by most modems '''
    def reset(self):
        try:
            query_command = self.query_command + ['-r']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)

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

    try:
        modem.SMS.set(number=sys.argv[2], text="Hello world")
        print(f"\n- sending:text - {modem.SMS.text}")
        print(f"- sending:number - {modem.SMS.number}")
        print(f"- sending:index - {modem.SMS.index}")
        modem.SMS.send()
    except Exception as error:
        print(error)
    
    indexes = modem.SMS.list()
    print('found sms\'', indexes)

    for index in indexes:
        try:
            print(index)
            modem.SMS.delete(index=index)
        except Exception as error:
            print(error)

    try:
        modem.toggle()
        print('ussd initiate ', modem.USSD.initiate("*155#"))
    except Exception as error:
        print(traceback.format_exc())
