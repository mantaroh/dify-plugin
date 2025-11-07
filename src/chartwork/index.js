const manifest = require('./manifest.json');

const DEFAULT_BASE_URL = 'https://api.chatwork.com/v2';

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
  }
}

class AuthenticationError extends Error {
  constructor(message, status, responseBody) {
    super(message);
    this.name = 'AuthenticationError';
    this.status = status;
    this.responseBody = responseBody;
  }
}

class ChartworkAPIError extends Error {
  constructor(message, status, responseBody) {
    super(message);
    this.name = 'ChartworkAPIError';
    this.status = status;
    this.responseBody = responseBody;
  }
}

class ChartworkClient {
  constructor({ apiToken, baseUrl, fetchImpl }) {
    if (!apiToken) {
      throw new ValidationError('Chartwork API トークン (apiToken) が設定されていません。');
    }
    this.apiToken = apiToken;
    this.baseUrl = (baseUrl || DEFAULT_BASE_URL).replace(/\/$/, '');
    this.fetchImpl = fetchImpl || (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : null);
    if (!this.fetchImpl) {
      throw new Error('fetch API が利用できない環境です。Node.js v18 以上を利用してください。');
    }
  }

  buildHeaders() {
    return {
      'X-ChatWorkToken': this.apiToken,
      'Content-Type': 'application/x-www-form-urlencoded'
    };
  }

  async postRoomMessage(roomId, bodyParams) {
    if (!roomId) {
      throw new ValidationError('roomId が指定されていません。設定の defaultRoomId を確認してください。');
    }
    const url = `${this.baseUrl}/rooms/${encodeURIComponent(roomId)}/messages`;
    const form = new URLSearchParams(bodyParams);

    const response = await this.fetchImpl(url, {
      method: 'POST',
      headers: this.buildHeaders(),
      body: form,
    });

    const text = await response.text();
    let json;
    try {
      json = text ? JSON.parse(text) : {};
    } catch (error) {
      throw new ChartworkAPIError(
        `Chartwork API のレスポンスを JSON として解釈できませんでした: ${error.message}`,
        response.status,
        text
      );
    }

    if (response.status === 401) {
      throw new AuthenticationError('Chartwork API トークンが不正です。', response.status, json);
    }

    if (!response.ok) {
      throw new ChartworkAPIError(`Chartwork API へのリクエストが失敗しました (status=${response.status})`, response.status, json);
    }

    return json;
  }
}

function buildMessagePayload({ message, selfMention, linkUrls, accountId }) {
  if (!message) {
    throw new ValidationError('message は必須です。');
  }
  let body = message.trim();

  if (linkUrls) {
    body = `+${body}`;
  }

  if (selfMention && accountId) {
    body = `[To:${accountId}] ${body}`;
  }

  return { body };
}

async function postRoomMessageAction({ settings = {}, inputs = {}, logger = console, fetchImpl }) {
  const { apiToken, baseUrl, defaultRoomId, accountId } = settings;
  const roomId = inputs.roomId || defaultRoomId;
  const { message, selfMention = false, linkUrls = false } = inputs;

  logger.debug?.('[chartwork] postRoomMessage - preparing request', {
    roomId,
    messageLength: typeof message === 'string' ? message.length : undefined,
    selfMention,
    linkUrls,
  });

  const client = new ChartworkClient({ apiToken, baseUrl, fetchImpl });
  const payload = buildMessagePayload({ message, selfMention, linkUrls, accountId });

  const result = await client.postRoomMessage(roomId, payload);

  const normalized = {
    messageId: result.message_id ?? result.messageId ?? null,
    roomId: roomId,
    postedAt: result.send_time ? new Date(result.send_time * 1000).toISOString() : null,
    raw: result,
  };

  logger.debug?.('[chartwork] postRoomMessage - completed', {
    messageId: normalized.messageId,
    roomId: normalized.roomId,
  });

  return normalized;
}

module.exports = {
  manifest,
  actions: {
    postRoomMessage: postRoomMessageAction,
  },
  errors: {
    ValidationError,
    AuthenticationError,
    ChartworkAPIError,
  },
  utils: {
    ChartworkClient,
    buildMessagePayload,
  },
};
