/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface RuntimeEnvConfig {
  PUBLIC_API_BASE_URL?: string;
}

interface Window {
  __ENV__?: RuntimeEnvConfig;
}
