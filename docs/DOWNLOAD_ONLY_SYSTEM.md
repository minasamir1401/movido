# 📥 MOVIDO - Download Links Only System

## Overview

النظام الآن يعتمد على **روابط التحميل المباشرة فقط** - تم إزالة نظام سيرفرات المشاهدة بالكامل.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Larooza Content Page                       │
│         (video.php?vid=xxx)                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Scraper extracts
                       ▼
┌─────────────────────────────────────────────────────────┐
│           Download Links Page                           │
│         (download.php?vid=xxx)                          │
│                                                          │
│  Contains:                                               │
│  - Quality options (1080p, 720p, 480p, etc.)            │
│  - Direct download URLs                                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Returns to Frontend
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Download Links List                        │
│                                                          │
│  [                                                       │
│    {"quality": "1080p", "url": "https://..."},          │
│    {"quality": "720p", "url": "https://..."},           │
│    {"quality": "480p", "url": "https://..."}            │
│  ]                                                       │
└─────────────────────────────────────────────────────────┘
```

## What Was Removed

### ❌ Deleted Functions (engine.py)

```python
# REMOVED:
- _extract_servers()          # استخراج سيرفرات المشاهدة
- _extract_direct_url()       # استخراج روابط الفيديو المباشرة
- enrich_server()             # تحسين بيانات السيرفرات
```

### ❌ Deleted Files

```
- backend/scraper/extractors/direct_url.py
- DIRECT_URL_EXTRACTION.md
- CURL_CFFI_UPGRADE.md
- VIDEO_GATEWAY_ARCHITECTURE.md
```

### ❌ Removed from API Response

```json
// OLD (with servers):
{
    "id": "xxx",
    "title": "Movie Title",
    "servers": [...]  // ❌ REMOVED
    "download_links": [...]
}

// NEW (download only):
{
    "id": "xxx",
    "title": "Movie Title",
    "download_links": [...]  // ✅ ONLY THIS
}
```

## What Remains

### ✅ Core Functions (engine.py)

```python
# KEPT:
- fetch_home()                # الصفحة الرئيسية
- search()                    # البحث
- fetch_category()            # الأقسام
- fetch_details()             # التفاصيل (بدون سيرفرات)
- _extract_downloads()        # روابط التحميل فقط
- _extract_series_episodes()  # حلقات المسلسلات
```

### ✅ API Response Structure

```json
{
    "id": "base64_encoded_url",
    "title": "Movie/Series Title",
    "description": "Description text",
    "poster": "/proxy/image?url=...",
    "type": "movie" | "series",
    "download_links": [
        {
            "quality": "1080p BluRay",
            "url": "https://download-server.com/file.mp4"
        },
        {
            "quality": "720p WEB-DL",
            "url": "https://download-server.com/file-720.mp4"
        }
    ],
    "episodes": []  // For series only
}
```

## Frontend Integration

### Before (with watch servers):

```typescript
// Watch.tsx - OLD
{
  servers.map((server) => (
    <button onClick={() => playServer(server)}>{server.name}</button>
  ));
}
```

### After (download only):

```typescript
// Download.tsx - NEW
{
  downloadLinks.map((link) => (
    <a href={link.url} download>
      تحميل {link.quality}
    </a>
  ));
}
```

## Benefits

### ✅ 1. Simplicity

- No complex server extraction logic
- No iframe handling
- No CORS issues
- No video player integration

### ✅ 2. Reliability

- Download links are more stable
- No server availability issues
- No video playback errors

### ✅ 3. Performance

- Faster scraping (less HTTP requests)
- Smaller API responses
- Less backend processing

### ✅ 4. User Experience

- Direct downloads
- No buffering issues
- Offline viewing
- Better quality control

## Usage Example

### API Call:

```bash
GET /api/movies/details/aHR0cHM6Ly9sYXJvb3phLmhvbWVzL3ZpZGVvLnBocD92aWQ9WXY3WTFZNEpF
```

### Response:

```json
{
  "id": "aHR0cHM6Ly9sYXJvb3phLmhvbWVzL3ZpZGVvLnBocD92aWQ9WXY3WTFZNEpF",
  "title": "السادة الافاضل",
  "description": "فيلم كوميدي مصري...",
  "poster": "/proxy/image?url=https%3A%2F%2Flarooza.homes%2Fuploads%2Fthumbs%2F...",
  "type": "movie",
  "download_links": [
    {
      "quality": "1080p",
      "url": "https://cdn.example.com/movie-1080p.mp4"
    },
    {
      "quality": "720p",
      "url": "https://cdn.example.com/movie-720p.mp4"
    },
    {
      "quality": "480p",
      "url": "https://cdn.example.com/movie-480p.mp4"
    }
  ],
  "episodes": []
}
```

## Migration Guide

### Frontend Changes Needed:

1. **Remove Watch Page** (optional)
   - Delete `src/pages/Watch.tsx` if not needed
   - Or convert to download page

2. **Update API Calls**
   - Remove references to `servers` field
   - Use only `download_links`

3. **Update UI Components**
   - Remove server selection buttons
   - Add download buttons/links
   - Show quality options

### Example Frontend Code:

```typescript
// Download.tsx
interface DownloadLink {
  quality: string;
  url: string;
}

interface MovieDetails {
  id: string;
  title: string;
  download_links: DownloadLink[];
}

function DownloadPage({ movieId }: { movieId: string }) {
  const [details, setDetails] = useState<MovieDetails | null>(null);

  useEffect(() => {
    fetch(`/api/movies/details/${movieId}`)
      .then((res) => res.json())
      .then(setDetails);
  }, [movieId]);

  if (!details) return <div>Loading...</div>;

  return (
    <div>
      <h1>{details.title}</h1>
      <h2>روابط التحميل:</h2>
      <ul>
        {details.download_links.map((link, i) => (
          <li key={i}>
            <a href={link.url} download className="download-btn">
              📥 تحميل {link.quality}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

## Testing

### Test Download Links Extraction:

```python
# backend/tools/test_downloads.py
import asyncio
from scraper.engine import scraper

async def test():
    # Test movie
    details = await scraper.fetch_details(
        "aHR0cHM6Ly9sYXJvb3phLmhvbWVzL3ZpZGVvLnBocD92aWQ9WXY3WTFZNEpF"
    )

    print(f"Title: {details['title']}")
    print(f"Type: {details['type']}")
    print(f"Download Links: {len(details['download_links'])}")

    for link in details['download_links']:
        print(f"  - {link['quality']}: {link['url'][:50]}...")

asyncio.run(test())
```

### Expected Output:

```
Title: السادة الافاضل
Type: movie
Download Links: 3
  - 1080p: https://cdn.example.com/movie-1080p.mp4...
  - 720p: https://cdn.example.com/movie-720p.mp4...
  - 480p: https://cdn.example.com/movie-480p.mp4...
```

## Summary

### What Changed:

- ❌ Removed: Watch servers extraction
- ❌ Removed: Direct URL extraction
- ❌ Removed: Video player integration
- ✅ Kept: Download links extraction
- ✅ Kept: All other scraping features

### Result:

- **Simpler** codebase
- **Faster** scraping
- **More reliable** data
- **Better** user experience (direct downloads)

---

**Status**: ✅ COMPLETE
**Date**: 2026-01-10
**Version**: 3.0.0 (Download-Only)
