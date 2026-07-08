import { create } from "zustand";

interface User {
  user_id: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  company_id: string;
  role: string;
  department?: string;
  designation?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  initialized: boolean;

  login: (token: string, user: User) => void;
  logout: () => void;
  loadUser: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,

  user: null,

  isAuthenticated: false,
  initialized: false,

  login: (token, user) => {
    localStorage.setItem("token", token);

    localStorage.setItem(
      "user",
      JSON.stringify(user)
    );

    set({
    token,
    user,
    isAuthenticated: true,
    initialized: true,
    });
  },

  logout: () => {
    localStorage.removeItem("token");

    localStorage.removeItem("user");

    set({
    token: null,
    user: null,
    isAuthenticated: false,
    initialized: true,
    });
  },

    loadUser: () => {

    const token = localStorage.getItem("token");
    const user = localStorage.getItem("user");

    if (!token || !user) {

        set({
        initialized: true,
        });

        return;
    }

    set({
        token,
        user: JSON.parse(user),
        isAuthenticated: true,
        initialized: true,
    });

    },
}));