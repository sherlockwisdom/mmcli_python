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
