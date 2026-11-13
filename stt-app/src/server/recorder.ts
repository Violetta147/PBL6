import { spawn, execFile, execSync, type ChildProcess } from 'node:child_process';
import { existsSync, createWriteStream, type WriteStream } from 'node:fs';
import { readdir, rm, stat, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, basename } from 'node:path';
import { randomUUID } from 'node:crypto';
import { promisify } from 'node:util';
import type { AudioDevice, RecorderState, Transcript } from '../contracts';
import { AppError } from './errors';
import { readSettings, type Settings } from './settings';
import { transcribe as defaultTranscribe } from './deepgram';

const execFileAsync = promisify(execFile);

export function createWavHeader(dataLength: number, sampleRate = 16000, numChannels = 1, bitsPerSample = 16): Uint8Array {
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const buffer = new Uint8Array(44);
  const view = new DataView(buffer.buffer);

  // "RIFF"
  buffer.set(new TextEncoder().encode('RIFF'), 0);
  view.setUint32(4, 36 + dataLength, true);
  buffer.set(new TextEncoder().encode('WAVE'), 8);

  // "fmt "
  buffer.set(new TextEncoder().encode('fmt '), 12);
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // "data"
  buffer.set(new TextEncoder().encode('data'), 36);
  view.setUint32(40, dataLength, true);

  return buffer;
}

export function createMockWavBuffer(durationSeconds = 1, sampleRate = 16000): Uint8Array {
  const numChannels = 1;
  const bitsPerSample = 16;
  const numSamples = Math.floor(sampleRate * Math.max(0.1, durationSeconds));
  const dataSize = numSamples * ((numChannels * bitsPerSample) / 8);
  const header = createWavHeader(dataSize, sampleRate, numChannels, bitsPerSample);
  const full = new Uint8Array(44 + dataSize);
  full.set(header, 0);

  const view = new DataView(full.buffer, 44);
  for (let i = 0; i < numSamples; i++) {
    // 440 Hz soft test tone
    const sample = Math.sin((2 * Math.PI * 440 * i) / sampleRate) * 8000;
    view.setInt16(i * 2, sample, true);
  }
  return full;
}

export function enumerateWindowsAudioDevices(): AudioDevice[] {
  const devices: AudioDevice[] = [];
  try {
    const regBase = 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\MMDevices\\Audio\\Capture';
    const rawKeys = execSync(`reg query "${regBase}"`, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 6000,
      windowsHide: true,
    });

    for (const line of rawKeys.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('HKEY_LOCAL_MACHINE')) continue;
      try {
        const stateOut = execSync(`reg query "${trimmed}" /v "DeviceState"`, {
          encoding: 'utf8',
          stdio: ['ignore', 'pipe', 'ignore'],
          timeout: 4000,
          windowsHide: true,
        });
        const stateMatch = stateOut.match(/DeviceState\s+REG_DWORD\s+0x([0-9a-fA-F]+)/);
        const state = stateMatch ? parseInt(stateMatch[1], 16) : null;
        if (state !== 1) continue; // Only DEVICE_STATE_ACTIVE

        const id = trimmed.split('\\').pop() || '';
        const propOut = execSync(`reg query "${trimmed}\\Properties"`, {
          encoding: 'utf8',
          stdio: ['ignore', 'pipe', 'ignore'],
          timeout: 4000,
          windowsHide: true,
        });

        let endpointName = '';
        let adapterName = '';
        for (const pLine of propOut.split('\n')) {
          const pt = pLine.trim();
          const friendlyMatch = pt.match(/\{a45c254e-df1c-4efd-8020-67d146a850e0\},2\s+REG_\w+\s+(.*)$/i);
          if (friendlyMatch) {
            endpointName = friendlyMatch[1].trim();
          }
          const adapterMatch = pt.match(/\{b3f8fa53-0004-438e-9003-51a46e139bfc\},6\s+REG_\w+\s+(.*)$/i);
          if (adapterMatch) {
            adapterName = adapterMatch[1].trim();
          }
        }

        const fullName = endpointName && adapterName
          ? `${endpointName} (${adapterName})`
          : (endpointName || adapterName || `Microphone ${id}`);

        devices.push({
          id,
          name: fullName,
          isDefault: false,
        });
      } catch {}
    }
  } catch {}

  // Fallback to PowerShell Win32_SoundDevice
  if (devices.length === 0) {
    try {
      const psOut = execSync('powershell -NoProfile -Command "Get-CimInstance Win32_SoundDevice | Where-Object { $_.Status -eq \'OK\' } | Select-Object -ExpandProperty Name"', {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 8000,
        windowsHide: true,
      });
      const names = psOut.split('\n').map((s) => s.trim()).filter(Boolean);
      for (const name of names) {
        devices.push({
          id: name.toLowerCase().replace(/[^a-z0-9]/g, '_'),
          name,
          isDefault: false,
        });
      }
    } catch {}
  }

  if (devices.length > 0) {
    devices[0].isDefault = true;
  }
  return devices;
}

