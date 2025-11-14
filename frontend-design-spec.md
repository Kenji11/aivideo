# Frontend Design Specification

## Overview
Clean, single-page video creation interface inspired by modern AI chat applications.

---

## Layout Structure

### 1. Top Header (Fixed)
```
┌────────────────────────────────────────────────────┐
│ 🎬 VideoAI Studio              My Projects        │
└────────────────────────────────────────────────────┘
```

**Components:**
- Left: Logo + Brand name "VideoAI Studio"
- Right: "My Projects" navigation link

**Styling:**
- Clean, minimal header
- Fixed position at top
- White background with subtle border

---

### 2. Main Content Area

#### Title Section
```
Create Your Video
Describe your vision and let AI bring it to life, or choose a template to get started
```

**Components:**
- H1: "Create Your Video"
- Subtitle: Descriptive text about the process

---

#### Form Fields

**1. Project Title**
- Label: "Project Title"
- Input: Text field
- Placeholder: "E.g., Summer Travel Vlog"
- Required field

**2. Description (Optional)**
- Label: "Description (optional)"
- Input: Textarea
- Placeholder: "Add more context about your project..."
- Optional field
- Multi-line input

**3. What would you like to create?**
- Label: "What would you like to create?"
- Input: Large textarea
- Placeholder: "Describe your video in detail. E.g., Create a promotional video about sustainable living with nature scenes, uplifting music, and inspirational quotes..."
- Main prompt input field
- This is where users describe their video requirements

---

#### Reference Materials Section

**Design Pattern: AI Chat Style (Small, Compact)**

```
┌──────────────────────────────────────────────┐
│              Reference Materials              │
│                                              │
│              ⬆️  Upload Icon                 │
│        Drag & drop or click to upload        │
│   Images, videos, or PDFs to guide the AI   │
│                                              │
│  ⚠️ For best results, upload clear,         │
│     high-quality reference materials         │
└──────────────────────────────────────────────┘
```

**Key Features:**
- **Compact size** (not taking up too much space)
- Drag & drop functionality
- Click to browse files
- Support: Images, videos, PDFs
- After upload: Show **small thumbnails** like AI chat applications
  - Small preview images (e.g., 80x80px or 100x100px)
  - File name below thumbnail
  - Remove button (X) on hover
  - Copy option available
- Multiple file support

**Interaction States:**
- Default: Dashed border, upload icon
- Hover: Highlighted border
- Drag over: Blue highlight
- After upload: Show compact thumbnail grid

**Example After Upload:**
```
Reference Materials
┌────┐ ┌────┐ ┌────┐
│img1│ │img2│ │ +  │  ← Add more
└────┘ └────┘ └────┘
logo.png product.jpg
```

---

#### Submit Button

```
┌────────────────────────────────────────────────┐
│           ✨ Start Creating                    │
└────────────────────────────────────────────────┘
```

**Properties:**
- Full width button
- Primary blue/accent color
- Disabled state when form invalid
- Loading state with spinner when generating

---

## Component Breakdown (React)

### File Structure
```
frontend/src/features/generate/
├── GeneratePage.tsx           # Main page wrapper
├── GenerateForm.tsx           # Main form component
├── FormHeader.tsx             # Title and subtitle
├── ProjectInfoSection.tsx     # Title + Description fields
├── PromptInput.tsx            # "What would you like to create?" field
├── CompactFileUpload.tsx      # ⭐ AI-chat-style file upload
│   ├── DropZone.tsx           # Drag & drop area
│   ├── FileThumbnail.tsx      # Small thumbnail component
│   └── FilePreviewGrid.tsx    # Grid of uploaded files
└── SubmitButton.tsx           # Start Creating button
```

### Key Components

#### 1. GeneratePage.tsx
```tsx
export default function GeneratePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <GenerateForm />
      </main>
    </div>
  );
}
```

#### 2. GenerateForm.tsx
```tsx
export function GenerateForm() {
  const [projectTitle, setProjectTitle] = useState('');
  const [description, setDescription] = useState('');
  const [prompt, setPrompt] = useState('');
  const [files, setFiles] = useState<File[]>([]);

  return (
    <div className="bg-white rounded-lg shadow-sm p-8">
      <FormHeader />
      <ProjectInfoSection 
        title={projectTitle}
        description={description}
        onTitleChange={setProjectTitle}
        onDescriptionChange={setDescription}
      />
      <PromptInput value={prompt} onChange={setPrompt} />
      <CompactFileUpload files={files} onChange={setFiles} />
      <SubmitButton 
        disabled={!projectTitle || !prompt}
        loading={isGenerating}
      />
    </div>
  );
}
```

