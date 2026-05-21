import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
import { viteMockServe } from 'vite-plugin-mock';
import { readFileSync } from 'fs';

const packageJson = JSON.parse(readFileSync('./package.json', 'utf8'));

export default defineConfig({
    plugins: [
        vue(),
        viteMockServe({
            mockPath: 'mock',
            enable: process.env.VITE_USE_MOCK === 'true',
        }),
    ],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },
    define: {
        'import.meta.env.APP_VERSION': JSON.stringify(packageJson.version),
    },
    server: {
        host: '0.0.0.0',
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://192.168.3.18:8000',
                changeOrigin: true,
            },
        },
    },
});
