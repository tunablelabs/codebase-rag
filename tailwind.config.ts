import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui'),],
};
export default config;


// import type { Config } from 'tailwindcss';
//
// const config: Config = {
//   content: [
//     './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
//     './src/components/**/*.{js,ts,jsx,tsx,mdx}',
//     './src/app/**/*.{js,ts,jsx,tsx,mdx}',
//   ],
//   theme: {
//     extend: {
//       colors: {
//         'output-light': '#f1f5f9', // Light mode background
//         'output-dark': '#1e293b', // Dark mode background
//         'output-light-text': '#1f2937', // Light mode text
//         'output-dark-text': '#e2e8f0', // Dark mode text
//       },
//     },
//   },
//   plugins: [require('daisyui')],
// };
// export default config;
