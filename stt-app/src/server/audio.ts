import { extname } from 'node:path';
import { MAX_AUDIO_BYTES } from '../contracts';
import { AppError } from './errors';
import { boundedBody } from './http';

export type AudioInput = { name: string; bytes: Uint8Array; contentType: string };
export async function readAudio(request: Request): Promise<AudioInput> {
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.startsWith('multipart/form-data;')) throw new AppError('file_required', 'Hãy tải lên một file WAV, MP3 hoặc FLAC.');
  const bytes = await boundedBody(request, MAX_AUDIO_BYTES + 128 * 1024);
  let form: FormData;
  try { form = await new Response(bytes as BodyInit, { headers: { 'Content-Type': contentType } }).formData(); }
  catch { throw new AppError('upload_invalid', 'Không đọc được dữ liệu tải lên. Hãy chọn lại file.'); }
  const entries = [...form.entries()];
  if (entries.length !== 1 || entries[0][0] !== 'file' || typeof entries[0][1] === 'string')
    throw new AppError('one_file_required', 'Mốc hiện tại nhận đúng một file cho mỗi yêu cầu.');
  const file = entries[0][1] as File;
  if (!file.size) throw new AppError('audio_empty', 'File audio trống.');
  if (file.size > MAX_AUDIO_BYTES) throw new AppError('audio_too_large', 'File audio phải nhỏ hơn hoặc bằng 20 MiB.', 413);
  const audio = new Uint8Array(await file.arrayBuffer());
  const prefix = (offset: number, s: string) => s.split('').every((c, i) => audio[offset + i] === c.charCodeAt(0));
  const extension = extname(file.name).toLowerCase();
  let mime = '';
  if (extension === '.wav' && prefix(0, 'RIFF') && prefix(8, 'WAVE')) mime = 'audio/wav';
  if (extension === '.flac' && prefix(0, 'fLaC')) mime = 'audio/flac';
  if (extension === '.mp3' && (prefix(0, 'ID3') || (audio[0] === 255 && (audio[1] & 224) === 224))) mime = 'audio/mpeg';
  if (!mime) throw new AppError('audio_format', 'Hỗ trợ WAV, MP3 và FLAC. Nội dung đầu file phải khớp định dạng đã chọn.');
  return { name: file.name.split(/[\\/]/).pop()!.replace(/[\x00-\x1f\x7f]/g, '').slice(0, 200), bytes: audio, contentType: mime };
}
