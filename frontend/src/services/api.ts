import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
  timeout: 12000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    return Promise.reject(new Error(typeof detail === "string" ? detail : error.message || "Could not reach the AstroGuard API."));
  },
);