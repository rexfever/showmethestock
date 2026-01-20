import { validateCSRFToken, sanitizeInput, validatePortfolioInput } from '../../../utils/security';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    // CSRF 토큰 검증
    const csrfToken = req.headers['x-csrf-token'];
    if (!(await validateCSRFToken(csrfToken))) {
      return res.status(403).json({ message: 'CSRF token validation failed' });
    }
    
    // 입력 검증
    const validationErrors = validatePortfolioInput(req.body);
    if (validationErrors.length > 0) {
      return res.status(400).json({ message: validationErrors.join(', ') });
    }
    
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ message: '토큰이 필요합니다' });
    }
    
    // 입력 데이터 정제
    const sanitizedBody = {
      ...req.body,
      ticker: sanitizeInput(req.body.ticker),
      name: sanitizeInput(req.body.name)
    };

    const response = await fetch('http://localhost:8010/portfolio/add', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(sanitizedBody)
    });

    const data = await response.json();

    if (response.ok) {
      res.status(200).json(data);
    } else {
      res.status(response.status).json(data);
    }
  } catch (error) {
    console.error('포트폴리오 추가 오류:', error);
    res.status(500).json({ message: '서버 오류가 발생했습니다' });
  }
}