export async function cleanupOrphanRecordings(dir = tmpdir()): Promise<number> {
  let cleaned = 0;
  try {
    const files = await readdir(dir);
    for (const file of files) {
      if (file.startsWith('pbl6_rec_') && (file.endsWith('.wav') || file.endsWith('.raw'))) {
        await rm(join(dir, file), { force: true }).catch(() => {});
        cleaned++;
      }
    }
  } catch {
    // Best-effort cleanup
  }
  return cleaned;
}

export type RecorderDeps = {
  readSettings: () => Promise<Settings>;
  transcribe: typeof defaultTranscribe;
  spawnProcess?: typeof spawn;
  execCommand?: typeof execFileAsync;
  enableSox?: boolean;
};

export class HardwareRecorder {
  private status: RecorderState['status'] = 'idle';
  private startTime = 0;
  private selectedDeviceId?: string;
  private error?: string;
  private currentSessionId?: string;
  private currentFilePath?: string;
  private currentRawPath?: string;
  private rawStream?: WriteStream;
  private childProcess?: ChildProcess;
  private timeoutTimer?: NodeJS.Timeout;
  private midDisconnectPartial = false;
  private activeTranscriptionPromise?: Promise<Transcript & { partial?: boolean }>;
  private lastTranscript?: (Transcript & { partial?: boolean }) | null;
  private isSubprocessMode: boolean;
  private isSoxMode: boolean;
  private deps: RecorderDeps;

  constructor(deps: Partial<RecorderDeps> = {}) {
    this.deps = {
      readSettings: deps.readSettings || readSettings,
      transcribe: deps.transcribe || defaultTranscribe,
      spawnProcess: deps.spawnProcess || spawn,
      execCommand: deps.execCommand || execFileAsync,
      enableSox: deps.enableSox,
    };
    this.isSubprocessMode = process.platform === 'linux' || Boolean(deps.spawnProcess);
    const isTest = Boolean(
      deps.spawnProcess ||
      deps.readSettings ||
      deps.transcribe ||
      process.env.NODE_ENV === 'test' ||
      process.env.NODE_TEST_CONTEXT
    );
    const soxBinaryPath = process.env.PBL6_STT_SOX_PATH || ['C:', 'sox', 'sox.exe'].join('\\');
    this.isSoxMode = process.platform === 'win32'
      && (deps.enableSox !== undefined
        ? deps.enableSox
        : (!isTest && (process.env.PBL6_STT_WIN_MIC === '1' || process.env.PBL6_STT_WIN_MIC === 'sox') && existsSync(soxBinaryPath)));
  }

  public getState(): RecorderState {
    const durationMs = this.status === 'recording'
      ? Math.max(0, Date.now() - this.startTime)
      : 0;
    return {
      status: this.status,
      durationMs,
      selectedDeviceId: this.selectedDeviceId,
      error: this.error,
    };
  }

