#!/bin/python3

# modem has
# - SMS
# - USSD

import traceback
import subprocess
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
        query_command=None

        # required for sending
        delivery_report=None
        validity=None
        data=None
        _set=False


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
                # mmcli_output = subprocess.check_output(cls.query_command, stderr=subprocess.STDOUT)
                # print(str(mmcli_output, 'unicode_escape'))
            except subprocess.CalledProcessError as error:
                # print(traceback.format_exc())
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                data=Modem.f_layer_parse(mmcli_output)
                cls.__build_attributes(data)

        @classmethod
        def __create(cls, number, text, delivery_report):
            mmcli_create_sms = []
            mmcli_create_sms += cls.modem.query_command + ["--messaging-create-sms"]
            mmcli_create_sms[-1] += f'=number={number},text="{text}"'
            try: 
                mmcli_output = subprocess.check_output(mmcli_create_sms, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')

            except subprocess.CalledProcessError as error:
                '''
                mmcli_exception_output(error)
                print(traceback.format_exc())
                '''
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                # print(mmcli_output)
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
            print(f"\n- sending sms: {cls.index}")
            if cls.index is None:
                raise Exception("failed to create sms - no index available")

            mmcli_send = cls.modem.query_command + ["-s", cls.index, "--send", f"--timeout={timeout}"] 
            try: 
                mmcli_output = subprocess.check_output(mmcli_send, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                # mmcli_exception_output(error)
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                return True
            return False

        @classmethod
        def delete(cls, index):
            print(f"\n- deleting sms: {index}")
            command = []
            command = cls.modem.query_command + [f"--messaging-delete-sms={index}"] 
            try: 
               # mmcli_output = subprocess.check_output(mmcli_delete_sms, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
               mmcli_output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')
            except subprocess.CalledProcessError as error:
                # mmcli_exception_output(error)
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                return True
            return False

    class USSD():
        modem=None

        @classmethod
        def __init__(cls, modem):
            cls.modem = modem

        @classmethod
        def initiate(cls, command, timeout=10):
            query_command = cls.modem.query_command
            query_command[1] = query_command[1].replace('K', '')
            ussd_command = query_command + [f'--3gpp-ussd-initiate={command}', f'--timeout={timeout}']
            try: 
                mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                # print(traceback.format_exc())
                cls.modem.USSD.cancel()
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.modem.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                mmcli_output = mmcli_output.split(": ", 1)[1].split("'")[1]
                return mmcli_output

        @classmethod
        def respond(cls, command):
            ussd_command = cls.modem.query_command + [f"--3gpp-ussd-respond={command}"]
            try: 
                mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT, shell=True).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                cls.modem.ussd.cancel()
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.modem.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                mmcli_output = mmcli_output.split(": '", 1)[1][:-1]
                return mmcli_output

        @classmethod
        def cancel(cls):
            ussd_command = cls.modem.query_command + [f"--3gpp-ussd-cancel"]
            try: 
                mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.modem.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
            else:
                return True
            
            return False

        @classmethod
        def status(cls):
            ussd_command = cls.modem.query_command + [f"--3gpp-ussd-status"]

            try: 
                mmcli_output = subprocess.check_output(ussd_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            except subprocess.CalledProcessError as error:
                # raise Exception(f"execution failed cmd={error.cmd} index={cls.modem.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
                raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
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
            # data = Modem.s_layer_parse(subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape'))
            # print(data)
            return [index for index in Modem.s_layer_parse(subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape'))]
            # return [index[1].split('/')[-1] for index in Modem.f_layer_parse(data)]
        except subprocess.CalledProcessError as error:
            # raise Exception(f"execution failed cmd={error.cmd} index={self.index} returncode={error.returncode} std(out/err)={error.stderr}")
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
            # print(line)
            if len(line) < 1:
                continue
            secs = line.split(' ')
            # print(secs)
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

    # MODEM:__init__
    def __init__(self, index):
        try:
            self.query_command = ["mmcli", f"-Km", index]
            self.index = index
            self.refresh()

            # self.sms = self.SMS(self)
            # self.ussd = self.USSD(self)
            self.SMS(self)
            self.USSD(self)
        except Exception as error:
            '''
            print("modem instantiation failed...")
            print(traceback.format_exc())
            '''
            raise Exception(error)

    def refresh(self):
        try:
            data=subprocess.check_output(self.query_command, stderr=subprocess.STDOUT)
            data=data.decode('unicode_escape')
            data = Modem.f_layer_parse(data)
            self.__build_attributes(data)
        except subprocess.CalledProcessError as error:
            # raise Exception(f"execution failed cmd={error.cmd} index={cls.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)
    
    def toggle(self):
        try:
            # query_command = self.query_command + ['-d', '&&'] + self.query_command + ['-e']
            query_command = self.query_command + ['-d']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            # print(mmcli_output)

            query_command = self.query_command + ['-e']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
            # print(mmcli_output)
        except subprocess.CalledProcessError as error:
            # raise Exception(f"execution failed cmd={error.cmd} index={self.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
            raise subprocess.CalledProcessError(cmd=error.cmd, output=error.output, returncode=error.returncode)

    def reset(self):
        try:
            # query_command = self.query_command + ['-d', '&&'] + self.query_command + ['-e']
            query_command = self.query_command + ['-r']
            mmcli_output = subprocess.check_output(query_command, stderr=subprocess.STDOUT).decode('unicode_escape')
        except subprocess.CalledProcessError as error:
            # raise Exception(f"execution failed cmd={error.cmd} index={self.index} returncode={error.returncode} stderr={error.stderr} stdout={error.stdout}")
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
        # assert(modem.SMS.send() == True)
        # assert(modem.SMS.delete() == True)
        modem.SMS.send()
    except Exception as error:
        print(error)
    
    indexes = modem.SMS.list()
    print('found sms\'', indexes)

    for index in indexes:
        try:
            # sms.delete()
            print(index)
            modem.SMS.delete(index=index)
        except Exception as error:
            # print(traceback.format_exc())
            print(error)

    ''' observations:
    - for some reason ussd fails after SMS message has been sent
    - without sending sms message, ussd happens.... why??
    '''

    try:
        # print('ussd initiate ', modem.ussd.initiate("*158*99#"))
        modem.toggle()
        # modem.reset()
        print('ussd initiate ', modem.USSD.initiate("*155#"))
    except Exception as error:
        print(traceback.format_exc())
    # print('ussd respond ', modem.ussd.respond("6"))
    # print('ussd respond ', modem.ussd.respond("4"))
