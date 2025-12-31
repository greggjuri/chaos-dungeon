/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark fantasy theme colors
        dungeon: {
          50: '#f8f6f4',
          100: '#e8e4df',
          200: '#d4ccc3',
          300: '#b8ab9c',
          400: '#9a8774',
          500: '#7d6a56',
          600: '#665545',
          700: '#534539',
          800: '#463a32',
          900: '#3d332d',
          950: '#211b17',
        },
      },
      fontFamily: {
        fantasy: ['Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};
