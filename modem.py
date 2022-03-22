#!/bin/python3

# modem has
# - SMS
# - USSD

import traceback
import subprocess
import re
import logging
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

    class MissingModem(Exception):
        def __init__(self):
            super().__init__()

    class MissingIndex(Exception):
        def __init__(self):
            super().__init__()

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

        delivery_report=None
        validity=None
        data=None
        _set=False

        query_command=None

        @staticmethod
        def sms_index_type_parser(data):
            data = data.split('\n')
            cats = {}
            for line in data:
                if len(line) > 0:
                    secs = line.split(' ')
                    cats[secs[-2].split('/')[-1]] = secs[-1].replace('(', '').replace(')', '')
            return cats

        
        def list(self, _filter=None):
            def filter_type(index, _type, expected):
                if _type == expected:
                    return index

            shell=False
            data=[]
            sms_list = []
            sms_list += self.modem.query_command + ["--messaging-list-sms"]
            if _filter is not None:
                sms_list[1] = sms_list[1].replace('K', '')
                sms_list += ["|", "grep", f'"{_filter}"']
                # sms_list = ' '.join(sms_list)
                # shell=True
            try: 
                mmcli_output = subprocess.check_output(sms_list, 
                        shell=shell,
                        stderr=subprocess.STDOUT).decode('unicode_escape')

                if _filter is not None:
                    data = Modem.SMS.sms_index_type_parser(mmcli_output)
                    cats = []
                    for index, _type in data.items():
                        filtered=filter_type(index, _type, _filter)
                        if filtered is not None:
                            cats.append(filtered)
                    data = cats
                else:
                    data = Modem.index_value_parser(mmcli_output)

            except subprocess.CalledProcessError as error:
                # logging.info("OUTPUT: %s", error.output)
                if error.output == b'':
                    return data
                raise error
            except Exception as error:
                raise error

            return data

        
        def __build_attributes(self, data):
            self.text = data["sms.content.text"]
            self.state = data["sms.properties.state"]
            self.number = data["sms.content.number"]
            self.timestamp = data["sms.properties.timestamp"]
            self.pdu_type = data["sms.properties.pdu-type"]


        @staticmethod
        def sms_key_value_parser(data):
            data = data.split('\n')
            details = {}
            m_detail=None
            sms_text = []

            is_sms_text = False
            for output in data:
                if output.find("sms.content.text") > -1:
                    is_sms_text = True
                    m_detail = output.split(': ')
                    if len(m_detail) > 1:
                        sms_text.append(m_detail[1])
                        continue

                if not is_sms_text or (
                        is_sms_text and re.search(r"^sms\.\w*\S\w*[\S]\w*\s*: ", output)):
                    is_sms_text = False

                    m_detail = output.split(': ')
                    if len(m_detail) > 1:
                        key = m_detail[0].replace(' ', '')
                        details[key] = m_detail[1]
                else:
                    sms_text.append(output)

            sms_text = '\n'.join(sms_text)
            details['sms.content.text'] = sms_text
            return details

        
        def __extract_message__(self):
            try: 
                mmcli_output = subprocess.check_output(self.query_command, 
                        stderr=subprocess.STDOUT, encoding='unicode_escape')

                data = Modem.SMS.sms_key_value_parser(mmcli_output)
                self.__build_attributes(data)

            except subprocess.CalledProcessError as error:
                raise error
            except Exception as error:
                raise error

        def __create__(self, number, text, delivery_report):
            mmcli_create_sms = []
            mmcli_create_sms += self.modem.query_command + ["--messaging-create-sms"]
            mmcli_create_sms[-1] += f'=number={number},text="{text}"'
            try: 
                mmcli_output = subprocess.check_output(mmcli_create_sms, 
                        stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')

                mmcli_output = mmcli_output.split(': ')
                creation_status = mmcli_output[0]
                sms_index = mmcli_output[1].split('/')[-1]
                if not sms_index.isdigit():
                    raise Modem.MissingIndex()
                else:
                    self.index = sms_index

            except subprocess.CalledProcessError as error:
                raise error
            except Exception as error:
                raise error

        # SMS:__init__
        def __init__(self, modem=None, index=None):
            if modem is None:
                if not index is None:
                    self.index = index
                    self.query_command = ["mmcli", "-Ks", self.index]
                    self.__extract_message__()
                else:
                    raise Modem.MissingIndex()

            else:
                self.modem = modem

        
        def set(self, number, text, delivery_report=None, validity=None, data=None):
            self.number = number
            self.text = text
            self.delivery_report=delivery_report
            self.validity=validity
            self.data=data

            if self.__create__(number, text, delivery_report):
                self._set=True
            
            return self

        
        def send(self, timeout=20):
            if self.index is None:
                raise Modem.MissingIndex()

            mmcli_send = self.modem.query_command + \
                    ["-s", self.index, "--send", f"--timeout={timeout}"] 
            logging.debug("query command: %s", mmcli_send)
            try: 
                return subprocess.check_output(
                        mmcli_send, 
                        stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                raise error

        def delete(self, index):
            command = []
            command = self.modem.query_command + [f"--messaging-delete-sms={index}"] 
            try: 
               return subprocess.check_output(command, 
                       stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                raise error

    class USSD:
        modem=None

        class CannotInitiateUSSD(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output
                super().__init__()

        class UnknownError(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output
                super().__init__()

        class ActiveSession(Exception):
            def __init__(self, command, output):
                self.command = command
                self.output = output
                super().__init__()

        
        def get_exception(self, command, output):
            exception_wrongstate_activesession = \
                    'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.WrongState: ' + \
                    'Cannot initiate USSD: a session is already active'
            if str(output).find(exception_wrongstate_activesession) > -1:
                return self.ActiveSession(command, output)

            exception_wrongstate_cannotinitiateussd = \
                'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.WrongState: ' + \
                'Cannot initiate USSD'
            exception_error_core_aborted = \
                    'GDBus.Error:org.freedesktop.ModemManager1.Error.Core.Aborted'
            if str(output).find(exception_wrongstate_cannotinitiateussd) > -1 or \
                    str(output).find(exception_error_core_aborted) > -1:
                return self.CannotInitiateUSSD(command, output)

            return self.UnknownError(command, output)

        
        def __init__(self, modem):
            self.modem = modem

        
        def initiate(self, command, timeout=60):
            query_command = self.modem.query_command
            query_command[1] = query_command[1].replace('K', '')
            ussd_command = query_command + [f'--3gpp-ussd-initiate={command}', f'--timeout={timeout}']
            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape')

                mmcli_output = mmcli_output.split(": ", 1)[1].split("'")[1]
                return mmcli_output
            except subprocess.CalledProcessError as error:
                raise self.get_exception(command=error.cmd, output=error.output)

        
        def respond(self, command, timeout=60):
            query_command = self.modem.query_command
            query_command[1] = query_command[1].replace('K', '')
            ussd_command = query_command + [f'--3gpp-ussd-respond={command}']
            try: 
                return subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT
                        ).decode('unicode_escape').split(": '", 1)[1][:-1]
            except subprocess.CalledProcessError as error:
                raise error

        
        def cancel(self):
            ussd_command = self.modem.query_command + [f"--3gpp-ussd-cancel"]
            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                ''' would most likely always raise this error, but can be ignored with no 
                consequences '''
                pass

        def status(self):
            ussd_command = self.modem.query_command + [f"--3gpp-ussd-status"]

            try: 
                mmcli_output = subprocess.check_output(ussd_command, 
                        stderr=subprocess.STDOUT).decode('unicode_escape').split('\n')

                s_details = {}
                for output in mmcli_output:
                    s_detail = output.split(': ')
                    if len(s_detail) > 1:
                        key = s_detail[0].replace(' ', '')
                        s_details[key] = s_detail[1]

                return s_details
            except subprocess.CalledProcessError as error:
                raise error
            except Exception as error:
                raise error


    @staticmethod
    def list():
        try:
            query_command=["mmcli", "-KL"]
            return [index for index in Modem.index_value_parser(
                subprocess.check_output(query_command, 
                    stderr=subprocess.STDOUT).decode('unicode_escape'))]
        except subprocess.CalledProcessError as error:
            raise error

    @staticmethod
    def key_value_parser(data):
        data = data.split('\n')
        details = {}
        m_detail=None
        for output in data:
            m_detail = output.split(': ')
            if len(m_detail) >= 2:
                key = m_detail[0].replace(' ', '')
                details[key] = m_detail[1]

        return details

    @staticmethod
    def index_value_parser(data):
        data = data.split('\n')
        n_modems = int(data[0].split(': ')[1])
        indexes = []
        for i in range(1, (n_modems + 1)):
            index = data[i].split('/')[-1]
            if index.isdigit():
                indexes.append(index)

        return indexes

    @staticmethod
    def gl_index_value_parser(data:str)->str:
        return data.split('/')[-1]

    def __build_attributes__(self, data):
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
        self.sim_index = Modem.gl_index_value_parser(data["modem.generic.sim"])

    # MODEM:__init__
    def __init__(self, index):
        try:
            self.query_command = ["mmcli", f"-Km", index]
            self.index = index
            self.refresh()

            self.sms = self.SMS(self)
            self.ussd = self.USSD(self)
        except Modem.MissingModem as error:
            raise Modem.MissingModem()
        except Modem.MissingIndex as error:
            raise Modem.MissingIndex()
        except Exception as error:
            raise Exception(error)

    def refresh(self):
        try:
            data=subprocess.check_output(self.query_command, 
                    stderr=subprocess.STDOUT)
            data=data.decode('unicode_escape')
            data = Modem.key_value_parser(data)
            self.__build_attributes__(data)
        except subprocess.CalledProcessError as error:
            raise error
    
    def disable(self):
        try:
            query_command = self.query_command + ['-d']
            mmcli_output = subprocess.check_output(query_command, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise error

    def enable(self):
        try:
            query_command = self.query_command + ['-e']
            mmcli_output = subprocess.check_output(query_command, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise error

    ''' reset may not be allowed by most modems '''
    def reset(self):
        try:
            query_command = self.query_command + ['-r']
            mmcli_output = subprocess.check_output(query_command, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            raise error

    def get_sim_imsi(self):
        ''' this only works if ModemManager --debug ''' 
        try:
            # sudo mmcli -m 4 --command=AT+CIMI
            # query_command = self.query_command + ["--command=AT+CIMI"]
            query_command = self.query_command + ["-i", self.sim_index]
            mmcli_output = subprocess.check_output(query_command, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')
            # return mmcli_output.split(" '")[1][0:-2]

            sim_data = Modem.key_value_parser(mmcli_output)
            # logging.debug("%s", sim_data)
            return sim_data['sim.properties.imsi']

        except subprocess.CalledProcessError as error:
            raise error
