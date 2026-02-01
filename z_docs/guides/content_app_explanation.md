# Content App Architecture & Implementation Guide

This document details the internal workings of the `content` app, focusing on the ingestion pipeline and the frontend "Aside" navigation system. It includes real implementation code and advice for refactoring to **Next.js**.

---

## 1. Backend: Ingestion Pipeline (`models.py`)

The core logic resides in `NotionContent.save()`. It transforms a raw ZIP export from Notion into a web-ready HTML file served via an iframe.

### A. The `save()` Workflow

When an admin uploads a `.zip` file, the following happens:

```python:content/models.py
def save(self, *args, **kwargs):
    # 1. Save first to get an ID (used for folder naming)
    super().save(*args, **kwargs)

    if self.zip_file:
        # Define extraction path: MEDIA_ROOT/html_content/<id>
        unzip_dir = os.path.join(settings.MEDIA_ROOT, 'html_content', str(self.id))
        
        # 2. Extract ZIP safely (hashing long filenames)
        with zipfile.ZipFile(self.zip_file.path, 'r') as zip_ref:
            filename_mapping = self._safe_extract_zip(zip_ref, unzip_dir)

        # 3. Process the extracted HTML file
        for root, _, files in os.walk(unzip_dir):
            for file in files:
                if file.endswith('.html'):
                    html_file_path = os.path.join(root, file)
                    
                    # 4. Rewrite relative image paths to absolute server URLs
                    self._rewrite_image_paths(html_file_path, filename_mapping)
                    
                    # 5. Inject scripts/styles (Scrollbar hiding, PostMessage)
                    self._inject_custom_scripts(html_file_path)
                    
                    # 6. Save relative path to DB
                    self.html_path = os.path.relpath(html_file_path, settings.MEDIA_ROOT)
                    break
```

### B. Path Rewriting & Cleaning

Notion exports images with relative paths (e.g., `<img src="My%20Image.png">`). We must convert these to absolute paths so they load inside the iframe.

```python:content/models.py
def _rewrite_image_paths(self, html_file_path, filename_mapping=None):
    with open(html_file_path, 'r+', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        for tag in soup.find_all(['img', 'a']):
            # ... (logic to skip external links) ...
            
            # Convert "My Image.png" -> "/media/html_content/123/hash123.jpg"
            # uses filename_mapping generated during extraction
            final_url = ... 
            tag[attr] = final_url

        # Save changes
        f.seek(0)
        f.write(str(soup))
```

### C. Script Injection (The "Glue")

To make the iframe behave like a native part of the app, we inject JS into the raw HTML.

```python:content/models.py
# Injected into the <head> of the Notion HTML
style = """
<style>
    /* Hide scrollbars inside iframe */
    body::-webkit-scrollbar { display: none; }
    html { scrollbar-width: none; }
</style>
"""

# Injected script to communicate with parent window
scroll_script = """
<script>
    // Detect when user scrolls to bottom of iframe content
    window.addEventListener('scroll', function() {
        if (document.documentElement.scrollHeight - window.innerHeight - 200 <= window.scrollY) {
            window.parent.postMessage('iframeScrollEnd', '*');
        }
    });

    // Handle image clicks (send to parent for modal)
    document.addEventListener('click', function(e) {
        if (e.target.tagName === 'IMG') {
            e.preventDefault();
            window.parent.postMessage({
                type: 'openImageModal',
                imageUrl: e.target.src
            }, '*');
        }
    });
</script>
"""
```

---

## 2. Frontend: The "Aside" System (SPA-like Behavior)

The app uses a custom JavaScript router in `base.js` to handle the right sidebar ("Aside") without refreshing the page or changing the URL.

### A. The "Aside" Container

The sidebar is a static `div` updated via AJAX.

```html:templates/base.html (Conceptual)
<div class="asideOn"> <!-- Main Sidebar Container -->
    <div class="aside-view">
        <!-- Dynamic Content Injected Here -->
    </div>
</div>
```

### B. Dynamic View Loading (`base.js`)

The function `loadAsideView` is the core router.

```javascript:static/js/base.js
// Config defines how to load each view
const ASIDE_VIEWS_CONFIG = {
    columnLists: {
        partialUrl: '/content/partial/column-lists/', 
        js: ['/static/js/columnLists.js'] // Dynamic JS loading
    },
    columnDetails: {
        partialUrlTemplate: '/content/partial/column-details/{id}/',
        js: ['/static/js/columnDetails.js'],
        renderCallback: 'setupColumnDetailsEvents'
    }
};

async function loadAsideView(viewName, id = null) {
    // 1. Fetch HTML fragment
    const response = await fetch(url);
    const html = await response.text();

    // 2. Inject HTML
    container.innerHTML = html;

    // 3. Load associated CSS/JS
    await loadResources(viewName);

    // 4. Save State (SessionStorage) - preserves state on refresh
    saveAsideState({ viewName, id });
}
```

