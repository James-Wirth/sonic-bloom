"""Real-time Music.app notifications via NSDistributedNotificationCenter."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

import objc
from Foundation import NSObject, NSRunLoop, NSDate, NSDistributedNotificationCenter


@dataclass(frozen=True, slots=True)
class MusicEvent:
    state: str
    name: str | None = None
    artist: str | None = None
    album: str | None = None


class _Observer(NSObject):
    @objc.python_method
    def initWithQueue_(self, q: queue.Queue[MusicEvent]):
        self = objc.super(_Observer, self).init()
        if self is None:
            return None
        self._queue = q
        return self

    def handleNotification_(self, notification):
        info = notification.userInfo()
        if not info:
            return
        state = str(info.get("Player State", ""))
        name = info.get("Name")
        artist = info.get("Artist")
        album = info.get("Album")
        self._queue.put(MusicEvent(
            state=state,
            name=str(name) if name else None,
            artist=str(artist) if artist else None,
            album=str(album) if album else None,
        ))


class MusicEventThread:
    """Background thread listening for Music.app playback notifications."""

    def __init__(self):
        self.queue: queue.Queue[MusicEvent] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        observer = _Observer.alloc().initWithQueue_(self.queue)
        center = NSDistributedNotificationCenter.defaultCenter()
        center.addObserver_selector_name_object_(
            observer, objc.selector(observer.handleNotification_, signature=b"v@:@"),
            "com.apple.Music.playerInfo", None,
        )
        loop = NSRunLoop.currentRunLoop()
        while not self._stop_event.is_set():
            loop.runMode_beforeDate_("NSDefaultRunLoopMode", NSDate.dateWithTimeIntervalSinceNow_(0.5))
        center.removeObserver_(observer)
