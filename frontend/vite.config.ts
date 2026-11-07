import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import {loadEnv} from 'vite';
const env=loadEnv(process.env.NODE_ENV || 'development','..','');
const target=process.env.API_PROXY_TARGET || env.API_PROXY_TARGET || 'http://127.0.0.1:8000';
export default defineConfig({plugins:[react()],envDir:'..',server:{host:'0.0.0.0',port:5173,strictPort:true,allowedHosts:true,proxy:{'/api':{target,ws:true},'/docs':{target},'/openapi.json':{target}}},build:{rollupOptions:{output:{manualChunks:{charts:['recharts']}}}},preview:{host:'0.0.0.0',allowedHosts:true},test:{environment:'jsdom',setupFiles:'./src/test-setup.ts',css:true}});