  public async listMicrophones(): Promise<AudioDevice[]> {
    if (process.platform === 'linux' || Boolean(this.deps.execCommand)) {
      try {
        const execCmd = this.deps.execCommand || execFileAsync;
        const { stdout } = await execCmd('pw-dump', ['Node']);
        const nodes = JSON.parse(stdout);
        const sources: AudioDevice[] = [];
        const priorities: number[] = [];

        if (Array.isArray(nodes)) {
          for (const node of nodes) {
            const mediaClass = node.info?.props?.['media.class'];
            if (mediaClass === 'Audio/Source') {
              const id = String(node.id || node.info?.props?.['node.name'] || randomUUID());
              const name = node.info?.props?.['node.description']
                || node.info?.props?.['node.nick']
                || node.info?.props?.['node.name']
                || `Microphone ${node.id}`;
              const prio = Number(node.info?.props?.['priority.session'] || 0);
              sources.push({ id, name, isDefault: false });
              priorities.push(prio);
            }
          }

          if (sources.length > 0) {
            let maxPrio = -Infinity;
            let defaultIdx = 0;
            for (let i = 0; i < sources.length; i++) {
              if (priorities[i] > maxPrio) {
                maxPrio = priorities[i];
                defaultIdx = i;
              }
            }
            sources[defaultIdx].isDefault = true;
            return sources;
          }

          // PipeWire returned nodes array, but 0 audio sources found -> mic disconnected
          return [];
        }
      } catch {
        // Fallback when pw-dump fails or not in pipewire environment
      }
      return [
        { id: 'default', name: 'Microphone mặc định (PipeWire)', isDefault: true },
      ];
    }

    if (process.platform === 'win32') {
      try {
        const winDevices = enumerateWindowsAudioDevices();
        if (winDevices.length > 0) {
          return winDevices;
        }
      } catch {}
      return [
        { id: 'default', name: 'Microphone mặc định (Hệ thống)', isDefault: true },
      ];
    }

    // Windows or macOS dev mock
    return [
      { id: 'default', name: 'Microphone mặc định (Hệ thống)', isDefault: true },
    ];
  }

  public async start(options?: {
    deviceId?: string;
    maxDurationSeconds?: number;
  }): Promise<RecorderState> {
    if (this.status === 'recording' || this.status === 'transcribing') {
      throw new AppError('recorder_busy', 'Đang trong phiên thu âm hoặc nhận dạng.', 409);
    }

    this.lastTranscript = null;
    this.activeTranscriptionPromise = undefined;

    const availableMics = await this.listMicrophones();
    if (availableMics.length === 0) {
      this.status = 'error';
      this.error = 'Không tìm thấy mic. Hãy kết nối mic rồi thử lại.';
      throw new AppError('no_microphone', 'Không tìm thấy mic. Hãy kết nối mic rồi thử lại.', 404);
    }

    const settings = await this.deps.readSettings();
    let targetDeviceId: string;

    if (options?.deviceId) {
      targetDeviceId = options.deviceId;
    } else if (settings.selectedMicrophoneId && availableMics.some(m => m.id === settings.selectedMicrophoneId)) {
      targetDeviceId = settings.selectedMicrophoneId;
    } else {
      // Fallback to available OS default microphone, keeping saved choice intact
      const defaultMic = availableMics.find(m => m.isDefault) || availableMics[0];
      targetDeviceId = defaultMic.id;
    }

    const maxDurationSeconds = options?.maxDurationSeconds || settings.maxRecordSeconds || 120;
    const sessionId = randomUUID();
    const filePath = join(tmpdir(), `pbl6_rec_${sessionId}.wav`);

    this.status = 'recording';
    this.startTime = Date.now();
    this.selectedDeviceId = targetDeviceId;
    this.error = undefined;
    this.currentSessionId = sessionId;
    this.currentFilePath = filePath;
    this.midDisconnectPartial = false;

    // Subprocess or mock start
    if (this.isSubprocessMode) {
      try {
        const args: string[] = ['--format', 's16', '--rate', '16000', '--channels', '1'];
        if (targetDeviceId && targetDeviceId !== 'default') {
          args.push('--target', targetDeviceId);
        }
        args.push(filePath);

        const child = (this.deps.spawnProcess || spawn)('pw-record', args, {
          stdio: ['ignore', 'ignore', 'pipe'],
        });
        this.childProcess = child;

        child.on('error', (err) => {
          // If pw-record fails to spawn, fallback attempt with arecord
          if (this.status === 'recording') {
            const fallback = (this.deps.spawnProcess || spawn)('arecord', [
              '-f', 'S16_LE', '-r', '16000', '-c', '1', filePath,
            ], { stdio: 'ignore' });
            this.childProcess = fallback;
            fallback.on('error', (arecordErr) => {
              this.cleanupProcessAndTimer();
              this.status = 'error';
              this.error = `Không thể khởi động thiết bị thu âm: ${arecordErr.message}`;
            });
            fallback.on('exit', () => {
              this.handleUnexpectedExit(filePath);
            });
          }
        });

        child.on('exit', () => {
          this.handleUnexpectedExit(filePath);
        });
      } catch (err) {
        this.status = 'error';
        this.error = `Lỗi khởi động thu âm: ${(err as Error).message}`;
        throw new AppError('record_start_failed', 'Không thể bắt đầu thu âm từ thiết bị.', 500);
      }
    } else if (this.isSoxMode) {
      try {
        const rawPath = filePath.replace(/\.wav$/, '.raw');
        this.currentRawPath = rawPath;
        const rawStream = createWriteStream(rawPath);
        this.rawStream = rawStream;

        const soxBin = process.env.PBL6_STT_SOX_PATH || ['C:', 'sox', 'sox.exe'].join('\\');
        const child = (this.deps.spawnProcess || spawn)(soxBin, [
          '-q', '-t', 'waveaudio', 'default',
          '-r', '16000', '-c', '1', '-b', '16',
          '-t', 'raw', '-',
        ], { stdio: ['ignore', 'pipe', 'pipe'] });
        this.childProcess = child;

        child.stdout?.pipe(rawStream);

        child.on('error', (err) => {
          this.cleanupProcessAndTimer();
          this.status = 'error';
          this.error = `Lỗi khởi động thiết bị SoX: ${err.message}`;
        });

        child.on('exit', () => {
          this.handleUnexpectedExit(filePath);
        });
      } catch (err) {
        this.status = 'error';
        this.error = `Lỗi khởi động thu âm SoX: ${(err as Error).message}`;
        throw new AppError('record_start_failed', 'Không thể bắt đầu thu âm từ thiết bị.', 500);
      }
    } else {
      // Windows / macOS / dev mock mode:
      await writeFile(filePath, Buffer.from(createMockWavBuffer(0.5)));
    }

    // Set max duration auto-stop timer
    const timeoutMs = Math.max(10, Math.round(maxDurationSeconds * 1000));
    this.timeoutTimer = setTimeout(() => {
      if (this.status === 'recording') {
        this.stop().catch(() => {});
      }
    }, timeoutMs);

    return this.getState();
  }