#### 3. CompactFileUpload.tsx (AI Chat Style)
```tsx
interface CompactFileUploadProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export function CompactFileUpload({ files, onChange }: CompactFileUploadProps) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Reference Materials
      </label>
      
      {/* Upload Area - Compact when empty */}
      {files.length === 0 ? (
        <DropZone onFilesAdded={onChange} />
      ) : (
        <FilePreviewGrid files={files} onRemove={handleRemove} />
      )}
      
      {/* Warning message */}
      <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 p-3 rounded">
        <AlertCircle className="h-4 w-4" />
        <span>For best results, upload clear, high-quality reference materials</span>
      </div>
    </div>
  );
}
```

#### 4. FilePreviewGrid.tsx (Small Thumbnails)
```tsx
export function FilePreviewGrid({ files, onRemove }: FilePreviewGridProps) {
  return (
    <div className="space-y-3">
      {/* Small thumbnail grid */}
      <div className="flex flex-wrap gap-3">
        {files.map((file, index) => (
          <FileThumbnail 
            key={index}
            file={file}
            onRemove={() => onRemove(index)}
          />
        ))}
        {/* Add more button */}
        <button className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400">
          <Plus className="mx-auto" />
        </button>
      </div>
    </div>
  );
}
```

#### 5. FileThumbnail.tsx (Small Preview)
```tsx
export function FileThumbnail({ file, onRemove }: FileThumbnailProps) {
  const [preview, setPreview] = useState<string>('');
  
  return (
    <div className="relative group w-20">
      {/* Small thumbnail - 80x80px */}
      <div className="w-20 h-20 border border-gray-200 rounded-lg overflow-hidden">
        <img 
          src={preview} 
          alt={file.name}
          className="w-full h-full object-cover"
        />
      </div>
      
      {/* Remove button on hover */}
      <button
        onClick={onRemove}
        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100"
      >
        <X className="h-3 w-3" />
      </button>
      
      {/* Filename below */}
      <p className="text-xs text-gray-600 mt-1 truncate">
        {file.name}
      </p>
    </div>
  );
}
```

---

## Design Principles

### 1. Simplicity
- Clean, uncluttered interface
- Focus on the prompt input
- Minimal distractions

### 2. AI Chat Inspired
- **Compact file uploads** (not large drop zones)
- Small thumbnail previews
- Easy copy/paste from clipboard
- Similar to ChatGPT, Claude, etc.

### 3. Progressive Disclosure
- Only show what's necessary
- Optional fields clearly marked
- Upload area compact until files added

### 4. Responsive
- Mobile-friendly
- Adapts to different screen sizes
- Touch-friendly targets

---

## Color Palette

- **Primary**: Blue (#3B82F6) - Buttons, links
- **Background**: Light gray (#F9FAFB) - Page background
- **Surface**: White (#FFFFFF) - Form container
- **Text**: Dark gray (#111827) - Primary text
- **Muted**: Gray (#6B7280) - Secondary text
- **Border**: Light gray (#E5E7EB) - Borders, dividers
- **Warning**: Amber (#F59E0B) - Info messages

---

## Spacing & Typography

### Spacing
- Container padding: 32px (2rem)
- Section gaps: 24px (1.5rem)
- Input padding: 12px (0.75rem)
- Button padding: 16px vertical (1rem)

### Typography
- H1 (Page title): 30px, Bold
- H2 (Section labels): 14px, Medium
- Body (Inputs): 16px, Regular
- Caption (Helper text): 14px, Regular

---

## Notes for Implementation

1. **Template Selector**: Not visible in this design
   - Could be added as tabs above the form
   - Or as dropdown in project info section
   - Or remove entirely and let AI choose based on prompt

2. **File Upload**: Critical feature
   - Must support drag & drop
   - Must support clipboard paste
   - Show **small** thumbnails (80-100px)
   - Not full-width previews

3. **Validation**:
   - Project title: Required
   - Prompt: Required
   - Description: Optional
   - Files: Optional

4. **Loading States**:
   - Disable button during generation
   - Show spinner in button
   - Redirect to progress page after submit

---

## User Flow

```
1. User lands on page
   ↓
2. Fills in project title (required)
   ↓
3. Optionally adds description
   ↓
4. Writes detailed prompt (required)
   ↓
5. Optionally uploads reference materials (small thumbnails)
   ↓
6. Clicks "Start Creating"
   ↓
7. Redirects to progress page (Person B's feature)
```

---

## Differences from Original PRD

### Original Plan:
- GenerateForm with template selector
- Asset uploader as separate component

### New Design:
- **Simpler**: No visible template selector
- **Cleaner**: Compact file upload (AI chat style)
- **Focused**: Main emphasis on the prompt field
- Let AI choose template based on prompt analysis

### Recommendation:
✅ Use this new design - it's cleaner and more user-friendly
✅ Move template selection to backend (Phase 1 determines template from prompt)
✅ Keep file upload small and compact

