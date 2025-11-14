# VideoAI Studio - Component Index

## Directory Structure

```
src/
├── App.tsx                           # Main application component
├── main.tsx                          # React entry point
├── index.css                         # Global styles & animations
├── vite-env.d.ts                    # Vite environment types
│
├── lib/
│   └── supabase.ts                  # Supabase client & types
│
├── components/                       # Reusable UI components
│   ├── Header.tsx                   # Navigation header
│   ├── UploadZone.tsx               # File upload handler
│   ├── ProjectCard.tsx              # Gallery card component
│   ├── StepIndicator.tsx            # Progress indicator
│   ├── ProcessingSteps.tsx          # Processing status display
│   ├── TemplateGallery.tsx          # Template browser
│   ├── NotificationCenter.tsx       # Toast notifications
│   ├── ShareModal.tsx               # Share/collaboration modal
│   ├── Onboarding.tsx               # Tutorial component
│   ├── QuickActions.tsx             # Fast action buttons
│   └── VideoEditor.tsx              # Video customization
│
└── pages/                            # Full-page components
    ├── Auth.tsx                     # Login/signup page
    ├── Settings.tsx                 # User preferences
    ├── Analytics.tsx                # Analytics dashboard
    └── Templates.tsx                # Template browser page
```

## Component Details

### App.tsx (Main)
**Purpose**: Root application component with state management
**Features**:
- Authentication state management
- Navigation between pages
- Notification system integration
- Processing pipeline logic
- User session handling

**Key Functions**:
- `handleSubmit()` - Video creation initiation
- `addNotification()` - Notification dispatch
- `handleSelectTemplate()` - Template selection handler
- `getCurrentStep()` - Step progression logic

**Dependencies**: All child components, pages, and utilities

---

### Components

#### Header.tsx
**Purpose**: Navigation and branding
**Props**:
- `userName?: string` - Display user name
- `onLogout?: () => void` - Logout handler
- `onProjectsClick?: () => void` - Projects navigation

**Features**:
- Logo with branding
- "My Projects" link
- User menu with logout
- Mobile responsive hamburger menu
- Smooth animations

---

#### UploadZone.tsx
**Purpose**: File upload handler with drag-and-drop
**Props**:
- `onFilesSelected?: (files: File[]) => void` - File callback
- `disabled?: boolean` - Disable uploads

**Features**:
- Drag-and-drop file upload
- Click to browse
- File validation (images, videos, PDFs)
- File list display with size
- Remove individual files
- Info alert about best practices

---

#### ProjectCard.tsx
**Purpose**: Gallery card for project display
**Props**:
- `project: Project` - Project data
- `onSelect?: (project: Project) => void` - Selection handler
- `onDelete?: (projectId: string) => void` - Delete handler

**Features**:
- Thumbnail display with gradient
- Hover play button animation
- Status badge with color coding
- Creation date display
- Quick delete button

---

#### StepIndicator.tsx
**Purpose**: Visual progress indicator
**Props**:
- `steps: Step[]` - Step definitions
- `currentStep: number` - Current progress

**Features**:
- Circular step icons
- Animated connecting lines
- Step labels
- Color-coded completion

---

#### ProcessingSteps.tsx
**Purpose**: Real-time processing status
**Props**:
- `steps: ProcessingStep[]` - Processing steps
- `elapsedTime?: number` - Elapsed time

**Features**:
- Status icons (checkmark, spinner, alert)
- Step-by-step animation
- Elapsed time display
- Color-coded status indicators

---

#### TemplateGallery.tsx
**Purpose**: Browse and display templates
**Props**:
- `templates: Template[]` - Available templates
- `onSelect: (template: Template) => void` - Selection handler
- `isLoading?: boolean` - Loading state

**Features**:
- Grid layout (responsive)
- Hover play button effect
- Category badges
- Featured indicator
- Loading skeleton animation

---

#### NotificationCenter.tsx
**Purpose**: Toast notification system
**Props**:
- `notifications: Notification[]` - Active notifications
- `onDismiss: (id: string) => void` - Dismiss handler

**Features**:
- Auto-dismiss after 5 seconds
- Manual close button
- Icon indicators by type
- Color-coded backgrounds
- Relative time display
- Notification counter badge (NotificationBell)

---

#### ShareModal.tsx
**Purpose**: Project sharing interface
**Props**:
- `projectId: string` - Project to share
- `projectTitle: string` - Display title
- `onClose: () => void` - Close handler

**Features**:
- Copy shareable link
- Email collaborator invitations
- Permission level selection
- Added collaborators list
- Remove collaborator option

---

#### Onboarding.tsx
**Purpose**: Interactive tutorial
**Props**:
- `onComplete: () => void` - Completion handler

**Features**:
- 5-step walkthrough
- Progress bar at top
- Navigation buttons
- Visual content display
- Skip to end option

---

#### QuickActions.tsx
**Purpose**: Fast action shortcuts
**Props**:
- `onNewProject: () => void` - New project handler
- `onViewProjects: () => void` - View projects handler
- `recentProjects?: Project[]` - Recent items

