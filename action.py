from datetime import datetime as dt
from typing import List

BODY_SIZE = 10
ACTION_ID_SIZE = 5
TIMESTAMP_ID_SIZE = 5
DATA_ID_SIZE = 10
DELIMITER = ","
OK = 'ok'
NOTOK = 'notok'
STRING = 'string'
LIST = 'list'
ERROR ='error'
DATETIME_FORMAT = "%d/%m/%Y, %H:%M:%S"

def encode_segment(data, size):
    data_bytes = data.encode('utf-8')
    header_bytes = len(data_bytes).to_bytes(size, byteorder='big')
    return header_bytes + data_bytes


def encode_message(action: str, data_list) -> bytes:
    action = encode_segment(action, ACTION_ID_SIZE)
    timestamp = encode_segment(dt.now().strftime(DATETIME_FORMAT), TIMESTAMP_ID_SIZE)
    content = encode_segment(DELIMITER.join(data_list), DATA_ID_SIZE)
    
    body = action + timestamp + content
    return len(body).to_bytes(BODY_SIZE, byteorder='big') + body


def decode_message(data):
    pos = 0

    action_size = int.from_bytes(data[pos:pos+ACTION_ID_SIZE], byteorder='big')
    pos += ACTION_ID_SIZE

    action = data[pos:pos+action_size].decode('utf-8')
    pos += action_size

    timestamp_size = int.from_bytes(data[pos:pos+TIMESTAMP_ID_SIZE], byteorder='big')
    pos += TIMESTAMP_ID_SIZE

    timestamp = dt.strptime(data[pos:pos+timestamp_size].decode('utf-8'), DATETIME_FORMAT)
    pos += timestamp_size

    data_size = int.from_bytes(data[pos:pos+DATA_ID_SIZE], byteorder='big')
    pos += DATA_ID_SIZE

    data = data[pos:pos+data_size].decode('utf-8').split(DELIMITER)

    return [action, timestamp, data]
