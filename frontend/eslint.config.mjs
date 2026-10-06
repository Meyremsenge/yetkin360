import coreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

// Next.js 16/eslint-config-next 16: FlatCompat (eski extends-köprüsü) artık
// eslint-plugin-react'in döngüsel referansları yüzünden "Converting circular
// structure to JSON" ile çöküyor — native flat-config export'ları doğrudan
// kullanılır (next'in kendi upgrade codemod'unun yaptığı düzeltme).
const eslintConfig = [
  { ignores: [".next/**", "node_modules/**"] },
  ...coreWebVitals,
  ...nextTypescript,
];

export default eslintConfig;
