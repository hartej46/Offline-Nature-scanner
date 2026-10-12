/**
 * Field Companion — Landing Page API Service
 * Fetches mobile app download metadata and backend health.
 */

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export interface MobileAppInfo {
  app_name: string;
  version: string;
  platform: string;
  filename: string;
  has_binary: boolean;
  file_size_bytes: number;
  file_size_formatted: string;
  download_url: string;
  external_download_url?: string;
  expo_slug: string;
  instructions: string[];
}

export interface BackendStatus {
  app?: string;
  status?: string;
  offline_ready?: boolean;
  species_count?: number;
}

/**
 * Fetch mobile app download information from the server.
 * Gracefully falls back to default release values if backend is unreachable or offline.
 */
export async function getMobileAppInfo(): Promise<MobileAppInfo> {
  try {
    const res = await fetch(`${API_BASE}/download/app/info`, {
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Offline or network error
  }

  // Robust offline fallback values
  return {
    app_name: 'Field Companion Mobile',
    version: '1.0.0',
    platform: 'Android (APK) & Expo Go (iOS/Android)',
    filename: 'FieldCompanion.apk',
    has_binary: true,
    file_size_bytes: 54945382,
    file_size_formatted: '52.4 MB',
    download_url: `${API_BASE}/download/app`,
    expo_slug: 'field-companion',
    instructions: [
      'Download FieldCompanion.apk directly from this server to your Android device',
      'Open the downloaded APK and tap "Install" (allow "Install Unknown Apps" if prompted)',
      'Alternatively, test instantly on iOS or Android using the free Expo Go app',
    ],
  };
}

/**
 * Get direct download link for Android APK
 */
export function getMobileAppDownloadUrl(): string {
  return `${API_BASE}/download/app`;
}

/**
 * Check backend connection status
 */
export async function checkBackendHealth(): Promise<{ online: boolean; speciesCount?: number }> {
  try {
    const res = await fetch(`${API_BASE}/`, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data: BackendStatus = await res.json();
      return { online: true, speciesCount: data.species_count || 731 };
    }
  } catch {
    // Backend offline or unreachable
  }
  return { online: false, speciesCount: 731 };
}