### C. The Iframe Resizer (`columnDetails.js`)

To make the iframe look seamless (no internal scrollbar), the parent page resizes the iframe to match its content height.

```javascript:static/js/columnDetails.js
function adjustIframeHeight() {
    const iframe = document.querySelector('.content-iframe');
    // Access iframe content (Same Origin Policy applies!)
    const iframeDoc = iframe.contentDocument; 
    
    // Set height to content height
    iframe.style.height = iframeDoc.documentElement.scrollHeight + 'px';
}
```

---

## 3. Refactoring to Next.js (Recommendation)

Since you are moving to **Next.js**, you can simplify this architecture significantly while maintaining the "no URL change" requirement if desired.

### A. Rendering Strategy: Stick with Iframes

**Why?** Notion HTML exports contain full `<html>`, `<head>`, and `<body>` tags with global styles (e.g., `body { margin: 0; font-family: sans-serif; }`).
*   **Bad:** Injecting this via `dangerouslySetInnerHTML` will break your Next.js app's global CSS.
*   **Good:** An `<iframe>` provides perfect CSS isolation.

### B. Navigation & State (The "No URL Change" Requirement)

In Next.js, you have two options to manage the sidebar state:

#### Option 1: URL-Driven State (Recommended for Next.js)
Use **Parallel Routes** and **Interception Routes**.
*   URL: `/feed?articleId=123` or `/feed/123`
*   The sidebar reads the URL search param or segment.
*   **Pros:** Deep linking works (users can share the link). Back button works naturally.
*   **Cons:** URL changes (violates your specific constraint, but is "Next.js idiomatic").

#### Option 2: Client-Side State (Replicating Current Behavior)
Use React State (`useState`, `useContext`) to toggle the sidebar.

```tsx
// components/Layout.tsx
'use client';

export default function Layout() {
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);

  return (
    <div className="flex">
      <MainFeed onSelect={setSelectedArticleId} />
      
      {/* The Aside Sidebar */}
      <aside className={`transition-transform ${selectedArticleId ? 'translate-x-0' : 'translate-x-full'}`}>
        {selectedArticleId && <ArticleViewer id={selectedArticleId} />}
      </aside>
    </div>
  );
}
```

### C. Serving the Content

Instead of Django Views returning HTML, serve the processed HTML files statically.

1.  **Storage**: Store the extracted HTML folders in an S3 bucket or a static file server (e.g., Nginx, Vercel Blob).
2.  **Viewer Component**:

```tsx
// components/ArticleViewer.tsx
'use client';

export default function ArticleViewer({ id }: { id: string }) {
  // Point to your static file storage
  const src = `https://your-storage.com/html_content/${id}/index.html`;

  return (
    <div className="w-full h-full overflow-y-auto">
      <iframe 
        src={src} 
        className="w-full border-0"
        onLoad={(e) => {
           // Auto-resize logic here if needed
           // OR just let the iframe scroll internally (simpler for mobile)
        }}
      />
    </div>
  );
}
```

### D. Implementation Details for Next.js

1.  **Image Paths**: The current Django logic rewrites paths to `/media/...`. For Next.js, ensure your `rewrite_image_paths` logic points to your new static asset domain (e.g., `https://cdn.myapp.com/content/${id}/...`).
2.  **PostMessage**: Keep the `postMessage` logic! React/Next.js handles this elegantly.

```tsx
// Inside ArticleViewer.tsx
useEffect(() => {
  const handleMessage = (event: MessageEvent) => {
    if (event.data.type === 'openImageModal') {
      // Open your React Modal
      setModalImage(event.data.imageUrl);
    }
  };

  window.addEventListener('message', handleMessage);
  return () => window.removeEventListener('message', handleMessage);
}, []);
```

### E. API Routes
Migrate `api_views.py` to Next.js **Route Handlers** (`app/api/...`).
*   `ColumnListAPIView` -> `GET /api/columns` (Query your DB - Postgres/Supabase/Prisma)
*   `RecordContentViewAPIView` -> `POST /api/analytics/view`

---

## Summary Checklist for Refactoring

1.  [ ] **Backend**: Port the `Zip Extraction` & `HTML Processing` logic (Python or Node.js).
    *   *Tip*: Python is great for this (BeautifulSoup). You might want to keep a small Python microservice or serverless function just for ingestion.
2.  [ ] **Storage**: Decide where to host the static HTML files (S3, Vercel Blob, or public folder).
3.  [ ] **Frontend**: Build a `SidebarContext` in Next.js to manage the open/close state without URL routing (if strict requirement).
4.  [ ] **Component**: Create a robust `IframeViewer` component that handles `postMessage` events for interactivity.
