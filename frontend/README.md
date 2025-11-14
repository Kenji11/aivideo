# VideoAI Studio - Frontend

React + TypeScript + Vite + Tailwind CSS frontend for AI video generation.

## Features

- 🎨 Clean, modern UI design
- 🌓 Dark/Light mode with smooth transitions
- 📁 AI-chat-style compact file upload
- 📱 Fully responsive
- ⚡ Fast development with Vite
- 🎯 TypeScript for type safety

## Getting Started

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will open at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/          # Shared components (Header)
├── features/
│   └── generate/       # Video generation feature
│       ├── GeneratePage.tsx
│       ├── GenerateForm.tsx
│       ├── CompactFileUpload.tsx
│       └── ...
├── hooks/              # Custom hooks (useDarkMode)
├── shared/
│   ├── components/ui/  # UI components (shadcn)
│   ├── lib/            # Utilities
│   └── types/          # TypeScript types
├── styles/             # Global styles
└── App.tsx             # Root component
```

## Dark Mode

Dark mode is implemented using Tailwind CSS's class-based dark mode and persists user preference in localStorage.

Toggle is in the top-right header.

## Technologies

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Lucide React (icons)

