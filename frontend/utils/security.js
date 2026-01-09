const CSRF_SECRET = process.env.CSRF_SECRET || 'default-csrf-secret-key';
const TOKEN_LIFETIME = 3600; // 1시간

// 브라우저 호환 랜덤 바이트 생성
function randomBytes(length) {
  const array = new Uint8Array(length);
  if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
    window.crypto.getRandomValues(array);
  } else {
    // 폴백: Math.random 사용 (보안 수준 낮음)
    for (let i = 0; i < length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('');
}

// 브라우저 호환 HMAC 생성 (Web Crypto API 사용)
async function createHmacSha256(data, secret) {
  // 서버 사이드 (Node.js 환경)
  if (typeof window === 'undefined') {
    // Next.js API 라우트나 서버 사이드에서는 require 사용
    let crypto;
    try {
      crypto = require('crypto');
    } catch (e) {
      // require가 실패하면 동적 import 시도
      const cryptoModule = await import('crypto');
      crypto = cryptoModule.default || cryptoModule;
    }
    return crypto.createHmac('sha256', secret).update(data).digest('hex');
  }
  
  // 클라이언트 사이드 (브라우저 환경)
  if (window.crypto && window.crypto.subtle) {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(secret);
    const messageData = encoder.encode(data);
    
    const key = await window.crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const signature = await window.crypto.subtle.sign('HMAC', key, messageData);
    const hashArray = Array.from(new Uint8Array(signature));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
  
  throw new Error('Crypto API not available');
}

// 타임 세이프 비교
function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

export async function generateCSRFToken(userId = null) {
  const timestamp = Math.floor(Date.now() / 1000);
  const randomValue = randomBytes(32);
  const userPart = userId ? String(userId) : 'anonymous';
  
  const tokenData = `${timestamp}:${userPart}:${randomValue}`;
  const signature = await createHmacSha256(tokenData, CSRF_SECRET);
  
  return `${tokenData}:${signature}`;
}

export async function validateCSRFToken(token, userId = null) {
  if (!token) return false;
  
  try {
    const parts = token.split(':');
    if (parts.length !== 4) return false;
    
    const [timestamp, userPart, randomValue, signature] = parts;
    
    // 시간 검증
    const now = Math.floor(Date.now() / 1000);
    if (now - parseInt(timestamp) > TOKEN_LIFETIME) return false;
    
    // 사용자 검증
    const expectedUser = userId ? String(userId) : 'anonymous';
    if (userPart !== expectedUser) return false;
    
    // 서명 검증
    const tokenData = `${timestamp}:${userPart}:${randomValue}`;
    const expectedSignature = await createHmacSha256(tokenData, CSRF_SECRET);
    
    return timingSafeEqual(signature, expectedSignature);
  } catch {
    return false;
  }
}

export function sanitizeInput(input) {
  if (typeof input !== 'string') return input;
  
  return input
    .replace(/[<>]/g, '') // XSS 방지
    .trim()
    .substring(0, 1000); // 길이 제한
}

export function validatePortfolioInput(data) {
  const errors = [];
  
  if (!data.ticker || typeof data.ticker !== 'string') {
    errors.push('유효한 종목 코드가 필요합니다');
  }
  
  if (!data.name || typeof data.name !== 'string') {
    errors.push('유효한 종목명이 필요합니다');
  }
  
  if (data.entry_price && (isNaN(data.entry_price) || data.entry_price < 0)) {
    errors.push('유효한 매수가가 필요합니다');
  }
  
  if (data.quantity && (isNaN(data.quantity) || data.quantity <= 0)) {
    errors.push('유효한 수량이 필요합니다');
  }
  
  return errors;
}