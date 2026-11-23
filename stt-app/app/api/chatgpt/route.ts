import { chatGptGet, chatGptPost } from '../../../src/server/chatgptConnection';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = chatGptGet;
export const POST = chatGptPost;