  private handleUnexpectedExit(filePath: string) {
    if (this.status !== 'recording') return;

    this.cleanupProcessAndTimer();

    stat(filePath).then(async (fileStats) => {
      if (fileStats && fileStats.size > 44) {
        // Partial audio recorded before mid-recording disconnect
        this.midDisconnectPartial = true;
        this.error = 'Mic bị ngắt kết nối. Đang nhận dạng phần đã thu.';
        this.triggerTranscription(filePath, true).catch(() => {});
      } else {
        this.status = 'error';
        this.error = 'Mic bị ngắt kết nối và không thu được âm thanh.';
        await rm(filePath, { force: true }).catch(() => {});
        this.currentFilePath = undefined;
      }
    }).catch(async () => {
      this.status = 'error';
      this.error = 'Mic bị ngắt kết nối.';
      await rm(filePath, { force: true }).catch(() => {});
      this.currentFilePath = undefined;
    });
  }

  private cleanupProcessAndTimer() {
    if (this.timeoutTimer) {
      clearTimeout(this.timeoutTimer);
      this.timeoutTimer = undefined;
    }
    this.childProcess = undefined;
  }

  private triggerTranscription(filePath: string, isPartial: boolean): Promise<Transcript & { partial?: boolean }> {
    this.status = 'transcribing';
    const durationSeconds = Math.max(0.1, (Date.now() - this.startTime) / 1000);

    const promise = (async () => {
      try {
        if (this.isSoxMode) {
          if (this.childProcess) {
            try { this.childProcess.kill(); } catch {}
            this.childProcess = undefined;
          }
          if (this.rawStream) {
            await new Promise<void>((resolve) => {
              this.rawStream?.end(() => resolve());
            });
            this.rawStream = undefined;
          }

          const rawPath = this.currentRawPath || filePath.replace(/\.wav$/, '.raw');
          const rawStats = await stat(rawPath).catch(() => null);
          if (rawStats && rawStats.size > 0) {
            const rawBytes = await readFile(rawPath);
            const wavHeader = createWavHeader(rawBytes.length, 16000, 1, 16);
            const fullWav = Buffer.concat([Buffer.from(wavHeader), rawBytes]);
            await writeFile(filePath, fullWav);
            await rm(rawPath, { force: true }).catch(() => {});
            this.currentRawPath = undefined;
          }
        } else if (!this.isSubprocessMode && !isPartial) {
          const mockWav = createMockWavBuffer(durationSeconds);
          await writeFile(filePath, Buffer.from(mockWav));
        }

        const fileStats = await stat(filePath).catch(() => null);
        if (!fileStats || fileStats.size <= 44) {
          throw new AppError('audio_empty', 'Không thu được âm thanh hoặc file rỗng.', 400);
        }

        const bytes = await readFile(filePath);
        const settings = await this.deps.readSettings();

        if (!settings.apiKey) {
          throw new AppError('key_missing', 'Chưa cấu hình API key trong Cài đặt.', 409);
        }

        const audio = {
          name: basename(filePath),
          bytes: new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength),
          contentType: 'audio/wav',
        };

        const transcript = await this.deps.transcribe(audio, settings);
        const finalResult = { ...transcript, ...(isPartial ? { partial: true } : {}) };
        this.lastTranscript = finalResult;
        return finalResult;
      } finally {
        await rm(filePath, { force: true }).catch(() => {});
        this.status = 'idle';
        this.currentFilePath = undefined;
        this.currentSessionId = undefined;
        this.activeTranscriptionPromise = undefined;
        this.midDisconnectPartial = false;
      }
    })();

