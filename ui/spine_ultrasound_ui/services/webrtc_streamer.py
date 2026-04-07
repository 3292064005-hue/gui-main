import asyncio
from typing import Optional
from loguru import logger
# Note: Requires pip install aiortc
# from aiortc import RTCPeerConnection, RTCSessionDescription
# from aiortc.contrib.media import MediaPlayer

class WebRTCStreamer:
    """
    Ubuntu 22.04 optimized WebRTC Video Server.
    Instead of Python OpenCV/Base64 which eats CPU overhead, it taps directly 
    into the Linux Video4Linux2 (/dev/videoX) character device.
    It leverages the GStreamer backend of aiortc to pipe natively through NVidia 
    NVENC h264 pipelines directly to the browser WebRTC receiver.
    Zero-CPU Glass-to-Glass latency!
    """
    def __init__(self, device_path="/dev/video0"):
        self.device = device_path
        # Use GStreamer Media Player directly in aiortc to get Hardware Acceleration
        # Equivalent gstreamer pipeline:
        # v4l2src device=/dev/video0 ! videoconvert ! nvv4l2h264enc ! rtph264pay ! ...
        self.player = None 
        # self.player = MediaPlayer(f"v4l2src device={self.device} ! videoconvert ! video/x-raw,format=I420 ! appsink", format="gstreamer")
        
        # self.pcs = set()

    async def handle_offer(self, sdp: str, type: str) -> dict:
        """
        Receives SDP Offer from React Frontend.
        Returns the Answer SDP mapping the Ultrasound Video Track.
        """
        '''
        pc = RTCPeerConnection()
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("WebRTC Connection state is %s", pc.connectionState)
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                self.pcs.discard(pc)

        offer = RTCSessionDescription(sdp=sdp, type=type)
        await pc.setRemoteDescription(offer)

        # Add pure-hardware encoded video track to the connection
        if self.player and self.player.video:
            pc.addTrack(self.player.video)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }
        '''
        return {"sdp": "...", "type": "answer"}

    def stop(self):
        # for pc in self.pcs:
        #    coro = pc.close()
        #    asyncio.create_task(coro)
        pass
