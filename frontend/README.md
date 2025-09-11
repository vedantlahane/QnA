# QnA Frontend

A modern React-based frontend for the AI-Powered Document Q&A System.

## 🚀 Features

- **React 19** with TypeScript for type safety
- **Vite** for fast development and building
- **Modern UI** with responsive design
- **Real-time chat interface** for document Q&A
- **File upload** with drag-and-drop support
- **Authentication** with login/register flows

## 🛠️ Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **ESLint** - Code linting
- **Tailwind CSS** - Styling (if configured)

## 📦 Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Build for production:**
   ```bash
   npm run build
   ```

5. **Preview production build:**
   ```bash
   npm run preview
   ```

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build

## 🌐 Development

The development server will start on `http://localhost:5173` by default.

### Project Structure

```
frontend/
├── public/           # Static assets
├── src/             # Source code
│   ├── components/  # React components
│   ├── pages/       # Page components
│   ├── hooks/       # Custom hooks
│   ├── utils/       # Utility functions
│   └── types/       # TypeScript types
├── index.html       # Main HTML file
├── package.json     # Dependencies and scripts
├── tsconfig.json    # TypeScript configuration
├── vite.config.ts   # Vite configuration
└── eslint.config.js # ESLint configuration
```

## 🔗 Backend Integration

This frontend communicates with the Django backend API. Make sure the backend is running on the configured API endpoint.

## 📝 Environment Variables

Create a `.env` file in the frontend root if needed:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## 🤝 Contributing

1. Follow the existing code style
2. Run `npm run lint` before committing
3. Test your changes thoroughly
4. Update documentation as needed

## 📄 License

This project is part of the QnA system. See main project license for details.
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
