import {
  getConversationHandler,
  patchConversationHandler,
  deleteConversationHandler,
} from '../../../../src/server/handlers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export const GET = getConversationHandler;
export const PATCH = patchConversationHandler;
export const DELETE = deleteConversationHandler;