    this.activeTranscriptionPromise = promise;
    return promise;
  }

  public async stop(): Promise<Transcript & { partial?: boolean }> {
    // If transcription is already in progress (e.g. triggered by auto-stop or disconnect), await it
    if (this.status === 'transcribing' && this.activeTranscriptionPromise) {
      return await this.activeTranscriptionPromise;
    }

    // If auto-stop already finished and cached result, return it
    if (this.status === 'idle' && this.lastTranscript) {
      const result = this.lastTranscript;
      this.lastTranscript = null;
      return result;
    }

    if (this.status !== 'recording') {
      throw new AppError('recorder_not_recording', 'Không có phiên thu âm đang chạy.', 409);
    }

    this.cleanupProcessAndTimer();

    const filePath = this.currentFilePath;
    const isPartial = this.midDisconnectPartial;

    if (this.childProcess) {
      // Gracefully signal process to stop and flush WAV header
      this.childProcess.kill('SIGINT');
      await new Promise<void>((resolve) => {
        if (!this.childProcess || this.childProcess.killed || this.childProcess.exitCode !== null) {
          return resolve();
        }
        const timeout = setTimeout(() => {
          this.childProcess?.kill();
          resolve();
        }, 1500);
        this.childProcess.on('exit', () => {
          clearTimeout(timeout);
          resolve();
        });
      });
      this.childProcess = undefined;
    }

    if (!filePath) {
      this.status = 'idle';
      throw new AppError('audio_empty', 'Không tìm thấy file âm thanh.', 400);
    }

    return await this.triggerTranscription(filePath, isPartial);
  }

  public async cancel(): Promise<{ cancelled: true }> {
    this.cleanupProcessAndTimer();

    if (this.childProcess) {
      try {
        this.childProcess.kill();
      } catch {}
      this.childProcess = undefined;
    }

    if (this.rawStream) {
      try { this.rawStream.end(); } catch {}
      this.rawStream = undefined;
    }
    if (this.currentRawPath) {
      await rm(this.currentRawPath, { force: true }).catch(() => {});
      this.currentRawPath = undefined;
    }

    if (this.currentFilePath) {
      await rm(this.currentFilePath, { force: true }).catch(() => {});
      this.currentFilePath = undefined;
    }

    this.status = 'idle';
    this.currentSessionId = undefined;
    this.midDisconnectPartial = false;
    this.activeTranscriptionPromise = undefined;
    this.lastTranscript = null;
    this.error = undefined;

    return { cancelled: true };
  }
}

// Global singleton instance
const globalRecorderKey = Symbol.for('pbl6.stt.recorder');
type GlobalWithRecorder = typeof globalThis & { [globalRecorderKey]?: HardwareRecorder };

export function getRecorder(deps?: Partial<RecorderDeps>): HardwareRecorder {
  const g = globalThis as GlobalWithRecorder;
  if (!g[globalRecorderKey] || deps) {
    const inst = new HardwareRecorder(deps);
    if (!deps) {
      g[globalRecorderKey] = inst;
      cleanupOrphanRecordings().catch(() => {});
    }
    return inst;
  }
  return g[globalRecorderKey]!;
}
