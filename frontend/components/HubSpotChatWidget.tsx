'use client';

import * as React from 'react';
import { useAuthStore } from '@/store/use-auth-store';
import Cookies from 'js-cookie';

declare global {
  interface Window {
    HubSpotConversations?: {
      widget: {
        load: (options?: { identify?: { token: string }; widgetOpen?: boolean }) => void;
        refresh: (options?: { openToNewThread?: boolean }) => void;
        status: () => { loaded: boolean };
      };
    };
    hsConversationsSettings?: {
      loadImmediately?: boolean;
    };
    hsConversationsOnReady?: Array<() => void>;
  }
}

export function HubSpotChatWidget() {
  const { user, isAuthenticated, hydrated } = useAuthStore();

  React.useEffect(() => {
    if (!hydrated) return;

    // Prevent immediate automatic loading of the widget until identity is configured
    window.hsConversationsSettings = {
      loadImmediately: false
    };

    const loadHubSpotScript = () => {
      if (document.getElementById('hubspot-conversations-script')) return;
      
      const portalId = process.env.NEXT_PUBLIC_HUBSPOT_PORTAL_ID || '47182741'; // Configured HubSpot portal
      const script = document.createElement('script');
      script.id = 'hubspot-conversations-script';
      script.type = 'text/javascript';
      script.async = true;
      script.defer = true;
      script.src = `https://js.hs-scripts.com/${portalId}.js`;
      document.body.appendChild(script);
    };

    const initializeIdentity = async () => {
      // Retrieve JWT access token to authenticate request to visitor-token endpoint
      const accessToken = Cookies.get('access_token');
      
      if (isAuthenticated && user && accessToken) {
        try {
          const companyWidgetId = user.company?.widget_id || 'webchat_default';
          
          const response = await fetch('/api/integrations/hubspot/visitor-token', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
              widget_id: companyWidgetId,
              email: user.email,
              firstName: user.name?.split(' ')[0] || '',
              lastName: user.name?.split(' ').slice(1).join(' ') || ''
            })
          });

          if (response.ok) {
            const data = await response.json();
            if (data.token) {
              // Load widget using signed identification token
              if (window.HubSpotConversations) {
                window.HubSpotConversations.widget.load({ identify: { token: data.token } });
              } else {
                window.hsConversationsOnReady = window.hsConversationsOnReady || [];
                window.hsConversationsOnReady.push(() => {
                  window.HubSpotConversations?.widget.load({ identify: { token: data.token } });
                });
              }
              return;
            }
          }
        } catch (error) {
          console.error("Failed to authenticate visitor token with HubSpot:", error);
        }
      }

      // Fallback: load widget anonymously
      if (window.HubSpotConversations) {
        window.HubSpotConversations.widget.load();
      } else {
        window.hsConversationsOnReady = window.hsConversationsOnReady || [];
        window.hsConversationsOnReady.push(() => {
          window.HubSpotConversations?.widget.load();
        });
      }
    };

    loadHubSpotScript();
    
    if (window.HubSpotConversations) {
      initializeIdentity();
    } else {
      window.hsConversationsOnReady = window.hsConversationsOnReady || [];
      window.hsConversationsOnReady.push(initializeIdentity);
    }
  }, [user, isAuthenticated, hydrated]);

  return null;
}
