#!/usr/bin/env python
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from common_precommit_utils import (
    console,
    get_all_provider_ids,
    initialize_breeze_precommit,
    run_command_via_breeze_shell,
)

initialize_breeze_precommit(__name__, __file__)


ALLOWED_FOLDERS = [
    "airflow-core/src/airflow",
    *[f"providers/{provider_id.replace('.', '/')}/src" for provider_id in get_all_provider_ids()],
    "dev",
    "docs",
    "task-sdk/src/airflow/sdk",
    "all_providers",
]

if len(sys.argv) < 2:
    console.print(f"[yellow]You need to specify the folder to test as parameter: {ALLOWED_FOLDERS}\n")
    sys.exit(1)

mypy_folders = sys.argv[1:]

for mypy_folder in mypy_folders:
    if mypy_folder not in ALLOWED_FOLDERS:
        console.print(
            f"\n[red]ERROR: Folder `{mypy_folder}` is wrong.[/]\n\n"
            f"All folders passed should be one of those: {ALLOWED_FOLDERS}\n"
        )
        sys.exit(1)

arguments = mypy_folders.copy()

for mypy_folder in mypy_folders:
    if mypy_folder == "all_providers":
        arguments.remove("all_providers")
        for provider_id in get_all_provider_ids():
            arguments.append(f"providers/{provider_id.replace('.', '/')}/src")
            arguments.append(f"providers/{provider_id.replace('.', '/')}/tests")
    elif mypy_folder.startswith("providers/"):
        arguments.append(f"{Path(mypy_folder).parent.as_posix()}/tests")
    if mypy_folder == "task-sdk/src/airflow/sdk":
        arguments.append("task-sdk/tests")
    if mypy_folder == "airflow-core/src/airflow":
        arguments.append("airflow-core/tests")

print("Running /opt/airflow/scripts/in_container/run_mypy.sh with arguments: ", arguments)

res = run_command_via_breeze_shell(
    [
        "/opt/airflow/scripts/in_container/run_mypy.sh",
        *arguments,
    ],
    warn_image_upgrade_needed=True,
    extra_env={
        "INCLUDE_MYPY_VOLUME": os.environ.get("INCLUDE_MYPY_VOLUME", "true"),
        # Need to mount local sources when running it - to not have to rebuild the image
        # and to let CI work on it when running on PRs from forks - because mypy-dev uses files
        # that are not available at the time when image is built in CI
        "MOUNT_SOURCES": "selected",
    },
)
ci_environment = os.environ.get("CI")
if res.returncode != 0:
    if ci_environment:
        console.print(
            "[yellow]You are running mypy with the folders selected. If you want to "
            "reproduce it locally, you need to run the following command:\n"
        )
        console.print("pre-commit run --hook-stage manual mypy-<folder> --all-files\n")
    upgrading = os.environ.get("UPGRADE_TO_NEWER_DEPENDENCIES", "false") != "false"
    if upgrading:
        console.print(
            "[yellow]You are running mypy with the image that has dependencies upgraded automatically.\n"
        )
    flag = " --upgrade-to-newer-dependencies" if upgrading else ""
    console.print(
        "[yellow]If you see strange stacktraces above, and can't reproduce it, please run"
        " this command and try again:\n"
    )
    console.print(f"breeze ci-image build --python 3.9{flag}\n")
    console.print("[yellow]You can also run `breeze down --cleanup-mypy-cache` to clean up the cache used.\n")
sys.exit(res.returncode)
