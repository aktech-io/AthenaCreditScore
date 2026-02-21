import React, { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(() => localStorage.getItem('athena_token'));
    const [user, setUser] = useState(() => {
        const u = localStorage.getItem('athena_user');
        return u ? JSON.parse(u) : null;
    });

    const login = useCallback((jwt, userData) => {
        localStorage.setItem('athena_token', jwt);
        localStorage.setItem('athena_user', JSON.stringify(userData));
        setToken(jwt);
        setUser(userData);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('athena_token');
        localStorage.removeItem('athena_user');
        setToken(null);
        setUser(null);
    }, []);

    const isAuthenticated = !!token;

    return (
        <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
