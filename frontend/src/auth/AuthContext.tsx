import React, { createContext, useContext, useEffect, useState } from 'react';
import { setUnauthorizedHandler } from '@/api/client';
import type { User } from '@/api/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signOut: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  signOut: () => {},
});

function hasCsrfCookie(): boolean {
  return document.cookie.includes('csrf_token=');
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const signOut = () => {
    fetch('/auth/logout', { method: 'POST', credentials: 'include' })
      .then(res => {
        // Backend redirects to Cognito logout — follow the redirect
        if (res.redirected) window.location.href = res.url;
        else window.location.href = '/signin';
      })
      .catch(() => { window.location.href = '/signin'; });
    setUser(null);
  };

  useEffect(() => {
    setUnauthorizedHandler(signOut);

    if (!hasCsrfCookie()) {
      setIsLoading(false);
      return;
    }

    fetch('/auth/me', { credentials: 'include' })
      .then(res => (res.ok ? res.json() : Promise.reject()))
      .then((data: User) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: hasCsrfCookie(), isLoading, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  return useContext(AuthContext);
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCurrentUser(): User | null {
  return useContext(AuthContext).user;
}
