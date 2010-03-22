# -*- coding: utf-8 -*-
"""
database_content.py

DatabaseContent, with marshalling and unmarshalling code
"""
from collections import namedtuple
import struct

from tools.marshalling import marshall_string, unmarshall_string

# d - timestamp
# ? - is_tompbstone
# B - segment_number
# I - segment size
# Q - total_size
# L - adler32
#16s- md5 
_content_template = "d?BIQL16s"
_content_template_size = struct.calcsize(_content_template)

factory =  namedtuple(
    "DatabaseContent", [
        "timestamp", 
        "is_tombstone", 
        "segment_number", 
        "segment_size", 
        "total_size", 
        "adler32",
        "md5",
        "file_name",
    ]
)

def marshall(content):
    """return a string of marshalled content"""
    packed_content = struct.pack(
        _content_template,
        content.timestamp, 
        content.is_tombstone, 
        content.segment_number, 
        content.segment_size, 
        content.total_size, 
        content.adler32,
        content.md5
    )
    packed_file_name = marshall_string(content.file_name)
    return "".join([packed_content, packed_file_name, ])

def unmarshall(data):
    """return a DatabaseContent tuple unmarshaled from raw data"""
    pos = 0
    content = struct.unpack(
        _content_template, data[pos:pos+_content_template_size]
    )
    pos += _content_template_size
    (file_name, _, ) = unmarshall_string(data, pos)
    total_content = list(content)
    total_content.append(file_name)
    return factory._make(total_content)
