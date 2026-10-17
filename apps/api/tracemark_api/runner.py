"""Bounded, killable processing with parent-owned transient shared memory."""

from __future__ import annotations

import multiprocessing
import pickle  # nosec B403
import threading
import time
from collections.abc import Callable
from contextlib import ExitStack, suppress
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from multiprocessing.shared_memory import SharedMemory
from tempfile import TemporaryDirectory
from typing import Any

from .uploads import UploadRejected

_RESULT_CAPACITY = 32 * 1024 * 1024


class ProcessingFailure(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _child(input_name: str, input_size: int, output_name: str, sender: Connection) -> None:
    source = output = None
    try:
        source = SharedMemory(name=input_name)
        output = SharedMemory(name=output_name)
        # These bytes are serialized by our parent process, never supplied as a
        # pickle by an upload or another external client.
        operation, arguments = pickle.loads(bytes(_view(source)[:input_size]))  # nosec B301
        from tracemark_watermark import CapacityError

        from . import processing

        function: Callable[..., dict[str, Any]] = processing.protect if operation == "protect" else processing.verify
        try:
            result = function(*arguments)
        except CapacityError:
            sender.send(
                (
                    False,
                    "invalid_image",
                    "This image is too small for protection. Try an image at least 432 × 432 pixels.",
                )
            )
        else:
            serialized = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
            if len(serialized) > _RESULT_CAPACITY:
                sender.send((False, "processing_failed", "The processed image exceeds the output limit."))
            else:
                _view(output)[: len(serialized)] = serialized
                # Tiny notifications cannot block on transferring image bytes.
                sender.send((True, len(serialized)))
    except UploadRejected as exc:
        sender.send((False, "invalid_image", str(exc)))
    except Exception:
        with suppress(BrokenPipeError, OSError):
            sender.send((False, "processing_failed", "The image could not be processed safely."))
    finally:
        if source is not None:
            source.close()
        if output is not None:
            output.close()
        sender.close()


def _view(memory: SharedMemory) -> memoryview:
    view = memory.buf
    if view is None:
        raise RuntimeError("processing buffer is closed")
    return view


def _release_memory(memory: SharedMemory) -> None:
    memory.close()
    with suppress(FileNotFoundError):
        memory.unlink()


class ProcessingRunner:
    def __init__(self, concurrency: int, timeout_seconds: float):
        self._slots = threading.BoundedSemaphore(concurrency)
        self.timeout_seconds = timeout_seconds
        self._cleanup_lock = threading.Lock()
        self._pending_cleanup = 0

    def run(self, operation: str, *arguments: Any) -> dict[str, Any]:
        with self._cleanup_lock:
            if self._pending_cleanup:
                raise ProcessingFailure("processing_busy", "Image processing is busy. Please try again shortly.")
        if not self._slots.acquire(blocking=False):
            raise ProcessingFailure("processing_busy", "Image processing is busy. Please try again shortly.")
        try:
            with ExitStack() as resources:
                if operation == "verify":
                    try:
                        temporary = resources.enter_context(TemporaryDirectory(prefix="tracemark-provenance-"))
                    except OSError:
                        temporary = None
                    arguments = (*arguments, temporary)
                serialized = pickle.dumps((operation, arguments), protocol=pickle.HIGHEST_PROTOCOL)
                source = SharedMemory(create=True, size=len(serialized))
                resources.callback(_release_memory, source)
                output = SharedMemory(create=True, size=_RESULT_CAPACITY)
                resources.callback(_release_memory, output)
                _view(source)[: len(serialized)] = serialized
                return self._execute(source, len(serialized), output, resources)
        finally:
            self._slots.release()

    def _reap(self, process: BaseProcess, resources: ExitStack) -> None:
        # A slow OS termination must retain its buffers/temp files and block new
        # admission. The request does not wait indefinitely for process teardown.
        process.join()
        process.close()
        resources.close()
        with self._cleanup_lock:
            self._pending_cleanup -= 1

    def _execute(self, source: SharedMemory, size: int, output: SharedMemory, resources: ExitStack) -> dict[str, Any]:
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_child, args=(source.name, size, output.name, sender), daemon=True)
        timer = None
        deadline = time.monotonic() + self.timeout_seconds

        def expire() -> None:
            with suppress(ValueError, OSError):
                if process.is_alive():
                    process.kill()

        try:
            process.start()
            sender.close()
            if time.monotonic() >= deadline:
                expire()
                raise ProcessingFailure(
                    "processing_timeout", "Processing exceeded the time limit. Try a smaller image."
                )
            timer = threading.Timer(max(0.001, deadline - time.monotonic()), expire)
            timer.daemon = True
            timer.start()
            if not receiver.poll(max(0.0, deadline - time.monotonic())):
                raise ProcessingFailure(
                    "processing_timeout", "Processing exceeded the time limit. Try a smaller image."
                )
            try:
                result = receiver.recv()
            except (EOFError, OSError) as exc:
                if time.monotonic() >= deadline:
                    raise ProcessingFailure(
                        "processing_timeout", "Processing exceeded the time limit. Try a smaller image."
                    ) from exc
                raise ProcessingFailure("processing_failed", "The image processor stopped unexpectedly.") from exc
            if not result[0]:
                raise ProcessingFailure(result[1], result[2])
            # Deserialization is restricted to our child-produced memory block.
            return dict(pickle.loads(bytes(_view(output)[: result[1]])))  # nosec B301
        finally:
            if timer is not None:
                timer.cancel()
                timer.join(timeout=1)
            receiver.close()
            sender.close()
            if process.pid is not None:
                process.join(timeout=0.2)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                if process.is_alive():
                    with self._cleanup_lock:
                        self._pending_cleanup += 1
                    threading.Thread(target=self._reap, args=(process, resources.pop_all()), daemon=True).start()
                else:
                    process.close()
