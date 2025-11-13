import fs from 'fs';
import path from 'path';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const filePath = path.join(process.cwd(), 'public', 'content', 'TRADING_STRATEGY_GUIDE.md');
    
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    const fileContent = fs.readFileSync(filePath, 'utf-8');
    
    res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
    res.status(200).send(fileContent);
  } catch (error) {
    console.error('가이드 파일 읽기 실패:', error);
    res.status(500).json({ error: 'Failed to load guide' });
  }
}
