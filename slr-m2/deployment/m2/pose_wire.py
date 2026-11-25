"""Binary LAN pose request header followed immediately by JPEG bytes."""
from struct import Struct

POSE_WS_PATH = "/ws/vision/pose"
# Frame sequence (0 means unbuffered), capture timestamp in seconds, and flags.
POSE_FRAME_HEADER = Struct("!QdB")
POSE_RUN_HANDS = 1
POSE_MEASURE = 2
MAX_POSE_FRAME_BYTES = 4 * 1024 * 1024
