import { useState, useEffect, useRef, useCallback } from 'react';

type ConnectionStatus = 'Connecting' | 'Connected' | 'Disconnected';

export const useWebSocket = (
  url: string,
  onMessage: (event: MessageEvent) => void
) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('Connecting');
  const wsRef = useRef<WebSocket | null>(null);
  
  // Initialize WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;
    
    ws.onopen = () => {
      setConnectionStatus('Connected');
    };
    
    ws.onmessage = onMessage;
    
    ws.onclose = () => {
      setConnectionStatus('Disconnected');
      
      // Try to reconnect after a delay
      setTimeout(() => {
        setConnectionStatus('Connecting');
      }, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('Disconnected');
    };
    
    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [url, onMessage]);
  
  // Function to send messages through the WebSocket
  const sendMessage = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);
  
  return { sendMessage, connectionStatus };
}; 