**Features**:
- Create new video button
- View projects button
- Recent projects list
- Hover animations
- Icon indicators

---

#### VideoEditor.tsx
**Purpose**: Video customization interface
**Props**:
- `onSave: (settings) => void` - Save handler
- `onCancel: () => void` - Cancel handler

**Features**:
- Duration slider (15-300s)
- Volume control (0-100%)
- Background color picker
- Text size adjustment
- Music track selection
- Save/Cancel buttons

---

### Pages

#### Auth.tsx
**Purpose**: Authentication (login/signup)
**Props**:
- `onAuthSuccess: () => void` - Success handler

**Features**:
- Toggle between login/signup modes
- Email input with validation
- Password input
- Full name input (signup)
- Error messages
- Success feedback
- Terms/Privacy links

---

#### Settings.tsx
**Purpose**: User preferences and configuration
**Props**:
- `onBack: () => void` - Navigate back

**Sections**:
1. **Appearance**: Theme selection
2. **Notifications**: Push & email digest
3. **Downloads**: Auto-download, quality
4. **Performance**: Cache management
5. **Help**: Documentation, support links

---

#### Analytics.tsx
**Purpose**: Performance dashboard
**Props**:
- `onBack: () => void` - Navigate back

**Displays**:
- KPI cards (videos, views, duration, growth)
- Bar chart: Videos created
- Line chart: Views trend
- Top videos table
- Weekly statistics

---

#### Templates.tsx
**Purpose**: Template browser and selection
**Props**:
- `onBack: () => void` - Navigate back
- `onSelectTemplate: (template) => void` - Selection handler

**Features**:
- Search functionality
- Category filtering
- Template gallery
- Template details
- Empty state message

---

## Utility Files

### lib/supabase.ts
**Purpose**: Database client setup and types

**Exports**:
- `supabase` - Configured client instance
- `Project` - Type definition
- `Video` - Type definition

---

## Style System (index.css)

### Custom Classes
```css
.btn-primary          /* Blue button */
.btn-secondary        /* Border button */
.input-field          /* Form input */
.card                 /* Card container */
.gradient-text        /* Gradient text effect */
```

### Animations
```css
@keyframes fadeIn     /* Opacity & Y-position */
@keyframes slideIn    /* X-position slide */
@keyframes pulse-subtle /* Pulsing opacity */
@keyframes float      /* Floating animation */
```

---

## Type Definitions

### Project
```typescript
type Project = {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  prompt: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}
```

### Template
```typescript
interface Template {
  id: string;
  name: string;
  description: string;
  category: 'marketing' | 'education' | 'entertainment' | 'social' | 'corporate';
  thumbnail_url?: string;
  is_featured: boolean;
}
```

### Notification
```typescript
interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}
```

---

## Component Relationships

```
App
├── Header
├── NotificationCenter
├── Auth (conditional)
├── Settings (conditional)
├── Analytics (conditional)
├── Templates (conditional)
└── Main Content
    ├── StepIndicator
    ├── Create Page
    │   ├── UploadZone
    │   └── QuickActions
    ├── Processing Page
    │   └── ProcessingSteps
    ├── Preview Page
    │   └── VideoEditor
    ├── Projects Page
    │   ├── ProjectCard (multiple)
    │   └── ShareModal (conditional)
    └── Template Browse
        └── TemplateGallery
```

---

## File Statistics

- **Components**: 12 files
- **Pages**: 4 files
- **Utilities**: 1 file
- **Core**: 2 files (App.tsx, main.tsx)
- **Total Source Files**: 19 files

---

## Import Hierarchy

### External Imports
```
React, Hooks (useState, useEffect)
Lucide React (icons)
Date-fns (date formatting)
Recharts (charts)
```

### Internal Imports
```
App.tsx
├── components/*
├── pages/*
├── lib/supabase
└── Supabase types
```

---

## State Management

### Global State (App.tsx)
- `appStep` - Current page/view
- `isLoggedIn` - Authentication status
- `notifications` - Toast notifications
- `projects` - User's projects
- `isProcessing` - Video processing flag

### Local State
- Component-specific state in each file
- Form state in Auth, Settings, VideoEditor
- Gallery state in TemplateGallery

---

## Performance Considerations

1. **Component Size**: All components <300 lines
2. **Code Splitting**: Pages loaded conditionally
3. **Lazy Loading**: Heavy components on-demand
4. **Memoization**: Ready for optimization
5. **Re-render Optimization**: Minimal prop drilling

---

## Accessibility Features

- Semantic HTML
- ARIA labels on buttons
- Keyboard navigation support
- Color contrast compliance
- Focus indicators
- Screen reader friendly

---

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers

---

## Future Component Ideas

1. **VideoPlayer.tsx** - Custom video player
2. **CollaboratorsList.tsx** - Collaborator management
3. **SearchBar.tsx** - Global search
4. **FilterPanel.tsx** - Advanced filtering
5. **ExportOptions.tsx** - Export format selection
6. **BillingPlans.tsx** - Pricing display
7. **TeamManager.tsx** - Team administration

