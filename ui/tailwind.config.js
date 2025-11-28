/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Medical/healthcare theme
        primary: {
          50: '#F0F7FF',
          100: '#E0EFFF',
          200: '#B8DBFF',
          300: '#8AC4FF',
          400: '#5AABFF',
          500: '#4A90E2',
          600: '#3B73B5',
          700: '#2C5688',
          800: '#1D395B',
          900: '#0E1C2E',
        },
        secondary: {
          50: '#F0FDF9',
          100: '#CCFBEF',
          200: '#99F6DF',
          300: '#7ED9C3',
          400: '#5EC9AD',
          500: '#3EB897',
          600: '#2E9478',
          700: '#1F705A',
          800: '#104C3B',
          900: '#00281D',
        },
        success: '#2ECC71',
        warning: '#F1C40F',
        error: '#E74C3C',
      },
      spacing: {
        'panel': '400px',
        'topbar': '64px',
      },
      animation: {
        'pulse-listening': 'pulse-listening 1.5s ease-in-out infinite',
        'pulse-recording': 'pulse-recording 1s ease-in-out infinite',
        'bounce-gentle': 'bounce-gentle 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
      },
      keyframes: {
        'pulse-listening': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
        'pulse-recording': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'bounce-gentle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(74, 144, 226, 0.15)',
        'glow': '0 0 20px rgba(74, 144, 226, 0.3)',
        'card': '0 4px 12px rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '24px',
      },
    },
  },
  plugins: [],
}
