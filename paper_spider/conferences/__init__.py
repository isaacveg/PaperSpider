# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from .acl import AclConference
from .atc import AtcConference
from .base import ConferenceBase
from .cvpr import CvprConference
from .emnlp import EmnlpConference
from .iclr import IclrConference
from .icml import IcmlConference
from .naacl import NaaclConference
from .neurips import NeuripsConference
from .nsdi import NsdiConference
from .osdi import OsdiConference
from .sigcomm import SigcommConference


def available_conferences() -> list[ConferenceBase]:
    return [
        NeuripsConference(),
        IcmlConference(),
        IclrConference(),
        CvprConference(),
        EmnlpConference(),
        AclConference(),
        NaaclConference(),
        SigcommConference(),
        NsdiConference(),
        OsdiConference(),
        AtcConference(),
    ]
