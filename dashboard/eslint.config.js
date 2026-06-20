// Minimal ESLint config for ESLint v10 (flat config format)
export default [
  {
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error",
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    files: ["**/*.{js,jsx,ts,tsx}"],
  },
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "next.config.js",
      "postcss.config.js",
      "tailwind.config.ts",
    ],
  },
];
