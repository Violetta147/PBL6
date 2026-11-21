import { getOskHandler, postOskHandler } from '../../../src/server/handlers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export const GET = getOskHandler;
export const POST = postOskHandler;
