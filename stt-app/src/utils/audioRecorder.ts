/**
 * Web Audio Recorder for Cross-Platform Desktop & Touchscreen Kiosk (Windows & Pi 4).
 * Encodes audio directly into 16,000 Hz Mono 16-bit PCM WAV (44-byte RIFF header).
 */

export function createWavHeader(
  dataLength: number,
  sampleRate = 16000,
  numChannels = 1,
  bitsPerSample = 16
): Uint8Array {
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const buffer = new Uint8Array(44);
  const view = new DataView(buffer.buffer);

  // "RIFF" chunk descriptor
  buffer.set(new TextEncoder().encode('RIFF'), 0);
  view.setUint32(4, 36 + dataLength, true);
  buffer.set(new TextEncoder().encode('WAVE'), 8);

  // "fmt " sub-chunk
  buffer.set(new TextEncoder().encode('fmt '), 12);
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // "data" sub-chunk
  buffer.set(new TextEncoder().encode('data'), 36);
  view.setUint32(40, dataLength, true);

  return buffer;
}

/**
 * Resamples a Float32Array from inputRate to targetRate using linear interpolation.
 */
export function resampleAudio(
  input: Float32Array,
  inputRate: number,
  targetRate = 16000
): Float32Array {
  if (inputRate === targetRate || input.length === 0) {
    return input;
  }
  const ratio = inputRate / targetRate;
  const outputLength = Math.round(input.length / ratio);
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const pos = i * ratio;
    const index = Math.floor(pos);
    const fraction = pos - index;
    const nextIndex = Math.min(index + 1, input.length - 1);
    output[i] = input[index] * (1 - fraction) + input[nextIndex] * fraction;
  }

  return output;
}

/**
 * Converts Float32 audio samples (-1.0 to 1.0) to 16-bit signed PCM integers.
 */
export function floatTo16BitPCM(input: Float32Array): Int16Array {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return output;
}

/**
 * Encodes 16-bit PCM buffer into standard WAV Blob with 44-byte RIFF header.
 */
export function encodeWavBlob(pcmData: Int16Array, sampleRate = 16000): Blob {
  const dataLength = pcmData.byteLength;
  const header = createWavHeader(dataLength, sampleRate, 1, 16);
  const full = new Uint8Array(header.length + dataLength);
  full.set(header, 0);
  full.set(new Uint8Array(pcmData.buffer, pcmData.byteOffset, pcmData.byteLength), header.length);
  return new Blob([full.buffer], { type: 'audio/wav' });
}

export interface AudioDeviceInfo {
  id: string;
  name: string;
  isDefault: boolean;
}

export class WebAudioRecorder {
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private chunks: Float32Array[] = [];
  private startTime = 0;
  private activeTrack: MediaStreamTrack | null = null;
  private isRecording = false;

  get recording(): boolean {
    return this.isRecording;
  }

  async startRecording(
    deviceId?: string,
    onDisconnect?: () => void
  ): Promise<void> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      throw new Error('navigator.mediaDevices.getUserMedia is not supported in this environment.');
    }

    // Stop any existing stream
    this.cancelRecording();

    const constraints: MediaStreamConstraints = {
      audio: deviceId && deviceId !== 'default' ? { deviceId: { exact: deviceId } } : true,
      video: false,
    };

    this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    const tracks = this.stream.getAudioTracks();
    if (tracks.length === 0) {
      throw new Error('No audio tracks found in media stream.');
    }

    this.activeTrack = tracks[0];
    this.activeTrack.onended = () => {
      if (this.isRecording) {
        this.isRecording = false;
        if (onDisconnect) {
          onDisconnect();
        }
      }
    };

    const AudioContextClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.audioContext = new AudioContextClass();

    this.chunks = [];
    this.startTime = Date.now();
    this.isRecording = true;

    this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
    // 4096 buffer size, 1 input channel, 1 output channel
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      const channel = e.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(channel));
    };

    this.sourceNode.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  stopRecording(): { blob: Blob; durationMs: number; hasAudio: boolean } {
    this.isRecording = false;
    const durationMs = this.startTime > 0 ? Date.now() - this.startTime : 0;

    // Clean up nodes and tracks
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.activeTrack) {
      this.activeTrack.onended = null;
      this.activeTrack = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }

    const sourceRate = this.audioContext?.sampleRate || 44100;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }

    // Merge all collected PCM chunks
    const totalLength = this.chunks.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    this.chunks = [];

    const hasAudio = merged.length > 0;
    // Resample to 16,000 Hz Mono
    const resampled = resampleAudio(merged, sourceRate, 16000);
    // Convert to 16-bit PCM
    const pcm16 = floatTo16BitPCM(resampled);
    // Package into WAV
    const blob = encodeWavBlob(pcm16, 16000);

    return { blob, durationMs, hasAudio };
  }

  cancelRecording(): void {
    this.isRecording = false;
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.activeTrack) {
      this.activeTrack.onended = null;
      this.activeTrack = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    this.chunks = [];
    this.startTime = 0;
  }

  static async enumerateMicrophones(): Promise<AudioDeviceInfo[]> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) {
      return [];
    }

    try {
      let devices = await navigator.mediaDevices.enumerateDevices();
      const hasLabels = devices.some((d) => d.kind === 'audioinput' && d.label.trim().length > 0);

      // If Chromium/Electron hasn't granted media access yet, device labels might be empty.
      // Warm up by briefly requesting a stream if possible.
      if (!hasLabels && navigator.mediaDevices.getUserMedia) {
        try {
          const warmUpStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
          warmUpStream.getTracks().forEach((t) => t.stop());
          devices = await navigator.mediaDevices.enumerateDevices();
        } catch {
          // If user denies or error, continue with available device IDs
        }
      }

      // Filter only audioinput devices
      const audioInputs = devices.filter((d) => d.kind === 'audioinput');

      // Separate physical devices with real IDs (excluding empty IDs or virtual 'default')
      const realDevices = audioInputs.filter(
        (d) => d.deviceId && d.deviceId !== 'default' && d.deviceId.trim().length > 0
      );

      if (realDevices.length > 0) {
        return realDevices.map((d, index) => ({
          id: d.deviceId,
          name: d.label.trim() || `Microphone ${index + 1}`,
          isDefault: index === 0,
        }));
      }

      // If no devices have explicit non-default IDs (e.g. only virtual default), return clean list.
      // Note: Do NOT return items with id: "" because "" is reserved for OS default in Settings.
      return audioInputs
        .filter((d) => d.deviceId && d.deviceId.trim().length > 0)
        .map((d, index) => ({
          id: d.deviceId,
          name:
            d.label.trim() ||
            (d.deviceId === 'default' ? 'Microphone mặc định' : `Microphone ${index + 1}`),
          isDefault: d.deviceId === 'default' || index === 0,
        }));
    } catch {
      return [];
    }
  }

  static onDeviceChange(callback: () => void): () => void {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.addEventListener) {
      return () => {};
    }
    const handler = () => callback();
    navigator.mediaDevices.addEventListener('devicechange', handler);
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', handler);
    };
  }
}
