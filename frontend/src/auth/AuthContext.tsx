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
    fetch('/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    setUser(null);
    window.location.href = '/signin';
  };

  useEffect(() => {
    setUnauthorizedHandler(signOut);

    if (!hasCsrfCookie()) {
      setIsLoading(false);
      return;
    }

    // Session exists — could fetch /auth/me here; for now derive from cookie presence
    setIsLoading(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: hasCsrfCookie(), isLoading, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export function useCurrentUser(): User | null {
  return useContext(AuthContext).user;
}
