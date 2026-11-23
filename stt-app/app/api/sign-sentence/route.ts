import { makeSignSentenceHandler, sentenceConfiguration, putSentenceConfiguration } from '../../../src/server/signSentence';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const POST = makeSignSentenceHandler();
export const GET = sentenceConfiguration;
export const PUT = putSentenceConfiguration;
