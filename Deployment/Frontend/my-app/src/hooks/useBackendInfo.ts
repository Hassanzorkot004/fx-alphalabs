import { useState, useEffect } from 'react';
import { API_URL } from '../config/constants';

interface BackendInfo {
  model: string;
  interval: number;
  version: string;
  status: string;
}

export function useBackendInfo() {
  const [info, setInfo] = useState<BackendInfo | null>(null);
  
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(res => res.json())
      .then(data => {
        setInfo({
          model: data.model || 'llama-3.1-70b',
          interval: data.run_every_mins || 60,
          version: data.version || '2.0',
          status: data.status || 'unknown'
        });
      })
      .catch(err => console.error('Failed to fetch backend info:', err));
  }, []);
  
  return info;
}
