/**
 * Mobile API Service Layer
 * Connects to FastAPI backend running on local laptop / device.
 */

import Constants from 'expo-constants';

function resolveDefaultApiBase(): string {
  // Try extracting host IP from Expo debugger host
  const hostUri = Constants.expoConfig?.hostUri || (Constants as any).manifest?.debuggerHost;
  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:8000`;
    }
  }

  // Fallback to active LAN IP for physical phone over WiFi
  return 'http://10.254.205.106:8000';
}

let API_BASE = resolveDefaultApiBase();

export function setApiBaseUrl(url: string) {
  API_BASE = url;
}

export function getApiBaseUrl(): string {
  return API_BASE;
}

export interface IdentifyResponse {
  response: string;
  spoken_response?: string;
  tts_url?: string;
  mode?: 'bird_audio' | 'voice_query';
  transcription?: string;
  tools_used: string[];
  iterations: number;
  tool_results: Array<{
    tool: string;
    args: Record<string, unknown>;
    result: Record<string, unknown>;
  }>;
  birdnet_detections?: Array<{
    common_name: string;
    sci_name: string;
    confidence: number;
    source?: string;
  }>;
  image_path?: string;
  audio_path?: string;
  tts_path?: string;
}

export interface JournalEntry {
  id: number;
  ts: string;
  common_name?: string;
  sci_name?: string;
  confidence?: number;
  source?: string;
  notes?: string;
  query_text?: string;
  response?: string;
  lat?: number;
  lon?: number;
}

export interface StatusResponse {
  app: string;
  model: { base_url: string; model: string };
  species_count: number;
  offline_ready: boolean;
  privacy: string;
}

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API error (${res.status}): ${errorText}`);
  }

  return res.json();
}

export async function identifyText(message: string, lat?: number, lon?: number): Promise<IdentifyResponse> {
  return fetchJson<IdentifyResponse>('/identify/text', {
    method: 'POST',
    body: JSON.stringify({ message, lat, lon }),
  });
}

import * as FileSystem from 'expo-file-system/legacy';

export async function identifyPhoto(
  photoInput: { uri?: string; base64?: string },
  message: string = 'What species is in this photo?'
): Promise<IdentifyResponse> {
  let base64Data = photoInput.base64;

  if (!base64Data && photoInput.uri) {
    try {
      base64Data = await FileSystem.readAsStringAsync(photoInput.uri, {
        encoding: FileSystem.EncodingType.Base64,
      });
    } catch (e) {
      console.log('Direct base64 read skipped, trying multipart upload:', e);
    }
  }

  if (base64Data) {
    return fetchJson('/identify/photo/base64', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: base64Data,
        message,
      }),
    });
  }

  if (photoInput.uri) {
    const uploadResult = await FileSystem.uploadAsync(`${API_BASE}/identify/photo`, photoInput.uri, {
      httpMethod: 'POST',
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
      fieldName: 'file',
      parameters: { message },
    });

    if (uploadResult.status < 200 || uploadResult.status >= 300) {
      throw new Error(`Photo upload failed (${uploadResult.status}): ${uploadResult.body}`);
    }

    return JSON.parse(uploadResult.body);
  }

  throw new Error('No photo URI or image data provided');
}

export async function identifyPhotoUri(
  fileUri: string,
  fileName: string = 'photo.jpg',
  message: string = 'What species is in this photo?'
): Promise<IdentifyResponse> {
  return identifyPhoto({ uri: fileUri }, message);
}


export async function identifyAudioUri(
  fileUri: string,
  fileName: string = 'audio.wav',
  lat?: number,
  lon?: number
): Promise<IdentifyResponse> {
  const parameters: Record<string, string> = {};
  if (lat !== undefined) parameters.lat = String(lat);
  if (lon !== undefined) parameters.lon = String(lon);

  const uploadResult = await FileSystem.uploadAsync(`${API_BASE}/identify/audio`, fileUri, {
    httpMethod: 'POST',
    uploadType: FileSystem.FileSystemUploadType.MULTIPART,
    fieldName: 'file',
    parameters,
  });

  if (uploadResult.status < 200 || uploadResult.status >= 300) {
    throw new Error(`Audio upload failed (${uploadResult.status}): ${uploadResult.body}`);
  }

  return JSON.parse(uploadResult.body);
}


export async function getJournal(query?: string): Promise<{ count: number; observations: JournalEntry[] }> {
  const q = query ? `?query=${encodeURIComponent(query)}` : '';
  return fetchJson(`/journal${q}`);
}

export async function addJournalEntry(entry: {
  common_name?: string;
  sci_name?: string;
  confidence?: number;
  source?: string;
  query_text?: string;
  response?: string;
  notes?: string;
  lat?: number;
  lon?: number;
  audio_path?: string;
  image_path?: string;
}): Promise<{ id: number; status: string }> {
  return fetchJson('/journal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  });
}

export async function getStatus(): Promise<StatusResponse> {
  return fetchJson('/status');
}

export interface ModelOption {
  id: string;
  name: string;
  subtitle: string;
  size_formatted: string;
  size_bytes: number;
  min_ram_gb: number;
  recommended_ram_gb: number;
  quantization: string;
  speed: string;
  description: string;
  is_installed: boolean;
  is_active: boolean;
}

export interface AvailableModelsResponse {
  models: ModelOption[];
  active_model_id: string | null;
  installed_count: number;
}

export async function getAvailableModels(deviceRamGb?: number): Promise<AvailableModelsResponse> {
  const q = deviceRamGb ? `?device_ram_gb=${deviceRamGb}` : '';
  return fetchJson(`/model/available${q}`);
}

export async function installModel(modelId: string): Promise<{ status: string; model_id: string; message: string }> {
  return fetchJson('/model/install', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export async function uninstallModel(modelId: string): Promise<{ status: string; model_id: string }> {
  return fetchJson('/model/uninstall', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export interface ModelPackStatus {
  model_id: string | null;
  name: string;
  version: string;
  status: string;
  pre_installed: boolean;
  is_installed: boolean;
  installed_models: string[];
  size_formatted: string;
}

export async function getModelPackStatus(): Promise<ModelPackStatus> {
  return fetchJson('/model/pack/status');
}


