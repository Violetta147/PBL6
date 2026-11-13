import { getConversationsHandler, postConversationHandler } from '../../../src/server/handlers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export const GET = getConversationsHandler;
export const POST = postConversationHandler;
