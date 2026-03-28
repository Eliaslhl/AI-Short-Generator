# Twitch Support Implementation

## Overview

This document outlines the implementation of Twitch support alongside the existing YouTube functionality in the AI Shorts Generator application.

## Architecture

### Frontend Structure

#### Source Selector (`/generate`)
- **File**: `SourceSelectorPage.tsx`
- **Purpose**: Allows users to choose between YouTube and Twitch as video sources
- **Navigation**:
  - YouTube → `/generate/youtube`
  - Twitch → `/generate/twitch`

#### Shared Components
- **GeneratorForm.tsx**: Reusable form component for both YouTube and Twitch
  - URL input (adapts placeholder/example based on source)
  - Max clips slider (respects plan limits)
  - Language selection
  - Subtitle style picker
  - Include subtitles toggle
  - Handles form validation and API calls

#### Source-Specific Pages
- **YouTubeGeneratorPage.tsx**: YouTube video generation interface
- **TwitchGeneratorPage.tsx**: Twitch video generation interface

Both pages are visually identical but adapt:
- Form placeholders/examples for their respective platforms
- API call parameters
- Backend handling

### Backend Structure

#### New Services

**twitch_service.py** (`backend/services/twitch_service.py`)
- Handles Twitch video downloads using yt-dlp
- Supports:
  - Direct clips: `https://www.twitch.tv/{channel}/clip/{clip_name}`
  - VODs: `https://www.twitch.tv/videos/{vod_id}`
- Validates URL format before download
- Extracts video metadata (title, duration)
- Returns `(video_path, title)` tuple for pipeline processing

#### API Integration

Current endpoint handles both YouTube and Twitch:
- `POST /api/generate`
  - Accepts `youtube_url` parameter
  - Can be extended to detect source from URL or add source parameter

#### Pipeline Processing

The existing pipeline (`run_pipeline()`) in `routes.py`:
1. Downloads video (now can use YouTube or Twitch service)
2. Transcribes audio
3. Analyzes segments for viral content
4. Renders short clips
5. Returns generated clips

No changes needed to steps 2-5 as they work with any video source.

## API Specifications

### Frontend API Client

```typescript
generatorApi.generate(
  youtubeUrl: string,
  maxClips: number = 3,
  language: string = '',
  subtitleStyle: string = 'default',
  includeSubtitles: boolean = true
)
```

**Updated in** `frontend-react/src/api/index.ts`
- Added `includeSubtitles` parameter
- Sends to backend as `include_subtitles`

### Backend Request Model

```python
class GenerateRequest(BaseModel):
    youtube_url: str  # Currently named "youtube_url"
    max_clips: int = 3
    language: str = ""
    subtitle_style: str = "default"
    transcription_mode: str = ""
```

**Recommendation for Future**: Consider renaming to `video_url` and adding a `source` field for clarity:
```python
class GenerateRequest(BaseModel):
    video_url: str
    source: Literal['youtube', 'twitch'] = 'youtube'
    max_clips: int = 3
    # ... rest of fields
```

## Component Reusability

### Shared `GeneratorForm` Component

```typescript
interface GeneratorFormProps {
  source: 'youtube' | 'twitch'
  placeholderUrl: string
  exampleUrl: string
  onGenerate: (request: GenerateFormRequest) => Promise<void>
  isLoading?: boolean
  error?: string
  maxClips?: number
  currentPlan?: string
}
```

This component handles:
- ✅ URL input validation (delegated to backend for actual validation)
- ✅ Clip count selection
- ✅ Language selection
- ✅ Subtitle styling
- ✅ Subtitle toggle
- ✅ Form submission
- ✅ Error display
- ✅ Plan-based feature limitations

### Usage in Both Pages

```typescript
<GeneratorForm
  source="youtube"  // or "twitch"
  placeholderUrl="https://www.youtube.com/watch?v=..."
  exampleUrl={EXAMPLE_URL}
  onGenerate={handleGenerate}
  isLoading={isLoading}
  error={error}
  maxClips={maxAllowed}
  currentPlan={user?.plan || 'free'}
/>
```

## User Experience

### Flow

1. User logs in/navigates to `/generate`
2. **Source Selector** displays two options:
   - YouTube (with description, features)
   - Twitch (with description, features)
3. User clicks desired source
4. Redirects to source-specific page (`/generate/youtube` or `/generate/twitch`)
5. User inputs video URL
6. Fills out generation options (clips, language, subtitle style)
7. Clicks "Generate Shorts"
8. Progress shown in real-time
9. Generated clips displayed in grid
10. User can preview/download clips

### Plan Limitations

Same across both sources:
- **Free**: 3 clips/month
- **Standard**: 5 clips/month
- **Pro**: 10 clips/month
- **Pro+**: 20 clips/month

## File Structure

```
frontend-react/
├── src/
│   ├── pages/
│   │   ├── SourceSelectorPage.tsx      [NEW]
│   │   ├── YouTubeGeneratorPage.tsx    [NEW - refactored from GeneratorPage]
│   │   ├── TwitchGeneratorPage.tsx     [NEW]
│   │   └── GeneratorPage.tsx           [KEPT for backward compatibility]
│   ├── components/
│   │   └── GeneratorForm.tsx           [NEW - shared form logic]
│   └── api/
│       └── index.ts                    [UPDATED - added includeSubtitles]

backend/
├── services/
│   ├── youtube_service.py              [EXISTING]
│   └── twitch_service.py               [NEW]
└── api/
    └── routes.py                       [UPDATED - handles both sources]
```

## Future Enhancements

1. **Rename API Field**: Change `youtube_url` → `video_url` + add `source` field
2. **Source Detection**: Auto-detect source from URL (YouTube vs Twitch patterns)
3. **Additional Platforms**: 
   - TikTok videos
   - Instagram Reels
   - Twitter/X videos
4. **Platform-Specific Optimizations**:
   - Twitch: Gaming moment detection
   - YouTube: Music/Copyright detection
5. **Batch Processing**: Generate from multiple URLs at once
6. **Webhook Notifications**: Notify when generation completes

## Testing Checklist

- [ ] YouTube video download and processing
- [ ] Twitch clip download (direct clip URL)
- [ ] Twitch VOD download (VOD video URL)
- [ ] Subtitle toggle works for both sources
- [ ] Language selection works for both sources
- [ ] Plan limits enforced correctly
- [ ] Progress bar updates for both sources
- [ ] Clips download correctly
- [ ] Mobile responsive design on source selector
- [ ] Error handling for invalid URLs

## Notes

- Both YouTube and Twitch services use `yt-dlp` for video downloads
- The rest of the processing pipeline (transcription, analysis, rendering) is agnostic to source
- UI is intentionally identical between sources to ensure consistency
- The source selector page uses a card-based design for clear visual distinction
- Authentication and subscription checks remain the same
