# -*- coding: utf-8 -*-
"""
archive_key_entire_reply.py

ArchiveKeyEntireReply message
"""
import struct

from tools.marshalling import marshall_string, unmarshall_string
from diyapi_database_server import database_content

# 32s - request-id 32 char hex uuid
# B   - result: 0 = success 
# Q   - previous size
_header_format = "!32sBQ"
_header_size = struct.calcsize(_header_format)

class ArchiveKeyEntireReply(object):
    """AMQP message to archive an entire key"""
   
    successful = 0
    error_invalid_duplicate = 1
    error_exception = 2

    def __init__(
        self, request_id, result, previous_size=0, error_message=""
    ):
        self.request_id = request_id
        self.result = result
        self.previous_size = previous_size
        self.error_message = error_message

    @property
    def error(self):
        return self.result != ArchiveKeyEntireReply.successful

    @classmethod
    def unmarshall(cls, data):
        """return a DatabaseKeyInsert message"""
        pos = 0
        request_id, result, previous_size = struct.unpack(
            _header_format, data[pos:pos+_header_size]
        )
        pos += _header_size

        if result == 0:
            return ArchiveKeyEntireReply(request_id, result, previous_size)

        (error_message, pos) = unmarshall_string(data, pos)

        return ArchiveKeyEntireReply(
            request_id, result, previous_size, error_message
        )

    def marshall(self):
        """return a data string suitable for transmission"""
        error_message_size = len(self.error_message)
        header = struct.pack(
            _header_format, 
            self.request_id, 
            self.result, 
            self.previous_size 
        )
        packed_error_message = marshall_string(self.error_message)
         
        return "".join([header, packed_error_message, ])
