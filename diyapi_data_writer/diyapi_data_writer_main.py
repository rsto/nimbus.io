# -*- coding: utf-8 -*-
"""
diyapi_data_writer_main.py

Stores received segments (1 for each sequence) 
in the incoming directory with a temp extension.
When final segment is received
fsyncs temp data file
renames into place,
fsyncs the directory into which the file was renamed
sends message to the database server to record key as stored.
ACK back to to requestor includes size (from the database server) 
of any previous key this key supersedes (for space accounting.)
"""
import logging
import os
import sys

from tools import amqp_connection
from tools import message_driven_process as process
from tools import repository

from diyapi_database_server import database_content
from messages.archive_key_entire import ArchiveKeyEntire
from messages.archive_key_entire_reply import ArchiveKeyEntireReply
from messages.database_key_insert import DatabaseKeyInsert
from messages.database_key_insert_reply import DatabaseKeyInsertReply

_log_path = u"/var/log/pandora/diyapi_data_writer.log"
_queue_name = "data_writer"
_routing_key_binding = "data_writer.*"
_key_insert_reply_routing_key = "data_writer.database_key_insert_reply"

def _handle_archive_key_entire(state, message_body):
    log = logging.getLogger("_handle_archive_key_entire")
    message = ArchiveKeyEntire.unmarshall(message_body)
    log.info("avatar_id = %s, key = %s" % (message.avatar_id, message.key, ))

    # if we already have a state entry for this request_id, something is wrong
    if message.request_id in state:
        error_string = "invalid duplicate request_id in ArchiveKeyEntire"
        log.error(error_string)
        reply = ArchiveKeyEntireReply(
            message.request_id,
            ArchiveKeyEntireReply.error_invalid_duplicate,
            error_message=error_string
        )
        return [(message.reply_exchange, message.reply_routing_key, reply, )] 

    # store the message content on disk
    input_path = repository.content_input_path(message.avatar_id, message.key) 
    content_path = repository.content_path(message.avatar_id, message.key) 
    try:
        with open(input_path, "w") as content_file:
            content_file.write(message.content)

        os.rename(input_path, content_path)
    except Exception, instance:
        log.exception("%s %s" % (message.avatar_id, message.key, ))
        reply = ArchiveKeyEntireReply(
            message.request_id,
            ArchiveKeyEntireReply.error_exception,
            error_message=str(instance)
        )
        return [(message.reply_exchange, message.reply_routing_key, reply, )] 

    # save the original message in state
    state[message.request_id] = message

    # send an insert request to the database, with the reply
    # coming back to us
    database_entry = database_content.factory(
        timestamp=message.timestamp, 
        is_tombstone=False,  
        segment_number=message.segment_number,  
        segment_size=len(message.content),  
        total_size=len(message.content),  
        adler32=message.adler32, 
        md5=message.md5 
    )
    local_exchange = amqp_connection.local_exchange_name
    database_request = DatabaseKeyInsert(
        message.request_id,
        message.avatar_id,
        local_exchange,
        _key_insert_reply_routing_key,
        message.key, 
        database_entry
    )
    return [(local_exchange, database_request.routing_key, database_request, )]

def _handle_key_insert_reply(state, message_body):
    log = logging.getLogger("_handle_key_insert_reply")
    message = DatabaseKeyInsertReply.unmarshall(message_body)

    # if we don't have any state for this message body, there's nobody we 
    # can complain too
    if message.request_id not in state:
        log.error("No state for %r" % (message.request_id, ))
        return

    original = state[message.request_id]
    del state[message.request_id]

    # if we got a database error, heave the data we stored
    if message.error:
        content_path = repository.content_path(
            original.avatar_id, original.key
        ) 
        log.error("%s %s database error: (%s) %s removing %s" % (
            original.avatar_id,
            original.key,
            message.result,
            message.error_message,
            content_path
        ))
        try:
            os.unlink(content_path)
        except Exception, instance:
            log.exception("%s %s %s" % (
                original.avatar_id, original.key, instance
            ))    

    reply = ArchiveKeyEntireReply(
        message.request_id,
        message.result,
        message.previous_size,
        message.error_message
    )

    reply_exchange = original.reply_exchange
    reply_routing_key = original.reply_routing_key
    return [(reply_exchange, reply_routing_key, reply, )]      

_dispatch_table = {
    ArchiveKeyEntire.routing_key    : _handle_archive_key_entire,
    _key_insert_reply_routing_key   : _handle_key_insert_reply,
}

if __name__ == "__main__":
    state = dict()
    sys.exit(
        process.main(
            _log_path, 
            _queue_name, 
            _routing_key_binding, 
            _dispatch_table, 
            state
        )
    )

