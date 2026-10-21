# LAN Audio

**Stream your computer's audio to multiple phones on the same local network.** Each listener can use their own wired or Bluetooth headphones.

LAN Audio started from a simple problem: while watching a film with a friend, sharing one pair of earbuds was awkward. The goal is to let everyone listen from their own device without needing a special multi-headphone Bluetooth setup.

> **Project status:** Prototype / in development. The current implementation is a laptop-hosted web app. An Android-native host is a possible future direction, not part of the current implementation.

## How it works

1. The host computer captures its system audio through the OS audio monitor source.
2. A Python server provides a host dashboard and WebRTC signalling.
3. A listener opens the provided link on a phone and joins the session.
4. WebRTC carries the real-time audio stream to the listener, where the phone plays it through its selected output device.

```mermaid
flowchart LR
    A[Computer system audio] --> B[PulseAudio / PipeWire monitor]
    B --> C[FFmpeg PCM capture]
    C --> D[Python server and audio track]
    D <-->|WebSocket signalling| E[Phone browser]
    D <-->|WebRTC media, usually UDP| E
    E --> F[Phone audio output]
    F --> G[Wired or Bluetooth headphones]
```

The signalling connection and media stream serve different purposes: WebSocket signalling exchanges connection information, while WebRTC transports the live audio. WebRTC commonly uses UDP when network conditions allow; the actual selected transport depends on ICE negotiation.

## Screenshots

### 1. Host Dashboard

The host dashboard displays a QR code that listeners can scan to open the LAN Audio listening page. It also shows the number of connected listeners, allowing the host to monitor active connections at a glance.

![LAN Audio host dashboard displaying the QR code and connected listeners](docs/screenshots/dashboard.png)

### 2. Phone Listener Interface

The listener interface allows users to connect their phones to the live audio stream and listen through their own wired or Bluetooth headphones. The Pause button disconnects the audio stream, while resuming reconnects to the live audio instead of replaying previously buffered audio.

![LAN Audio mobile listener interface showing an active audio connection](docs/screenshots/listener.png)

## Current features

- Capture desktop audio on Linux using a PulseAudio-compatible monitor source (including PipeWire's PulseAudio compatibility layer).
- Browser-based host and listener interfaces.
- WebRTC audio delivery to connected listeners.
- QR-code-based joining in the host dashboard, if enabled in the current UI.
- Designed for a local network; no cloud audio relay is required for a same-LAN session.

Features and behavior may vary as the prototype develops. Verify them against the current code before treating them as production-ready.

## Architecture and technology

- **Python / FastAPI** — web server and signalling endpoints.
- **FFmpeg** — captures and converts the selected system-audio monitor source to PCM.
- **aiortc / WebRTC** — audio tracks and browser media connections.
- **WebSockets** — signalling between the browser clients and the server.
- **HTML / JavaScript** — host and listener pages.
- **PulseAudio-compatible audio interface** — access to the Linux system-audio monitor.

## Requirements

- Linux host with a working PulseAudio-compatible audio server (PulseAudio or PipeWire with its PulseAudio compatibility service).
- Python 3.10+ recommended.
- FFmpeg built with PulseAudio input support.
- A modern browser on the host and listener devices.
- Host and listener devices on the same Wi-Fi/LAN, with firewall rules allowing the required local connections.

Bluetooth audio output adds latency of its own, so the host-to-phone network latency is only part of the overall delay.

## Run locally

These instructions describe the expected workflow; update filenames or commands if the current source tree differs.

1. Install FFmpeg and verify that the system audio monitor source is available:

   ```bash
   pactl list short sources
   ```

   Look for a source ending in `.monitor`.

2. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/albinea/LAN-Audio.git
   cd LAN-Audio
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the Python dependencies. If the repository contains a dependency file, use it:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the audio source to match your machine. For example, a source name may look like:

   ```text
   alsa_output.pci-0000_05_00.6.analog-stereo.monitor
   ```

   This is only an example; use the monitor source returned by your own system.

5. Start the FastAPI application using the entry point and command defined by the project. For example, if the module is `app.py` and the ASGI app is named `app`:

   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

6. Open the host dashboard on the host computer, then open its LAN address on the listener phone. Use the app's displayed listener URL or QR code if available.

**Note:** The repository is currently being initialized. This README is a project overview and setup outline; exact run commands, dependency files, firewall ports, and UI features should be aligned with the source code as it is added.

## Limitations

- The current host captures Linux system audio; it is not yet a universal cross-platform host.
- Some apps and protected content may restrict system-audio capture on certain operating systems.
- Bluetooth headphones can introduce noticeable delay.
- Real-world latency and multi-listener capacity need to be measured rather than assumed.
- WebRTC connectivity can depend on firewall and network configuration.

## Contributing

Issues and pull requests are welcome. Please include your operating system, browser, audio server, and relevant logs when reporting a problem. Do not include private data or access tokens in logs.

## License

No license has been added yet. Until a license is included, the repository's default copyright applies and reuse rights should not be assumed.
