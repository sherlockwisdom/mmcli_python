#!/usr/bin/env python3

import logging
import json
import subprocess

class SMS:

    def __init__(self, modem_index: str, dbus_path: str = None) -> None:
        """
        """
        self.modem_index = modem_index
        self.dbus_path = dbus_path

        if dbus_path:
            self.__construct_sms_object__()

    def __construct_sms_object__(self) -> None:
        """Builds an SMS object for the specified sms_dbus_path.
        """
        single_sms_list =["mmcli", "-Js", self.dbus_path] 
        try: 
            mmcli_output = subprocess.check_output(single_sms_list, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')

        except subprocess.CalledProcessError as error:
            raise error

        except Exception as error:
            raise error

        else:
            sms_message = self.__json_parse_mmcli_output__(mmcli_output=mmcli_output)
            sms_message = sms_message['sms']

            self.content = sms_message['content']
            self.properties = sms_message['properties']

    def get_text(self) -> str:
        """Get SMS text message.
        """
        return self.content['text']

    def get_number(self) -> str:
        """Get number of SMS sender.
        """
        return self.content['number']
    
    def get_timestamp(self) -> str:
        """Get timestamp of SMS.
        """
        return self.properties['timestamp']


    def __json_parse_mmcli_output__(self, mmcli_output: str) -> dict:
        """ 
        """
        json_object = json.loads(mmcli_output)
        return json_object

    def __filter_for__(self, messages_dbus_paths: list, filter_for: str) -> None:
        """
        """
        filtered_list = []
        for message_dbus_path in messages_dbus_paths:
            sms = SMS(modem_index=self.modem_index, 
                    dbus_path=message_dbus_path)

            if sms.properties['state'] == filter_for:
                filtered_list.append(message_dbus_path)
                logging.debug("[FOUND] filtered: %s", message_dbus_path)
            else:
                logging.debug("filtered: %s", message_dbus_path)

        return filtered_list

    def list(self, filter_for: str = None) -> list:
        """Get a list of SMS messages dbus_paths in Modem.
        """
        sms_list =["mmcli", "-Jm", self.modem_index, "--messaging-list-sms"] 

        try: 
            mmcli_output = subprocess.check_output(sms_list, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')

        except subprocess.CalledProcessError as error:
            raise error

        except Exception as error:
            raise error

        else:
            list_of_messages_dbus_paths = self.__json_parse_mmcli_output__(
                    mmcli_output=mmcli_output)
            list_of_messages_dbus_paths = list_of_messages_dbus_paths['modem.messaging.sms']

            if filter_for:
                list_of_messages_dbus_paths = self.__filter_for__(
                        messages_dbus_paths=list_of_messages_dbus_paths, filter_for=filter_for)

            return list_of_messages_dbus_paths


    def __send__(self, sms_dbus_path: str, timeout: int) -> str:
        """
        """
        send_send_action =["mmcli", "-m", self.modem_index, 
        "-s", sms_dbus_path, "--send", "--timeout=%d" %(timeout)]

        try: 
            mmcli_output = subprocess.check_output(send_send_action, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')

        except subprocess.CalledProcessError as error:
            raise error

        except Exception as error:
            raise error

        else:
            return mmcli_output


    def __create_sms__(self, data:str, number: str) -> str:
        """
        """
        sms_create_action =["mmcli", "-m", self.modem_index, 
        '--messaging-create-sms=' \
                'text="%s",number=%s' % (data, number)]

        try: 
            mmcli_output = subprocess.check_output(sms_create_action, 
                    stderr=subprocess.STDOUT).decode('unicode_escape')

        except subprocess.CalledProcessError as error:
            raise error

        except Exception as error:
            raise error
        
        else:
            sms_dbus_path = mmcli_output.split('Successfully created new SMS: ')
            if len(sms_dbus_path) == 2:
                mmcli_output = sms_dbus_path[1]
            return mmcli_output.replace('\n', '')


    def send(self, data: str, number: str, timeout: int = 30) -> str:
        """
        """
        try:
            sms_dbus_path = self.__create_sms__(data = data, number = number)
            logging.debug(sms_dbus_path)
        except Exception as error:
            raise error
        else:
            try:
                return self.__send__(sms_dbus_path=sms_dbus_path, timeout=timeout)

            except subprocess.CalledProcessError as error:
                raise error

            except Exception as error:
                raise error

    def delete(self) -> str:
        sms_delete_action = ["mmcli", "-m", 
                self.modem_index, "--messaging-delete-sms=%s" % (self.dbus_path)] 
        try: 
           return subprocess.check_output(sms_delete_action, 
                   stderr=subprocess.STDOUT).decode('unicode_escape').replace('\n', '')

        except subprocess.CalledProcessError as error:
            raise error

        except Exception as error:
            raise error


if __name__ == "__main__":
    import sys, os

    logging.basicConfig(level='DEBUG')

    s = SMS(modem_index=sys.argv[1])
    """
    if(len(sys.argv) > 2):
        logging.info("filtering for: %s", sys.argv[2])
        logging.info(s.list(filter_for=sys.argv[2]))
    else:
        logging.debug(s.list())
    """


    """
    try:
        s.send(number=sys.argv[2], data=sys.argv[3])
    except Exception as error:
        logging.exception(error)
    """
    s = SMS(modem_index=sys.argv[1], dbus_path=sys.argv[2])
    logging.debug(s.delete())
