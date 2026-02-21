import React, { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(() => localStorage.getItem('athena_client_token'));
    const [user, setUser] = useState(() => {
        const u = localStorage.getItem('athena_client_user');
        return u ? JSON.parse(u) : null;
    });

    const login = useCallback((jwt, userData) => {
        localStorage.setItem('athena_client_token', jwt);
        localStorage.setItem('athena_client_user', JSON.stringify(userData));
        setToken(jwt); setUser(userData);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('athena_client_token');
        localStorage.removeItem('athena_client_user');
        setToken(null); setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
