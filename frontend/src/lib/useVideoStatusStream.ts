import { useState, useEffect, useRef } from 'react';
import { StatusResponse } from './api';
import { getVideoStatus } from './api';
import { getIdToken } from './firebase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseVideoStatusStreamResult {
  status: StatusResponse | null;
  error: Error | null;
  isConnected: boolean;
}

/**
 * Custom hook for real-time video status updates using Server-Sent Events (SSE)
 * Automatically falls back to polling if SSE fails
 */
export function useVideoStatusStream(
  videoId: string | null,
  enabled: boolean = true
): UseVideoStatusStreamResult {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [usePolling, setUsePolling] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);
  const usePollingRef = useRef(false); // Track polling state to prevent infinite loops

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!videoId || !enabled) {
      // Cleanup
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      setIsConnected(false);
      usePollingRef.current = false;
      return;
    }

    // Try SSE first (unless we've already determined polling is needed)
    if (!usePollingRef.current && !usePolling) {
      const connectSSE = async () => {
        try {
          // Get auth token for SSE connection
          const token = await getIdToken();
          if (!token) {
            usePollingRef.current = true;
            setUsePolling(true);
            return;
          }

          // Build SSE URL with auth token as query parameter
          // Note: EventSource doesn't support custom headers, so we pass token as query param
          const sseUrl = `${API_URL}/api/status/${videoId}/stream?token=${encodeURIComponent(token)}`;
          
          // Create EventSource
          const eventSource = new EventSource(sseUrl);
          eventSourceRef.current = eventSource;

          eventSource.onopen = () => {
            setIsConnected(true);
            setError(null);
          };

          eventSource.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data) as StatusResponse;
              // Removed excessive console.log for performance
              if (isMountedRef.current) {
                setStatus(data);
                setError(null);
              }
            } catch (err) {
              console.error('[SSE] Failed to parse message:', err);
              setError(err instanceof Error ? err : new Error('Failed to parse SSE message'));
            }
          };

          eventSource.addEventListener('close', () => {
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            setIsConnected(false);
          });

          eventSource.addEventListener('error', (event: MessageEvent) => {
            console.error('[SSE] Error event:', event);
            const errorData = event.data ? JSON.parse(event.data) : {};
            if (errorData.error) {
              console.error('[SSE] Server error:', errorData.error);
            }
            // Fallback to polling on any error
            eventSource.close();
            setIsConnected(false);
            usePollingRef.current = true;
            setUsePolling(true);
          });

          eventSource.onerror = () => {
            // If SSE fails (connection error, auth failure, etc.), fallback to polling
            if (eventSource.readyState === EventSource.CLOSED) {
              setIsConnected(false);
              usePollingRef.current = true;
              setUsePolling(true);
            } else if (eventSource.readyState === EventSource.CONNECTING) {
              // Still connecting, wait a bit
              setTimeout(() => {
                if (eventSource.readyState === EventSource.CLOSED) {
                  setIsConnected(false);
                  usePollingRef.current = true;
                  setUsePolling(true);
                }
              }, 2000);
            }
          };
        } catch (err) {
          console.error('[SSE] Failed to create EventSource:', err);
          setError(err instanceof Error ? err : new Error('Failed to create SSE connection'));
          usePollingRef.current = true;
          setUsePolling(true);
        }
      };

      connectSSE();
    }

    // Fallback to polling if SSE failed or is disabled
    if (usePollingRef.current || usePolling) {
      // Prevent duplicate polling connections
      if (pollingIntervalRef.current) {
        return;
      }
      
      const pollStatus = async () => {
        try {
          const statusData = await getVideoStatus(videoId);
          // Removed excessive console.log for performance
          if (isMountedRef.current) {
            setStatus(statusData);
            setError(null);
          }
        } catch (err) {
          console.error('[Polling] Failed to poll status:', err);
          if (isMountedRef.current) {
            setError(err instanceof Error ? err : new Error('Failed to poll status'));
          }
        }
      };

      // Poll immediately, then every 2-3 seconds
      pollStatus();
      pollingIntervalRef.current = setInterval(pollStatus, 2500);
      setIsConnected(false);
    }

    // Cleanup function
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      setIsConnected(false);
    };
  }, [videoId, enabled, usePolling]);

  return { status, error, isConnected };
}

