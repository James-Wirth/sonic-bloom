"""Apple Music control via PyObjC ScriptingBridge."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass


def _f(code: str) -> int:
    return struct.unpack(">I", code.encode("ascii"))[0]


PLAYER_STATES = {
    _f("kPSP"): "playing", _f("kPSp"): "paused", _f("kPSS"): "stopped",
    _f("kPSF"): "fast_forward", _f("kPSR"): "rewinding",
}

REPEAT_MODES = {"off": _f("kRpO"), "one": _f("kRp1"), "all": _f("kRpA")}
REPEAT_LABELS = {v: k for k, v in REPEAT_MODES.items()}


class MusicAppError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Track:
    name: str
    artist: str
    album: str
    duration: float
    persistent_id: str
    genre: str = ""
    year: int = 0
    track_number: int = 0
    loved: bool = False
    store_id: str | None = None


@dataclass(frozen=True, slots=True)
class PlayerState:
    state: str
    volume: int
    shuffle: bool
    repeat: str
    current_track: Track | None


@dataclass(frozen=True, slots=True)
class Playlist:
    name: str
    persistent_id: str
    track_count: int


def _read_track(sb_track) -> Track:
    try:
        store_id = None
        try:
            raw = sb_track.storeID()
            if raw and str(raw) not in ("", "0", "missing value"):
                store_id = str(raw)
        except Exception:
            pass

        loved = False
        try:
            loved = bool(sb_track.loved())
        except Exception:
            pass

        return Track(
            name=str(sb_track.name() or "Unknown"),
            artist=str(sb_track.artist() or "Unknown"),
            album=str(sb_track.albumArtist() and sb_track.album() or sb_track.album() or ""),
            duration=float(sb_track.duration() or 0),
            persistent_id=str(sb_track.persistentID()),
            genre=str(sb_track.genre() or ""),
            year=int(sb_track.year() or 0),
            track_number=int(sb_track.trackNumber() or 0),
            loved=loved,
            store_id=store_id,
        )
    except Exception as e:
        raise MusicAppError(f"Could not read track: {e}") from e


class MusicApp:
    """Interface to Music.app via ScriptingBridge."""

    def __init__(self):
        from ScriptingBridge import SBApplication
        self._app = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")

    @property
    def is_running(self) -> bool:
        return bool(self._app.isRunning())

    def activate(self):
        self._app.activate()
        time.sleep(0.5)

    def _ensure_running(self):
        if not self.is_running:
            self.activate()
            if not self.is_running:
                raise MusicAppError("Music.app is not running and could not be started.")

    def current_track(self) -> Track | None:
        self._ensure_running()
        try:
            ct = self._app.currentTrack()
            if ct and ct.persistentID():
                return _read_track(ct)
        except Exception:
            pass
        return None

    def player_state(self) -> PlayerState:
        self._ensure_running()
        state = PLAYER_STATES.get(self._app.playerState(), "unknown")
        volume = int(self._app.soundVolume())
        shuffle = bool(self._app.shuffleEnabled())
        repeat_raw = self._app.songRepeat()
        repeat = REPEAT_LABELS.get(repeat_raw, "off")
        track = self.current_track()
        return PlayerState(
            state=state, volume=volume, shuffle=shuffle,
            repeat=repeat, current_track=track,
        )

    def playpause(self) -> str:
        self._ensure_running()
        self._app.playpause()
        time.sleep(0.1)
        return PLAYER_STATES.get(self._app.playerState(), "unknown")

    def pause(self):
        self._ensure_running()
        self._app.pause()

    def stop(self):
        self._ensure_running()
        self._app.stop()

    def next_track(self):
        self._ensure_running()
        self._app.nextTrack()

    def previous_track(self):
        self._ensure_running()
        self._app.previousTrack()

    def set_volume(self, volume: int):
        self._ensure_running()
        self._app.setSoundVolume_(max(0, min(100, volume)))

    def set_shuffle(self, enabled: bool):
        self._ensure_running()
        self._app.setShuffleEnabled_(enabled)

    def set_repeat(self, mode: str):
        self._ensure_running()
        code = REPEAT_MODES.get(mode)
        if code is None:
            raise MusicAppError(f"Invalid repeat mode: {mode!r}. Use 'off', 'one', or 'all'.")
        self._app.setSongRepeat_(code)

    def play_track(self, persistent_id: str):
        self._ensure_running()
        track = self._find_track(persistent_id)
        # playOnce_(False) allows repeat; True can no-op if track is already current
        track.playOnce_(False)
        time.sleep(0.3)
        state = PLAYER_STATES.get(self._app.playerState(), "unknown")
        if state != "playing":
            raise MusicAppError(f"Playback did not start (state: {state})")

    def search_library(self, query: str, limit: int = 10) -> list[Track]:
        self._ensure_running()
        library = self._library_playlist()
        if library is None:
            return []
        results = library.searchFor_only_(query, 0)
        if not results:
            return []
        tracks = []
        for sb_track in results:
            try:
                tracks.append(_read_track(sb_track))
            except MusicAppError:
                continue
            if len(tracks) >= limit:
                break
        return tracks

    def recently_played(self, limit: int = 10) -> list[Track]:
        self._ensure_running()
        try:
            from Foundation import NSSortDescriptor
            lib = self._library_playlist()
            if lib is None:
                return []
            all_tracks = lib.tracks()
            sort = NSSortDescriptor.sortDescriptorWithKey_ascending_("playedDate", False)
            sorted_tracks = all_tracks.sortedArrayUsingDescriptors_([sort])
            tracks = []
            for sb_track in sorted_tracks:
                try:
                    if sb_track.playedDate():
                        tracks.append(_read_track(sb_track))
                except Exception:
                    continue
                if len(tracks) >= limit:
                    break
            return tracks
        except Exception:
            return []

    def get_library_stats(self) -> dict:
        self._ensure_running()
        lib = self._library_playlist()
        if lib is None:
            return {"error": "No library found"}
        tracks = lib.tracks()
        count = len(tracks) if tracks else 0
        total_time = sum(float(t.duration() or 0) for t in tracks) if tracks else 0
        return {
            "track_count": count,
            "total_hours": round(total_time / 3600, 1),
        }

    def list_playlists(self) -> list[Playlist]:
        self._ensure_running()
        playlists = []
        for p in self._app.sources()[0].userPlaylists():
            try:
                name = str(p.name())
                pid = str(p.persistentID())
                count = len(p.tracks()) if p.tracks() else 0
                playlists.append(Playlist(name=name, persistent_id=pid, track_count=count))
            except Exception:
                continue
        return playlists

    def get_playlist_tracks(self, playlist_name: str, limit: int = 25) -> list[Track]:
        self._ensure_running()
        playlist = self._find_playlist(playlist_name)
        tracks = []
        for sb_track in playlist.tracks():
            try:
                tracks.append(_read_track(sb_track))
            except MusicAppError:
                continue
            if len(tracks) >= limit:
                break
        return tracks

    def play_playlist(self, playlist_name: str):
        self._ensure_running()
        playlist = self._find_playlist(playlist_name)
        playlist.playOnce_(False)
        time.sleep(0.3)

    def _find_track(self, persistent_id: str):
        lib = self._library_playlist()
        if lib is None:
            raise MusicAppError("No library found")
        tracks = lib.tracks()
        for t in tracks:
            try:
                if str(t.persistentID()) == persistent_id:
                    return t
            except Exception:
                continue
        raise MusicAppError(f"Track not found: {persistent_id}")

    def _find_playlist(self, name: str):
        for p in self._app.sources()[0].userPlaylists():
            try:
                if str(p.name()).lower() == name.lower():
                    return p
            except Exception:
                continue
        raise MusicAppError(f"Playlist not found: {name!r}")

    def _library_playlist(self):
        try:
            sources = self._app.sources()
            if sources:
                playlists = sources[0].libraryPlaylists()
                if playlists:
                    return playlists[0]
        except Exception:
            pass
        return None


def play_store_track(store_id: str):
    """Play an Apple Music catalog track by its store ID."""
    import MediaPlayer as MP
    from Foundation import NSRunLoop, NSDate

    from sonic_bloom.bridge import get_music

    try:
        get_music().stop()
    except MusicAppError:
        pass

    player = MP.MPMusicPlayerController.systemMusicPlayer()
    descriptor = MP.MPMusicPlayerStoreQueueDescriptor.alloc().initWithStoreIDs_([store_id])
    player.setQueueWithDescriptor_(descriptor)
    player.prepareToPlay()

    loop = NSRunLoop.currentRunLoop()
    deadline = time.time() + 5
    while time.time() < deadline:
        loop.runMode_beforeDate_("NSDefaultRunLoopMode", NSDate.dateWithTimeIntervalSinceNow_(0.1))
        if player.playbackState() == MP.MPMusicPlaybackStatePlaying:
            return

    player.play()

    time.sleep(0.5)
    if player.playbackState() != MP.MPMusicPlaybackStatePlaying:
        raise MusicAppError(f"Could not play store track {store_id}. Check Apple Music permissions.")
