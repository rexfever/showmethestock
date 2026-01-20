import crypto from 'crypto';

const CSRF_SECRET = process.env.CSRF_SECRET || 'default-csrf-secret-key';
const TOKEN_LIFETIME = 3600; // 1시간

export function generateCSRFToken(userId = null) {
  const timestamp = Math.floor(Date.now() / 1000);
  const randomValue = crypto.randomBytes(32).toString('hex');
  const userPart = userId ? String(userId) : 'anonymous';
  
  const tokenData = `${timestamp}:${userPart}:${randomValue}`;
  const signature = crypto
    .createHmac('sha256', CSRF_SECRET)
    .update(tokenData)
    .digest('hex');
  
  return `${tokenData}:${signature}`;
}

export function validateCSRFToken(token, userId = null) {
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
    const expectedSignature = crypto
      .createHmac('sha256', CSRF_SECRET)
      .update(tokenData)
      .digest('hex');
    
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expectedSignature, 'hex')
    );
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