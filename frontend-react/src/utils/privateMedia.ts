import type { Clip } from '../types'

const PRIVATE_CLIP_MEDIA_PATH = /^\/api\/jobs\/[^/?#]+\/clips\/\d+\/media$/

export function getPrivateClipMediaUrl(clip: Pick<Clip, 'file'>): string | undefined {
  return PRIVATE_CLIP_MEDIA_PATH.test(clip.file) ? clip.file : undefined
}

export function getPrivateClipDownloadUrl(
  clip: Pick<Clip, 'file' | 'download_url'>,
): string | undefined {
  const mediaUrl = getPrivateClipMediaUrl(clip)
  if (!mediaUrl) return undefined

  const expectedDownloadUrl = `${mediaUrl}?download=true`
  return clip.download_url === expectedDownloadUrl || !clip.download_url
    ? expectedDownloadUrl
    : undefined
}
