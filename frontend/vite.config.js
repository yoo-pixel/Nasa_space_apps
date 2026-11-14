import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: { port: 5173 },
    build: {
        rolldownOptions: {
            output: {
                codeSplitting: {
                    groups: [
                        { name: "react", test: new RegExp("node_modules/(?:react|react-dom|react-router|react-router-dom|@tanstack)/"), priority: 30 },
                        { name: "charts", test: new RegExp("node_modules/(?:recharts|d3-[^/]+)/"), priority: 20 },
                        { name: "icons", test: new RegExp("node_modules/lucide-react/"), priority: 10 },
                        { name: "http", test: new RegExp("node_modules/axios/"), priority: 10 },
                    ],
                },
            },
        },
    },
});
