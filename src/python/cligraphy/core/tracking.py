#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Session and execution tracking"""


from collections import namedtuple
import uuid
import os

TrackingInformation = namedtuple('TrackingInformation', 'session_uuid,execution_uuid')


def get_tracking():
    """Initializes our tracking information"""
    session_uuid = os.getenv('CLIGRAPHY_SESSION_UUID', None)
    if session_uuid is None:
        # Create new session
        session_uuid = str(uuid.uuid4())
        os.environ['CLIGRAPHY_SESSION_UUID'] = session_uuid

    return TrackingInformation(session_uuid=session_uuid, execution_uuid=str(uuid.uuid4()))

TRACKING = get_tracking()
