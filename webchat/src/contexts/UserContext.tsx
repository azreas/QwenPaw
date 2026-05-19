import React, { createContext, useContext, useState, useCallback } from "react";

interface UserInfo {
  userId: string;
  username: string;
  agentId: string;
}

interface UserContextType {
  user: UserInfo | null;
  setUser: (user: UserInfo | null) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<UserInfo | null>(() => {
    const userId = localStorage.getItem("webchat_user_id");
    const username = localStorage.getItem("webchat_username");
    const agentId = localStorage.getItem("webchat_agent_id");
    if (userId && username) {
      return { userId, username, agentId: agentId || "default" };
    }
    return null;
  });

  const setUser = useCallback((user: UserInfo | null) => {
    setUserState(user);
    if (user) {
      localStorage.setItem("webchat_user_id", user.userId);
      localStorage.setItem("webchat_username", user.username);
      localStorage.setItem("webchat_agent_id", user.agentId);
    } else {
      localStorage.removeItem("webchat_user_id");
      localStorage.removeItem("webchat_username");
      localStorage.removeItem("webchat_agent_id");
    }
  }, []);

  const logout = useCallback(() => {
    setUserState(null);
    localStorage.removeItem("webchat_token");
    localStorage.removeItem("webchat_user_id");
    localStorage.removeItem("webchat_username");
    localStorage.removeItem("webchat_agent_id");
  }, []);

  return (
    <UserContext.Provider value={{ user, setUser, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
