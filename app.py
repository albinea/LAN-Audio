
import asyncio
import io
import os
import socket
import subprocess
from fractions import Fraction
from contextlib import asynccontextmanager

import av
import qrcode
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRelay
from aiortc.mediastreams import MediaStreamError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


AUDIO_SOURCE = os.getenv("AUDIO_SOURCE", "").strip()
MAX_CLIENTS = int(os.getenv("MAX_CLIENTS", "3"))

pcs = set()
relay = MediaRelay()
audio_track = None
lock = asyncio.Lock()


class PulseCaptureTrack(MediaStreamTrack):
    """Capture stereo PCM from system FFmpeg and expose it to WebRTC."""

    kind = "audio"

    def __init__(self, source):
        super().__init__()

        self.sample_rate = 48000
        self.channels = 2
        self.samples_per_frame = 960  # 20 ms at 48 kHz
        self.frame_bytes = self.samples_per_frame * self.channels * 2
        self.pts = 0

        command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-fflags", "nobuffer",
        "-probesize", "32",
        "-analyzeduration", "0",
        "-f", "pulse",
        "-fragment_size", str(self.frame_bytes),
        "-i", AUDIO_SOURCE,
        "-vn",
        "-ac", "2",
        "-ar", "48000",
        "-acodec", "pcm_s16le",
        "-flush_packets", "1",
        "-f", "s16le",
        "pipe:1",
]
        

        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=None,
            bufsize=0,
        )

        if self.process.stdout is None:
            self.process.kill()
            raise RuntimeError("Could not open FFmpeg audio output.")

    def _read_exact(self, size):
        """Read one complete interleaved stereo PCM frame."""
        chunks = []
        remaining = size

        while remaining:
            chunk = self.process.stdout.read(remaining)

            if not chunk:
                raise EOFError("FFmpeg stopped producing audio.")

            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)

    async def recv(self):
        if self.readyState != "live":
            raise MediaStreamError

        try:
            pcm = await asyncio.to_thread(
                self._read_exact, self.frame_bytes
            )
        except (EOFError, OSError, ValueError) as exc:
            self.stop()
            raise MediaStreamError from exc

        frame = av.AudioFrame(
            format="s16",
            layout="stereo",
            samples=self.samples_per_frame,
        )

        frame.planes[0].update(pcm)
        frame.sample_rate = self.sample_rate
        frame.pts = self.pts
        frame.time_base = Fraction(1, self.sample_rate)

        self.pts += self.samples_per_frame
        return frame

    def stop(self):
        if self.readyState == "ended":
            return

        super().stop()

        if self.process.poll() is None:
            self.process.terminate()

            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        if self.process.stdout:
            self.process.stdout.close()


def get_lan_ip():
    """Find the IP used for the default outbound network route."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global audio_track

    if not AUDIO_SOURCE:
        raise RuntimeError(
            "Set AUDIO_SOURCE to your system-output monitor, "
            "normally ending in .monitor."
        )

    # FFmpeg captures the monitor as 48 kHz stereo PCM.
    audio_track = PulseCaptureTrack(AUDIO_SOURCE)

    # Detect an FFmpeg startup failure before accepting connections.
    await asyncio.sleep(0.3)

    if audio_track.process.poll() is not None:
        audio_track.stop()
        audio_track = None
        raise RuntimeError(
            "FFmpeg exited while opening the audio source. "
            "Check the monitor name and run the FFmpeg capture test."
        )

    try:
        yield
    finally:
        await asyncio.gather(
            *(pc.close() for pc in list(pcs)),
            return_exceptions=True,
        )
        pcs.clear()

        if audio_track is not None:
            audio_track.stop()
            audio_track = None


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def host_dashboard():
    return FileResponse("static/host.html")


@app.get("/listen")
async def listener_page():
    return FileResponse("static/listen.html")


@app.get("/health")
async def health():
    connected = sum(
        1 for pc in pcs
        if pc.connectionState == "connected"
    )

    return {
        "ok": True,
        "connected": connected,
        "max_clients": MAX_CLIENTS,
    }


@app.get("/qr.png")
async def qr_png():
    url = f"http://{get_lan_ip()}:8000/listen"
    image = qrcode.make(url)

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    async with lock:
        active = sum(
            1 for pc in pcs
            if pc.connectionState != "closed"
        )

        if active >= MAX_CLIENTS:
            await ws.send_json({
                "type": "error",
                "message": f"Room full: maximum {MAX_CLIENTS} listeners.",
            })
            await ws.close(code=1008)
            return

        pc = RTCPeerConnection()
        pcs.add(pc)

    try:
        while True:
            message = await ws.receive_json()

            if message.get("type") != "offer":
                continue

            offer = RTCSessionDescription(
                sdp=message["sdp"],
                type="offer",
            )

            await pc.setRemoteDescription(offer)

            # Give each listener its own subscription to the same source.
            #pc.addTrack(relay.subscribe(audio_track))
            pc.addTrack(relay.subscribe(audio_track, buffered=False))
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            await ws.send_json({
                "type": "answer",
                "sdp": pc.localDescription.sdp,
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_json({
                "type": "error",
                "message": str(exc),
            })
        except Exception:
            pass
    finally:
        await pc.close()
        pcs.discard(pc)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
