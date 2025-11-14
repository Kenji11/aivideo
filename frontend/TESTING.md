# 🎬 VideoAI Studio Frontend - Local Testing Guide

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

Or use the setup script:
```bash
cd frontend
./setup.sh
```

### 2. Start Development Server
```bash
npm run dev
```

The app will automatically open at **http://localhost:5173**

---

## Features to Test

### ✅ Dark/Light Mode
- Look for the sun/moon icon in the top-right header
- Click to toggle between dark and light modes
- Should have smooth transitions
- Preference is saved in localStorage (refresh page to verify)

### ✅ Form Fields
- **Project Title**: Required field
- **Description**: Optional textarea
- **Prompt**: Required large textarea for video description

### ✅ Compact File Upload (AI Chat Style!)
- **Before upload**: Shows dashed border drop zone
- **Drag & Drop**: Drag images/videos/PDFs
- **Click to upload**: Click the drop zone
- **After upload**: Shows small thumbnails (80x80px) in a grid
- **Hover thumbnails**: Red X button appears to remove
- **Add more**: Click the "+" button to add more files
- **Supported**: Images, videos, PDFs

### ✅ Submit Button
- Disabled when form invalid (no title or prompt)
- Shows loading spinner when clicked
- Blue primary color

### ✅ Responsive Design
- Try resizing the browser window
- Should work on mobile sizes

---

## What's Included

### Components
- `Header` - Top navigation with dark mode toggle
- `GenerateForm` - Main form container
- `FormHeader` - Page title and subtitle
- `ProjectInfoSection` - Title and description inputs
- `PromptInput` - Main prompt textarea
- `CompactFileUpload` - AI-chat-style file upload
- `DropZone` - Drag & drop area
- `FilePreviewGrid` - Grid of thumbnails
- `FileThumbnail` - Individual file preview (80x80px)
- `SubmitButton` - Submit with loading state

### Features
- ✅ Dark/Light mode with localStorage persistence
- ✅ Smooth color transitions
- ✅ Compact file thumbnails (like ChatGPT/Claude)
- ✅ Drag & drop support
- ✅ File type icons (image, video, PDF)
- ✅ Hover effects and animations
- ✅ Form validation
- ✅ Responsive design
- ✅ TypeScript for type safety
- ✅ Tailwind CSS for styling

---

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Beautiful icons
- **Dark Mode** - Class-based with smooth transitions

---

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Header.tsx              # 🌙 With dark mode toggle
│   ├── features/generate/
│   │   ├── GeneratePage.tsx
│   │   ├── GenerateForm.tsx
│   │   ├── FormHeader.tsx
│   │   ├── ProjectInfoSection.tsx
│   │   ├── PromptInput.tsx
│   │   ├── CompactFileUpload.tsx   # ⭐ AI chat style!
│   │   ├── DropZone.tsx
│   │   ├── FilePreviewGrid.tsx
│   │   ├── FileThumbnail.tsx       # Small 80x80px previews
│   │   └── SubmitButton.tsx
│   ├── hooks/
│   │   └── useDarkMode.ts          # Custom dark mode hook
│   ├── shared/
│   │   ├── lib/utils.ts
│   │   └── types/index.ts
│   ├── styles/
│   │   └── globals.css             # Tailwind + custom styles
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

---

## Troubleshooting

### Port Already in Use
If port 5173 is busy:
```bash
npm run dev -- --port 3000
```

### Dependencies Not Installing
Try:
```bash
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Errors
Make sure you're using Node 18+:
```bash
node --version
```

---

## Next Steps After Testing

1. ✅ Verify dark mode works
2. ✅ Test file upload with drag & drop
3. ✅ Check responsive design on mobile
4. ✅ Verify form validation works
5. 📸 Take screenshots if needed
6. 🚀 Ready for backend integration!

---

## Notes

- Backend API not connected yet (that's Day 1 work!)
- Submit button currently shows alert (placeholder)
- File uploads stored in state only (not sent to server yet)
- Ready for Person A to connect to POST /api/generate endpoint

---

**Enjoy testing!** 🎉

