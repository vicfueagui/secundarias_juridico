/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./licencias/templates/**/*.html",
    "./staticfiles/styleguide.html",
    "./staticfiles/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          700: "#5B0F28",
          600: "#701432",
          500: "#8A1B3F",
          100: "#F5EEF1",
        },
        accent: {
          600: "#9A643D",
          500: "#AC764C",
        },
        gold: {
          500: "#D6B74D",
          600: "#BFA23E",
        },
        info: {
          500: "#5792B1",
          100: "#E4F1F7",
        },
        neutral: {
          900: "#2F2F2F",
          800: "#414141",
          700: "#5F5F5E",
          600: "#777879",
          500: "#96989B",
          400: "#CACBCE",
          200: "#E4E6E8",
          150: "#EEF0F2",
          100: "#F7F8F9",
        },
        success: {
          500: "#2E7D54",
          100: "#E3F3EB",
        },
        warning: {
          500: "#B57F2E",
          100: "#F7F0E1",
        },
        error: {
          500: "#B22E3A",
          100: "#F9E4E6",
        },
      },
      fontFamily: {
        display: ["Montserrat", "Montserrat Alternates", "Raleway", "sans-serif"],
        base: ["Source Sans 3", "Inter", "Source Sans Pro", "sans-serif"],
      },
      borderRadius: {
        xs: "4px",
        sm: "8px",
        md: "12px",
        lg: "16px",
        pill: "9999px",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(0, 0, 0, 0.06)",
        md: "0 4px 12px rgba(0, 0, 0, 0.08)",
      },
      spacing: {
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "24px",
        6: "32px",
        7: "48px",
        8: "64px",
      },
      maxWidth: {
        container: "1200px",
      },
    },
  },
  plugins: [],
};
