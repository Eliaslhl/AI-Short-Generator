import { describe, expect, it } from 'vitest'
import {
  getPrivateClipDownloadUrl,
  getPrivateClipMediaUrl,
} from './privateMedia'

describe('private clip media URLs', () => {
  it('uses the private API media URL directly for previews', () => {
    expect(getPrivateClipMediaUrl({ file: '/api/jobs/job-1/clips/0/media' })).toBe(
      '/api/jobs/job-1/clips/0/media',
    )
  })

  it('uses the API download URL for each clip index', () => {
    expect(
      getPrivateClipDownloadUrl({
        file: '/api/jobs/job-1/clips/2/media',
        download_url: '/api/jobs/job-1/clips/2/media?download=true',
      }),
    ).toBe('/api/jobs/job-1/clips/2/media?download=true')
  })

  it('falls back only to a private API URL when download_url is absent', () => {
    expect(getPrivateClipDownloadUrl({ file: '/api/jobs/job-1/clips/1/media' })).toBe(
      '/api/jobs/job-1/clips/1/media?download=true',
    )
  })

  it('does not create a link from public or malformed clip references', () => {
    expect(getPrivateClipMediaUrl({ file: '/clips/job-1/clip.mp4' })).toBeUndefined()
    expect(getPrivateClipDownloadUrl({ file: '/clips/job-1/clip.mp4' })).toBeUndefined()
    expect(
      getPrivateClipDownloadUrl({
        file: '/api/jobs/job-1/clips/0/media',
        download_url: '/clips/job-1/clip.mp4',
      }),
    ).toBeUndefined()
  })
})
