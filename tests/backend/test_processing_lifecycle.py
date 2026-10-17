"""Simulate delayed OS termination without substituting watermark detections."""

from __future__ import annotations

import pickle
import threading
import time
from multiprocessing.shared_memory import SharedMemory
from typing import Any

import pytest
from tracemark_api import runner as processing


def test_delayed_process_exit_retains_resources_and_blocks_new_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    exited = threading.Event()
    cleaned = threading.Event()
    released: list[str] = []
    message = pickle.dumps({"completed": True})
    release_memory = processing._release_memory

    def release(memory: SharedMemory) -> None:
        release_memory(memory)
        released.append(memory.name)
        if len(released) == 2:
            cleaned.set()

    class Connection:
        def close(self) -> None:
            pass

        def poll(self, timeout: float) -> bool:
            return True

        def recv(self) -> tuple[bool, int]:
            return True, len(message)

    class Process:
        pid = 1

        def __init__(self, *, args: tuple[Any, ...], **kwargs: Any) -> None:
            self.output_name = args[2]

        def start(self) -> None:
            output = SharedMemory(name=self.output_name)
            try:
                processing._view(output)[: len(message)] = message
            finally:
                output.close()

        def join(self, timeout: float | None = None) -> None:
            if timeout is None:
                assert exited.wait(5)

        def is_alive(self) -> bool:
            return not exited.is_set()

        def terminate(self) -> None:
            pass  # Model an OS that has acknowledged termination but not exited.

        kill = terminate

        def close(self) -> None:
            assert exited.is_set(), "closing a live process must never be attempted"

    class Context:
        @staticmethod
        def Process(**kwargs: Any) -> Process:
            return Process(**kwargs)

        @staticmethod
        def Pipe(*, duplex: bool) -> tuple[Connection, Connection]:
            return Connection(), Connection()

    monkeypatch.setattr(processing.multiprocessing, "get_context", lambda mode: Context())
    monkeypatch.setattr(processing, "_release_memory", release)
    runner = processing.ProcessingRunner(1, 1)
    try:
        assert runner.run("protect") == {"completed": True}
        assert released == []  # Buffers still belong to the unreaped child.
        with pytest.raises(processing.ProcessingFailure, match="busy"):
            runner.run("protect")
    finally:
        exited.set()
    assert cleaned.wait(5)
    deadline = time.monotonic() + 5
    while True:
        try:
            assert runner.run("protect") == {"completed": True}
            break
        except processing.ProcessingFailure:
            assert time.monotonic() < deadline
            time.sleep(0.01)
