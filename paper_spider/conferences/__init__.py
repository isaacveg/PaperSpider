# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from .base import ConferenceBase
from .iclr import IclrConference
from .icml import IcmlConference
from .neurips import NeuripsConference


def available_conferences() -> list[ConferenceBase]:
    return [NeuripsConference(), IcmlConference(), IclrConference()]
